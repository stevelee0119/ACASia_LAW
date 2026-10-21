"""TK-91 증거 과장(EVI-OVR) 구조적 탐지 및 확정 기준 검증 시험.

- 설계 메모 92_evi_ovr_evidence_overreach_design.md 및 평가 측 조건부 승인 조건 4개/2차 지침 준수
- 합성 양성 4건, 대조군 5건, 실제 진입점 파이프라인 시험 1건
"""

import pytest
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.evidence_consistency import check_evidence_overreach, check_exhibits


def _make_doc(*texts: str, doc_id: str = "doc_ovr_test_1") -> NormalizedDocument:
    blocks = [
        Block(block_id=f"b{i+1}", text=t, page=1, visible=True, source_layer="visible_text")
        for i, t in enumerate(texts)
    ]
    page = Page(page_number=1, blocks=blocks, width=595.0, height=842.0)
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="0000000000000000000000000000000000000000000000000000000000000000",
        pages=[page],
    )


# --- 1. 합성 양성 시험 (4건) -----------------------------------------------------------

def test_positive_notice_sender_identified_overreach_verified_b():
    """양성 1 (조건 1): 발신인(원고)이 확인된 일방 최고서로 피고의 계약해제 동의·승낙 주장 시 확정 B(VERIFIED·HIGH)."""
    doc = _make_doc(
        "원고가 피고에게 발송한 최고서에 따라 피고는 계약 해제에 동의하였는바(갑 제3호증), 원상회복을 구합니다.",
        "입증방법",
        "1. 갑 제1호증 매매계약서",
        "2. 갑 제3호증 내용증명우편(최고서) (발신인: 원고)",
    )
    findings = check_evidence_overreach(doc)
    ovr = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr) == 1
    f = ovr[0]
    assert f.evidence_grade == EvidenceGrade.B
    assert f.severity == Severity.HIGH
    assert f.status == VerificationStatus.CONTRADICTED
    assert "갑 제3호증" in f.title
    assert "상대방 승낙" in f.title


def test_positive_estimate_payment_completion_overreach_verified_b():
    """양성 2 (2차 지침 1항): 견적서로 공사대금 전액 완납/정산 완료 주장 시 발신인 불문 확정 B(VERIFIED·HIGH)."""
    doc = _make_doc(
        "피고는 공사대금 5,000만 원을 전액 정산 완료하였으므로(을 제2호증), 추가 청구는 부당합니다.",
        "입증방법",
        "1. 을 제1호증 공사도급계약서",
        "2. 을 제2호증 공사 견적서",
    )
    findings = check_evidence_overreach(doc)
    ovr = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr) == 1
    f = ovr[0]
    assert f.evidence_grade == EvidenceGrade.B
    assert f.severity == Severity.HIGH
    assert f.status == VerificationStatus.CONTRADICTED
    assert "을 제2호증" in f.title
    assert "완납" in f.title or "정산" in f.detail


def test_positive_identifier_payment_overreach_verified_b():
    """양성 3: 통장 표지 사본으로 물품대금 완납 주장 시 확정 B(VERIFIED·HIGH)."""
    doc = _make_doc(
        "원고는 물품대금 전액을 완납한 사실을(갑 제4호증) 분명히 밝힙니다.",
        "입증방법",
        "1. 갑 제1호증 물품공급계약서",
        "2. 갑 제4호증 통장 표지 사본",
    )
    findings = check_evidence_overreach(doc)
    ovr = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr) == 1
    f = ovr[0]
    assert f.evidence_grade == EvidenceGrade.B
    assert f.severity == Severity.HIGH
    assert "갑 제4호증" in f.title


def test_positive_diagnostic_direct_assertion_unverified_c():
    """양성 4 (조건 2): 진단서 단독으로 가해 사실을 직접 입증한다고 단정한 경우 미확인 C(UNVERIFIED·MEDIUM)."""
    doc = _make_doc(
        "피고가 원고에게 불법행위를 가한 사실은 상해진단서(갑 제5호증)로 직접 확인됩니다.",
        "입증방법",
        "1. 갑 제5호증 상해진단서",
    )
    findings = check_evidence_overreach(doc)
    ovr = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr) == 1
    f = ovr[0]
    assert f.evidence_grade == EvidenceGrade.C
    assert f.severity == Severity.MEDIUM
    assert f.status == VerificationStatus.UNVERIFIED
    assert "갑 제5호증" in f.title


