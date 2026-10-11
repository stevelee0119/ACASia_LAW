"""Generic dynamic/state and observed morphology composition contracts."""
import json

import pytest

from packages.legal_engine.event_temporal_propositions import (
    AUXILIARY_APPLICATION_MAPPINGS, AUXILIARY_SOURCE_SENSES, case_bound_event_evidence,
)


def _evidence(argument, tail):
    text = argument + '을 ' + tail
    size = len(argument)
    return text, case_bound_event_evidence(text, [0, size], [size, size + 1], len(text))


@pytest.mark.parametrize('argument', ['실험', '학습', '수업'])
@pytest.mark.parametrize('head,auxiliary', [('해', '둔'), ('완료해', '놓은'), ('완수하여', '둔')])
def test_nonlegal_first_event_proof_needs_no_later_assertion(argument, head, auxiliary):
    text, proof = _evidence(argument, head + ' ' + auxiliary + ' 이후')
    assert proof
    assert text[slice(*proof['argument_span'])] == argument
    assert text[slice(*proof['case_span'])] == '을'
    assert text[slice(*proof['head_span'])] == head
    assert text[slice(*proof['auxiliary_span'])] == auxiliary
    assert text[slice(*proof['connective_span'])] == ('여' if head.endswith('하여') else '해')
    assert text[slice(*proof['morphology_span'])] == ('은' if auxiliary == '놓은' else '둔')
    assert proof['analytical_adnominal_ending'] == ('-은' if auxiliary == '놓은' else '-ㄴ')
    assert proof['supports_authored_event_assertion'] is True
    assert proof['total_requirement_completion'] is False
    assert proof['fulfillment_verified'] is False
    assert proof['underlying_facts_verified'] is False
    assert proof['legal_sufficiency_verified'] is False
    if head == '해':
        assert proof['head_category'] == 'AUTHORED_DIRECT_ACTION'
        assert proof['selected_source_senses'][0]['source_sense_key'] == '하다:1:1'
        assert proof['supports_asserted_fulfillment'] is False
        assert proof['total_completion_asserted'] is False
    else:
        assert proof['head_category'] == 'COMPLETION'
        assert proof['supports_asserted_fulfillment'] is True
        assert proof['total_completion_asserted'] is True
    assert json.loads(json.dumps(proof)) == proof


@pytest.mark.parametrize('tail', [
    '평온해 놓은 이후', '유효해 둔 이후', '확실해 놓은 이후',
    '해 두려는 이후', '해 놓을 이후', '해 두는 이후',
    '해 둔 이후라면', '해 둔 이후라고 가정하면', '해 둔 이후의 계획',
    '해 놓은사람 이후', '해 놓은것 이후', '해 놓는 이후',
    '수행해 놓은 이후', '실행해 둔 이후', '끝내 놓은 이후',
    '계획해 둔 이후', '준비해 놓은 이후', '중단해 둔 이후', '포기해 놓은 이후',
    '유예해 둔 이후', '연기해 놓은 이후', '검토해 놓은 이후', '가정해 둔 이후',
    '미완료해 놓은 이후', '준완수해 둔 이후', '일부 해 놓은 이후',
    '좋게 해 둔 이후', '해 둔 사실을 확인한 이후', '하지 않고 해 둔 이후',
    '계획을 완료해 놓은 이후', '서류를 작성해 둔 이후',
])
def test_auxiliary_alone_never_certifies_unknown_stative_or_other_action(tail):
    _, proof = _evidence('실험', tail)
    assert proof is None


def test_mismatched_object_case_or_intervening_argument_abstains():
    text = '실험 계획을 해 둔 이후'
    assert case_bound_event_evidence(text, [0, 2], [5, 6], len(text)) is None
    text = '실험이 해 둔 이후'
    assert case_bound_event_evidence(text, [0, 2], [2, 3], len(text)) is None


def test_source_senses_and_application_categories_are_separate():
    assert len(AUXILIARY_SOURCE_SENSES) == 8
    for source in AUXILIARY_SOURCE_SENSES:
        assert source['source'].startswith('https://krdict.korean.go.kr/')
        assert source['definition'] and source['retrieved_on'] == '2026-10-11'
        assert source['source_sense_key'] in AUXILIARY_APPLICATION_MAPPINGS
        assert 'category' not in source
    assert AUXILIARY_APPLICATION_MAPPINGS['하다:1:1'] != 'COMPLETION'
    assert AUXILIARY_APPLICATION_MAPPINGS['놓다:2:2'] == 'STATE_CONTINUATION_NOT_ACTION_PROOF'
    assert AUXILIARY_APPLICATION_MAPPINGS['-은:1:3'] == 'CURRENT_STATE_NOT_ACTION_PROOF'
