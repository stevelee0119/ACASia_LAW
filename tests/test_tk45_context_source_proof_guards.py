"""Public source-cost and nominal argument-identity guards, before rework."""
import pytest

from packages.legal_engine import legal_rules
from tests.test_tk45_clause_effect_contract import LEAD, _trace_pipeline
from tests.test_tk45_authored_predicate_scope import LIMIT


@pytest.mark.parametrize('body', [
    '이 사건 변제공탁 자료를 검토한 뒤 별건 변제공탁을 완료하였으므로',
    '변제공탁 자료를 검토한 뒤 다른 사건의 변제공탁을 완료하였으므로',
    '피고의 변제공탁 자료를 검토한 뒤 원고의 변제공탁을 완료하였으므로',
    '해당 변제공탁 자료를 검토한 뒤 해당 변제공탁을 완료하였으므로',
])
def test_unproved_event_or_possessor_qualification_keeps_verification(monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
    assert all('contextual_resolution' not in row for row in trace['requirements'])


@pytest.mark.parametrize('prefix', ['', '피고는 '])
def test_unqualified_requirement_in_shared_grammatical_subject_scope_stays_normal(monkeypatch, tmp_path, prefix):
    body = prefix + '변제공탁 자료를 검토한 뒤 변제공탁을 완료하였으므로'
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert not findings, trace
    assert any('contextual_resolution' in row for row in trace['requirements'])


@pytest.mark.parametrize('count', [250, 500, 1000])
def test_repeated_shared_endpoint_indexes_words_once_without_suffix_copies(monkeypatch, count):
    text = '변제공탁 서류를 ' * count + '확인한 뒤 변제공탁을 완료하였으므로'
    signals = legal_rules.load_defense_groups()['structural_signals']
    observations = legal_rules._defense_requirement_observations(
        text, signals['stated_requirements'], signals['limited_conclusions'],
        signals.get('requirement_polarities', {}))
    original = legal_rules.re.finditer
    scanned = []

    def measured(pattern, source, *args, **kwargs):
        if pattern == r'[가-힣]+':
            scanned.append(len(source))
        return original(pattern, source, *args, **kwargs)

    monkeypatch.setattr(legal_rules.re, 'finditer', measured)
    resolved = legal_rules._contextual_requirement_resolution(text, observations, [])
    assert len(resolved) <= 1
    assert scanned and sum(scanned) <= len(text)
