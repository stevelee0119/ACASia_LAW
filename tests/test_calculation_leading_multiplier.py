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
    """공통 점검표 1항: VerificationPipeline 실제 진입점에서 수 × 금액 산식 불일치 탐지 검증."""
    doc_path = tmp_path / "sample_calc_brief.txt"
    doc_path.write_text(
        "1. 용역 대금 청구\n"
        "청구 내역 : 3 × 500,000원 = 2,000,000원\n",
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
    assert "차이 500,000원" in calc_findings[0].title
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
