"""Capability failures fail closed; valid decoder abstention stays compatible."""
from __future__ import annotations

from dataclasses import replace

import pytest

from .post013_occurrence_projection import occurrence_projection
from .test_post013_tk55_occurrence_trace_spike import _traced_argument, _claim_slice, _compare
from .test_post013_tk55_excerpt_offsets_spike import _source
from .test_post013_tk55_cascade_source_spike import PHONES
from .test_post013_tk55_boundary_spike import _route


INVALID = (
    'range_none', 'range_string', 'range_list', 'range_dict', 'range_set', 'range_generator',
    'range_flat', 'range_empty', 'range_one_endpoint', 'range_three_endpoints', 'range_pair_list',
    'range_pair_string', 'endpoint_string', 'endpoint_none', 'endpoint_bool', 'endpoint_float',
    'endpoint_nan', 'endpoint_inf', 'negative_start', 'negative_end', 'reversed', 'oversized',
    'range_overlap', 'range_reordered', 'owned_outside_selection',
    'origins_list', 'origins_string', 'origins_dict', 'origins_set', 'origins_generator',
    'origins_scalar', 'origins_short', 'origins_long', 'origin_string', 'origin_bool', 'origin_float',
    'origin_nan', 'origin_inf', 'origin_negative', 'origin_foreign', 'origin_duplicate', 'origin_reordered',
    'source_none', 'source_list', 'foreign_source_spelling', 'rendered_none', 'rendered_foreign_leaf',
)


