from pathlib import Path
from decimal import Decimal
import timeit
import pytest

from packages.common.enums import FindingType, VerificationStatus
from packages.claim_engine.calculation import evaluate_expression, LEADING_MULTIPLIER_RE
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)


# --- 0. 공통 점검표 1항: 실제 진입점 실행 시험 ---

def test_pipeline_entrypoint_leading_multiplier_calculation(tmp_path: Path):
    """공통 점검표 1항: VerificationPipeline 실제 진입점에서 선행 항목명이 결합된 수 × 금액 산식 불일치 탐지 검증."""
    doc_path = tmp_path / "sample_calc_brief.txt"
    doc_path.write_text(
        "물품대장 1차 12건 × 15,000원 = 210,000원 수량과 단가를 곱한 금액을 원금으로 적는다.\n",
        encoding="utf-8",
    )

    pipeline = VerificationPipeline()
    context = ProjectContext(project_id="test_calc_proj")
    inputs = [
        DocumentInput(
            document_id="doc_calc_test",
            path=str(doc_path),
            filename="sample_calc_brief.txt",
            mime_type="text/plain",
        )
    ]

    run_res = pipeline.run("run_calc_eval", context, inputs)
    assert run_res is not None
    assert len(run_res.documents) == 1

    doc_res = run_res.documents[0]
    calc_findings = [f for f in doc_res.findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(calc_findings) == 1
    assert "차이 30,000원" in calc_findings[0].title
    assert "물품대장 1차 12건 × 15,000원 = 210,000원" in (calc_findings[0].evidence[0].excerpt if calc_findings[0].evidence else "")
    assert calc_findings[0].status == VerificationStatus.CONTRADICTED



# --- 1. 양성 예시 3건 (수 × 금액) ---

def test_leading_multiplier_positive_case_1_basic():
    """양성 1: 단순 수 × 금액 (3 × 500,000원 = 1,500,000원) 검증."""
    res = evaluate_expression("3 × 500,000원")
    assert res == Decimal("1500000")


def test_leading_multiplier_positive_case_2_with_unit_month():
    """양성 2: 단위 수(개월) × 금액 (3개월 × 1,000,000원 = 3,000,000원) 검증."""
    res = evaluate_expression("3개월 × 1,000,000원")
    assert res == Decimal("3000000")


def test_leading_multiplier_positive_case_3_asterisk_and_count():
    """양성 3: 별표 기호 및 횟수 단위 (12회 * 150,000원 = 1,800,000원) 검증."""
    res = evaluate_expression("12회 * 150,000원")
    assert res == Decimal("1800000")


# --- T1: calculation.py 새 꼴 3변형 시험 (천 단위 쉼표 수 × 정수, 결과 뒤 단위·조사) ---

def test_calculation_comma_number_times_integer_mismatch():
    """T1 변형 1: 천 단위 쉼표 수 × 정수 = 잘못 적힌 결과 (50,000 × 3 = 140,000원)."""
    from packages.claim_engine.calculation import row_final_amount
    amt, check = row_final_amount("재료비 50,000 × 3 = 140,000원")
    assert amt is not None
    assert amt.value == Decimal("140000")
    assert check is not None
    assert check.computed == Decimal("150000")
    assert not check.matches


def test_calculation_integer_times_comma_number_with_josa():
    """T1 변형 2: 정수 × 천 단위 쉼표 수 = 잘못 적힌 결과 뒤 조사 (3 × 50,000 = 140,000원으로 계산된다)."""
    from packages.claim_engine.calculation import row_final_amount
    amt, check = row_final_amount("수량 단가 3 × 50,000 = 140,000원으로 계산된다")
    assert amt is not None
    assert amt.value == Decimal("140000")
    assert check is not None
    assert check.computed == Decimal("150000")
    assert not check.matches


def test_calculation_unit_amount_times_count_with_predicate():
    """T1 변형 3: 단위 금액 × 수 = 잘못 적힌 결과 뒤 서술어 (15,000원 × 12 = 210,000원에 달한다)."""
    from packages.claim_engine.calculation import row_final_amount
    amt, check = row_final_amount("노무비 15,000원 × 12 = 210,000원에 달한다")
    assert amt is not None
    assert amt.value == Decimal("210000")
    assert check is not None
    assert check.computed == Decimal("180000")
    assert not check.matches


# --- 2. 대조군 3건 (오탐 방지) ---

def test_leading_multiplier_control_case_1_single_amount():
    """대조군 1: 산식이 아닌 단순 단일 금액 표기는 None을 반환해야 한다."""
    res = evaluate_expression("500,000원")
    assert res is None


def test_leading_multiplier_control_case_2_non_formula_text():
    """대조군 2: 곱셈 기호 없는 일반 설명 텍스트는 None을 반환해야 한다."""
    res = evaluate_expression("3개월 동안 현장에서 근무하였습니다.")
    assert res is None


def test_leading_multiplier_control_case_3_non_amount_multiplication():
    """대조군 3: 금액 단위가 없는 순수 숫자 곱셈은 금액 산식으로 평가하지 않는다."""
    res = evaluate_expression("3 × 5")
    assert res is None


def test_y7_non_currency_area_and_year_formula():
    """Y7: 통화 표지가 없는 면적·치수·연도 산식은 산식 결과가 없어야 한다 (한국어 주석)."""
    # 1. 연도 곱셈 ('2,024 × 3 = 6,072') -> 통화 표지 없으므로 산식 결과 없음
    from packages.claim_engine.calculation import row_final_amount
    amt, check = row_final_amount("2,024 × 3 = 6,072")
    assert check is None, f"연도 곱셈에서 산식 검증 발생 오탐: {check}"

    # 2. 면적 산식 ('면적 150 × 20 = 3,000제곱미터') -> 통화 표지 없으므로 산식 결과 없음
    amt_area, check_area = row_final_amount("면적 150 × 20 = 3,000제곱미터")
    assert check_area is None, f"면적 산식에서 산식 검증 발생 오탐: {check_area}"

    # 3. evaluate_expression 단독 호출 시에도 통화 없으면 None
    assert evaluate_expression("2,024 × 3") is None
    assert evaluate_expression("150 × 20") is None


# --- 3. 기존 산식 호환성 검증 ---

def test_formula_backward_compatibility():
    """기존 '금액 × 수' 및 '금액 + 금액' 산식이 정상 작동하는지 확인."""
    assert evaluate_expression("500,000원 × 3") == Decimal("1500000")
    assert evaluate_expression("1,000,000원 + 200,000원") == Decimal("1200000")


# --- 4. 공통 점검표 2항: 새 정규식 성능비 검증 ---

def test_leading_multiplier_regex_performance():
    """공통 점검표 2항: LEADING_MULTIPLIER_RE의 1배/4배 최솟값 비 < 8.0, 4배 < 1.0초 검증."""
    base_text = "3개월 × 1,000,000원\n12회 * 150,000원\n5개 x 50,000원\n" * 10
    text_1x = base_text
    text_4x = base_text * 4

    runs = 100
    repeats = 3
    t1 = min(timeit.repeat(lambda: list(LEADING_MULTIPLIER_RE.finditer(text_1x)), number=runs, repeat=repeats)) / runs
    t4 = min(timeit.repeat(lambda: list(LEADING_MULTIPLIER_RE.finditer(text_4x)), number=runs, repeat=repeats)) / runs

    t1_adj = max(t1, 0.0001)
    ratio = t4 / t1_adj
    assert ratio < 8.0, f"LEADING_MULTIPLIER_RE 비정상 성능 비: {ratio}"
    assert t4 < 1.0, f"LEADING_MULTIPLIER_RE 4배 최솟값 1초 초과: {t4}s"
