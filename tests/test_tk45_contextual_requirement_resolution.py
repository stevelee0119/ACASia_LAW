"""Public actual-TXT contextual-resolution controls, before product rework."""
import pytest

from tests.test_tk45_clause_effect_contract import LEAD, _trace_pipeline
from tests.test_tk45_authored_predicate_scope import LIMIT


@pytest.mark.parametrize('body', [
    '변제공탁 서류를 확인한 뒤 변제공탁을 완료하였으므로',
    '변제공탁 기록을 검토한 후 변제공탁을 이행하였으므로',
    '변제공탁 내역을 정리한 다음 변제공탁을 마쳤으므로',
])
def test_same_requirement_context_and_independent_realization_keep_normal_limit(monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert not findings, trace
    assert any(row['state'] == 'UNCERTAIN' and row['reason'] == 'CHANGED_ARGUMENT' for row in trace['requirements'])
    assert any(row['state'] == 'POSITIVE' and row.get('predicate_semantics', {}).get('supports_asserted_fulfillment') for row in trace['requirements'])


@pytest.mark.parametrize('body', [
    '변제공탁을 하지 않았으나 변제공탁을 완료하였으므로',
    '변제공탁을 이행하지 않았으나 변제공탁을 완료하였으므로',
    '변제공탁 서류를 확인한 뒤 전액을 지급하였으므로',
    '변제공탁 기록을 검토한 후 상계의 의사표시가 도달하였으므로',
    '피고는 변제공탁 서류를 확인한 뒤 원고는 변제공탁을 완료하였으므로',
    '원고는 변제공탁 기록을 검토한 후 새 당사자는 변제공탁을 이행하였으므로',
    '변제공탁 서류를 확인한 뒤 변제공탁을 중단하였으므로',
    '변제공탁 기록을 검토한 후 변제공탁을 하였으므로',
    '변제공탁 서류를 확인한 뒤 변제공탁을 일부 완료하였으므로',
    '변제공탁 기록을 검토한 후 변제공탁을 완료할 계획을 세웠으므로',
    '변제공탁 서류를 확인한 뒤 원고는 “변제공탁을 완료하였다”고 주장하였으므로',
    '변제공탁 기록을 검토한 후 상대방은 “변제공탁을 이행하였다”고 주장하였으므로',
])
def test_unrelated_actor_requirement_denial_or_uncertain_evidence_keeps_verification(monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
