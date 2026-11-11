"""Public synthetic checks: pending quote comparison must not erase other evidence."""
import asyncio
import pytest
import test_lv_contract_review_eval as t
from packages.legal_engine.argument_validity_verifier import summarize_argument_findings

PAIRS = [('매수인', '대금지급'), ('임차인', '차임지급'), ('수급인', '공사완성')]

@pytest.mark.parametrize('party,duty', PAIRS)
@pytest.mark.parametrize('source_field', ['full_text', 'summary'])
def test_real_distortion_keeps_finding_and_summary(party, duty, source_field):
    holding = f'{party}의 {duty} 의무가 계약 해제로 소멸하였'
    source = (f'원심은 {holding}다고 판단하였다. '
              '그러나 이러한 원심의 판단에는 계약 해제 요건에 관한 법리를 오해하여 판결에 영향을 미친 위법이 있다.')
    claim = f'대법원은 {holding}다고 인정하였다.'
    c = t._citation(context=claim, attributes={'case_claim': claim})
    result = t._verifier([dict(case_number=c.case_number, court='대법원', **{source_field: source})]).verify_citations([c])
    assert any(f.confidence_features.get('verdict_label') == 'REVERSED_REMAND_CONFUSION' for f in result.findings)
    table = asyncio.run(t.verify_argument_validity(t._doc(claim), [c], result.data['verdicts'], []))
    assert table.rows[0].basis == 'CONTRADICTION'
    assert any(str(f.type) == 'LEGAL_ARGUMENT_INVALID' and str(f.status) == 'CONTRADICTED' for f in table.findings)
    assert summarize_argument_findings(table.findings, table.overall_validity_summary)['contradicted_count'] == 1

@pytest.mark.parametrize('party,duty', PAIRS)
@pytest.mark.parametrize('semantic_status,expected_basis', [('CONTRADICTED', 'CONTRADICTION'), ('DISTINGUISHABLE', 'DISTINGUISHABLE')])
@pytest.mark.parametrize('quote_level', ['VERIFIED', 'UNVERIFIED'])
def test_validated_semantic_evidence_survives_quote_pending(party, duty, semantic_status, expected_basis, quote_level):
    source = f'{party}의 {duty} 의무는 계약 해제 여부와 별도로 검토한다.'
    c = t._citation(context='인용한 법리를 이 사건 주장에 적용합니다.')
    verdict = dict(citation_id='c', status='PARTIALLY_VERIFIED',
                   levels={'level1': 'VERIFIED', 'level3': quote_level},
                   review={'quote_diff_status': 'UNVERIFIED' if quote_level == 'UNVERIFIED' else 'EXACT_MATCH'},
                   official_record={'case_number': c.case_number, 'full_text': source})
    semantic = dict(citation_id='c', status=semantic_status, model_executed=True,
                    source_quotes_validated=True, evidence_quotes=[source], reason='검증된 근거에 따른 별도 의미 검토 결과')
    router = t._CaptureRouter()
    table = asyncio.run(t.verify_argument_validity(t._doc(c.context), [c], [verdict], [],
                                                   semantic_reviews=[semantic], router=router))
    assert table.rows[0].basis == expected_basis
    assert any(str(f.type) == 'LEGAL_ARGUMENT_INVALID' for f in table.findings)
    if semantic_status == 'CONTRADICTED':
        assert summarize_argument_findings(table.findings, table.overall_validity_summary)['contradicted_count'] == 1
    assert router.requests, 'Independent evidence must retain the existing advisory review route.'
