"""Public actual-TXT contract for independent reference versus requirement acts.

Design-first controls: earlier expectations stay frozen. The three new normal
cases require independently proved source frames, not a positive override.
"""
import json
import pytest

from tests.test_tk45_clause_effect_contract import LEAD, _trace_pipeline
from tests.test_tk45_authored_predicate_scope import LIMIT


@pytest.mark.parametrize('body', [
    '상계의 의사표시 서류를 참조한 뒤 변제공탁을 완료하였으므로',
    '수령거절 자료를 검토한 후 변제공탁을 이행하였으므로',
    '기산점 서류를 검토한 다음 변제공탁을 완수하였으므로',
])
def test_independently_proved_reference_and_other_requirement_act_keep_normal_limit(monkeypatch, tmp_path, body):
    text = LEAD + body + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    contexts = [row for row in trace['requirements'] if 'contextual_proposition' in row]
    assert contexts
    actual = [row for row in trace['requirements'] if row.get('predicate_semantics', {}).get('supports_asserted_fulfillment')]
    assert actual
    for row in contexts:
        proof = row['contextual_proposition']
        assert row['state'] == proof['original_state'] == 'UNCERTAIN'
        assert row['reason'] == proof['original_reason'] == 'CHANGED_ARGUMENT'
        assert all(row['requirement_identity'] != target['requirement_identity'] for target in actual)
        assert proof['kind'] == 'REFERENCE_NON_REQUIREMENT_ASSERTION'
        assert proof['supports_requirement_fulfillment'] is False
        assert proof['underlying_facts_verified'] is False
        assert proof['legal_sufficiency_verified'] is False
        assert proof['mapping_authority'] == 'APPLICATION_NOT_NIKL_CLASSIFICATION'
        assert proof['selected_source_senses']
        assert text[slice(*proof['object_case_span'])] in {'을', '를'}
        assert text[slice(*proof['object_span'])] in {'서류', '자료'}
        assert text[slice(*proof['predicate_span'])] in {'참조한', '검토한'}
        assert text[slice(*proof['closure_span'])] in {'뒤', '후', '다음'}
        assert text[slice(*proof['requirement_modifier_span'])] in {'상계의 의사표시', '수령거절', '기산점'}
        assert proof['authored'] is True
        assert proof['local_subject_span'] is None
        assert row['reference_selection_support']['discharges_reference_requirement'] is False
        assert json.loads(json.dumps(proof)) == proof


