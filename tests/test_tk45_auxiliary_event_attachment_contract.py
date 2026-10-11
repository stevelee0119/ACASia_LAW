"""Approved source-composition controls; original observations stay frozen."""
import json
import pytest

from tests.test_tk45_clause_effect_contract import LEAD, _trace_pipeline
from tests.test_tk45_authored_predicate_scope import LIMIT


@pytest.mark.parametrize('first,later,head,auxiliary', [
    ('상계의 의사표시를 완료해 놓은 이후', '변제공탁을 완료하였으므로', '완료해', '놓은'),
    ('변제공탁을 완수해 둔 이후', '상계의 의사표시를 완료하였으므로', '완수해', '둔'),
    ('변제공탁을 완결해 놓은 이후', '상계의 의사표시를 완료하였으므로', '완결해', '놓은'),
    ('상계의 의사표시를 해 둔 이후', '변제공탁을 완료하였으므로', '해', '둔'),
    ('변제공탁을 해 놓은 이후', '상계의 의사표시를 완료하였으므로', '해', '놓은'),
])
def test_direct_first_event_action_composes_with_result_maintaining_auxiliary(
        monkeypatch, tmp_path, first, later, head, auxiliary):
    text = LEAD + first + ' ' + later + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    original = [row for row in trace['requirements'] if row['state'] == 'UNCERTAIN']
    assert original and all(row['reason'] == 'CHANGED_ARGUMENT' for row in original)
    assert not findings, trace
    for row in original:
        proof = row['case_bound_event_assertion']
        assert proof['argument_span'] == row['event_frame']['argument_span']
        assert proof['case_span'] == row['event_frame']['case_span']
        assert proof['original_state'] == row['state'] == 'UNCERTAIN'
        assert proof['original_reason'] == row['reason'] == 'CHANGED_ARGUMENT'
        assert proof['attachment_kind'] == 'DYNAMIC_RESULTATIVE_AUXILIARY'
        assert text[slice(*proof['head_span'])] == head
        assert text[slice(*proof['auxiliary_span'])] == auxiliary
        assert text[slice(*proof['temporal_span'])] == '이후'
        assert proof['supports_authored_event_assertion'] is True
        assert proof['underlying_facts_verified'] is False
        assert proof['legal_sufficiency_verified'] is False
        assert proof['total_requirement_completion'] is False
        assert proof['fulfillment_verified'] is False
        assert text[slice(*proof['morphology_span'])] == ('은' if auxiliary == '놓은' else '둔')
        assert text[slice(*proof['connective_span'])] == '해'
        if head == '해':
            assert proof['head_lemma'] == '하다'
            assert proof['head_category'] == 'AUTHORED_DIRECT_ACTION'
            assert proof['supports_asserted_fulfillment'] is False
            assert proof['total_completion_asserted'] is False
        if auxiliary == '놓은':
            scope = proof['auxiliary_scope_resolution']
            assert scope['origin'] == 'LOCAL_SUBJECT_MATCH'
            assert scope['source_span'] == proof['auxiliary_span']
            assert scope['original_scope_index_preserved'] is True
            assert scope['other_breaks_ignored'] is False
        assert json.loads(json.dumps(proof)) == proof
        support = row['case_bound_event_selection_support']
        assert support['later_act_certifies_first'] is False
        assert support['different_acts_merged'] is False


@pytest.mark.parametrize('body', [
    '상계의 의사표시를 해 놓을 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 두려는 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 두는 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 계획해 둔 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 준비해 놓은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 중단해 놓은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 유예해 둔 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 포기해 놓은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 가정해 놓은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 검토해 둔 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 유효해 놓은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 평온해 둔 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 좋게 해 둔 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 일부 해 둔 이후 변제공탁을 완료하였으므로',
    '일부 상계의 의사표시를 해 놓은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 하지 않은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 하지 않고 해 둔 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 둔 사실을 검토한 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시 서류를 해 놓은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 둔 이후라고 가정하면 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 둔 이후의 계획을 검토한 뒤 변제공탁을 완료하였으므로',
    '절차가 유효하다면, 상계의 의사표시를 해 둔 이후 변제공탁을 완료하였으므로',
    '절차가 유효하다면; 상계의 의사표시를 해 놓은 이후 변제공탁을 완료하였으므로',
    '내일 상계의 의사표시를 해 둔 이후 변제공탁을 완료하였으므로',
    '피고는 상계의 의사표시를 해 둔 이후 원고는 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 둔 이후 상대방은 “변제공탁을 완료하였다”고 주장하나',
    '상계의 의사표시를 해 둔 이후 변제공탁을 하였으므로',
])
def test_auxiliary_does_not_certify_unproved_action_or_erase_other_source_scope(
        monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
    assert all('case_bound_event_assertion' not in row for row in trace['requirements'])


def test_reported_auxiliary_event_preserves_its_existing_result_without_author_proof(monkeypatch, tmp_path):
    text = (LEAD + '상대방은 “상계의 의사표시를 해 둔 이후”라고 주장하나 '
            + '변제공탁을 완료하였으므로' + LIMIT)
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    assert all('case_bound_event_assertion' not in row for row in trace['requirements'])


@pytest.mark.parametrize('first', ['하여 둔 이후', '완수하여 둔 이후', '완료하였고'])
def test_already_normal_legacy_action_forms_are_not_reclassified(monkeypatch, tmp_path, first):
    text = LEAD + '상계의 의사표시를 ' + first + ' 변제공탁을 완료하였으므로' + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    assert all('case_bound_event_assertion' not in row for row in trace['requirements'])


def test_source_composition_gap_has_own_case_and_no_existing_exact_predicate_token(monkeypatch, tmp_path):
    from packages.legal_engine import event_temporal_propositions as events
    from packages.legal_engine.predicate_semantics import past_predicate_evidence

    calls = []
    original = events.case_bound_event_evidence

    def measured(text, argument_span, case_span, end):
        calls.append((text[case_span[1]:end], original(text, argument_span, case_span, end)))
        return calls[-1][1]

    monkeypatch.setattr('packages.legal_engine.legal_rules.case_bound_event_evidence', measured)
    text = LEAD + '상계의 의사표시를 완료해 놓은 이후 변제공탁을 완료하였으므로' + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert calls
    tokens = calls[0][0].split()
    assert len(tokens) == 3
    assert all(past_predicate_evidence(token, event_object=True) is None for token in tokens)
    assert all(token not in events._REGULAR_FORMS for token in tokens)
    assert any(row['event_frame']['case_span'] and not row.get('predicate_chain')
               for row in trace['requirements'] if row['state'] == 'UNCERTAIN')
