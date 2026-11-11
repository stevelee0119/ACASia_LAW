import asyncio
import pytest
import test_lv_contract_review_eval as t

FULL = ('원심은 매수인의 대금지급 의무가 계약 해제로 소멸하였다고 판단하였다. '
        '그러나 이러한 원심의 판단에는 계약 해제 요건에 관한 법리를 오해하여 판결에 영향을 미친 위법이 있다.')

@pytest.mark.parametrize('claim', [
    '원심은 매수인의 대금지급 의무가 계약 해제로 소멸하였다고 판단하였으나 대법원은 이를 파기하였다.',
    '대법원에서 배척된 원심의 견해는 매수인의 대금지급 의무가 계약 해제로 소멸하였다는 것이다.',
    '매수인의 대금지급 의무가 계약 해제로 소멸하였다는 원심 판단은 상고심에서 파기되었다.',
])
def test_accurate_description_of_reversed_holding_is_not_distortion(claim):
    c=t._citation(attributes={'case_claim':claim})
    records=[dict(case_number=c.case_number,court='대법원',full_text=FULL)]
    result=t._verifier(records).verify_citations([c])
    assert not any(f.confidence_features.get('verdict_label')=='REVERSED_REMAND_CONFUSION' for f in result.findings)

def test_distortion_subtype_survives_real_verdict_serialization():
    claim='매수인의 대금지급 의무가 계약 해제로 소멸하였다고 판단하였다.'
    c=t._citation(attributes={'case_claim':claim},context=claim)
    result=t._verifier([dict(case_number=c.case_number,court='대법원',full_text=FULL)]).verify_citations([c])
    assert any(f.confidence_features.get('verdict_label')=='REVERSED_REMAND_CONFUSION' for f in result.findings)
    table=asyncio.run(t.verify_argument_validity(t._doc(claim),[c],result.data['verdicts'],[]))
    assert table.rows[0].basis=='CONTRADICTION'
    assert '파기환송' in table.rows[0].validity_verdict
