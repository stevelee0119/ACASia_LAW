from __future__ import annotations

from types import SimpleNamespace

import pytest

from packages.common.config import reset_settings
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Finding, NormalizedDocument
from packages.evidence_graph import (
    analyze_evidence_graph,
    build_evidence_graph,
    deduplicate_findings_by_graph,
)
from packages.verification_engine.finalize import finalize_document_findings
from packages.verification_engine.review_items import build_document_review_items


def _make_finding(
    fid: str,
    *,
    ftype: FindingType = FindingType.STATUTE_NONEXISTENT,
    status: VerificationStatus = VerificationStatus.NOT_FOUND,
    grade: EvidenceGrade = EvidenceGrade.B,
    severity: Severity = Severity.HIGH,
    advisory: bool = False,
    citation_id: str | None = None,
    claim_id: str | None = None,
    title: str = "검증 항목",
) -> Finding:
    feats = {}
    if citation_id:
        feats["citation_id"] = citation_id
    if claim_id:
        feats["claim_id"] = claim_id
    return Finding.create(
        type=ftype,
        title=title,
        detail=f"{title} 상세",
        severity=severity,
        evidence_grade=grade,
        status=status,
        engine="test_engine",
        advisory_only=advisory,
        confidence_features=feats,
    ) | {} if False else Finding(
        finding_id=fid,
        type=ftype,
        title=title,
        detail=f"{title} 상세",
        severity=severity,
        evidence_grade=grade,
        status=status,
        engine="test_engine",
        advisory_only=advisory,
        confidence_features=feats,
    )


def test_analyzer_detects_broken_chain_missing_element_and_unsupported_exhibit() -> None:
    graph = build_evidence_graph(
        "doc-p1",
        citations=[
            {"citation_id": "CIT_1", "raw_text": "가상판례 1호", "status": "NOT_FOUND", "page": 1},
        ],
        exhibits=[
            {"label": "갑 제2호증", "status": "UNATTACHED", "attached": False},
        ],
        claims=[
            {
                "claim_id": "CLM_LEGAL",
                "type": "LEGAL_ARGUMENT",
                "text": "계약 해지에 따른 손해배상 청구가 성립한다.",
                "citation_ids": ["CIT_1"],
            },
            {
                "claim_id": "CLM_FACT_1",
                "type": "FACT",
                "text": "적법한 해지 통지가 도달하였다.",
            },
            {
                "claim_id": "CLM_FACT_2",
                "type": "FACT",
                "text": "갑 제2호증에 따라 손해가 발생하였다.",
            },
        ],
        requirement_rules={"손해배상": ["해지 통지", "인과관계 입증"]},
    )

    analysis = analyze_evidence_graph(graph)
    assert analysis["summary"]["broken_authority_chain_count"] == 1
    assert analysis["broken_authority_chains"][0]["citation_id"] == "CIT_1"

    assert analysis["summary"]["missing_prerequisite_count"] == 1
    assert analysis["missing_prerequisite_elements"][0]["element_label"] == "인과관계 입증"

    assert analysis["summary"]["unsupported_fact_count"] == 1
    assert analysis["unsupported_fact_elements"][0]["exhibit_label"] == "갑 제2호증"


def test_analyzer_control_valid_graph_has_zero_defects() -> None:
    graph = build_evidence_graph(
        "doc-ctrl-1",
        citations=[
            {"citation_id": "CIT_OK", "raw_text": "유효 법령 조문", "status": "VERIFIED", "page": 1},
        ],
        exhibits=[
            {"label": "갑 제1호증", "status": "ATTACHED", "attached": True},
        ],
        claims=[
            {
                "claim_id": "CLM_L",
                "type": "LEGAL_ARGUMENT",
                "text": "불법행위 손해배상 요건이 충족된다.",
                "citation_ids": ["CIT_OK"],
            },
            {
                "claim_id": "CLM_F",
                "type": "FACT",
                "text": "갑 제1호증으로 손해액 산정이 증명된다.",
            },
        ],
        requirement_rules={"손해배상": ["손해액 산정"]},
    )

    analysis = analyze_evidence_graph(graph)
    assert analysis["summary"]["broken_authority_chain_count"] == 0
    assert analysis["summary"]["missing_prerequisite_count"] == 0
    assert analysis["summary"]["unsupported_fact_count"] == 0


