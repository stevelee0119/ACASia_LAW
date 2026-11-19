# -*- coding: utf-8 -*-
"""TK-214 — 시간 측정 도구 자체의 시험 (측정 방법을 믿을 수 있는지).

수용 기준 3('측정 방법 자체의 시험이 있다')을 충족한다. 도구가 틀리면 그것을 쓰는 모든
성능 시험이 함께 틀리므로 여기서 먼저 잰다.
"""
from __future__ import annotations

import math
import time

import pytest

from tests.perf_scaling import (
    DEFAULT_REPEATS,
    best_of,
    growth_exponent,
    timings_interleaved,
)

MAX_EXPONENT = 1.5


# --- best_of: N회 중 최솟값 --------------------------------------------------

def test_best_of_takes_the_minimum_not_the_last_or_mean():
    """한 번 느린 실행이 섞여도 최솟값이 나와야 한다 — 부하에 깨지지 않는 근거."""
    delays = [0.05, 0.001, 0.05, 0.05, 0.05]
    seq = iter(delays)

    def work():
        time.sleep(next(seq))

    elapsed = best_of(work, repeats=len(delays))
    assert elapsed < 0.02, elapsed          # 최솟값(0.001)에 가깝다
    assert elapsed < sum(delays) / len(delays)   # 평균(0.04)보다 작다


def test_best_of_runs_exactly_repeats_times():
    calls = []
    best_of(lambda: calls.append(1), repeats=4)
    assert len(calls) == 4


def test_best_of_default_repeats_is_more_than_one():
    """기본값이 1이면 단발 측정으로 되돌아간다."""
    assert DEFAULT_REPEATS > 1
    calls = []
    best_of(lambda: calls.append(1))
    assert len(calls) == DEFAULT_REPEATS


def test_best_of_rejects_zero_repeats():
    with pytest.raises(ValueError):
        best_of(lambda: None, repeats=0)


def test_best_of_measures_real_work_not_zero():
    elapsed = best_of(lambda: time.sleep(0.01), repeats=2)
    assert 0.005 < elapsed < 0.5, elapsed


def test_best_of_restores_gc_even_on_failure():
    import gc

    was_enabled = gc.isenabled()

    def boom():
        raise RuntimeError("일부러 실패")

    with pytest.raises(RuntimeError):
        best_of(boom, repeats=1)
    assert gc.isenabled() == was_enabled


# --- growth_exponent: 기울기 -------------------------------------------------

def test_growth_exponent_of_linear_data_is_about_one():
    sizes = (1000, 2000, 4000, 8000)
    timings = [n * 1e-6 for n in sizes]
    assert abs(growth_exponent(sizes, timings) - 1.0) < 0.05


def test_growth_exponent_of_quadratic_data_is_about_two():
    sizes = (1000, 2000, 4000, 8000)
    timings = [(n ** 2) * 1e-12 for n in sizes]
    assert abs(growth_exponent(sizes, timings) - 2.0) < 0.05


def test_growth_exponent_of_constant_data_is_about_zero():
    sizes = (1000, 2000, 4000, 8000)
    assert abs(growth_exponent(sizes, [0.01] * 4)) < 0.05


def test_growth_exponent_needs_at_least_two_points():
    with pytest.raises(ValueError):
        growth_exponent((1000,), [0.01])
    with pytest.raises(ValueError):
        growth_exponent((1000, 2000), [0.01])


def test_growth_exponent_rejects_identical_sizes():
    with pytest.raises(ValueError):
        growth_exponent((1000, 1000, 1000), [0.01, 0.02, 0.03])


def test_growth_exponent_survives_one_noisy_point():
    """한 점이 10배 튀어도 기울기가 한계를 넘지 않는다 — 두 점 비율과 다른 점."""
    sizes = (1000, 2000, 4000, 8000)
    clean = [n * 1e-6 for n in sizes]
    noisy = list(clean)
    noisy[1] *= 10
    assert growth_exponent(sizes, noisy) < MAX_EXPONENT


# --- 실제 작업으로 재는 끝에서 끝까지 ---------------------------------------

def test_measure_flags_quadratic_work_and_clears_linear_work():
    """제곱 시간 작업은 한계를 넘고 선형 작업은 넘지 않아야 한다(TK-142와 같은 단언)."""

    def quadratic(text):
        n = len(text) // 40
        return sum(1 for i in range(n) for _ in range(i))

    def linear(text):
        return sum(1 for _ in range(len(text) * 4))

    sizes = (1000, 2000, 4000, 8000)
    texts = [" " * n for n in sizes]
    assert growth_exponent(sizes, timings_interleaved(quadratic, texts)) > MAX_EXPONENT
    assert growth_exponent(sizes, timings_interleaved(linear, texts)) < MAX_EXPONENT


