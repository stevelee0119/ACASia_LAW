# -*- coding: utf-8 -*-
"""시간 측정 단언의 공용 도구 (TK-214, 2026-11-19 사용자 결정 1안).

왜 필요한가
-----------
공용 실행기에서 한 번 재고 절대 한계와 비교하면 **코드의 성능이 아니라 그때의 부하를 잰다.**
2026-11-19 `test_tk76_incons_c_eval.py::test_linear_time_on_20k_chars`가 한계 0.5초에 0.751초로
실패했는데, 같은 커밋의 다른 실행에서는 통과했고 평가 측 7회 측정의 중앙값은 0.041초(한계의
1/10 아래)였다. 평상시 여유가 10배를 넘어도 단발 측정은 깨진다.

부하는 측정을 **늦추기만 한다**(빠르게 만들지 않는다). 그래서 N회 중 **최솟값**이 참값에 가장
가깝고, 한 번의 부하로 깨지지 않는다. 한계와 엄격도는 그대로 두고 통계만 바꾼다.

선형성·증가율을 보는 시험은 한 점으로 기울기를 구할 수 없으므로 길이 묶음을 교차 측정한다
(TK-142가 `tests/test_pii_redos_linear.py`에서 쓴 방법을 여기로 올렸다).

쓰는 법
-------
    from tests.perf_scaling import best_of, fastest_of, growth_exponent, timings_interleaved

    elapsed = best_of(lambda: detect(text))        # 한 점: N회 중 최솟값
    assert elapsed < 0.1

    elapsed, found = fastest_of(lambda: PATTERN.search(evil))   # 결과도 쓸 때
    assert found is None and elapsed < 0.1

    timings = timings_interleaved(detect, [" " * n for n in SIZES])
    assert growth_exponent(SIZES, timings) < 1.5   # 여러 점: log-log 기울기
"""
from __future__ import annotations

import gc
import math
from time import perf_counter
from typing import Callable, Sequence

# 기본 반복 수. 늘리면 잡음에 더 강해지지만 시험이 그만큼 길어진다.
DEFAULT_REPEATS = 5


def fastest_of(work: Callable[[], object], repeats: int = DEFAULT_REPEATS):
    """`work`를 repeats회 돌려 **가장 짧은 소요 시간과 마지막 결과**를 돌려준다.

    부하는 측정을 늦추기만 하므로 최솟값이 참값에 가깝다. GC는 잠시 끈다 —
    수집이 한 번에 몰리면 그 측정만 길어진다. 예외가 나도 GC를 되살린다.

    결과를 함께 돌려주는 까닭: 재던 구간의 반환값을 뒤의 단언이 쓰는 자리가 많다.
    `tests/test_tk56_structured_name_boundary.py`의 `_fastest_of`(TK-147)와 같은 꼴이다.

    주의: **반복이 결과를 빠르게 만드는 작업에는 쓰지 않는다**(측정 구간 안에 캐시 적재가
    들어 있으면 2회차부터 캐시 적중 시간을 재게 된다). 캐시가 있으면 적재를 측정 구간
    밖에서 먼저 하고, 재는 것은 적중 경로만으로 둔다.
    """
    if repeats < 1:
        raise ValueError("repeats는 1 이상이어야 한다")
    best, result = float("inf"), None
    gc.collect()
    gc.disable()
    try:
        for _ in range(repeats):
            started = perf_counter()
            result = work()
            best = min(best, perf_counter() - started)
    finally:
        gc.enable()
    return best, result


def best_of(work: Callable[[], object], repeats: int = DEFAULT_REPEATS) -> float:
    """소요 시간만 필요할 때. `fastest_of`의 첫 값이다."""
    return fastest_of(work, repeats)[0]