def test_deduplicate_findings_by_graph_merges_same_component_and_preserves_controls() -> None:
    f_primary = _make_finding(
        "FND_1",
        ftype=FindingType.STATUTE_NONEXISTENT,
        status=VerificationStatus.CONTRADICTED,
        grade=EvidenceGrade.A,
        citation_id="CIT_1",
        title="근거 판례 모순",
    )
    f_dup = _make_finding(
        "FND_2",
        ftype=FindingType.STATUTE_NONEXISTENT,
        status=VerificationStatus.NOT_FOUND,
        grade=EvidenceGrade.B,
        claim_id="CLM_1",
        title="동일 연쇄 주장 경고",
    )
    f_diff_type = _make_finding(
        "FND_3",
        ftype=FindingType.EVIDENCE_DATE_INVALID,
        status=VerificationStatus.CONTRADICTED,
        grade=EvidenceGrade.B,
        claim_id="CLM_1",
        title="별개 날짜 오류",
    )
    f_advisory = _make_finding(
        "FND_4",
        ftype=FindingType.STATUTE_NONEXISTENT,
        status=VerificationStatus.UNVERIFIED,
        grade=EvidenceGrade.C,
        advisory=True,
        claim_id="CLM_1",
        title="참고용 경고",
    )
    f_disconnected = _make_finding(
        "FND_5",
        ftype=FindingType.STATUTE_NONEXISTENT,
        status=VerificationStatus.NOT_FOUND,
        grade=EvidenceGrade.B,
        citation_id="CIT_2",
        title="별도 컴포넌트 경고",
    )

    graph = build_evidence_graph(
        "doc-dedup",
        citations=[
            {"citation_id": "CIT_1", "raw_text": "판례A", "status": "CONTRADICTED"},
            {"citation_id": "CIT_2", "raw_text": "판례B", "status": "NOT_FOUND"},
        ],
        claims=[
            {"claim_id": "CLM_1", "type": "LEGAL_ARGUMENT", "text": "주장", "citation_ids": ["CIT_1"]},
        ],
        findings=[f_primary, f_dup, f_diff_type, f_advisory, f_disconnected],
    )

    kept, analysis = deduplicate_findings_by_graph(
        [f_primary, f_dup, f_diff_type, f_advisory, f_disconnected],
        graph,
    )
    kept_ids = [f.finding_id for f in kept]
    assert kept_ids == ["FND_1", "FND_3", "FND_4", "FND_5"]
    assert analysis["summary"]["merged_finding_count"] == 1
    assert f_primary.confidence_features["graph_deduplicated"] is True
    assert any(m["finding_id"] == "FND_2" for m in f_primary.confidence_features["merged_findings"])

    # Also verify finalize_document_findings integration
    finalized = finalize_document_findings(
        [_make_finding("FND_1", grade=EvidenceGrade.A, status=VerificationStatus.CONTRADICTED, citation_id="CIT_1"),
         _make_finding("FND_2", grade=EvidenceGrade.B, status=VerificationStatus.NOT_FOUND, claim_id="CLM_1")],
        None,
        "doc-dedup",
        evidence_graph=graph,
    )
    assert [f.finding_id for f in finalized] == ["FND_1"]


def test_review_items_attach_prerequisite_checklist_only_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = build_evidence_graph(
        "doc-rev",
        citations=[{"citation_id": "CIT_1", "raw_text": "가상조문", "status": "NOT_FOUND"}],
        claims=[{"claim_id": "CLM_1", "type": "LEGAL_ARGUMENT", "text": "손해배상 청구", "citation_ids": ["CIT_1"]}],
        findings=[_make_finding("FND_1", citation_id="CIT_1")],
        requirement_rules={"손해배상": ["과실 입증"]},
    )
    analysis = analyze_evidence_graph(graph)
    doc = NormalizedDocument(document_id="doc-rev", filename="sample.txt", mime_type="text/plain", sha256="0" * 64)
    doc_result = SimpleNamespace(
        document_id="doc-rev",
        filename="sample.txt",
        findings=[_make_finding("FND_1", citation_id="CIT_1")],
        citations=[{"citation_id": "CIT_1", "raw_text": "가상조문", "type": "STATUTE"}],
        claims=[],
        exhibits=[],
        engine_data={
            "legal_verdicts": [{"citation_id": "CIT_1", "status": "NOT_FOUND"}],
            "evidence_graph_analysis": analysis,
        },
    )
    ctx = SimpleNamespace()

    # Shadow mode (default): reasoning_sections must not be altered
    monkeypatch.setenv("LV_EVIDENCE_GRAPH_MODE", "shadow")
    reset_settings()
    shadow_items = build_document_review_items(doc_result, doc, ctx)
    assert shadow_items
    assert not (shadow_items[0].reasoning_sections or {}).get("prerequisite_checklist")

    # Canary mode: prerequisite_checklist is attached
    monkeypatch.setenv("LV_EVIDENCE_GRAPH_MODE", "canary")
    reset_settings()
    canary_items = build_document_review_items(doc_result, doc, ctx)
    checklist = (canary_items[0].reasoning_sections or {}).get("prerequisite_checklist") or []
    rules = {c["rule"] for c in checklist}
    assert "BROKEN_AUTHORITY_CHAIN" in rules
    assert "MISSING_PREREQUISITE_ELEMENT" in rules
    reset_settings()
