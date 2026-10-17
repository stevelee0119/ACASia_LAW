"""서증 번호 및 목록 불일치(EVI-NUM) 구조 기반 검증 시험.

실제 진입점(VerificationPipeline.run), 다른 표현 양성 5건(축 1~4),
대조군 4건(완결 선언 없음, 기제출 원용, 가지번호 묶음, 통상 정상 서면) 포함.
사건 고유 리터럴 하드코딩 금지 규칙 준수.
"""
from __future__ import annotations

import pytest

from packages.common.config import reset_settings
from packages.common.enums import FindingType, EvidenceGrade
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.evidence_consistency import check_evidence_numbering_mismatches
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)


def _make_doc(lines: list[str], doc_id: str = "test-doc") -> NormalizedDocument:
    """테스트용 NormalizedDocument 헬퍼 (한국어 주석)."""
    blocks = [Block(block_id=f"b{i}", text=line, page=1) for i, line in enumerate(lines)]
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=blocks)],
    )


# --- 1. 실제 진입점 파이프라인 시험 (VerificationPipeline.run) ---
def test_pipeline_entrypoint_evidence_numbering_mismatches(tmp_path, monkeypatch):
    """실제 파이프라인 진입점(VerificationPipeline.run)을 통한 EVI-NUM 검출 검증."""
    sample_text = (
        "원고는 피고의 의무 불이행을 입증하기 위하여 별지 증거목록에 없는 갑 제6호증 발주서를 근거로 주장합니다.\n"
        "입증방법: 갑 제1호증 계약서, 갑 제2호증 내역서 (이 서면의 제출 증거 전부)"
    )
    doc_path = tmp_path / "brief_num_mismatch.txt"
    doc_path.write_text(sample_text, encoding="utf-8")

    with monkeypatch.context() as patch:
        patch.setenv("LV_ALLOW_NETWORK", "0")
        patch.setenv("LV_DATA_DIR", str(tmp_path / "data"))
        reset_settings()
        try:
            pipeline = VerificationPipeline()
            result = pipeline.run(
                "pipeline-num-run",
                ProjectContext("pipeline-num-project"),
                [DocumentInput("brief-num-1", str(doc_path), doc_path.name)],
            )
        finally:
            reset_settings()

    assert not result.errors
    assert len(result.documents) == 1
    doc_result = result.documents[0]

    num_findings = [
        f for f in doc_result.findings
        if f.type == FindingType.EVIDENCE_LIST_MISMATCH
        and f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"
    ]
    assert len(num_findings) >= 1
    finding = num_findings[0]
    assert finding.evidence_grade == EvidenceGrade.B
    assert "갑 제6호증" in finding.title or "갑 제6호증" in finding.detail


