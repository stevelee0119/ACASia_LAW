"""Evaluator public synthetic contract regressions; no private probe text."""
import asyncio
import json
import pytest
from packages.common.enums import CitationType, AdapterStatus, Severity
from packages.common.schemas import Citation, Block, Page, NormalizedDocument
from packages.legal_engine.legal_rules import _calculate_dynamic_deadline
from packages.legal_engine.argument_validity_verifier import verify_argument_validity, _extract_linked_claim
from packages.legal_engine.verifier import LegalVerifier
from packages.source_adapters import SourceRegistry
from packages.source_adapters.base import AdapterResponse

def _doc(text):
    return NormalizedDocument('d', 'test.txt', 'text/plain', '0'*64,
        [Page(page_number=1, blocks=[Block(block_id='b', text=text, page=1)])])

def _citation(**kw):
    data = dict(citation_id='c', type=CitationType.CASE, raw_text='대법원 2021다67283 판결',
        court='대법원', case_number='2021다67283', canonical_case_number='2021다67283', page=1)
    data.update(kw)
    return Citation(**data)

@pytest.mark.parametrize('tail', [
    '2024. 10. 22.\n원고 대리인 변호사',
    '증명서 발급신청 접수일: 2024. 10. 22.',
    '원고는 2024. 10. 22. 본 소를 제기할 예정입니다.',
    '원고는 2024. 10. 22. 본 소를 제기하지 않았습니다.',
    '소제기일: 2024. 4. 1.\n소제기일: 2024. 10. 22.',
])
def test_lv01_missing_or_ambiguous_filing_suspends(tail):
    text = '원처분일: 2024. 3. 7.\n통지일: 2024. 3. 19.\n' + tail
    result = _calculate_dynamic_deadline(_doc(text), '통보일부터 제소기간 90일을 계산합니다.')
    assert '각하 위험' not in result and '기간 준수' not in result
    assert '보류' in result

def test_lv01_elapsed_days_are_not_a_legal_deadline_verdict():
    result = _calculate_dynamic_deadline(_doc('원처분일: 2024. 3. 7.\n소제기일: 2024. 4. 1.'), '')
    assert '25일' in result
    assert '각하 위험' not in result and '기간 준수' not in result

class _CaptureRouter:
    def __init__(self): self.requests = []
    def has_available_provider(self, **kw): return True
    async def consult_all(self, role, request, **kw):
        self.requests.append(request)
        return []

@pytest.mark.parametrize('mode', ['no_span', 'attribute'])
def test_lv02_evaluation_context_reaches_model(mode):
    raw = '대법원 2021다67283 판결'
    first = raw + '에 따라 책임을 검토합니다.'
    exception = '다만 서면 합의로 면제된 채무에는 위 원칙을 적용하지 않습니다.'
    full = first + ' ' + exception
    c = _citation(context=full if mode == 'no_span' else first,
        attributes={} if mode == 'no_span' else {'claim_text': full},
        span=None if mode == 'no_span' else (0, len(raw)))
    router = _CaptureRouter()
    result = asyncio.run(verify_argument_validity(_doc(full), [c],
        [{'citation_id':'c', 'status':'NOT_FOUND', 'levels':{'level1':'NOT_FOUND'}}], [], router=router))
    assert exception in result.rows[0].evaluation_context
    sent = json.loads(router.requests[0].user)['items'][0]['surrounding_context_and_claim']
    assert exception in sent

def test_lv02_second_occurrence_uses_its_own_claim():
    raw = '대법원 2021다67283 판결'
    a = raw + '에 따라 책임이 인정됩니다.'
    b = raw + '은 요건이 달라 이 사건에 적용되지 않습니다.'
    text = a + '\n다른 쟁점입니다.\n' + b
    start = text.rindex(raw)
    c = _citation(context=text, span=(start, start + len(raw)))
    result = _extract_linked_claim(c, _doc(text))
    assert '적용되지 않습니다' in result
    assert '책임이 인정됩니다' not in result

class _Law:
    def __init__(self, records): self.records = records
    def search_case(self, *args, **kw):
        return AdapterResponse(AdapterStatus.READY, self.records, None, 'synthetic')

def _verifier(records):
    registry = SourceRegistry()
    registry.legal[0] = _Law(records)
    return LegalVerifier(registry)

@pytest.mark.parametrize('court,number', [
    ('대법원', '2021다67283'), ('헌법재판소', '2021헌바672'), ('서울지방법원', '2021가단67283'),
])
def test_lv03_empty_search_does_not_prove_nonexistence(court, number):
    c = _citation(court=court, case_number=number, canonical_case_number=number)
    v = _verifier([]).verify_case(c)
    assert v.levels.get('authority_status') != 'CONFIRMED_NONEXISTENT'
    assert not any(f.severity == Severity.CRITICAL or 'FAKE_PRECEDENT' in f.tags for f in v.findings)

def test_lv03_lower_court_identifiers_do_not_collide():
    from packages.legal_engine.authority_status import make_authority_id
    a = _citation(court='서울중앙지방법원', case_number='2021가단67283', canonical_case_number='2021가단67283')
    b = _citation(court='부산지방법원', case_number='2021가단67283', canonical_case_number='2021가단67283')
    assert make_authority_id(a) != make_authority_id(b)

@pytest.mark.parametrize('quote', ['', '   ', '...'])
def test_quote_absent_is_not_exact_match(quote):
    from packages.legal_engine.quote_diff import categorize_quote_diff
    text = '매도인은 계약에서 정한 기한 안에 인도하여야 하며 이행 조건을 확인해야 한다.'
    r = categorize_quote_diff(quote, text)
    assert r['status'] != 'EXACT_MATCH'

def test_quote_summary_only_cannot_verify_full_text():
    quote = '매도인은 계약에서 정한 기한 안에 인도하여야 하며 이행 조건을 확인해야 한다.'
    record = dict(case_number='2021다67283', court='대법원', full_text='', summary=quote)
    v = _verifier([record]).verify_case(_citation(quoted_text=quote))
    assert v.levels['level3'] == 'UNVERIFIED'

def test_quote_unaligned_substantive_difference_is_not_minor_wording():
    from packages.legal_engine.quote_diff import categorize_quote_diff
    official = '채무자는 정해진 기한 안에 지급할 의무가 있으며 서면으로 합의한 특별한 사정이 없는 한 변제를 거절할 수 없다.'
    quote = '매수인은 정해진 기한 안에 인도할 의무가 없으며 서면으로 합의한 사정이 없어도 계약을 해제할 수 있다.'
    r = categorize_quote_diff(quote, official)
    assert 'MINOR_WORDING' not in r['diff_categories']
