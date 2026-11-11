"""Public checks of the submitted Round-5 producer/consumer state matrix."""
import asyncio
import pytest
import test_lv_contract_review_eval as t

@pytest.mark.parametrize('status', ['UNKNOWN','SUSPENDED','UNVERIFIED'])
def test_unverified_producer_with_residual_categories_stays_unverified(status):
    c=t._citation(context='이 판례를 근거로 책임을 검토합니다.')
    verdict={'citation_id':'c','status':status,'levels':{'level1':status,'level3':'UNVERIFIED'},
             'review':{'quote_diff_categories':['NUMERIC'],'quote_diff_status':'UNVERIFIED'}}
    table=asyncio.run(t.verify_argument_validity(t._doc(c.raw_text),[c],[verdict],[],router=t._CaptureRouter()))
    assert not any(str(f.type) == "LEGAL_ARGUMENT_INVALID" for f in table.findings)
    # Missing evidence must not become a confirmed mismatch just because categories exist.
    assert not any(row.verification_status=='CONTRADICTED' or row.basis=='CONTENT_MISMATCH' for row in table.rows)
    assert all(row.to_dict()['actionable_guidance']['action_type']=='SOURCE_VERIFICATION' for row in table.rows)

@pytest.mark.parametrize('party', ['매수인','임차인','수급인'])
def test_summary_only_real_verifier_does_not_become_original_match(party):
    quote=party+'은 계약에서 정한 기한 안에 의무를 이행하여야 하며 특별한 사정이 있는 경우에는 달리 정할 수 있다.'
    c=t._citation(quoted_text=quote,context=quote)
    result=t._verifier([dict(case_number=c.case_number,court='대법원',full_text='',summary=quote)]).verify_citations([c])
    assert result.data['verdicts'][0]['levels']['level3']=='UNVERIFIED'
    table=asyncio.run(t.verify_argument_validity(t._doc(c.raw_text+' '+quote),[c],result.data['verdicts'],[],router=t._CaptureRouter()))
    assert table.rows
    row=table.rows[0]
    assert not any(str(f.type) == "LEGAL_ARGUMENT_INVALID" for f in table.findings)
    assert row.basis!='OFFICIAL_CONFIRMED'
    assert '원문 일치' not in row.validity_verdict
    assert row.to_dict()['actionable_guidance']['action_type']=='SOURCE_VERIFICATION'

@pytest.mark.parametrize('quote', ['집행 절차의 단계별 송달 방법을 검토한다.','관할 구역의 획정과 소송 비용의 부담을 확인한다.','문서 보관 기간 및 신청서의 서식을 정한다.'])
def test_unaligned_quote_keeps_declared_source_verification_action(quote):
    official='채무자는 정해진 기한 안에 지급할 의무가 있으며 서면으로 합의한 특별한 사정이 없는 한 변제를 거절할 수 없다.'
    c=t._citation(quoted_text=quote)
    result=t._verifier([dict(case_number=c.case_number,court='대법원',full_text=official)]).verify_citations([c])
    assert result.data['verdicts'][0]['review']['quote_diff_status']=='UNALIGNED_QUOTE'
    table=asyncio.run(t.verify_argument_validity(t._doc(c.raw_text+' '+quote),[c],result.data['verdicts'],[],router=t._CaptureRouter()))
    assert table.rows
    # The submitted matrix explicitly promises SOURCE_VERIFICATION for UNALIGNED_QUOTE.
    assert table.rows[0].to_dict()['actionable_guidance']['action_type']=='SOURCE_VERIFICATION'
