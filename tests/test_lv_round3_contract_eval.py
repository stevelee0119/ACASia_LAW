"""Public tests for unresolved role, occurrence, and producer/consumer contracts."""
import asyncio
import json
import pytest
import test_lv_contract_review_eval as t

@pytest.mark.parametrize('role',['원처분일','통지일','소제기일'])
def test_lv01_conflicting_role_is_explicitly_suspended(role):
    text=f'{role}: 2025. 3. 1.\n{role}: 2025. 3. 3.\n'
    if role!='소제기일':text+='소제기일: 2025. 4. 9.'
    result=t._calculate_dynamic_deadline(t._doc(text),'제소기간 검토')
    assert '보류' in result
    assert '기간 준수' not in result and '각하 위험' not in result

@pytest.mark.parametrize('following',['면담 예정일은 추후 정한다.','추가 자료 제출 여부는 미정이다.','검토할 경우를 따로 기재한다.'])
def test_lv01_unrelated_next_line_does_not_negate_actual_filing(following):
    text='원처분일: 2025. 3. 1.\n소제기일: 2025. 4. 9.\n'+following
    result=t._calculate_dynamic_deadline(t._doc(text),'제소기간 검토')
    assert '39일' in result
    assert '기간 준수' not in result and '각하 위험' not in result

@pytest.mark.parametrize('number',['2021다67283','2020다67284','2019다67285'])
def test_lv02_second_occurrence_in_same_paragraph_reaches_model(number):
    raw=f'대법원 {number} 판결';first=raw+'에 따라 책임이 인정됩니다.';second=raw+'은 이 사건에 적용되지 않습니다.'
    text=first+' '+second;start=text.rindex(raw)
    c=t._citation(raw_text=raw,case_number=number,canonical_case_number=number,context=text,span=(start,start+len(raw)),attributes={'reading_span':[start,start+len(raw)]})
    router=t._CaptureRouter();out=asyncio.run(t.verify_argument_validity(t._doc(text),[c],[{'citation_id':'c','status':'NOT_FOUND','levels':{'level1':'NOT_FOUND'}}],[],router=router))
    sent=json.loads(router.requests[0].user)['items'][0]['surrounding_context_and_claim']
    assert '적용되지 않습니다' in sent
    assert '책임이 인정됩니다' not in out.rows[0].evaluation_context

@pytest.mark.parametrize('prefix',['다른 쟁점만 설명합니다.','본문의 일반 안내입니다.','자료 목록을 정리합니다.'])
def test_lv02_valid_range_without_anchor_is_not_trusted(prefix):
    raw='대법원 2021다67283 판결';claim=raw+'에 따라 책임을 검토합니다.';text=prefix+'\n'+claim
    c=t._citation(context=claim,span=None,attributes={'reading_span':[0,len(prefix)]})
    assert raw in t._extract_linked_claim(c,t._doc(text))

@pytest.mark.parametrize('attestation',[
    {'exhaustive':True},
    {'exhaustive':True,'source':'unverified'},
    {'exhaustive':True,'checked_at':'2001-01-01','scope':'different collection'},
])
def test_lv03_citation_attributes_are_not_adapter_attestation(attestation):
    from packages.legal_engine.authority_status import is_covered_precedent_scope
    assert not is_covered_precedent_scope(t._citation(attributes={'coverage_attestation':attestation}))

@pytest.mark.parametrize('suffix',['별도 절차의 기간은 783일이다.','독립된 표의 수량은 426개이다.','부록에서 다룬 금액은 952원이다.'])
def test_quote_unrelated_section_does_not_create_numeric_difference(suffix):
    from packages.legal_engine.quote_diff import categorize_quote_diff
    original='채무자는 정해진 기한 안에 지급할 의무가 있으며 서면으로 합의한 특별한 사정이 없는 한 변제를 거절할 수 없다.'
    quote='매수인은 정해진 기한 안에 인도할 의무가 없으며 서면으로 합의한 사정이 없어도 계약을 해제할 수 있다.'
    a=categorize_quote_diff(quote,original);b=categorize_quote_diff(quote,original+'\n'+suffix)
    assert 'NUMERIC' not in a['diff_categories']
    assert 'NUMERIC' not in b['diff_categories']

@pytest.mark.parametrize('party,duty',[('매수인','대금지급'),('임차인','차임지급'),('수급인','공사완성')])
def test_lv05_history_heading_does_not_suppress_explicit_false_adoption(party,duty):
    holding=f'{party}의 {duty} 의무가 계약 해제로 소멸하였'
    full=f'원심은 {holding}다고 판단하였다. 그러나 이러한 원심의 판단에는 계약 해제 요건에 관한 법리를 오해하여 판결에 영향을 미친 위법이 있다.'
    claim=f'대법원은 {holding}다고 인정하였다.'
    def out(txt):
        c=t._citation(context=txt,attributes={'case_claim':txt})
        return t._verifier([dict(case_number=c.case_number,court='대법원',full_text=full)]).verify_citations([c])
    assert any(f.confidence_features.get('verdict_label')=='REVERSED_REMAND_CONFUSION' for f in out(claim).findings)
    assert any(f.confidence_features.get('verdict_label')=='REVERSED_REMAND_CONFUSION' for f in out('사건 경과를 정리합니다. '+claim).findings)

@pytest.mark.parametrize('basis',['DISTINGUISHABLE','UNVERIFIED','NEW_UNKNOWN_STATUS'])
def test_lv06_application_or_unknown_status_does_not_assert_quote_difference(basis):
    from packages.legal_engine.actionable_guidance import generate_actionable_guidance
    g=generate_actionable_guidance(basis=basis,cited_authority='대법원 2021다67283 판결')
    assert '원문과 차이가 있습니다' not in g['guidance_summary']
    assert g['action_type']!='QUOTE_REVIEW'

@pytest.mark.parametrize('basis',['UNCONFIRMED','UNCONFIRMED_SOURCE_LIMIT'])
def test_lv06_unconfirmed_draft_does_not_assert_nonpublication(basis):
    from packages.legal_engine.actionable_guidance import generate_actionable_guidance
    g=generate_actionable_guidance(basis=basis,cited_authority='대법원 2021다67283 판결')
    assert '전문이 수록되지 않은 판결입니다' not in g['draft_motion_text']


def test_lv06_found_record_alone_does_not_confirm_quote_match():
    from packages.legal_engine.actionable_guidance import generate_actionable_guidance
    g=generate_actionable_guidance(basis='OFFICIAL_CONFIRMED',cited_authority='대법원 2021다67283 판결')
    assert '원문 일치가 확인되었습니다' not in g['guidance_summary']
