"""Public leading-condition scope controls before the minimal guard."""
import pytest

from tests.test_tk45_clause_effect_contract import LEAD, _trace_pipeline
from tests.test_tk45_authored_predicate_scope import LIMIT

REFERENCE_ACT = '상계의 의사표시 서류를 참조한 뒤 변제공탁을 완료하였으므로'


@pytest.mark.parametrize('prefix', ['절차가 유효하다면, ', '서류를 검토한 경우, ', '절차가 유효하다면; '])
def test_preceding_separator_does_not_close_condition_on_reference_and_actual_act(monkeypatch, tmp_path, prefix):
    text = LEAD + prefix + REFERENCE_ACT + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace
    assert all('reference_selection_support' not in row for row in trace['requirements'])


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
