"""Independent generic event/source tests, without legal noun disambiguation."""
import json
import pytest

from packages.legal_engine.event_temporal_propositions import (
    APPLICATION_MAPPINGS, TEMPORAL_SOURCE_SENSES, case_bound_event_evidence,
)


@pytest.mark.parametrize('argument,case,predicate', [
    ('실험', '을', '완료한'), ('학습', '을', '완수한'), ('수업', '을', '완결한'),
])
def test_generic_original_event_has_its_own_source_proof_without_another_act(argument, case, predicate):
    text = argument + case + ' ' + predicate + ' 이후'
    end = len(argument)
    proof = case_bound_event_evidence(text, [0, end], [end, end + 1], len(text))
    assert proof
    assert text[slice(*proof['argument_span'])] == argument
    assert text[slice(*proof['case_span'])] == case
    assert text[slice(*proof['predicate_span'])] == predicate
    assert text[slice(*proof['morphology_span'])] == '한'
    assert text[slice(*proof['temporal_span'])] == '이후'
    assert proof['supports_authored_event_assertion'] is True
    assert proof['underlying_facts_verified'] is False
    assert proof['legal_sufficiency_verified'] is False
    assert all(row['category'] == 'COMPLETION' for row in proof['selected_source_senses'])
    assert json.loads(json.dumps(proof)) == proof


@pytest.mark.parametrize('tail', [
    '완료할 이후', '완료하는 이후', '완료하다 이후', '완료한',
    '완료한 이후라고 가정하면', '완료한 이후의 계획', '완료한 이후라도',
    '일부 완료한 이후', '완료하지 않은 이후', '완료한 사실을 확인한 이후',
    '계획한 이후', '준비한 이후', '중단한 이후', '포기한 이후',
    '수행한 이후', '완료한것 이후', '완료한사람 이후',
])
def test_dynamic_past_and_relative_time_must_be_exact_attached_source(tail):
    text = '실험을 ' + tail
    assert case_bound_event_evidence(text, [0, 2], [2, 3], len(text)) is None


def test_temporal_grammar_senses_are_separate_from_application_mapping():
    assert len(TEMPORAL_SOURCE_SENSES) == 3
    assert {(row['lemma'], row['homonym_number'], row['sense_number'])
            for row in TEMPORAL_SOURCE_SENSES} == {('-ㄴ', 3, 1), ('-ㄴ', 3, 2), ('이후', 0, 2)}
    for row in TEMPORAL_SOURCE_SENSES:
        assert row['definition'] and row['source'] and row['retrieved_on']
        assert 'category' not in row
        assert row['source_sense_key'] in APPLICATION_MAPPINGS
    assert not any(row['lemma'] == '-ㄴ-' or row['homonym_number'] == 2
                   for row in TEMPORAL_SOURCE_SENSES)
