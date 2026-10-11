"""Design-first actual-TXT controls for the original case-bound event clause."""
import pytest

from tests.test_tk45_clause_effect_contract import LEAD, _trace_pipeline
from tests.test_tk45_authored_predicate_scope import LIMIT


@pytest.mark.parametrize('first,later,predicate', [
    ('상계의 의사표시를 완료한 이후', '변제공탁을 완료하였으므로', '완료한'),
    ('변제공탁을 완수한 이후', '상계의 의사표시를 완료하였으므로', '완수한'),
    ('변제공탁을 완결한 이후', '상계의 의사표시를 완료하였으므로', '완결한'),
])
def test_first_case_bound_past_completion_is_independent_of_later_event(monkeypatch, tmp_path, first, later, predicate):
    text = LEAD + first + ' ' + later + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    original = [row for row in trace['requirements'] if row['state'] == 'UNCERTAIN']
    assert original and all(row['reason'] == 'CHANGED_ARGUMENT' for row in original)
    assert all(row['event_frame']['case_span'] and not row.get('predicate_chain') for row in original)
    assert not findings, trace
    for row in original:
        proof = row['case_bound_event_assertion']
        assert proof['kind'] == 'SOURCE_BOUND_PAST_EVENT_ASSERTION'
        assert row['state'] == proof['original_state'] == 'UNCERTAIN'
        assert row['reason'] == proof['original_reason'] == 'CHANGED_ARGUMENT'
        assert proof['argument_span'] == row['event_frame']['argument_span']
        assert proof['case_span'] == row['event_frame']['case_span']
        assert text[slice(*proof['predicate_span'])] == predicate
        assert text[slice(*proof['morphology_span'])] == proof['observed_morphology'] == '한'
        assert text[slice(*proof['temporal_span'])] == '이후'
        assert proof['tense'] == 'PAST_ADNOMINAL'
        assert proof['underlying_facts_verified'] is False
        assert proof['legal_sufficiency_verified'] is False
        assert proof['mapping_authority'] == 'APPLICATION_NOT_NIKL_CLASSIFICATION'
        assert proof['selected_source_senses']
        assert proof['authored'] is True
        support = row['case_bound_event_selection_support']
        assert support['different_acts_merged'] is False
        assert support['later_act_certifies_first'] is False
        assert all(row['requirement_identity'] != target['requirement_identity']
                   for target in trace['requirements'] if target['state'] == 'POSITIVE')


@pytest.mark.parametrize('body', [
    '상계의 의사표시를 완료할 때 변제공탁을 완료하였으므로',
    '상계의 의사표시를 완료할 계획을 세운 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 일부 완료한 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 완료한 이후라면 변제공탁을 완료하였으므로',
    '상계의 의사표시를 하지 않았으나 변제공탁을 완료하였으므로',
    '피고는 상계의 의사표시를 완료한 이후 원고는 변제공탁을 완료하였으므로',
    '상계의 의사표시를 완료한 사실을 확인한 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시가 적법한지를 검토한 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 완료한 배경에서 변제공탁을 완료하였으므로',
    '상계의 의사표시 서류를 완료한 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 중단한 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 완료하지 않은 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 완료한 이후 변제공탁을 하였으므로',
    '절차가 유효하다면, 상계의 의사표시를 완료한 이후 변제공탁을 완료하였으므로',
    '절차가 유효하다면; 상계의 의사표시를 완료한 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 완료한 이후라고 가정하면 변제공탁을 완료하였으므로',
    '내일 상계의 의사표시를 완료한 이후 변제공탁을 완료하였으므로',
    '상계의 의사표시를 완료한 이후의 계획을 검토한 뒤 변제공탁을 완료하였으므로',
    '상계의 의사표시를 완료한 이후 상대방이 변제공탁을 완료하였으므로',
    '일부 상계의 의사표시를 완료한 이후 변제공탁을 완료하였으므로',
])
def test_case_or_temporal_words_do_not_certify_unknown_or_denied_event(monkeypatch, tmp_path, body):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + body + LIMIT)
    assert findings, trace
    assert all('case_bound_event_assertion' not in row for row in trace['requirements'])


def test_another_unknown_requirement_is_not_removed_by_two_actual_acts(monkeypatch, tmp_path):
    text = (LEAD + '수령거절 여부를 확인한 뒤 상계의 의사표시를 완료한 이후 '
            + '변제공탁을 완료하였으므로' + LIMIT)
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace
    assert any(row['state'] == 'UNCERTAIN' and 'case_bound_event_assertion' not in row
               for row in trace['requirements'])


def test_reported_first_event_is_not_an_authored_completion_certificate(monkeypatch, tmp_path):
    text = (LEAD + '상대방은 “상계의 의사표시를 완료한 이후”라고 주장하나 '
            + '변제공탁을 완료하였으므로' + LIMIT)
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    assert all('case_bound_event_assertion' not in row for row in trace['requirements'])


def test_quoted_later_event_cannot_certify_selection_of_an_unresolved_first_event(monkeypatch, tmp_path):
    text = (LEAD + '상계의 의사표시를 완료한 이후 상대방은 “변제공탁을 완료하였다”라고 주장하나'
            + LIMIT)
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace


def test_case_bound_observation_is_not_the_nominal_information_object_frame(monkeypatch, tmp_path):
    from packages.legal_engine import legal_rules

    original = legal_rules.reference_frame_evidence
    calls = []

    def measured(*args):
        calls.append(args[1:])
        return original(*args)

    monkeypatch.setattr(legal_rules, 'reference_frame_evidence', measured)
    text = LEAD + '상계의 의사표시를 완료한 이후 변제공탁을 완료하였으므로' + LIMIT
    _, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    context = next(row for row in trace['requirements'] if row['state'] == 'UNCERTAIN')
    assert context['reason'] == 'CHANGED_ARGUMENT'
    assert context['event_frame']['argument_binding'] == 'OBSERVED_CASE_ARGUMENT'
    assert context['event_frame']['case_span']
    first, end = context['predicate_span']
    assert legal_rules._CONTEXT_ARGUMENT_RE.match(text, first, end) is None
    assert calls == []


@pytest.mark.parametrize('length', [8000, 16000, 32000])
def test_case_attachment_actual_txt_requested_ranges_are_local(monkeypatch, tmp_path, length):
    from packages.legal_engine import event_temporal_propositions

    original = event_temporal_propositions._ATTACHMENT
    requested = []

    class Measured:
        def fullmatch(self, text, start, end):
            requested.append(end - start)
            return original.fullmatch(text, start, end)

    monkeypatch.setattr(event_temporal_propositions, '_ATTACHMENT', Measured())
    block = LEAD + '상계의 의사표시를 완료한 이후 변제공탁을 완료하였으므로' + LIMIT + ' '
    text = block * (length // len(block))
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace
    assert requested and sum(requested) <= len(text)
    assert max(requested) <= len(' 완료한 이후 ')
