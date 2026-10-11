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
        assert all(row['requirement_identity'] != target['requirement_identity'] for target in actual)
        assert proof['kind'] == 'REFERENCE_NON_REQUIREMENT_ASSERTION'
        assert proof['supports_requirement_fulfillment'] is False
        assert proof['underlying_facts_verified'] is False
        assert proof['legal_sufficiency_verified'] is False
        assert proof['mapping_authority'] == 'APPLICATION_NOT_NIKL_CLASSIFICATION'
        assert proof['selected_source_senses']
        assert text[slice(*proof['object_case_span'])] in {'을', '를'}
        assert text[slice(*proof['predicate_span'])]
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


@pytest.mark.parametrize('body', [
    '상계의 의사표시 서류를 참조한 뒤 절차가 유효하다면 변제공탁을 완료하였으므로',
    '피고의 상계의 의사표시 서류를 검토한 뒤 원고의 변제공탁을 완료하였으므로',
    '별건 상계의 의사표시 자료를 검토한 뒤 이 사건 변제공탁을 완료하였으므로',
])
def test_cross_scope_or_unknown_qualification_still_keeps_verification(monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
