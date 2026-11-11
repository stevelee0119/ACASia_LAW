"""Public regressions: exact-match rows must initialize their own counteraction."""
import asyncio
import pytest
import test_lv_contract_review_eval as t

@pytest.mark.parametrize('party', ['매수인', '임차인', '수급인'])
@pytest.mark.parametrize('prepend_pending', [False, True])
def test_exact_match_has_its_own_counteraction(party, prepend_pending):
    quote = party + '은 계약에서 정한 기한 안에 의무를 이행하여야 하며 특별한 사정이 있는 경우에는 달리 정할 수 있다.'
    c = t._citation(quoted_text=quote, context=quote)
    verdicts = t._verifier([dict(case_number=c.case_number, court='대법원', full_text=quote)]).verify_citations([c]).data['verdicts']
    citations = [c]
    if prepend_pending:
        pending = t._citation(citation_id='pending', case_number='2020다67284', canonical_case_number='2020다67284',
                              raw_text='대법원 2020다67284 판결', context='판결문 사본 확인이 필요합니다.')
        citations.insert(0, pending)
        verdicts = t._verifier([]).verify_citations([pending]).data['verdicts'] + verdicts
    table = asyncio.run(t.verify_argument_validity(t._doc(c.raw_text + ' ' + quote), citations, verdicts, []))
    exact = next(row for row in table.rows if row.citation_id == c.citation_id)
    assert exact.basis == 'OFFICIAL_CONFIRMED'
    assert '직접 비교 검토' in exact.recommended_counteraction
    assert exact.to_dict()['actionable_guidance']['action_type'] == 'APPLICATION_CHECK'
    if prepend_pending:
        previous = next(row for row in table.rows if row.citation_id == 'pending')
        assert exact.recommended_counteraction != previous.recommended_counteraction
