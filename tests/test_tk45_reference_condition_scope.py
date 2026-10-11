"""Public leading-condition scope controls before the minimal guard."""
import pytest

from packages.legal_engine import legal_rules
from tests.test_tk45_clause_effect_contract import LEAD, _trace_pipeline
from tests.test_tk45_authored_predicate_scope import LIMIT

REFERENCE_ACT = '상계의 의사표시 서류를 참조한 뒤 변제공탁을 완료하였으므로'


@pytest.mark.parametrize('prefix', ['절차가 유효하다면, ', '서류를 검토한 경우, ', '절차가 유효하다면; '])
def test_preceding_separator_does_not_close_condition_on_reference_and_actual_act(monkeypatch, tmp_path, prefix):
    text = LEAD + prefix + REFERENCE_ACT + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace
    assert all('reference_selection_support' not in row for row in trace['requirements'])
    blocked = [row for row in trace['requirements'] if 'reference_scope_abstention' in row]
    assert blocked
    for row in blocked:
        _assert_condition_witness(text, row, 'reference_scope_abstention')


def test_conditional_reference_itself_is_not_a_temporal_reference_closure(monkeypatch, tmp_path):
    text = LEAD + '상계의 의사표시 서류를 검토한 경우, 변제공탁을 완료하였으므로' + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace
    assert all('contextual_proposition' not in row for row in trace['requirements'])


@pytest.mark.parametrize('prior', ['절차가 유효하다면 서류를 검토한다. ', '서류를 검토한 경우 기록을 남긴다. '])
def test_condition_in_an_independent_prior_sentence_is_not_document_global(monkeypatch, tmp_path, prior):
    text = prior + LEAD + REFERENCE_ACT + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace


@pytest.mark.parametrize('prefix,act', [
    ('절차가 유효하다면, ', '변제공탁 서류를 확인한 뒤 변제공탁을 완료하였으므로'),
    ('서류를 검토한 경우, ', '변제공탁 기록을 검토한 후 변제공탁을 이행하였으므로'),
    ('절차가 유효하다면; ', '변제공탁 내역을 정리한 다음 변제공탁을 마쳤으므로'),
])
def test_old_same_identity_proof_also_requires_closed_conditional_scope(monkeypatch, tmp_path, prefix, act):
    text = LEAD + prefix + act + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace
    assert all('contextual_resolution' not in row for row in trace['requirements'])
    blocked = [row for row in trace['requirements'] if 'contextual_resolution_scope_abstention' in row]
    assert blocked
    for row in blocked:
        _assert_condition_witness(text, row, 'contextual_resolution_scope_abstention')


def _assert_condition_witness(text, row, key):
    evidence = row[key]
    assert row['state'] == evidence['original_state'] == 'UNCERTAIN'
    assert row['reason'] == 'CHANGED_ARGUMENT'
    assert evidence['reason'] == 'PRECEDING_CONDITION_UNCLOSED'
    assert evidence['conditional_attachment'] == 'UNKNOWN'
    first, end = evidence['condition_witness_span']
    assert text[first:end] in {'다면', '한 경우'}
    first, end = evidence['reset_boundary_span']
    assert text[first:end] in {',', ';'}
    assert evidence['scope_start'] <= evidence['condition_witness_span'][0]


@pytest.mark.parametrize('prior,closed', [
    ('절차가 유효하다면 서류를 검토한다. ', True),
    ('절차가 유효하다면. ', False),
])
def test_shared_source_index_requires_actual_finite_and_sentence_terminal(prior, closed):
    text = prior + REFERENCE_ACT
    signals = legal_rules.load_defense_groups()['structural_signals']
    rows = legal_rules._defense_requirement_observations(
        text, signals['stated_requirements'], signals['limited_conclusions'],
        signals.get('requirement_polarities', {}))
    original = [(row['state'], row['reason'], row['span'], row['predicate_span']) for row in rows]
    resolved = legal_rules._contextual_requirement_resolution(text, rows, [])
    assert [(row['state'], row['reason'], row['span'], row['predicate_span']) for row in rows] == original
    context = next(row for row in rows if row['state'] == 'UNCERTAIN')
    if closed:
        assert resolved
        proof = context['contextual_proposition']
        witness = proof['sentence_closure_witness']
        first, end = witness['boundary_span']
        assert text[first:end] == '.'
        assert proof['condition_scope_start'] == end
        first, end = witness['finite_span']
        assert text[first:end] == '한다'
    else:
        assert not resolved
        assert 'contextual_proposition' not in context
        evidence = context['reference_scope_abstention']
        assert evidence['conditional_attachment'] == 'UNKNOWN'
        assert evidence['scope_start'] == 0
        first, end = evidence['condition_witness_span']
        assert text[first:end] == '다면'


@pytest.mark.parametrize('separator', ['\n', ',\n'])
def test_formatting_newline_does_not_certify_conditional_closure(monkeypatch, tmp_path, separator):
    text = LEAD + '절차가 유효하다면' + separator + REFERENCE_ACT + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace
    blocked = [row['reference_scope_abstention'] for row in trace['requirements']
               if 'reference_scope_abstention' in row]
    assert blocked
    assert all(row['conditional_attachment'] == 'UNKNOWN' for row in blocked)


@pytest.mark.parametrize('role', ['REPORTED', 'UNCERTAIN'])
def test_quote_finite_and_terminal_cannot_close_authored_condition(role):
    prior = '절차가 유효하다면 “서류를 검토하였다. ”, '
    text = prior + REFERENCE_ACT
    signals = legal_rules.load_defense_groups()['structural_signals']
    rows = legal_rules._defense_requirement_observations(
        text, signals['stated_requirements'], signals['limited_conclusions'],
        signals.get('requirement_polarities', {}))
    quotations = [{'span': [prior.index('“'), prior.index('”') + 1], 'role': role}]
    assert not legal_rules._contextual_requirement_resolution(text, rows, quotations)
    context = next(row for row in rows if row['state'] == 'UNCERTAIN')
    assert context['reference_scope_abstention']['conditional_attachment'] == 'UNKNOWN'


def test_reported_finite_and_terminal_cannot_close_authored_condition():
    text = '절차가 유효하다면 서류를 검토한다고 판시하였다. ' + REFERENCE_ACT
    signals = legal_rules.load_defense_groups()['structural_signals']
    rows = legal_rules._defense_requirement_observations(
        text, signals['stated_requirements'], signals['limited_conclusions'],
        signals.get('requirement_polarities', {}))
    assert not legal_rules._contextual_requirement_resolution(text, rows, [])
    context = next(row for row in rows if row['state'] == 'UNCERTAIN')
    assert context['reference_scope_abstention']['conditional_attachment'] == 'UNKNOWN'
