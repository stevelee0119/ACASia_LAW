# -*- coding: utf-8 -*-
"""한글·숫자 병기 금액 불일치 항목 머리 위치 보강 검증 시험 (한국어 주석)."""
from __future__ import annotations

from pathlib import Path
import timeit
import pytest

from packages.common.enums import FindingType, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.korean_amount import words_digits_mismatches, ITEM_HEADING_RE
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)


def _make_doc(*lines: str, doc_id: str = "doc_kr_amt") -> NormalizedDocument:
    blocks = [
        Block(block_id=f"b{i+1}", text=line, page=1, visible=True, block_type="paragraph")
        for i, line in enumerate(lines)
    ]
    page = Page(page_number=1, blocks=blocks)
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[page],
    )


# --- 0. 공통 점검표 1항: 실제 진입점 실행 시험 ---

def test_pipeline_entrypoint_korean_amount_heading(tmp_path: Path):
    """공통 점검표 1항: VerificationPipeline 실제 진입점에서 항목 머리가 결합된 한글·숫자 병기 불일치 탐지 검증."""
    doc_path = tmp_path / "sample_brief_incons.txt"
    doc_path.write_text(
        "[검수대장 1차] 금 칠백만원(7,500,000원)\n",
        encoding="utf-8",
    )

    pipeline = VerificationPipeline()
    context = ProjectContext(project_id="test_incons_proj")
    inputs = [
        DocumentInput(
            document_id="doc_incons_pipe",
            path=str(doc_path),
            filename="sample_brief_incons.txt",
            mime_type="text/plain",
        )
    ]

    run_res = pipeline.run("run_incons_eval", context, inputs)
    assert run_res is not None
    assert len(run_res.documents) == 1

    doc_res = run_res.documents[0]
    incons_findings = [f for f in doc_res.findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(incons_findings) == 1
    f = incons_findings[0]
    assert "[검수대장 1차]" in f.detail
    assert f.confidence_features.get("heading") == "검수대장 1차"
    assert f.status == VerificationStatus.CONTRADICTED


# --- 1. 양성 예시 3건 (항목 머리 + 금액 불일치) ---

def test_korean_amount_heading_positive_case_1_bracket():
    """양성 1: 대괄호 항목 머리와 한글-숫자 불일치 ([검수대장 1차] 오백만원 / 5,500,000원)."""
    doc = _make_doc("[검수대장 1차] 물품 납품 대금은 금 오백만원(5,500,000원)으로 기재되었습니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 1
    assert "[검수대장 1차]" in findings[0].detail
    assert findings[0].confidence_features.get("heading") == "검수대장 1차"


def test_korean_amount_heading_positive_case_2_thick_bracket():
    """양성 2: 굵은 괄호 항목 머리와 한글-숫자 불일치 (【2차 납품】 삼백만원 / 2,000,000원)."""
    doc = _make_doc("【2차 납품】 공급가액은 일금 삼백만원(2,000,000원)입니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 1
    assert "[2차 납품]" in findings[0].detail
    assert findings[0].confidence_features.get("heading") == "2차 납품"


def test_korean_amount_heading_positive_case_3_numbered_heading():
    """양성 3: 번호형 항목 머리와 한글-숫자 불일치 (1. 물품 대금 \\n 금 칠백만원 / 7,500,000원)."""
    doc = _make_doc("1. 물품 대금", "공급 대금은 금 칠백만원(7,500,000원)으로 정산되었습니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 1
    assert "[1. 물품 대금]" in findings[0].detail
    assert findings[0].confidence_features.get("heading") == "1. 물품 대금"


# --- 2. 대조군 3건 (오탐 방지) ---

def test_korean_amount_heading_control_case_1_consistent_with_heading():
    """대조군 1: 항목 머리가 있으나 한글 금액과 숫자 금액이 완벽히 일치하는 정상 문서."""
    doc = _make_doc("[검수대장 1차] 물품 납품 대금은 금 오백만원(5,000,000원)으로 기재되었습니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 0


def test_korean_amount_heading_control_case_2_consistent_without_heading():
    """대조군 2: 항목 머리가 없고 본문에서 한글 금액과 숫자 금액이 일치하는 정상 문서."""
    doc = _make_doc("해당 계약의 정산 금액은 금 칠백만원(7,000,000원)입니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 0


def test_korean_amount_heading_control_case_3_non_amount_text():
    """대조군 3: 항목 머리는 있으나 금액 병기 표현이 없는 일반 서술 문서."""
    doc = _make_doc("[검토 보고] 관련 물품에 대한 현장 검수를 일정에 맞춰 완료하였습니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 0


# --- 3. 공통 점검표 2항: 새 정규식 성능비 검증 ---

def test_item_heading_regex_performance():
    """공통 점검표 2항: ITEM_HEADING_RE의 1배/4배 최솟값 비 < 8.0, 4배 < 1.0초 검증."""
    base_text = (
        "[검수대장 1차] 납품 내역 확인\n"
        "【2차 납품】 부품 인도 완료\n"
        "<물품 목록> 공급 규격 검토\n"
        "1. 세부 정산 내역\n"
        "일반적인 사실관계 서술 문장입니다.\n"
    ) * 10
    text_1x = base_text
    text_4x = base_text * 4

    runs = 100
    repeats = 3
    t1 = min(timeit.repeat(lambda: list(ITEM_HEADING_RE.finditer(text_1x)), number=runs, repeat=repeats)) / runs
    t4 = min(timeit.repeat(lambda: list(ITEM_HEADING_RE.finditer(text_4x)), number=runs, repeat=repeats)) / runs

    t1_adj = max(t1, 0.0001)
    ratio = t4 / t1_adj
    assert ratio < 8.0, f"ITEM_HEADING_RE 비정상 성능 비: {ratio}"
    assert t4 < 1.0, f"ITEM_HEADING_RE 4배 최솟값 1초 초과: {t4}s"