# --- 2. 대조군 시험 (5건) -------------------------------------------------------------

def test_control_notice_proper_dispatch_proof_no_finding():
    """대조 1: 통지·최고 발송 사실 자체를 입증하는 정상 서면 오탐 배제."""
    doc = _make_doc(
        "원고는 피고에게 채무 이행을 최고하는 내용증명을 발송하였습니다(갑 제2호증).",
        "입증방법",
        "1. 갑 제1호증 차용증",
        "2. 갑 제2호증 내용증명우편",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"통지 사실 정상 입증은 과장으로 판정되지 않아야 함: {findings}"


def test_control_diagnostic_result_indirect_proof_no_finding():
    """대조 2 (조건 2): 진단서로 상해 발생 결과를 입증하는 통상 실무 간접증거 인용 오탐 배제."""
    doc = _make_doc(
        "피고의 불법행위로 인해 원고는 전치 3주의 상해를 입었는바(갑 제4호증), 치료비 상당의 손해배상을 구합니다.",
        "입증방법",
        "1. 갑 제4호증 상해진단서",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"진단서의 결과 입증 및 통상 간접증거 인용은 오탐 배제되어야 함: {findings}"


def test_control_financial_receipt_proof_no_finding():
    """대조 3: 입금확인증으로 공사대금 지급 사실을 입증하는 정상 서면 오탐 배제."""
    doc = _make_doc(
        "피고는 공사대금 3,000만 원을 정상 지급 완료하였습니다(을 제3호증).",
        "입증방법",
        "1. 을 제3호증 입금확인증",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"금융 입금확인증으로 지급 입증은 정상이므로 오탐 배제되어야 함: {findings}"


def test_control_bundled_exhibits_with_proof_no_finding():
    """대조 4 (조건 3): 복수 서증 결합 원용(견적서 + 입금확인증) 시 과장 판정 배제."""
    doc = _make_doc(
        "원고는 공사대금을 정산 지급 완료하였습니다(을 제2호증, 을 제3호증).",
        "입증방법",
        "1. 을 제2호증 공사 견적서",
        "2. 을 제3호증 계좌거래내역 입금확인증",
    )
    findings = check_evidence_overreach(doc)
    assert len(findings) == 0, f"입금확인증이 결합 원용되었으므로 과장으로 판정되지 않아야 함: {findings}"


def test_control_notice_unknown_sender_fixed_to_grade_c():
    """대조 5 (조건 1 및 2차 지침 2항): 발신인 불명 내용증명으로 상대방 채무승인 주장 시 C등급(UNVERIFIED)으로 고정."""
    doc = _make_doc(
        "피고는 자신의 채무를 명시적으로 승인하였습니다(갑 제6호증 내용증명).",
        "입증방법",
        "1. 갑 제6호증 내용증명우편",
    )
    findings = check_evidence_overreach(doc)
    ovr = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr) == 1, f"발신인 불명 내용증명의 채무승인 주장은 C등급으로 검출되어야 함: {ovr}"
    f = ovr[0]
    # 평가 측 지침: 대조 5의 기대값은 EvidenceGrade.C로 고정
    assert f.evidence_grade == EvidenceGrade.C
    assert f.severity == Severity.MEDIUM
    assert f.status == VerificationStatus.UNVERIFIED


# --- 3. 실제 진입점 파이프라인 연계 시험 (1건) ---------------------------------------

def test_pipeline_evidence_overreach_entrypoint():
    """실제 check_exhibits 진입점을 통한 EVI-OVR 검출 및 속성 완전성 검증."""
    doc = _make_doc(
        "원고는 피고에게 공사비 산출내역서(을 제2호증)에 따라 공사대금을 전액 완납하였습니다.",
        "입증방법",
        "1. 을 제1호증 공사도급계약서",
        "2. 을 제2호증 공사비 산출내역서",
    )
    findings = check_exhibits(doc)
    ovr_findings = [f for f in findings if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]
    assert len(ovr_findings) == 1
    f = ovr_findings[0]
    assert f.evidence_grade == EvidenceGrade.B
    assert f.confidence_features.get("exhibit") == "을 제2호증"
    assert f.confidence_features.get("category") == "ESTIMATE_OVERREACH"
    assert "을 제2호증" in f.evidence[0].excerpt
