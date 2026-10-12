"""Read-only observation of the original TK-43 timer; no assertions are changed.

Observer timings do not substitute for the original test's elapsed assertion.
The observer adds a small amount of overhead and can affect GC scheduling.
"""
from __future__ import annotations

import gc
import json
import sys
import threading
import time

_TARGET = 'tests/test_tk43_particle_sentences.py::test_label_regex_repeated_sentence_input_time'
_active = False
_inside = False
_returns = 0
_boundaries = [None, None]
_starts = {}
_events = []
_record = None
_code = None
_previous_profile = None
_installed = False


def _profile(frame, event, arg):
    global _inside, _returns
    if frame.f_code is _code and arg is time.perf_counter:
        if event == 'c_return':
            _returns += 1
            if _returns == 1:
                _boundaries[0] = time.perf_counter()
                _inside = True
        elif event == 'c_call' and _returns == 1:
            _inside = False
            _boundaries[1] = time.perf_counter()


def _gc_callback(phase, info):
    if not _active:
        return
    generation = info['generation']
    if phase == 'start':
        _starts[generation] = (time.perf_counter(), _inside)
    else:
        end = time.perf_counter()
        start, was_inside = _starts.pop(generation, (end, _inside))
        _events.append({
            'generation': generation, 'start': start, 'end': end,
            'gc_thread_ident': threading.get_ident(),
            'seconds': end - start,
            'inside_original_timer_start': was_inside,
            'inside_original_timer_end': _inside,
            'collected': info['collected'], 'uncollectable': info['uncollectable'],
        })


def pytest_configure(config):
    gc.callbacks.append(_gc_callback)


def pytest_runtest_call(item):
    global _active, _inside, _returns, _boundaries, _events, _code
    global _record, _previous_profile, _installed
    if item.nodeid != _TARGET:
        return
    _active = True
    _inside = False
    _returns = 0
    _boundaries = [None, None]
    _events = []
    _code = item.obj.__code__
    _previous_profile = sys.getprofile()
    _record = {
        'nodeid': _TARGET, 'gc_count': gc.get_count(),
        'gc_threshold': gc.get_threshold(), 'gc_stats': gc.get_stats(),
        'threads': threading.active_count(),
        'call_wall_start': time.perf_counter(), 'call_cpu_start': time.thread_time(),
        'prior_profiler_present': _previous_profile is not None,
        'target_thread_ident': threading.get_ident(),
        'boundary_observation_abstained': _previous_profile is not None,
        'observer_changes_assertions_or_clock': False,
        'observer_overhead_and_GC_scheduling_perturbation_possible': True,
    }
    _installed = _previous_profile is None
    if _installed:
        sys.setprofile(_profile)


def pytest_runtest_logreport(report):
    if _record is not None and report.nodeid == _TARGET and report.when == 'call':
        _record['original_test_outcome'] = report.outcome


def pytest_runtest_teardown(item):
    global _active
    if not _active or item.nodeid != _TARGET:
        return
    if _installed:
        sys.setprofile(None)
    _record.update(
        call_wall_seconds=time.perf_counter() - _record.pop('call_wall_start'),
        call_thread_cpu_seconds=time.thread_time() - _record.pop('call_cpu_start'),
        original_counter_boundaries_observed=list(_boundaries),
        gc_events=list(_events), gc_after=gc.get_count(),
    )
    _active = False


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if _record is not None:
        terminalreporter.write_line('CI_TIMER_DIAGNOSTIC ' + json.dumps(_record, sort_keys=True))


def pytest_unconfigure(config):
    if _gc_callback in gc.callbacks:
        gc.callbacks.remove(_gc_callback)
