"""Public synthetic integration regressions for the second LV evaluation."""
import asyncio
import json
import pytest
import test_lv_contract_review_eval as t

@pytest.mark.parametrize('claim', ['제소기간을 검토한다.', '90일 기간을 주장한다.', '기간 준수 여부가 쟁점이다.'])
def test_lv01_claim_words_do_not_establish_legal_deadline(claim):
    result=t._calculate_dynamic_deadline(t._doc('원처분일: 2025. 3. 1.\n소제기일: 2025. 4. 9.'),claim)
    assert '39일' in result
    assert '기간 준수' not in result and '각하 위험' not in result

@pytest.mark.parametrize('tail', ['소제기일: 2025. 4. 9. 예정', '2025. 4. 9. 본 소를 제기할 경우', '심판청구일: 2025. 4. 9.'])
def test_lv01_event_role_and_modality_are_not_actual_filing(tail):
    result=t._calculate_dynamic_deadline(t._doc('원처분일: 2025. 3. 1.\n'+tail),'제소기간 검토')
    assert '보류' in result
    assert '기간 준수' not in result and '각하 위험' not in result

@pytest.mark.parametrize('prefix_count',[14,18,20])
def test_lv02_real_extractor_coordinate_reaches_actual_model(prefix_count):
    from packages.legal_engine.citation_extractor import extract_citations
    raw='대법원 2021다67283 판결'
    text='사건 경위를 기록합니다. '*prefix_count+'\n'+raw+'에 따라 책임이 인정됩니다.\n별도 쟁점은 관할입니다.\n'+'추가 설명입니다. '*25
    doc=t._doc(text); citations=extract_citations(doc); assert len(citations)==1
    c=citations[0];router=t._CaptureRouter()
    out=asyncio.run(t.verify_argument_validity(doc,[c],[{'citation_id':c.citation_id,'status':'NOT_FOUND','levels':{'level1':'NOT_FOUND'}}],[],router=router))
    assert raw in out.rows[0].evaluation_context
    sent=json.loads(router.requests[0].user)['items'][0]['surrounding_context_and_claim']
    assert raw in sent and '책임이 인정됩니다' in sent

@pytest.mark.parametrize('repeat',[12,18,24])
def test_lv02_extractor_window_must_not_silently_drop_adjacent_exception(repeat):
    from packages.legal_engine.citation_extractor import extract_citations
    raw='대법원 2021다67283 판결'
    exception='다만 서면 특약으로 채무가 면제된 경우는 제외합니다.'
    text=raw+'에 따라 '+ '계약의 조건을 모두 확인하고 '*repeat+'책임을 검토합니다. '+exception
    assert len(text)<1000
    doc=t._doc(text);cs=extract_citations(doc);assert len(cs)==1
    router=t._CaptureRouter()
    out=asyncio.run(t.verify_argument_validity(doc,cs,[{'citation_id':cs[0].citation_id,'status':'NOT_FOUND','levels':{'level1':'NOT_FOUND'}}],[],router=router))
    sent=json.loads(router.requests[0].user)['items'][0]['surrounding_context_and_claim']
    assert exception in sent and exception in out.rows[0].evaluation_context

@pytest.mark.parametrize('quote', ['집행 절차의 단계별 송달 방법을 검토한다.', '관할 구역의 획정과 소송 비용의 부담을 확인한다.', '문서 보관 기간 및 신청서의 서식을 정한다.'])
def test_quote_low_overlap_is_not_proof_of_fabrication(quote):
    from packages.legal_engine.quote_diff import categorize_quote_diff
    full='매수인은 계약상 대금지급 의무를 부담하며 이행 조건을 확인하여야 한다.'
    result=categorize_quote_diff(quote,full)
    assert result['status']!='FABRICATED_QUOTE'
    assert 'FABRICATED_QUOTE' not in result['diff_categories']
    v=t._verifier([dict(case_number='2021다67283',court='대법원',full_text=full)]).verify_case(t._citation(quoted_text=quote))
    assert not any('FABRICATED_QUOTE' in f.tags for f in v.findings)

@pytest.mark.parametrize('party,duty',[('매수인','대금지급'),('임차인','차임지급'),('수급인','공사완성')])
def test_lv05_explicit_lower_court_history_is_not_supreme_adoption(party,duty):
    holding=f'{party}의 {duty} 의무가 계약 해제로 소멸하였'
    full=f'원심은 {holding}다고 판단하였다. 그러나 이러한 원심의 판단에는 계약 해제 요건에 관한 법리를 오해하여 판결에 영향을 미친 위법이 있다.'
    claim=f'원심은 {holding}다고 판단하였다. 이 내용은 사건 경과의 설명이다.'
    c=t._citation(attributes={'case_claim':claim},context=claim)
    result=t._verifier([dict(case_number=c.case_number,court='대법원',full_text=full)]).verify_citations([c])
    assert not any(f.confidence_features.get('verdict_label')=='REVERSED_REMAND_CONFUSION' for f in result.findings)

@pytest.mark.parametrize('number',['2021다67283','2020다67284','2019다67285'])
def test_lv06_unknown_source_does_not_become_quote_mismatch(number):
    c=t._citation(case_number=number,canonical_case_number=number,context='해당 판결을 근거로 책임을 검토한다.')
    result=t._verifier([]).verify_citations([c])
    out=asyncio.run(t.verify_argument_validity(t._doc(c.context),[c],result.data['verdicts'],[]))
    guidance=out.rows[0].actionable_guidance
    assert guidance['action_type']=='SOURCE_VERIFICATION'
    assert '원문과 차이가 있습니다' not in guidance['guidance_summary']

@pytest.mark.parametrize('text',[
    '이 계약은 장래 불이행 시 계약을 해제할 수 있다는 일반 조항을 둔다.',
    '원고는 부당이득반환을 청구하지 않는다. 본건은 계약대금 청구이다.',
    '원고는 불법행위 손해배상을 청구하지 않는다. 본건은 약정금 청구이다.',
])
def test_lv06_nonclaims_are_not_omitted_elements(text):
    from packages.legal_engine.actionable_guidance import check_cause_of_action_elements
    assert not check_cause_of_action_elements(t._doc(text))

def test_lv06_impossible_number_row_does_not_raise():
    from packages.legal_engine.argument_validity_verifier import _fabrication_row
    c=t._citation(case_number='2099다67283',canonical_case_number='2099다67283',context='사건번호의 정정을 확인한다.')
    row=_fabrication_row(c)
    assert row.authority_id
    assert row.verification_status=='SUSPICIOUS'
    assert row.actionable_guidance['action_tier']!='CONFIRMED_ERROR'

@pytest.mark.parametrize('court,number',[('대법원','2021다67283'),('헌법재판소','2021헌바672'),('서울중앙지방법원','2021가단67283')])
def test_lv03_court_level_does_not_attest_exhaustive_coverage(court,number):
    from packages.legal_engine.authority_status import is_covered_precedent_scope
    assert not is_covered_precedent_scope(t._citation(court=court,case_number=number,canonical_case_number=number))