@pytest.mark.parametrize('body', [
    '상계의 의사표시를 하지 않았으나 변제공탁을 완료하였으므로',
    '수령거절을 하지 않았으나 변제공탁을 완료하였으므로',
    '상계의 의사표시 효력을 확인한 뒤 변제공탁을 완료하였으므로',
    '수령거절 여부를 확인한 후 변제공탁을 이행하였으므로',
    '기산점 서류를 처리한 다음 변제공탁을 완료하였으므로',
    '상계의 의사표시 서류를 검토할 계획을 세운 뒤 변제공탁을 완료하였으므로',
    '상계의 의사표시를 하지 않았다는 서류를 검토한 뒤 변제공탁을 완료하였으므로',
    '피고는 상계의 의사표시 서류를 검토한 뒤 원고는 변제공탁을 완료하였으므로',
    '상대방은 “상계의 의사표시 서류를 검토하였다”고 주장한 뒤 변제공탁을 완료하였으므로',
    '상계의 의사표시 서류를 검토한 뒤 변제공탁을 일부 완료하였으므로',
    '상계의 의사표시 서류를 검토한 뒤 변제공탁을 중단하였으므로',
    '상계의 의사표시 서류를 검토한 뒤 변제공탁을 하였으므로',
    '변제공탁 서류를 확인한 뒤 전액을 지급하였으므로',
    '변제공탁 기록을 검토한 후 상계의 의사표시가 도달하였으므로',
    '상계의 의사표시 서류를 검토하였으므로',
])
def test_reference_words_do_not_override_denial_unknown_status_or_missing_actual_assertion(monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace


@pytest.mark.parametrize('tail', [
    '검토하지 않고', '검토한 적이 없으나', '검토한 사람이',
])
def test_negated_experience_or_person_modifier_is_not_reference_closure(monkeypatch, tmp_path, tail):
    body = '상계의 의사표시 서류를 ' + tail + ' 변제공탁을 완료하였으므로'
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
    assert all('contextual_proposition' not in row for row in trace['requirements'])
    assert all(row.status.value == 'SUSPICIOUS' for row in findings)


@pytest.mark.parametrize('prefix', ['피고는 ', '작성자는 '])
def test_explicit_carried_actor_has_exact_source_provenance(monkeypatch, tmp_path, prefix):
    text = LEAD + prefix + '상계의 의사표시 서류를 참조한 뒤 변제공탁을 완료하였으므로' + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    proof = next(row['contextual_proposition'] for row in trace['requirements'] if 'contextual_proposition' in row)
    assert text[slice(*proof['local_subject_span'])] == prefix.strip()


@pytest.mark.parametrize('reference,closure', [
    ('참조하였으나', '으나'), ('검토했습니다,', '습니다'), ('참조하였습니다;', '습니다'),
])
def test_independent_finite_reference_keeps_exact_predicate_and_boundary(monkeypatch, tmp_path, reference, closure):
    text = LEAD + '상계의 의사표시 서류를 ' + reference + ' 변제공탁을 완료하였으므로' + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    proof = next(row['contextual_proposition'] for row in trace['requirements'] if 'contextual_proposition' in row)
    assert text[slice(*proof['predicate_span'])] == reference.rstrip(',;')
    assert text[slice(*proof['closure_span'])] == closure
    assert text[slice(*proof['clause_boundary_span'])] in {'으나', ',', ';'}
    assert proof['supports_requirement_fulfillment'] is False


@pytest.mark.parametrize('requirement,case', [('상계의 의사표시', '를'), ('수령거절', '을')])
def test_direct_denial_keeps_original_overclaim_selection(monkeypatch, tmp_path, requirement, case):
    text = LEAD + requirement + case + ' 하지 않았으나 변제공탁을 완료하였으므로' + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace
    assert any(row['state'] == 'DENIED' and row['reason'] == 'ATTACHED_NEGATIVE_PREDICATE'
               for row in trace['requirements'])
    assert all('contextual_proposition' not in row for row in trace['requirements'])
    assert all(not row['verdict'].startswith('요건 확인 요청') for row in trace['selected_findings'])


@pytest.mark.parametrize('length', [8000, 16000, 32000])
def test_reference_selection_actual_txt_preserves_local_input_bounds(monkeypatch, tmp_path, length):
    from packages.legal_engine import legal_rules

    original = legal_rules._contextual_requirement_resolution
    checked = []

    def measured(text, observations, quotations):
        checked.append(len(text))
        return original(text, observations, quotations)

    monkeypatch.setattr(legal_rules, '_contextual_requirement_resolution', measured)
    block = LEAD + '상계의 의사표시 서류를 참조한 뒤 변제공탁을 완료하였으므로' + LIMIT + ' '
    text = block * (length // len(block))
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    assert checked and sum(checked) <= len(text) * 2
    assert max(checked) <= len(block) * 2


@pytest.mark.parametrize('body', [
    '상계의 의사표시 서류를 참조한 뒤 절차가 유효하다면 변제공탁을 완료하였으므로',
    '피고의 상계의 의사표시 서류를 검토한 뒤 원고의 변제공탁을 완료하였으므로',
    '별건 상계의 의사표시 자료를 검토한 뒤 이 사건 변제공탁을 완료하였으므로',
])
def test_cross_scope_or_unknown_qualification_still_keeps_verification(monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
