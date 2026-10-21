"""TK-84 내부 참고자료 대조 결과의 모델 의견 및 인용문 전문 보존 시험 (표시 결함 해소).

민사소송 및 기업 법무 실무에서 내부 참고자료(규정·지침 등) 대조 시
모델 의견 및 서면/규정 인용문이 80자·120자에서 잘리지 않고,
제목은 고정 문구({참고자료명} 내부 참고자료 대조 — 법적 구속력 미판단)로 유지되며
상세 설명 및 표 본문에 전문이 온전히 제공되는지 검증한다.
"""
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List

import pytest

from packages.common.config import get_settings
from packages.common.enums import (
    EvidenceGrade,
    FindingType,
    Severity,
    VerificationProfile,
    VerificationStatus,
)
from packages.common.storage import sha256_file
from packages.rag_engine.library import ReferenceLibrary
from packages.verification_engine.candidate_verifier import ModelCandidate, verify_rag_candidate
from packages.verification_engine.gate import evaluate_gate, risk_index
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)
from packages.verification_engine.review_items import build_document_review_items


def test_tk84_candidate_verifier_full_text():
    """TK-84 단위 검증: 200자 이상의 의견과 200자 이상의 인용문이 잘리지 않고 온전히 보존됨을 검증."""
    # 200자 이상의 서면 주장 및 규정 인용, 모델 의견
    long_claim = (
        "원고는 피고 회사의 사내 복무규정 제45조 제1항에 따라 모든 근로자는 연장근로에 대한 사전 승인을 "
        "받아야만 시간외수당을 청구할 수 있다고 주장하면서, 사후 승인이나 묵시적 지시에 의한 연장근로는 "
        "일체 수당 지급 대상에서 제외된다고 강변하나 이는 근로기준법상 실근로시간 보장의 취지에 배치됩니다."
    )
    long_basis = (
        "복무규정 제45조(시간외근무): 근로자가 시간외근무를 수행하고자 하는 때에는 사전에 부서장의 "
        "서면 승인을 얻어야 한다. 다만, 긴급한 업무상 필요로 인하여 사전에 승인을 받지 못한 불가피한 "
        "사유가 있는 경우에는 사후 3일 이내에 소명자료를 첨부하여 사후 승인을 신청할 수 있다."
    )
    long_explanation = (
        "원고 서면 주장은 사후 승인 가능성을 완전히 부인하고 있으나, 참고자료인 복무규정 제45조 단서에서는 "
        "긴급한 업무상 필요에 의한 불가피한 사유가 있는 경우 사후 3일 이내에 소명자료를 제출하여 사후 승인을 "
        "받을 수 있도록 명시하고 있으므로, 서면의 절대적 사전승인 주장은 복무규정 문언과 정면으로 모순됩니다."
    )

    assert len(long_claim) >= 150
    assert len(long_basis) >= 150
    assert len(long_explanation) >= 150

    candidate = ModelCandidate(
        candidate_id="cand-tk84-01",
        model_name="mock-gemini-legal",
        claim_quote=long_claim,
        defect_type="FACT_CONTRADICTION",
        source_id="REF_HR_RULES",
        source_title="인사복무규정집",
        basis_quote=long_basis,
        explanation=long_explanation,
    )

    source = {
        "source_id": "REF_HR_RULES",
        "title": "인사복무규정집",
        "text": f"규정 전문: {long_basis} 기타 조항 생략.",
    }

    # 1. candidate_verifier 실행
    finding, err = verify_rag_candidate(
        candidate,
        document_text=f"문서 본문: {long_claim} 기타 서술.",
        sources=[source],
        document_id="doc_tk84",
        is_reference_contradiction=True,
        claim_id="C_LONG",
        claim_text=long_claim,
    )
    assert err is None
    assert finding is not None

    # 2. 요구 1: 제목은 고정 문구(참고자료명 + 내부 참고자료 대조 — 법적 구속력 미판단)이며 모델 의견 제외
    expected_title = "인사복무규정집 내부 참고자료 대조 — 법적 구속력 미판단"
    assert finding.title == expected_title
    assert long_explanation not in finding.title
    assert finding.confidence_features.get("model_opinion") == long_explanation

    # 3. 요구 2: detail에 모델 의견 전문과 두 인용 전문이 잘리지 않고 포함됨
    assert long_claim in finding.detail
    assert long_basis in finding.detail
    assert long_explanation in finding.detail

    # 4. 근거 excerpt 상한 300자 내에서 전문 보존됨
    assert len(finding.evidence) == 2
    assert finding.evidence[0].excerpt == long_claim[:300]
    assert finding.evidence[1].excerpt == long_basis[:300]

    # 5. 요구 3: C등급, SUSPICIOUS, LOW 유지
    assert finding.evidence_grade == EvidenceGrade.C
    assert finding.status == VerificationStatus.SUSPICIOUS
    assert finding.severity == Severity.LOW