# --- 2. 양성 시험 1 (축 1: 완결 목록에 없는 호증 번호 인용) ---
def test_positive_complete_list_missing_exhibit():
    """축 1: 완결을 선언한 증거목록에 없는 호증을 본문에서 인용."""
    doc = _make_doc([
        "원고는 갑 제12호증 배수 점검일지로 피고의 과실을 입증합니다.",
        "증거목록: 갑 제1호증 ~ 갑 제11호증, 이 서면의 제출 증거 전부",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 1
    f = findings[0]
    assert f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"
    assert "갑 제12호증" in f.title


# --- 3. 양성 시험 2 (축 2: 연속 범위 선언 후 중간 누락) ---
def test_positive_continuous_range_gap():
    """축 2: 을 제1호증부터 제4호증까지 연속 제출 선언 후 중간 번호 누락."""
    doc = _make_doc([
        "피고는 을 제1호증부터 을 제4호증까지 빠짐없이 연속 제출하며 본건 사실관계를 소명합니다.",
        "입증방법",
        "1. 을 제1호증 견적서",
        "2. 을 제2호증 세금계산서",
        "3. 을 제4호증 출고확인서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) >= 1
    gap_findings = [f for f in findings if f.confidence_features.get("defect_code") == "CONTINUOUS_RANGE_GAP"]
    assert len(gap_findings) == 1
    assert "을 제3호증" in gap_findings[0].title


# --- 4. 양성 시험 3 (축 3: 본문·목록 동일 자료명의 호증 번호 불일치) ---
def test_positive_mismatched_exhibit_number_same_name():
    """축 3: 동일한 자료명(운반 사진)이 본문과 목록에서 서로 다른 호증 번호로 매핑됨."""
    doc = _make_doc([
        "본문에서는 갑 제22호증 운반 사진에 나타난 바와 같이 하자 상태가 심각합니다.",
        "입증방법",
        "1. 갑 제23호증 운반 사진",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) >= 1
    name_mismatches = [f for f in findings if f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"]
    assert len(name_mismatches) == 1
    assert "운반 사진" in name_mismatches[0].title
    assert "갑 제22호증" in name_mismatches[0].detail and "갑 제23호증" in name_mismatches[0].detail


# --- 5. 양성 시험 4 (축 1: 별지 목록 밖 번호 원용) ---
def test_positive_annex_missing_reference():
    """축 1: 별지 증거목록에 없는 호증을 원용."""
    doc = _make_doc([
        "원고는 별지 증거목록에 없는 갑 제6호증 발주서를 근거로 납품이 완료되었다고 주장합니다.",
        "별지 증거목록 전부: 갑 제1호증, 갑 제2호증",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) >= 1
    annex_missing = [f for f in findings if f.confidence_features.get("defect_code") == "EVIDENCE_REFERENCE_MISSING"]
    assert len(annex_missing) >= 1
    assert "갑 제6호증" in annex_missing[0].title


# --- 6. 양성 시험 5 (축 4: 선언 개수와 실제 목록 수 불일치) ---
def test_positive_count_mismatch():
    """축 4: 증거목록에서 총 4개 선언했으나 실제 목록은 3개."""
    doc = _make_doc([
        "입증방법: 총 4개 서증을 제출합니다.",
        "1. 갑 제1호증 계약서",
        "2. 갑 제2호증 영수증",
        "3. 갑 제3호증 통장사본",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 1
    f = findings[0]
    assert f.confidence_features.get("defect_code") == "EXHIBIT_COUNT_MISMATCH"
    assert f.confidence_features.get("declared_count") == 4
    assert f.confidence_features.get("actual_count") == 3


# --- 7. 대조군 시험 1 (완결 선언 없는 부분 목록 정상 보호) ---
def test_control_incomplete_list_not_flagged():
    """대조군 1: 완결 선언 없는 목록에서 본문이 다른 호증을 인용해도 결함 아님 (정상 서면)."""
    doc = _make_doc([
        "원고는 갑 제1호증 및 갑 제5호증을 참조하여 변론을 준비하였습니다.",
        "입증방법",
        "1. 갑 제1호증 품의서",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"완결 선언 없는 부분 목록은 결함으로 잡히지 않아야 함: {findings}"


# --- 8. 대조군 시험 2 (이전 제출 호증 재인용 정상 보호) ---
def test_control_prior_submission_reference():
    """대조군 2: 앞서 제출한 호증 재인용은 목록에 없더라도 규칙 레벨에서 정상 보호."""
    doc = _make_doc([
        "원고는 앞서 제출한 갑 제2호증 영수증에 기재된 금액을 다시 원용합니다.",
        "증거목록 (이 서면의 제출 증거 전부)",
        "1. 갑 제5호증 점검표",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"앞서 제출한 호증 재인용은 제외되어야 함: {findings}"


# --- 9. 대조군 시험 3 (정상적인 가지번호 묶음 제출 정상 보호) ---
def test_control_normal_sub_numbering():
    """대조군 3: 정상적인 가지번호(갑 제1호증의 1, 2) 묶음 제출은 결함 아님."""
    doc = _make_doc([
        "원고는 갑 제1호증의 1 및 갑 제1호증의 2를 제출합니다.",
        "입증방법",
        "1. 갑 제1호증의 1 사진",
        "2. 갑 제1호증의 2 사진",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0


# --- 10. 대조군 시험 4 (통상 정상 소송서면) ---
def test_control_normal_pleading_no_defects():
    """대조군 4: 번호 불일치가 없는 통상 소송서면."""
    doc = _make_doc([
        "원고는 갑 제1호증 계약서에 따라 피고에게 이행을 촉구하였습니다.",
        "입증방법",
        "1. 갑 제1호증 계약서",
        "2. 갑 제2호증 내용증명",
    ])
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0
