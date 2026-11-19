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
