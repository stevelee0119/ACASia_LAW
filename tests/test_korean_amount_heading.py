from pathlib import Path
import timeit
import gc
import pytest

from packages.common.enums import FindingType, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.korean_amount import (
    words_digits_mismatches,
    BRACKET_HEADING_RE,
    _find_item_heading,
)
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
    """공통 점검표 1항: VerificationPipeline 실제 진입점에서 같은 줄 명사구 항목명이 결합된 한글·숫자 병기 불일치 탐지 검증."""
    doc_path = tmp_path / "sample_brief_incons.txt"
    doc_path.write_text(
        "창고정산 1차 320,000원(금 사십이만원)을 같은 지급액의 표기로 기재한다.\n",
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
    assert "창고정산 1차" in f.detail
    assert "창고정산 1차 320,000원(금 사십이만원)" in (f.evidence[0].excerpt if f.evidence else "")
    assert f.confidence_features.get("heading") == "창고정산 1차"
    assert f.status == VerificationStatus.CONTRADICTED


# --- 1. 양성 예시 3건 (항목 머리 + 금액 불일치) ---

def test_korean_amount_heading_positive_case_1_noun_phrase():
    """양성 1: 괄호 없는 선행 명사구 항목명 (창고정산 1차 오백만원 / 5,500,000원)."""
    doc = _make_doc("창고정산 1차 금 오백만원(5,500,000원)으로 기재되었습니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 1
    assert "창고정산 1차" in findings[0].detail
    assert findings[0].confidence_features.get("heading") == "창고정산 1차"


def test_korean_amount_heading_positive_case_2_bracket():
    """양성 2: 대괄호 항목 머리와 한글-숫자 불일치 ([검수대장 1차] 삼백만원 / 2,000,000원)."""
    doc = _make_doc("[검수대장 1차] 공급가액은 일금 삼백만원(2,000,000원)입니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 1
    assert "[검수대장 1차]" in findings[0].detail
    assert findings[0].confidence_features.get("heading") == "[검수대장 1차]"


def test_korean_amount_heading_positive_case_3_thick_bracket():
    """양성 3: 굵은 괄호 항목 머리와 한글-숫자 불일치 (【2차 납품】 칠백만원 / 7,500,000원)."""
    doc = _make_doc("【2차 납품】 정산 대금은 금 칠백만원(7,500,000원)입니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 1
    assert "【2차 납품】" in findings[0].detail
    assert findings[0].confidence_features.get("heading") == "【2차 납품】"


# --- 2. 대조군 3건 (오탐 방지 및 소제목 미대체 검증) ---

def test_korean_amount_heading_control_case_1_consistent_with_heading():
    """대조군 1: 항목 머리가 있으나 한글 금액과 숫자 금액이 완벽히 일치하는 정상 문서."""
    doc = _make_doc("창고정산 1차 물품 납품 대금은 금 오백만원(5,000,000원)으로 기재되었습니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 0


def test_korean_amount_heading_control_case_2_no_heading_substitution():
    """대조군 2: 같은 줄에 항목명이 없고 윗줄에 소제목만 있는 경우, 소제목으로 대체하지 않고 heading 없이 방출."""
    doc = _make_doc("1. 소제목 라인", "단순 서술 문장 안에서 금 칠백만원(7,500,000원)이 기재되었습니다.")
    findings = words_digits_mismatches(doc)
    assert len(findings) == 1
    assert "heading" not in findings[0].confidence_features
    assert "1. 소제목 라인" not in findings[0].detail


def test_korean_amount_heading_control_case_3_long_sentence_no_heading():
    """대조군 3: 항목명이 아닌 긴 서술 문장에서는 heading을 추출하지 않는다 (FP-TRAP 오탐 방지)."""
    text = "원고는 피고에게 여러 차례 지급을 요청하였으나 피고는 금 칠백만원(7,500,000원)만을 지급하겠다고 통보하였습니다."
    doc = _make_doc(text)
    findings = words_digits_mismatches(doc)
    assert len(findings) == 1
    assert "heading" not in findings[0].confidence_features


def test_korean_amount_heading_control_case_date_prefix_stripped():
    """대조군 4: 같은 줄 항목명 앞에 날짜가 있는 경우, 날짜 문자열이 항목명에 들어가지 않음을 단언 (#114 회귀 방지)."""
    text = "2023. 2. 29. 창고정산 1차 320,000원(금 사십이만원)을 같은 지급액의 표기로 기재한다."
    doc = _make_doc(text)
    findings = words_digits_mismatches(doc)
    assert len(findings) == 1
    heading = findings[0].confidence_features.get("heading")
    assert heading == "창고정산 1차"
    assert "2023" not in heading
    assert "29" not in heading
    assert "창고정산 1차 320,000원(금 사십이만원)" in (findings[0].evidence[0].excerpt if findings[0].evidence else "")


# --- 3. 공통 점검표 2항: 새 정규식 성능비 검증 ---

def test_bracket_heading_regex_performance():
    """공통 점검표 2항: BRACKET_HEADING_RE의 1배/4배 최솟값 비 < 8.0, 4배 < 1.0초 검증."""
    base_text = (
        "[검수대장 1차] 납품 내역 확인\n"
        "【2차 납품】 부품 인도 완료\n"
        "<물품 목록> 공급 규격 검토\n"
        "일반적인 사실관계 서술 문장입니다.\n"
    ) * 10
    text_1x = base_text
    text_4x = base_text * 4

    times_1x = []
    times_4x = []
    gc_was_enabled = gc.isenabled()
    try:
        gc.disable()
        for _ in range(3):
            t0 = timeit.default_timer()
            list(BRACKET_HEADING_RE.finditer(text_1x))
            times_1x.append(timeit.default_timer() - t0)
        for _ in range(3):
            t0 = timeit.default_timer()
            list(BRACKET_HEADING_RE.finditer(text_4x))
            times_4x.append(timeit.default_timer() - t0)
    finally:
        if gc_was_enabled:
            gc.enable()

    t1 = max(min(times_1x), 0.0001)
    t4 = min(times_4x)
    ratio = t4 / t1
    assert ratio < 8.0, f"BRACKET_HEADING_RE 비정상 성능 비: {ratio:.2f}"
    assert t4 < 1.0, f"BRACKET_HEADING_RE 4배 최솟값 1초 초과: {t4:.6f}s"