def test_timings_interleaved_returns_one_timing_per_input():
    timings = timings_interleaved(lambda t: len(t), ["a", "bb", "ccc"], rounds=2)
    assert len(timings) == 3
    assert all(t >= 0 for t in timings)


def test_timings_interleaved_visits_inputs_in_turn_each_round():
    """교차 측정이어야 부하가 한 입력에만 몰리지 않는다."""
    seen = []
    timings_interleaved(lambda t: seen.append(t), ["a", "b", "c"], rounds=3)
    assert seen == ["a", "b", "c"] * 3


def test_log_of_zero_timing_does_not_blow_up():
    """아주 빠른 작업이 0초로 측정되어도 기울기를 구할 수 있다."""
    sizes = (1000, 2000, 4000, 8000)
    assert math.isfinite(growth_exponent(sizes, [0.0, 0.0, 0.0, 0.0]))


# --- fastest_of: 시간과 결과를 함께 --------------------------------------

def test_fastest_of_returns_time_and_last_result():
    from tests.perf_scaling import fastest_of

    calls = []

    def work():
        calls.append(1)
        return len(calls)

    elapsed, result = fastest_of(work, repeats=3)
    assert result == 3            # 마지막 결과
    assert len(calls) == 3
    assert elapsed >= 0


def test_fastest_of_time_matches_best_of():
    from tests.perf_scaling import best_of, fastest_of

    seq = iter([0.04, 0.001, 0.04])
    e1, _ = fastest_of(lambda: time.sleep(next(seq)), repeats=3)
    seq2 = iter([0.04, 0.001, 0.04])
    e2 = best_of(lambda: time.sleep(next(seq2)), repeats=3)
    assert e1 < 0.02 and e2 < 0.02


def test_fastest_of_rejects_zero_repeats():
    from tests.perf_scaling import fastest_of

    with pytest.raises(ValueError):
        fastest_of(lambda: None, repeats=0)


def test_fastest_of_restores_gc_even_on_failure():
    import gc

    from tests.perf_scaling import fastest_of

    was = gc.isenabled()
    with pytest.raises(RuntimeError):
        fastest_of(lambda: (_ for _ in ()).throw(RuntimeError("실패")), repeats=1)
    assert gc.isenabled() == was


# --- 자가 보정 상대 한계 (TK-214 2차) ---------------------------------------
# 부하 검증에서 최솟값만으로는 0.1초급 단언이 깨지는 것을 확인했다. 지속적 포화 부하는 모든
# 회차를 똑같이 늦추므로 최솟값도 늦어진다. 그래서 같은 실행의 기준 작업으로 보정한다.

def test_slowdown_factor_is_at_least_one_on_an_idle_machine():
    """더 빠른 기계에서 한계가 조여지면 거짓 실패가 난다. 하한은 1.0이다."""
    from tests.perf_scaling import reset_calibration_cache, slowdown_factor

    reset_calibration_cache()
    assert slowdown_factor() >= 1.0


def test_slowdown_factor_is_capped():
    """환경이 병적으로 느려도 단언이 무력해지지 않아야 한다."""
    from tests import perf_scaling as ps

    original = ps.CALIBRATION_BASELINE_SECONDS
    try:
        ps.CALIBRATION_BASELINE_SECONDS = 1e-12   # 아주 빠른 기준 = 엄청난 감속으로 보인다
        ps.reset_calibration_cache()
        assert ps.slowdown_factor() == ps.MAX_SLOWDOWN
    finally:
        ps.CALIBRATION_BASELINE_SECONDS = original
        ps.reset_calibration_cache()


def test_assert_within_scales_the_limit_by_the_measured_factor():
    """기준값을 10배 작게 두면(=10배 느린 기계로 보임) 한계도 그만큼 늘어난다."""
    from tests import perf_scaling as ps

    original = ps.CALIBRATION_BASELINE_SECONDS
    try:
        ps.CALIBRATION_BASELINE_SECONDS = original / 10
        ps.reset_calibration_cache()
        factor = ps.assert_within(0.5, 0.1, "10배 느린 기계")   # 0.5 < 0.1 × 약 10
        assert 5 < factor <= ps.MAX_SLOWDOWN
    finally:
        ps.CALIBRATION_BASELINE_SECONDS = original
        ps.reset_calibration_cache()


def test_assert_within_still_fails_on_a_blown_up_target():
    """엄격도 유지: 감속 배수를 크게 보이게 해도 폭주한 대상은 여전히 실패한다.

    ReDoS 폭주는 100~1000배이고 감속 배수는 상한이 50이므로 가려지지 않는다.
    """
    from tests import perf_scaling as ps

    original = ps.CALIBRATION_BASELINE_SECONDS
    try:
        ps.CALIBRATION_BASELINE_SECONDS = 1e-12      # 배수가 상한(50)까지 올라간다
        ps.reset_calibration_cache()
        with pytest.raises(AssertionError) as err:
            ps.assert_within(0.1 * ps.MAX_SLOWDOWN * 2, 0.1, "폭주")
        assert "보정 한계" in str(err.value)
    finally:
        ps.CALIBRATION_BASELINE_SECONDS = original
        ps.reset_calibration_cache()


