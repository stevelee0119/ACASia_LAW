"""Public regressions: preserve output evidence and proposition-local attribution."""
import asyncio
import pytest
import test_lv_contract_review_eval as t

OFFICIAL='채무자는 정해진 기한 안에 지급할 의무가 있으며 서면으로 합의한 특별한 사정이 없는 한 변제를 거절할 수 없다.'

@pytest.mark.parametrize('party', ['매수인','임차인','수급인'])
def test_quote_change_reaches_table_without_becoming_official_match(party):
    quote=party+'은 정해진 기한 안에 인도할 의무가 없으며 서면으로 합의한 사정이 없어도 계약을 해제할 수 있다.'
    c=t._citation(quoted_text=quote,context='위 판결에 따라 책임을 검토합니다.')
    result=t._verifier([dict(case_number=c.case_number,court='대법원',full_text=OFFICIAL)]).verify_citations([c])
    table=asyncio.run(t.verify_argument_validity(t._doc(c.raw_text+' '+quote),[c],result.data['verdicts'],[],router=t._CaptureRouter()))
    row=table.rows[0]
    assert row.basis!='OFFICIAL_CONFIRMED'
    assert '공식 원문 일치' not in row.validity_verdict
    assert row.to_dict()['actionable_guidance']['action_type'] in {'QUOTE_REVIEW','SOURCE_VERIFICATION'}
    assert row.quote_diff_categories

@pytest.mark.parametrize('before,after', [('거절할 수 없다','거절할 수 있다'),('채무자는','채권자는'),('정해진 기한','약정한 기한')])
def test_existing_quote_meaningful_change_field_survives_serialization(before,after):
    from packages.legal_engine.quote_diff import quote_changes
    quote=OFFICIAL.replace(before,after);expected=quote_changes(quote,OFFICIAL)
    assert expected is not None
    c=t._citation(quoted_text=quote)
    result=t._verifier([dict(case_number=c.case_number,court='대법원',full_text=OFFICIAL)]).verify_citations([c])
    review=result.data['verdicts'][0]['review']
    assert 'quote_meaningful_change' in review
    assert review['quote_meaningful_change'] is expected['meaningful']

@pytest.mark.parametrize('party,duty', [('매수인','대금지급'),('임차인','차임지급'),('수급인','공사완성')])
def test_correct_supreme_reversal_is_not_false_adoption(party,duty):
    holding=f'{party}의 {duty} 의무가 계약 해제로 소멸하였'
    full=f'원심은 {holding}다고 판단하였다. 그러나 이러한 원심의 판단에는 계약 해제 요건에 관한 법리를 오해하여 판결에 영향을 미친 위법이 있다.'
    def has_distortion(claim):
        c=t._citation(context=claim,attributes={'case_claim':claim})
        result=t._verifier([dict(case_number=c.case_number,court='대법원',full_text=full)]).verify_citations([c])
        return any(f.confidence_features.get('verdict_label')=='REVERSED_REMAND_CONFUSION' for f in result.findings)
    assert has_distortion(f'대법원은 {holding}다고 인정하였다.')
    assert not has_distortion(f'대법원은 {holding}다고 판단한 원심판결을 파기하였다.')
