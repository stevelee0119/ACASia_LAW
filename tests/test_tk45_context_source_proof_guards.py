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
    text = LEAD + body + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace
    assert all('contextual_resolution' not in row for row in trace['requirements'])
    contexts = [row for row in trace['requirements'] if 'contextual_resolution_abstention' in row]
    assert contexts
    for row in contexts:
        assert row['state'] == 'UNCERTAIN'
        proof = row['contextual_resolution_abstention']
        assert proof['reason'] == 'ARGUMENT_QUALIFIER_UNRESOLVED'
        assert proof['requirement_identity_only'] is True
        assert any(text[first:end].strip() for first, end in
                   (proof['context_prefix_span'], proof['realization_prefix_span']))
    assert any(row['state'] == 'POSITIVE' for row in trace['requirements'])


@pytest.mark.parametrize('prefix', ['', '피고는 '])
def test_unqualified_requirement_in_shared_grammatical_subject_scope_stays_normal(monkeypatch, tmp_path, prefix):
    body = prefix + '변제공탁 자료를 검토한 뒤 변제공탁을 완료하였으므로'
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert not findings, trace
    contexts = [row for row in trace['requirements'] if 'contextual_resolution' in row]
    assert contexts
    for row in contexts:
        assert row['state'] == 'UNCERTAIN'
        proof = row['contextual_resolution']
        assert proof['unqualified_argument_attachment'] is True
        assert proof['original_state'] == 'UNCERTAIN'
        assert proof['underlying_facts_verified'] is False
        assert proof['legal_sufficiency_verified'] is False
        if prefix:
            first, end = proof['local_subject_span']
            assert (LEAD + body + LIMIT)[first:end] == prefix.strip()


@pytest.mark.parametrize('count', [250, 500, 1000])
def test_repeated_shared_endpoint_indexes_words_once_without_suffix_copies(monkeypatch, count):
    text = '변제공탁 서류를 ' * count + '확인한 뒤 변제공탁을 완료하였으므로'
    signals = legal_rules.load_defense_groups()['structural_signals']
    observations = legal_rules._defense_requirement_observations(
        text, signals['stated_requirements'], signals['limited_conclusions'],
        signals.get('requirement_polarities', {}))
    original = legal_rules.re.finditer
    scanned = []
    index_scanned = []

    class IndexedPattern:
        def __init__(self, pattern):
            self.pattern = pattern

        def finditer(self, source, *args, **kwargs):
            index_scanned.append(len(source))
            return self.pattern.finditer(source, *args, **kwargs)

        def __getattr__(self, name):
            return getattr(self.pattern, name)

    for name in ('_REQUIREMENT_CLAUSE_END_RE', '_FINITE_PREDICATE_RE',
                 '_ARGUMENT_CASE_RE', '_LOCAL_SUBJECT_RE',
                 '_RESOLUTION_SCOPE_BREAK_RE', '_RESOLUTION_ATTRIBUTION_RE'):
        monkeypatch.setattr(legal_rules, name, IndexedPattern(getattr(legal_rules, name)))

    def measured(pattern, source, *args, **kwargs):
        if pattern == r'[가-힣]+':
            scanned.append(len(source))
        return original(pattern, source, *args, **kwargs)

    monkeypatch.setattr(legal_rules.re, 'finditer', measured)
    resolved = legal_rules._contextual_requirement_resolution(text, observations, [])
    assert len(resolved) <= 1
    assert scanned and sum(scanned) <= len(text)
    # Count requested full-source ranges for all six compiled index passes
    # plus the word pass; this does not claim regex CPU or total pipeline cost.
    assert len(index_scanned) == 6
    assert sum(index_scanned) + sum(scanned) == 7 * len(text)