def test_tk84_pipeline_entrypoint_reference_text_truncation(tmp_path, monkeypatch):
    """실제 VerificationPipeline 진입점 시험 (TK-84 점검표 1항):
    실제 파이프라인 및 review_items 생성 과정에서 200자 의견과 인용문 전문이 온전히 표출됨을 검증.
    """
    long_claim = (
        "수급인은 발주자의 추가공사 지시에 따라 기성고 비율 80% 이상의 공정을 완료하였으므로 공사대금의 "
        "즉시 지급을 구하며 계약서 제15조에 따른 지체상금 공제는 부당하다고 주장합니다."
    )
    long_basis = (
        "특약조건 제15조: 기성고 80% 이상 도달 시 지체상금은 공사 완료일까지 유예하되 최종 정산 시 "
        "상호 정산서 합의를 거쳐 확정 지급한다."
    )
    long_explanation = (
        "수급인의 즉시 전액 지급 주장은 기성고 80% 달성 시 지체상금 유예 규정과는 부합하나, 최종 정산 시 "
        "상호 정산서 합의를 거쳐 확정 지급하도록 정한 특약조건 제15조 절차 규정과 모순되는 측면이 있습니다."
    )

    doc_text = f"공사대금 청구서. {long_claim}"
    doc_path = tmp_path / "contract_tk84.txt"
    doc_path.write_text(doc_text, encoding="utf-8")

    source = {
        "source_id": "REF_SPECIAL",
        "title": "공사특약조건",
        "text": f"특약 원문: {long_basis}",
    }

    def fake_sync(self, query=None):
        self.summary.update(
            status="READY",
            files_seen=1,
            files_indexed=1,
            checked_at="2026-10-20T00:00:00Z",
            issues=[],
        )

    monkeypatch.setattr(ReferenceLibrary, "sync", fake_sync)

    def fake_review_document(document_result, references, router, context, pii):
        document_result.claims = [
            {"claim_id": "CLM_TK84", "type": "FACT", "text": long_claim},
        ]
        review = {
            "status": "ADVISORY_REVIEWED",
            "sources": [source],
            "observations": [
                {
                    "relationship": "CONTRADICTS",
                    "claim_id": "CLM_TK84",
                    "claim_quote": long_claim,
                    "source_id": "REF_SPECIAL",
                    "source_quote": long_basis,
                    "explanation": long_explanation,
                    "advisory_only": True,
                }
            ],
            "rejected_observations": [],
            "model_executed": True,
            "review_completed": True,
        }
        document_result.engine_data["rag"] = review
        return review

    monkeypatch.setattr("packages.rag_engine.review.review_document", fake_review_document)

    pipeline = VerificationPipeline()
    pipeline.settings = replace(
        get_settings(),
        rag_drive_folder_id="synthetic_folder",
        allow_network=False,
    )
    doc_input = DocumentInput(
        "doc_tk84",
        str(doc_path),
        doc_path.name,
        sha256=sha256_file(doc_path),
        mime_type="text/plain",
    )
    context = ProjectContext("test-tk84", profile=VerificationProfile.QUICK)

    result = pipeline.run("run-tk84", context, [doc_input])
    doc_res = result.documents[0]

    # Finding 검증
    rag_findings = [
        f for f in doc_res.findings
        if (getattr(f, "confidence_features", None) or {}).get("rule_id") == "RAG.REFERENCE_CONTRADICTION"
    ]
    assert len(rag_findings) == 1
    f = rag_findings[0]
    assert f.title == "공사특약조건 내부 참고자료 대조 — 법적 구속력 미판단"
    assert long_claim in f.detail
    assert long_basis in f.detail
    assert long_explanation in f.detail

    # review_items 검증: 확인할 항목 표에서 claim_text에 전문이 온전히 들어있는지 확인
    items = doc_res.review_items
    rag_item = next((it for it in items if f.finding_id in (it.finding_ids or [])), None)
    assert rag_item is not None
    # 표 본문(claim_text)에 detail 전문이 포함되어 잘리지 않음
    assert long_explanation in rag_item.claim_text


def test_tk84_gate_risk_index_excluded():
    """TK-84 안전성 검증: RAG.REFERENCE_CONTRADICTION은 risk_index 가중치 합산에서 계속 제외됨을 검증."""
    candidate = ModelCandidate(
        candidate_id="cand-tk84-02",
        model_name="mock-gemini-legal",
        claim_quote="주장 인용문",
        defect_type="FACT_CONTRADICTION",
        source_id="REF1",
        source_title="참고자료",
        basis_quote="규정 인용문",
        explanation="의견",
    )
    source = {"source_id": "REF1", "title": "참고자료", "text": "규정 인용문이 있는 원문"}
    finding, _ = verify_rag_candidate(
        candidate,
        document_text="주장 인용문이 있는 서면 본문",
        sources=[source],
        document_id="doc1",
        is_reference_contradiction=True,
        claim_id="C1",
        claim_text="주장 인용문",
    )
    assert finding is not None

    # risk_index에서 제외되어 0점 유지
    r_idx, details = risk_index([finding])
    assert r_idx == 0
    assert len(details) == 0
