"""TK-76 3주기 1항: 본문 산식 일반화(A 산식) 단위 및 통합 검산 시험.

M2~M7 조건부 승인 규칙 반영:
- M2: 뺄셈 기호 가드 (공백/단위 한정, 날짜·사건번호 하이픈 제외 대조)
- M3: 단위 뒤 한국어 조사 분리 (은/는/이/가/을/를/의/에/에서/로/씩/과/와/도/만)
- M4: 결과 연결 표지 엄격화 (동일 절, 피연산자 2개 이상, 마지막 수치 한정)
- M5: 2~8자 일반 한글 명사구 이름표 허용 (닫힌 목록 배제)
- M7: 정당한 차이 가드 (부가세/세액 가산, 근사치, 범위, 상대방 주장 인용)
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from packages.claim_engine.calculation import CalculationEngine, _check_statement_formula
from packages.common.enums import FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page


def make_doc(text: str) -> NormalizedDocument:
    """합성 테스트용 NormalizedDocument 생성 헬퍼."""
    doc = NormalizedDocument(
        document_id="test_doc",
        filename="test.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
    )
    p = Page(page_number=1, width=595.0, height=842.0)
    b = Block(
        block_id="b1",
        page=1,
        text=text,
        bbox=(50.0, 50.0, 500.0, 100.0),
        block_type="paragraph",
        source_layer="visible_text",
    )
    p.blocks.append(b)
    doc.pages.append(p)
    return doc


# --- 1. A 산식 양성 시험 (Positive Tests) ----------------------------------------------------

def test_multiplication_narrative_statement_detected():
    """서술형 곱셈: 단가에 수량을 곱한 결과가 기재와 다른 경우 탐지."""
    text = "단가 50,000원에 3회를 곱하면 160,000원이다."
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    
    formula_findings = [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(formula_findings) == 1
    f = formula_findings[0]
    assert f.status == VerificationStatus.CONTRADICTED
    assert f.severity == Severity.HIGH
    assert float(f.confidence_features["stated"]) == 160000.0
    assert float(f.confidence_features["computed"]) == 150000.0


def test_non_currency_quantity_multiplication_detected():
    """비금액 일반 단위 수량 산식: 상자 단위 반복 수량 곱셈의 계산 오차 탐지."""
    text = "매월 5상자씩 12개월은 총 55상자이다."
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    
    formula_findings = [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(formula_findings) == 1
    assert float(formula_findings[0].confidence_features["stated"]) == 55.0
    assert float(formula_findings[0].confidence_features["computed"]) == 60.0


def test_labeled_addition_statement_detected():
    """이름표 부착 덧셈 (M5): 2~8자 일반 한글 명사구 라벨 뒤 등호 덧셈 오차 탐지."""
    text = "청구원금: 100만 원 + 200만 원 = 350만 원"
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    
    formula_findings = [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(formula_findings) == 1
    assert float(formula_findings[0].confidence_features["stated"]) == 3500000.0
    assert float(formula_findings[0].confidence_features["computed"]) == 3000000.0


def test_subtraction_narrative_deduction_detected():
    """서술형 뺄셈: 공제·순액 서술어 뒤 결과 오차 탐지."""
    text = "총액 1,000만 원에서 300만 원을 공제하면 순액은 600만 원입니다."
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    
    formula_findings = [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(formula_findings) == 1
    assert float(formula_findings[0].confidence_features["stated"]) == 6000000.0
    assert float(formula_findings[0].confidence_features["computed"]) == 7000000.0


def test_equals_multiplication_with_custom_unit_detected():
    """등호 곱셈 (M8): 비금액 일반 단위(상자, 회) 곱셈 등호식 오차 탐지."""
    text = "10상자 × 5회 = 60상자"
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    
    formula_findings = [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(formula_findings) == 1
    assert float(formula_findings[0].confidence_features["stated"]) == 60.0
    assert float(formula_findings[0].confidence_features["computed"]) == 50.0


def test_equals_subtraction_detected():
    """등호 뺄셈 (M2): 명시적 단위가 결합된 수치 간 뺄셈 등호식 오차 탐지."""
    text = "1,000만 원 - 300만 원 = 800만 원"
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    
    formula_findings = [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(formula_findings) == 1
    assert float(formula_findings[0].confidence_features["stated"]) == 8000000.0
    assert float(formula_findings[0].confidence_features["computed"]) == 7000000.0


# --- 2. 대조군 시험 (Negative Controls / Guards) ----------------------------------------------

def test_date_and_case_number_hyphen_not_flagged():
    """M2 대조군: 날짜(YYYY-MM-DD) 및 사건번호 하이픈을 뺄셈 연산자로 오인하지 않음."""
    text = "2024-05-01 접수된 2023가합1234-1 사건의 청구금액 1,000만 원"
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    assert not [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]


def test_valid_calculation_with_josa_not_flagged():
    """M3 대조군: 단위 뒤에 조사가 결합되었으나 계산 결과가 정확히 일치하는 경우 불일치 미발행."""
    text = "10상자만을 납품받았으나 5만 원씩 정산하여 총 50만 원 지급함"
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    assert not [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]


def test_plain_josa_enumeration_not_treated_as_formula():
    """M4 대조군: 단순 서술 문장 내 '은/는' 나열은 산식으로 오인하지 않음."""
    text = "원고는 10만 원을 청구하였고 피고는 20만 원을 변제하였다."
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    assert not [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]


def test_tax_and_vat_addition_guard_not_flagged():
    """M7 대조군: 부가세·세액 가산 문맥이 있는 경우 단순 산술 불일치 배제."""
    text = "공급가액 50만 원이며, 부가세 5만 원을 가산하여 총 55만 원입니다."
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    assert not [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]


def test_approximate_modifier_guard_not_flagged():
    """M7 대조군: '약', '대략' 등 근사치 수식어가 결합된 경우 산술 오차 배제."""
    text = "매월 약 200만 원씩 6개월간 총 1,100만 원을 지급받음"
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    assert not [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]


def test_range_modifier_guard_not_flagged():
    """M7 대조군: '~', '내지' 등 범위 수식어가 결합된 경우 산술 오차 배제."""
    text = "1회 10만 원씩 3회 내지 5회에 걸쳐 총 40만 원 상당에 달함"
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    assert not [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]


def test_claim_quote_guard_not_flagged():
    """M7 대조군: 상대방 주장 인용 또는 가정 문맥 배제."""
    text = "원고는 100만 원에 5회를 곱하면 600만 원이라 주장하나 이는 사실과 다르다."
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    assert not [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]


def test_incompatible_units_not_flagged():
    """단위 호환성: 피연산자 간 단위가 상이하여 산술 비교가 불가능한 경우 배제."""
    text = "사과 10개와 배 20상자는 합계 35상자이다."
    doc = make_doc(text)
    engine = CalculationEngine()
    findings = engine.verify_document(doc)
    assert not [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]
