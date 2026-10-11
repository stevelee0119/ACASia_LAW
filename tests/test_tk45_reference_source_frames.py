"""Generic source/morphology checks, independent of legal requirement words."""
import json
import pytest

from packages.legal_engine.reference_propositions import (
    APPLICATION_ROLES, SOURCE_SENSES, reference_frame_evidence,
)


@pytest.mark.parametrize('modifier,tail', [
    ('실험', ' 서류를 검토한 뒤'),
    ('분류', ' 자료를 참조한 후'),
    ('도감', ' 자료를 검토하였으므로'),
    ('연구', ' 서류를 참조했습니다'),
])
def test_generic_information_frame_requires_observed_case_and_source_closure(modifier, tail):
    text = modifier + tail
    proof = reference_frame_evidence(text, len(modifier), len(text))
    assert proof and proof['kind'] == 'REFERENCE_NON_REQUIREMENT_ASSERTION'
    assert text[slice(*proof['object_case_span'])] in {'을', '를'}
    assert text[slice(*proof['closure_span'])] in {'뒤', '후', '으므로', '습니다'}
    assert proof['supports_requirement_fulfillment'] is False
    assert proof['underlying_facts_verified'] is False
    assert proof['legal_sufficiency_verified'] is False
    assert proof['mapping_authority'] == 'APPLICATION_NOT_NIKL_CLASSIFICATION'
    assert json.loads(json.dumps(proof)) == proof


@pytest.mark.parametrize('tail', [
    ' 서류 검토한 뒤', ' 서류가 검토한 뒤', ' 서류를 검토한 사람이',
    ' 자료를 검토한 적이 없으나', ' 자료를 검토하지 않고',
    ' 자료를 검토할 계획을 세웠으므로', ' 자료를 검토신청한 뒤',
    ' 자료를 참조요청하였으므로', ' 자료를 검토한다',
    ' 자료를 완료하였으므로', ' 실험을 검토한 뒤',
    ' 존재를 확인한 뒤', ' 효력을 검토한 뒤',
    ' 자료가 사실임을 확인한 뒤', ' 기록을 검토한 뒤',
])
def test_missing_case_wrong_governor_or_unknown_sense_remains_unknown(tail):
    assert reference_frame_evidence(tail, 0, len(tail)) is None


def test_individual_source_senses_and_application_roles_are_separate():
    assert {row['lemma'] for row in SOURCE_SENSES} == {'참조하다', '검토하다', '서류', '자료', '확인하다', '기록'}
    record_senses = [row for row in SOURCE_SENSES if row['lemma'] == '기록']
    assert [row['sense_number'] for row in record_senses] == [1, 2]
    assert {APPLICATION_ROLES[row['source_sense_key']] for row in record_senses} == {'PRESERVED_INFORMATION', 'PERFORMANCE_RECORD'}
    for row in SOURCE_SENSES:
        assert row['definition'] and row['hanja'] and row['retrieved_on'] == '2026-10-11'
        assert row['source'].startswith('https://krdict.korean.go.kr/')
        assert 'category' not in row and 'role' not in row


@pytest.mark.parametrize('tail,reference', [(' 자료를 검토한 뒤', True), ('을 완료하였으므로', False)])
def test_nonlegal_event_and_information_txt_do_not_create_legal_requirements(monkeypatch, tmp_path, tail, reference):
    from tests.test_tk45_clause_effect_contract import _trace_pipeline

    modifier = '실험'
    text = modifier + tail + ' 연구를 계속하였다.'
    proof = reference_frame_evidence(text, len(modifier), len(modifier + tail))
    assert bool(proof) is reference
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings and not trace['requirements']
