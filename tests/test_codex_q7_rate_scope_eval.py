"""Public synthetic regression tests, independent of the private evaluator grid."""
import pytest
from packages.claim_engine.calculation import CalculationEngine
from packages.common.schemas import Block, Page, NormalizedDocument

def _findings(text):
    doc = NormalizedDocument(document_id="d", filename="d.txt", mime_type="text/plain", sha256="0"*64,
        pages=[Page(page_number=1, blocks=[Block(block_id="b", text=text, page=1)])])
    return CalculationEngine().verify_document(doc)

@pytest.mark.parametrize("text", [
    "상담원 4명에게 각 25,000원씩 매일 사흘 동안 지급하여 합계 300,000원이다.",
    "연구원 5명에게 각 80,000원씩 매월 석 달간 지급하여 합계 1,200,000원이다.",
    "강사 8명에게 각 45,000원씩 시간당 지급하여 합계 720,000원이다.",
])
def test_rate_basis_after_money_is_not_a_single_payment(text):
    assert not _findings(text)

@pytest.mark.parametrize("text", [
    "상담원 4명에게 각 25,000원씩 지급하여 합계 110,000원이다.",
    "연구원 5명에게 각 80,000원씩 지급하여 합계 420,000원이다.",
    "매월 보고서를 작성한다. 강사 8명에게 각 45,000원씩 지급하여 합계 370,000원이다.",
])
def test_single_payment_mismatch_remains_detected(text):
    assert _findings(text)

@pytest.mark.parametrize("text", [
    "상담원 4명에게 각 25,000원씩 지급하여 합계 100,000원이다.",
    "연구원 5명에게 각 80,000원씩 지급하여 합계 400,000원이다.",
    "강사 8명에게 각 45,000원씩 지급하여 합계 360,000원이다.",
])
def test_correct_single_payment_has_no_finding(text):
    assert not _findings(text)

@pytest.mark.parametrize("text", [
    "매일 사흘 동안 상담원 4명에게 각 25,000원씩 지급하여 합계 300,000원이다.",
    "매월 석 달간 연구원 5명에게 각 80,000원씩 지급하여 합계 1,200,000원이다.",
    "시간당 강사 8명에게 각 45,000원씩 지급하여 합계 720,000원이다.",
])
def test_rate_basis_before_count_is_not_lost(text):
    assert not _findings(text)

@pytest.mark.parametrize("text", [
    "매월 보고서를 작성하지만 상담원 4명에게 각 25,000원씩 지급하여 합계 110,000원이다.",
    "매년 보고서를 작성하고 연구원 5명에게 각 80,000원씩 지급하여 합계 420,000원이다.",
    "매주 보고서를 작성한다. 강사 8명에게 각 45,000원씩 지급하여 합계 370,000원이다.",
])
def test_unrelated_period_does_not_disable_current_calculation(text):
    assert _findings(text)