def _invalid(evidence, case):
    request, source, ranges, rendered, origins = evidence
    n = len(source)
    alternatives = {
        'range_none': None, 'range_string': '0,1', 'range_list': list(ranges),
        'range_dict': {'start': 0, 'end': n}, 'range_set': set(ranges),
        'range_generator': iter(ranges), 'range_flat': (0, n), 'range_empty': (),
        'range_one_endpoint': ((0,),), 'range_three_endpoints': ((0, n, n),),
        'range_pair_list': ([0, n],), 'range_pair_string': ('ab',),
        'endpoint_string': (('0', n),), 'endpoint_none': ((None, n),),
        'endpoint_bool': ((False, n),), 'endpoint_float': ((0.0, n),),
        'endpoint_nan': ((float('nan'), n),), 'endpoint_inf': ((0, float('inf')),),
        'negative_start': ((-1, n),), 'negative_end': ((0, -1),),
        'reversed': ((n, 0),), 'oversized': ((0, n + 1),),
        'range_overlap': ((0, n), (1, n)), 'range_reordered': ((1, n), (0, 1)),
        'owned_outside_selection': ((1, n),),
    }
    if case in alternatives:
        ranges = alternatives[case]
    elif case.startswith('origins_'):
        origins = {
            'origins_list': list(origins), 'origins_string': '0' * len(origins),
            'origins_dict': dict(enumerate(origins)), 'origins_set': set(origins),
            'origins_generator': iter(origins), 'origins_scalar': 0,
            'origins_short': origins[:-1], 'origins_long': origins + (None,),
        }[case]
    elif case.startswith('origin_'):
        changed = list(origins)
        replacement = {
            'origin_string': '0', 'origin_bool': False, 'origin_float': 0.0,
            'origin_nan': float('nan'), 'origin_inf': float('inf'),
            'origin_negative': -1, 'origin_foreign': n, 'origin_duplicate': origins[0],
        }
        if case == 'origin_reordered':
            changed.reverse()
        elif case == 'origin_duplicate':
            changed[1] = replacement[case]
        else:
            changed[0] = replacement[case]
        origins = tuple(changed)
    elif case == 'source_none':
        source = None
    elif case == 'source_list':
        source = list(source)
    elif case == 'foreign_source_spelling':
        source = 'X' + source[1:]
    elif case == 'rendered_none':
        rendered = None
    else:
        # Structurally valid source/trace, but it describes another leaf.
        source = rendered = '{"body":"별도 일반 자료"}'
        ranges, origins = ((0, len(source)),), tuple(range(len(source)))
    return request, source, ranges, rendered, origins


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
@pytest.mark.parametrize('case', INVALID)
@pytest.mark.parametrize('pii', (False, True), ids=('benign', 'mandatory_pii'))
def test_present_invalid_capability_is_blocked_before_actual_provider_and_budget(monkeypatch, producer, case, pii):
    evidence = producer(_source('일반 법령 검토 자료', 'closing_quote_outside'))
    _, before, reserved = _route(monkeypatch, evidence[0])
    assert len(before) == len(reserved) == 1
    candidate = replace(evidence[0], metadata={'contact': PHONES[0]}) if pii else None
    status, matches, outcome, sent, reserved = _compare(monkeypatch, _invalid(evidence, case), candidate=candidate)
    assert status == 'INVALID_TRACE' and matches == ()
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == (
        'PII_INPUT_BLOCKED' if pii else 'INPUT_CONTRACT_VIOLATION')


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
@pytest.mark.parametrize('mode', ('opaque', 'unsupported', 'work', 'decoder'))
@pytest.mark.parametrize('pii', (False, True), ids=('benign', 'mandatory_pii'))
def test_valid_capability_abstention_preserves_actual_provider_budget_and_wire(monkeypatch, producer, mode, pii):
    from . import post013_occurrence_projection as module
    evidence = producer('일반 자료 ' + '가' * 1600 if mode == 'unsupported'
                        else _source('일반 법령 검토 자료', 'closing_quote_outside'))
    if mode == 'opaque':
        evidence = (*evidence[:4], None)
    elif mode in ('work', 'decoder'):
        def fail(*args):
            raise RuntimeError('Synthetic local work budget') if mode == 'work' else ValueError('Synthetic decoder error')
        monkeypatch.setattr(module, '_validated_tokens' if mode == 'work' else '_mapped_nodes', fail)
    _, before, reserved_before = _route(monkeypatch, evidence[0])
    candidate = replace(evidence[0], metadata={'contact': PHONES[0]}) if pii else None
    status, matches, outcome, sent, reserved = _compare(monkeypatch, evidence, candidate=candidate)
    assert status == {'opaque': 'ABSTAIN_NO_TRACE', 'unsupported': 'ABSTAIN_UNSUPPORTED',
                      'work': 'ABSTAIN_WORK', 'decoder': 'ABSTAIN_DECODER'}[mode]
    assert matches == ()
    assert len(before) == len(reserved_before) == 1
    if pii:
        assert sent == reserved == []
        assert outcome.executions[0].input_privacy['failure_code'] == 'PII_INPUT_BLOCKED'
    else:
        assert len(sent) == len(reserved) == 1
        assert sent[0].user == before[0].user == evidence[0].user


@pytest.mark.parametrize('case', INVALID[:-1])
def test_malformed_capability_never_enters_source_decoder_or_opaque_fallback(monkeypatch, case):
    from . import post013_occurrence_projection as module
    source = '{"body":"일반 자료"}'
    evidence = (None, source, ((0, len(source)),), source, tuple(range(len(source))))
    def forbidden(*args):
        raise AssertionError('Invalid-present capability entered the decoder')
    monkeypatch.setattr(module, '_mapped_nodes', forbidden)
    _, source, ranges, rendered, origins = _invalid(evidence, case)
    assert occurrence_projection(source, ranges, rendered, origins) == ('INVALID_TRACE', ())


def test_missing_trace_does_not_hide_invalid_source_selection():
    assert occurrence_projection('資料', (('0', 2),), '資料', None) == ('INVALID_TRACE', ())
    assert occurrence_projection('資料', ((0, 2),), '資料', None) == ('ABSTAIN_NO_TRACE', ())
    assert occurrence_projection('', ((0, 0),), '', ()) == ('ABSTAIN_UNSUPPORTED', ())
