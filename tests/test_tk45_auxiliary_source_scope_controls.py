"""Exact certified predicate consumption never removes genuine scope breaks."""
from copy import deepcopy

import pytest

from tests.test_tk45_clause_effect_contract import LEAD, _trace_pipeline
from tests.test_tk45_authored_predicate_scope import LIMIT


@pytest.mark.parametrize('body', [
    '상계의 의사표시를 해 놓은 이후 원고는 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 놓은 이후 놓은 변제공탁을 완료하였으므로',
    '상계의 의사표시를 놓은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 “놓은” 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 놓은 이후라면 변제공탁을 완료하였으므로',
    '상계의 의사표시를 해 놓은 이후라고 주장하며 변제공탁을 완료하였으므로',
    '절차가 유효하다면; 상계의 의사표시를 해 놓은 이후 변제공탁을 완료하였으므로',
])
def test_source_word_elsewhere_actor_quote_report_or_condition_is_not_ignored(monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
    assert all('case_bound_event_assertion' not in row for row in trace['requirements'])


def test_all_original_observation_fields_are_preserved(monkeypatch, tmp_path):
    from packages.legal_engine import legal_rules

    originals = []
    observe = legal_rules._defense_requirement_observations

    def snapshot(*args, **kwargs):
        rows = observe(*args, **kwargs)
        originals.extend(deepcopy(rows))
        return rows

    monkeypatch.setattr(legal_rules, '_defense_requirement_observations', snapshot)
    text = LEAD + '상계의 의사표시를 해 놓은 이후 변제공탁을 완료하였으므로' + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings
    assert len(originals) == len(trace['requirements'])
    for before, after in zip(originals, trace['requirements']):
        assert all(after[key] == value for key, value in before.items())
    first = next(row for row in trace['requirements'] if row['state'] == 'UNCERTAIN')
    support = first['case_bound_event_selection_support']
    later = trace['requirements'][support['later_observation_index']]
    assert first['requirement_identity'] != later['requirement_identity']
    assert not support['different_acts_merged'] and not support['later_act_certifies_first']


def test_nonmatching_source_predicate_span_does_not_remove_topic_match(monkeypatch, tmp_path):
    from packages.legal_engine import legal_rules

    original = legal_rules.case_bound_event_evidence

    def conflicting_span(*args):
        proof = original(*args)
        if proof:
            proof['auxiliary_span'] = proof['head_span']
        return proof

    monkeypatch.setattr(legal_rules, 'case_bound_event_evidence', conflicting_span)
    findings, _ = _trace_pipeline(monkeypatch, tmp_path,
        LEAD + '상계의 의사표시를 해 놓은 이후 변제공탁을 완료하였으므로' + LIMIT)
    assert findings


def test_other_scope_origin_at_same_source_start_still_blocks(monkeypatch, tmp_path):
    import re
    from packages.legal_engine import legal_rules

    original = legal_rules._RESOLUTION_ATTRIBUTION_RE
    monkeypatch.setattr(legal_rules, '_RESOLUTION_ATTRIBUTION_RE',
                        re.compile('(?:' + original.pattern + ')|놓은'))
    findings, trace = _trace_pipeline(monkeypatch, tmp_path,
        LEAD + '상계의 의사표시를 해 놓은 이후 변제공탁을 완료하였으므로' + LIMIT)
    assert findings
    assert all('case_bound_event_assertion' not in row for row in trace['requirements'])
