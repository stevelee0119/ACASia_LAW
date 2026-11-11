"""Public synthetic checks for still-open contracts from round 3."""
import asyncio
import pytest
import test_lv_contract_review_eval as t

@pytest.mark.parametrize('following', ['면담은 미정이다.', '추가 자료는 제출할 예정이다.', '검토할 경우 별도로 협의한다.'])
def test_lv01_modality_is_local_to_filing_sentence(following):
    before='원처분일: 2025. 3. 1.\n2025. 4. 9. 본 소를 제기하였다.'
    assert '39일' in t._calculate_dynamic_deadline(t._doc(before),'기간 검토')
    assert '39일' in t._calculate_dynamic_deadline(t._doc(before+' '+following),'기간 검토')

@pytest.mark.parametrize('bad_span', [['0','20'], [0.0,20.0], 1])
def test_lv02_invalid_coordinate_type_does_not_abort_review(bad_span):
    raw='대법원 2021다67283 판결';claim=raw+'에 따라 책임을 검토합니다.'
    c=t._citation(context=claim,attributes={'reading_span':bad_span})
    router=t._CaptureRouter()
    result=asyncio.run(t.verify_argument_validity(t._doc(claim),[c],
        [{'citation_id':'c','status':'NOT_FOUND','levels':{'level1':'NOT_FOUND'}}],[],router=router))
    assert result.rows
    assert raw in result.rows[0].evaluation_context

@pytest.mark.parametrize('payload', [
    {'exhaustive':True,'verified_adapter':True,'source':'scourt','scope':'supreme_court'},
    {'exhaustive':'false','verified_adapter':'false','source':'glaw','scope':'precedent'},
    {'exhaustive':True,'verified_adapter':True,'source':'law.go.kr','scope':'precedent','checked_at':'2000-01-01'},
])
def test_lv03_self_asserted_adapter_flag_is_not_validated_evidence(payload):
    from packages.legal_engine.authority_status import is_covered_precedent_scope
    c=t._citation(attributes={'coverage_attestation':payload})
    assert not is_covered_precedent_scope(c)

@pytest.mark.parametrize('party', ['매수인','임차인','수급인'])
def test_quote_actual_verifier_does_not_reduce_changed_claim_to_excerpt(party):
    from packages.legal_engine.quote_diff import categorize_quote_diff
    official='채무자는 정해진 기한 안에 지급할 의무가 있으며 서면으로 합의한 특별한 사정이 없는 한 변제를 거절할 수 없다.'
    quote=party+'은 정해진 기한 안에 인도할 의무가 없으며 서면으로 합의한 사정이 없어도 계약을 해제할 수 있다.'
    helper=categorize_quote_diff(quote,official)
    assert helper['status']=='MODIFIED_QUOTE'
    assert 'NEGATION' in helper['diff_categories']
    c=t._citation(quoted_text=quote)
    v=t._verifier([dict(case_number=c.case_number,court='대법원',full_text=official)]).verify_case(c)
    # A concrete mismatch or explicit uncertainty is acceptable; an excerpt-only signal is not.
    assert v.levels['level3']!='TRUNCATED'
    assert v.review.get('quote_diff_categories')

@pytest.mark.parametrize('party,duty', [('매수인','대금지급'),('임차인','차임지급'),('수급인','공사완성')])
def test_lv05_other_matter_reversal_does_not_exempt_false_adoption(party,duty):
    holding=f'{party}의 {duty} 의무가 계약 해제로 소멸하였'
    full=f'원심은 {holding}다고 판단하였다. 그러나 이러한 원심의 판단에는 계약 해제 요건에 관한 법리를 오해하여 판결에 영향을 미친 위법이 있다.'
    claim=f'대법원은 {holding}다고 인정하였다.'
    def verdict(text):
        c=t._citation(context=text,attributes={'case_claim':text})
        out=t._verifier([dict(case_number=c.case_number,court='대법원',full_text=full)]).verify_citations([c])
        return any(f.confidence_features.get('verdict_label')=='REVERSED_REMAND_CONFUSION' for f in out.findings)
    assert verdict(claim)
    assert verdict('별개 사건의 처분은 취소되었다. '+claim)

@pytest.mark.parametrize('basis', ['UNKNOWN','SUSPENDED','NEW_UNKNOWN_STATUS'])
def test_lv06_unknown_state_stays_neutral_with_difference_metadata(basis):
    from packages.legal_engine.actionable_guidance import generate_actionable_guidance
    out=generate_actionable_guidance(basis=basis,cited_authority='대법원 2021다67283 판결',quote_diff_categories=['NUMERIC'])
    assert out['action_type']=='SOURCE_VERIFICATION'
    assert '원문과 차이가 있습니다' not in out['guidance_summary']