def timings_interleaved(
    func: Callable[[object], object], inputs: Sequence, rounds: int = DEFAULT_REPEATS
) -> list:
    """입력별 최솟값. 입력을 번갈아 재서(교차 측정) 부하가 한 입력에만 몰리지 않게 한다."""
    best = [float("inf")] * len(inputs)
    gc.collect()
    gc.disable()
    try:
        for _ in range(rounds):
            for i, item in enumerate(inputs):
                started = perf_counter()
                func(item)
                best[i] = min(best[i], perf_counter() - started)
    finally:
        gc.enable()
    return best


def growth_exponent(sizes: Sequence[float], timings: Sequence[float]) -> float:
    """log(시간)-log(크기) 최소자승 기울기. 선형이면 약 1, 제곱이면 약 2.

    두 점 비율로 보면 한 점의 잡음이 결과를 크게 흔든다. 네 점 이상의 기울기로 본다.
    """
    if len(sizes) != len(timings) or len(sizes) < 2:
        raise ValueError("크기와 시간이 같은 길이로 2개 이상 있어야 한다")
    xs = [math.log(n) for n in sizes]
    ys = [math.log(max(t, 1e-6)) for t in timings]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        raise ValueError("크기가 모두 같아 기울기를 구할 수 없다")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


# ---------------------------------------------------------------------------
# 자가 보정 상대 한계 (TK-214 2차, 2026-11-19 사용자 결정 1안)
#
# 왜 최솟값만으로는 부족한가: 평가 측 부하 검증(4코어에 바쁜 루프 8개)에서 N회 최솟값으로
# 바꾼 뒤에도 0.1초급 단언이 깨졌다. **지속적 포화 부하는 모든 회차를 똑같이 늦추므로
# 최솟값도 함께 늦어진다.** 최솟값은 일시적 스파이크에만 듣는다.
#
# 균일한 감속에 면역인 것은 상대적 측도다. 그래서 같은 실행 안에서 **기준 작업**을 함께 재어
# 그 기계·그 순간이 기준보다 몇 배 느린지 구하고, 한계를 그만큼 늘려 비교한다. 기계 속도와
# 부하가 약분되므로 엄격도는 유지된다 — ReDoS 폭주는 100~1000배이고 배수는 상한이 50이다.
#
# **기준 작업은 평균으로 잰다. 최솟값으로 재면 안 된다.** 평가 측 실측(2026-11-19):
#
#     기준 20,000회, 4코어에 바쁜 루프 8개
#       최솟값 0.000825초 → 배수 0.99  (부하를 전혀 감지하지 못한다)
#       평균   0.002479초 → 배수 2.96  (실제 감속과 맞는다)
#
# 짧은 작업의 최솟값은 빈 타임슬라이스에 끼어들어 부하와 무관하게 빠르다. 기계의 '그 순간
# 처리량'은 평균이다. 첫 구현이 최솟값을 써서 배수가 1.00으로 나왔고, 부하 검증에서
# 0.1481초 > 보정 한계 0.1000초(감속 배수 1.00)로 실패해 그것을 잡았다.
#
# 기준 작업 크기도 재서 골랐다(부하 없음 / 포화 부하의 평균, 평균을 5번 재어 중앙값):
#
#        20,000회  0.000912 / 0.003135  배수 3.44  흔들림 1.11배  비용 0.006초
#       200,000회  0.009953 / 0.022747  배수 2.29  흔들림 1.07배  비용 0.050초
#     1,000,000회  0.049898 / 0.134967  배수 2.70  흔들림 1.05배  비용 0.150초
#
# 200,000회를 쓴다 — 흔들림이 작고 비용이 낮다. 비용은 과정 단위 캐시로 한 번만 든다.
#
# 중요: 이 보정은 **대상 작업을 반복하지 않는다.** 기준 작업만 반복한다. 그래서 상태가 쌓이거나
# 동시성을 함께 재는 자리(반복하면 단언이 깨지는 자리)에도 쓸 수 있다.
# ---------------------------------------------------------------------------

# 기준 작업: 순수 파이썬 정수 연산. 캐시·IO·난수에 좌우되지 않고 CPU만 쓴다.
CALIBRATION_ITERATIONS = 200_000
CALIBRATION_REPEATS = 5