def test_assert_within_message_names_limit_factor_and_scaled_limit():
    from tests.perf_scaling import assert_within

    with pytest.raises(AssertionError) as err:
        assert_within(99.0, 0.1, "느린 자리")
    text = str(err.value)
    assert "느린 자리" in text
    assert "기준 한계 0.1초" in text
    assert "감속 배수" in text


def test_assert_within_returns_the_factor_for_logging():
    from tests.perf_scaling import assert_within

    factor = assert_within(0.0, 0.1)
    assert factor >= 1.0


def test_calibration_work_is_cpu_bound_and_stable():
    """기준 작업이 흔들리면 보정 자체를 믿을 수 없다. 5회 측정의 편차를 본다."""
    from tests.perf_scaling import _calibration_work, mean_of

    runs = [mean_of(_calibration_work, repeats=3) for _ in range(5)]
    assert min(runs) > 0
    assert max(runs) / min(runs) < 3.0, runs   # 공용 실행기에서도 이 정도는 넘지 않는다


def test_calibration_work_result_does_not_depend_on_call_count():
    """캐시가 끼면 2회차부터 빨라져 배수가 틀어진다."""
    from tests.perf_scaling import _calibration_work

    assert _calibration_work() == _calibration_work()


# --- 보정은 평균으로 잰다 (최솟값으로 재면 부하를 못 본다) --------------------
# 평가 측 실측(2026-11-19, 4코어에 바쁜 루프 8개): 기준 20,000회의 최솟값은 0.000825초로
# 부하 없을 때와 같아 배수가 0.99로 나왔고, 평균은 0.002479초로 배수 2.96이었다.
# 첫 구현이 최솟값을 써서 부하 검증에서 '0.1481초 > 보정 한계 0.1000초(배수 1.00)'로 실패했다.

def test_mean_of_is_not_the_minimum():
    """한 번 느린 실행이 섞이면 평균은 커져야 한다 — 이것이 부하를 보는 신호다."""
    from tests.perf_scaling import best_of, mean_of

    # mean_of는 준비 회차를 한 번 더 돌리므로 값이 하나 더 필요하다.
    delays = [0.0, 0.001, 0.001, 0.001, 0.001, 0.05]
    seq = iter(delays)
    mean = mean_of(lambda: time.sleep(next(seq)), repeats=len(delays) - 1)
    seq2 = iter(delays[1:])
    best = best_of(lambda: time.sleep(next(seq2)), repeats=len(delays) - 1)
    assert mean > best * 3, (mean, best)


def test_mean_of_discards_a_warmup_run():
    """첫 호출의 적재 비용이 평균에 섞이면 한가한 기계에서도 배수가 1을 넘는다."""
    from tests.perf_scaling import mean_of

    calls = []
    mean_of(lambda: calls.append(1), repeats=3)
    assert len(calls) == 4       # 준비 1회 + 측정 3회


def test_mean_of_rejects_zero_repeats():
    from tests.perf_scaling import mean_of

    with pytest.raises(ValueError):
        mean_of(lambda: None, repeats=0)


def test_slowdown_factor_is_one_on_this_idle_machine():
    """기준값이 이 환경에 맞게 잡혀 있는지. 1.0보다 크게 나오면 한계가 느슨해진다."""
    from tests.perf_scaling import reset_calibration_cache, slowdown_factor

    reset_calibration_cache()
    assert slowdown_factor() < 1.5


# --- 배수 캐시 --------------------------------------------------------------

def test_slowdown_factor_is_cached_within_the_window():
    """자리마다 다시 재면 시험 전체가 그만큼 길어진다."""
    from tests import perf_scaling as ps

    ps.reset_calibration_cache()
    first = ps.slowdown_factor()
    original = ps.CALIBRATION_BASELINE_SECONDS
    try:
        ps.CALIBRATION_BASELINE_SECONDS = original / 1000   # 다시 재면 크게 달라질 값
        assert ps.slowdown_factor() == first                # 캐시가 살아 있다
        assert ps.slowdown_factor(refresh=True) > first     # refresh면 다시 잰다
    finally:
        ps.CALIBRATION_BASELINE_SECONDS = original
        ps.reset_calibration_cache()


def test_reset_calibration_cache_clears_it():
    from tests import perf_scaling as ps

    ps.slowdown_factor()
    ps.reset_calibration_cache()
    assert ps._calibration_cache["factor"] is None
