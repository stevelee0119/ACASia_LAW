"""Public actual-TXT contextual-resolution controls, before product rework."""
import json
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
    source = LEAD + body + LIMIT
    contextual = next(row for row in trace['requirements'] if 'contextual_resolution' in row)
    proof = contextual['contextual_resolution']
    target = trace['requirements'][proof['realization_observation_index']]
    assert contextual['state'] == proof['original_state'] == 'UNCERTAIN'
    assert contextual['requirement_identity'] == target['requirement_identity']
    assert source[slice(*proof['context_case_span'])] == '를' or source[slice(*proof['context_case_span'])] == '을'
    assert source[slice(*proof['context_argument_span'])] in {'서류', '기록', '내역'}
    assert source[slice(*proof['realization_argument_span'])] == '변제공탁'
    assert source[slice(*proof['realization_predicate_span'])] in {'완료하였으므로', '이행하였으므로', '마쳤으므로'}
    assert proof['source_semantic_support'] and proof['shared_local_subject_scope']
    assert not proof['legal_sufficiency_verified'] and not proof['underlying_facts_verified']
    assert json.loads(json.dumps(proof)) == proof


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


@pytest.mark.parametrize('body', [
    '변제공탁 서류를 확인한 뒤 변제공탁 기록을 검토한 후 변제공탁을 완료하였으므로',
    '변제공탁 기록을 검토하였다, 변제공탁 내역을 정리한 다음 변제공탁을 마쳤으므로',
])
def test_multiple_context_mentions_keep_each_original_source_relation(monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert not findings, trace
    rows = [row for row in trace['requirements'] if 'contextual_resolution' in row]
    assert len(rows) == 2 and all(row['state'] == 'UNCERTAIN' for row in rows)
    assert len({row['contextual_resolution']['realization_observation_index'] for row in rows}) == 1


@pytest.mark.parametrize('middle', [
    '새 당사자는 기록을 확인한 뒤 ',
    '원고가 자료를 검토한 후 ',
    '“작성 절차를 점검하였다”고 보고한 뒤 ',
    '절차가 유효하다면 ',
])
def test_intervening_subject_quote_or_condition_blocks_context_resolution(monkeypatch, tmp_path, middle):
    body = '변제공탁 서류를 확인한 뒤 ' + middle + '변제공탁을 완료하였으므로'
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
    assert all('contextual_resolution' not in row for row in trace['requirements'])


@pytest.mark.parametrize('prefix', ['절차가 유효하다면 ', '서류를 확인하면 '])
def test_condition_before_context_does_not_become_an_unconditional_realization(monkeypatch, tmp_path, prefix):
    body = prefix + '변제공탁 서류를 확인한 뒤 변제공탁을 완료하였으므로'
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
    assert all('contextual_resolution' not in row for row in trace['requirements'])


@pytest.mark.parametrize('length', [8000, 16000, 32000])
def test_actual_txt_context_resolution_keeps_local_work_bounds(monkeypatch, tmp_path, length):
    from packages.legal_engine import legal_rules
    original = legal_rules._contextual_requirement_resolution
    checked = []

    def measured(text, observations, quotations):
        checked.append(len(text))
        return original(text, observations, quotations)

    monkeypatch.setattr(legal_rules, '_contextual_requirement_resolution', measured)
    block = LEAD + '변제공탁 서류를 확인한 뒤 변제공탁을 완료하였으므로' + LIMIT + ' '
    text = block * (length // len(block))
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    assert checked and sum(checked) <= len(text) * 2
    assert max(checked) <= len(block) * 2