# 부하 없는 평가 환경(이 저장소의 컨테이너, CPython 3.13, 2026-11-19)에서 5회 평균을 5번 재어
# 중앙값 0.009714초였다(준비 회차를 버린 뒤 5회 평균을 5번, 0.009546~0.009751). 이 값은 '기준 기계의 속도'를 뜻할 뿐이고, 이보다 느린
# 기계·부하에서는 배수가 1보다 커져 한계가 늘어난다. 더 빠른 기계에서 조여지지는 않는다.
CALIBRATION_BASELINE_SECONDS = 0.009714

# 배수 상한. 환경이 병적으로 느려도 단언이 무력해지지 않게 막는다.
MAX_SLOWDOWN = 50.0

# 과정 단위 캐시. 이 시간이 지나면 다시 잰다(실행 중 부하가 변한다).
CALIBRATION_CACHE_SECONDS = 20.0
_calibration_cache = {"at": None, "factor": None}


def _calibration_work() -> int:
    total = 0
    for i in range(CALIBRATION_ITERATIONS):
        total += i * i % 7
    return total


def mean_of(work: Callable[[], object], repeats: int = CALIBRATION_REPEATS) -> float:
    """`work`를 repeats회 돌려 **평균** 소요 시간을 돌려준다.

    보정에는 평균을 쓴다(최솟값이 아니다). 위 주석의 실측 근거를 보라.
    """
    if repeats < 1:
        raise ValueError("repeats는 1 이상이어야 한다")
    total = 0.0
    gc.collect()
    gc.disable()
    try:
        work()          # 준비 회차는 버린다 — 첫 호출의 적재·분기 예측 비용이 평균을 부풀린다
        for _ in range(repeats):
            started = perf_counter()
            work()
            total += perf_counter() - started
    finally:
        gc.enable()
    return total / repeats


def reset_calibration_cache() -> None:
    """캐시를 비운다. 시험에서 쓴다."""
    _calibration_cache["at"] = None
    _calibration_cache["factor"] = None


def slowdown_factor(repeats: int = CALIBRATION_REPEATS, refresh: bool = False) -> float:
    """이 기계·이 순간이 기준보다 몇 배 느린지. 1.0 이상 MAX_SLOWDOWN 이하.

    같은 과정에서 CALIBRATION_CACHE_SECONDS 안에 다시 물으면 잰 값을 그대로 쓴다
    (자리마다 다시 재면 시험 전체가 그만큼 길어진다).
    """
    now = perf_counter()
    cached_at, cached = _calibration_cache["at"], _calibration_cache["factor"]
    if (not refresh and cached is not None and cached_at is not None
            and now - cached_at < CALIBRATION_CACHE_SECONDS):
        return cached
    measured = mean_of(_calibration_work, repeats)
    factor = min(max(measured / CALIBRATION_BASELINE_SECONDS, 1.0), MAX_SLOWDOWN)
    _calibration_cache["at"] = perf_counter()
    _calibration_cache["factor"] = factor
    return factor


def assert_within(
    elapsed: float,
    limit: float,
    detail: str = "",
    repeats: int = CALIBRATION_REPEATS,
) -> float:
    """`elapsed`가 **보정된** 한계 안인지 단언하고 쓰인 배수를 돌려준다.

    `limit`은 기준 기계에서의 한계다. 실제 비교는 `limit × 감속 배수`로 한다.
    실패 메시지에 원래 한계·배수·보정된 한계를 함께 적어 사람이 원인을 가릴 수 있게 한다.
    """
    factor = slowdown_factor(repeats)
    allowed = limit * factor
    assert elapsed < allowed, (
        f"{detail + ' ' if detail else ''}"
        f"{elapsed:.4f}초 > 보정 한계 {allowed:.4f}초 "
        f"(기준 한계 {limit}초 × 감속 배수 {factor:.2f})"
    )
    return factor
