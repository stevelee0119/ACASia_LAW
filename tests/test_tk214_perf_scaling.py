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
