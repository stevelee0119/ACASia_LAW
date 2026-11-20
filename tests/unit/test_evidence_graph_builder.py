"""Unit tests for Legal Evidence Graph builder (P3 PR-12)."""
from __future__ import annotations

from packages.evidence_graph import EdgeKind, NodeKind, build_evidence_graph


def test_build_evidence_graph_connects_claims_elements_authorities_exhibits_and_spans():
    claims = [
        {
            "claim_id": "c1",
            "type": "LEGAL_ARGUMENT",
            "text": "피고의 행위는 직무상 정당한 명령에 따른 것이므로 위법성이 조각된다.",
            "page": 2,
            "block_id": "b10",
            "span": [0, 35],
            "citation_ids": ["cit1"],
        },
        {
            "claim_id": "c2",
            "type": "FACT",
            "text": "명령서는 갑 제1호증으로 제출되었다.",
            "page": 2,
            "block_id": "b11",
            "span": [36, 56],
        },
    ]
    citations = [
        {
            "citation_id": "cit1",
            "type": "CASE",
            "raw_text": "대법원 2020다99999 판결",
            "status": "NOT_FOUND",
            "page": 2,
            "block_id": "b10",
            "span": [10, 24],
        }
    ]
    exhibits = [
        {"exhibit_id": "e1", "label": "갑 제1호증", "status": "ATTACHED", "attached": True},
    ]
    findings = [
        {
            "finding_id": "F_1",
            "status": "NOT_FOUND",
            "confidence_features": {"citation_id": "cit1"},
        }
    ]
    rules = {
        "위법성이 조각": ["명령의 존재", "명령의 적법성"],
    }

    graph = build_evidence_graph(
        "doc_graph_1",
        claims=claims,
        citations=citations,
        exhibits=exhibits,
        findings=findings,
        requirement_rules=rules,
    )
    summary = graph.summary()
    assert summary["nodes_by_kind"][NodeKind.LEGAL_CLAIM.value] == 1
    assert summary["nodes_by_kind"][NodeKind.FACT_ASSERTION.value] == 1
    assert summary["nodes_by_kind"][NodeKind.REQUIREMENT_ELEMENT.value] == 2
    assert summary["nodes_by_kind"][NodeKind.AUTHORITY_SOURCE.value] == 1
    assert summary["nodes_by_kind"][NodeKind.EXHIBIT_EVIDENCE.value] == 1
    assert summary["nodes_by_kind"][NodeKind.SOURCE_SPAN.value] >= 2

    # Broken authority undermines legal claim
    undermines = graph.outgoing("AUTH_cit1", kind=EdgeKind.UNDERMINES)
    assert len(undermines) == 1
    assert undermines[0].target_id == "CLM_c1"

    # Requirement element "명령의 존재" is satisfied by fact assertion c2, while "명령의 적법성" remains PENDING
    req_nodes = [n for n in graph.nodes.values() if n.kind == NodeKind.REQUIREMENT_ELEMENT]
    by_label = {n.label: n.status for n in req_nodes}
    assert by_label["명령의 존재"] == "ASSERTED"
    assert by_label["명령의 적법성"] == "PENDING"

    # All nodes belong to one connected component when ignoring SOURCE_SPAN hubs
    comps = graph.connected_components()
    assert len(comps) == 1
