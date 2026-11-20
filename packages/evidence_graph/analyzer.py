"""Legal Evidence Graph analyzer, alert deduplication, and prerequisite checklist (P3 PR-13)."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .schema import EdgeKind, LegalEvidenceGraph, NodeKind


_BROKEN_EXHIBIT_STATUSES = frozenset({"UNATTACHED", "MISSING", "CONTRADICTED"})


def analyze_evidence_graph(graph: LegalEvidenceGraph) -> Dict[str, Any]:
    """Analyze a `LegalEvidenceGraph` for broken chains, missing elements, and dedup clusters."""
    broken_authority_chains: List[Dict[str, Any]] = []
    missing_prerequisite_elements: List[Dict[str, Any]] = []
    unsupported_fact_elements: List[Dict[str, Any]] = []

    for node in graph.nodes.values():
        if node.kind in (NodeKind.LEGAL_CLAIM, NodeKind.FACT_ASSERTION):
            for edge in graph.incoming(node.node_id, kind=EdgeKind.UNDERMINES):
                src = graph.nodes.get(edge.source_id)
                if src is not None and src.kind == NodeKind.AUTHORITY_SOURCE:
                    broken_authority_chains.append({
                        "claim_node_id": node.node_id,
                        "claim_id": node.attributes.get("claim_id"),
                        "claim_label": node.label,
                        "authority_node_id": src.node_id,
                        "citation_id": src.attributes.get("citation_id"),
                        "authority_label": src.label,
                        "authority_status": src.status,
                        "reason": edge.attributes.get("reason") or src.status,
                        "finding_ids": list(src.attributes.get("finding_ids") or []),
                    })

        if node.kind == NodeKind.LEGAL_CLAIM:
            for edge in graph.outgoing(node.node_id, kind=EdgeKind.REQUIRES_ELEMENT):
                req = graph.nodes.get(edge.target_id)
                if req is None or req.kind != NodeKind.REQUIREMENT_ELEMENT:
                    continue
                satisfiers = graph.incoming(req.node_id, kind=EdgeKind.ASSERTS_SATISFACTION)
                if not satisfiers:
                    missing_prerequisite_elements.append({
                        "claim_node_id": node.node_id,
                        "claim_id": node.attributes.get("claim_id"),
                        "claim_label": node.label,
                        "element_node_id": req.node_id,
                        "element_label": req.label,
                        "finding_ids": list(node.attributes.get("finding_ids") or []),
                    })

        if node.kind == NodeKind.FACT_ASSERTION:
            for edge in graph.outgoing(node.node_id, kind=EdgeKind.PROVED_BY_EXHIBIT):
                exh = graph.nodes.get(edge.target_id)
                if exh is not None and exh.status in _BROKEN_EXHIBIT_STATUSES:
                    unsupported_fact_elements.append({
                        "fact_node_id": node.node_id,
                        "claim_id": node.attributes.get("claim_id"),
                        "fact_label": node.label,
                        "exhibit_node_id": exh.node_id,
                        "exhibit_label": exh.label,
                        "exhibit_status": exh.status,
                        "finding_ids": list(node.attributes.get("finding_ids") or []),
                    })

    # Connected component clustering for finding deduplication
    components = graph.connected_components(ignore_kinds={NodeKind.SOURCE_SPAN})
    finding_to_component: Dict[str, int] = {}
    dedup_clusters: List[Dict[str, Any]] = []
    for comp_idx, comp_nids in enumerate(components):
        comp_fids: List[str] = []
        for nid in comp_nids:
            node = graph.nodes.get(nid)
            if node is None:
                continue
            for fid in node.attributes.get("finding_ids") or []:
                fid_str = str(fid)
                if fid_str not in finding_to_component:
                    finding_to_component[fid_str] = comp_idx
                if fid_str not in comp_fids:
                    comp_fids.append(fid_str)
        if len(comp_fids) >= 2:
            dedup_clusters.append({
                "component_id": comp_idx,
                "node_ids": comp_nids,
                "finding_ids": comp_fids,
            })

    return {
        "document_id": graph.document_id,
        "broken_authority_chains": broken_authority_chains,
        "missing_prerequisite_elements": missing_prerequisite_elements,
        "unsupported_fact_elements": unsupported_fact_elements,
        "dedup_clusters": dedup_clusters,
        "finding_to_component": finding_to_component,
        "summary": {
            "broken_authority_chain_count": len(broken_authority_chains),
            "missing_prerequisite_count": len(missing_prerequisite_elements),
            "unsupported_fact_count": len(unsupported_fact_elements),
            "dedup_cluster_count": len(dedup_clusters),
        },
    }


def _finding_rank_key(finding: Any) -> Tuple[int, int]:
    from packages.verification_engine.finalize import verdict_rank
    return verdict_rank(finding)


def deduplicate_findings_by_graph(
    findings: List[Any],
    graph: LegalEvidenceGraph,
) -> Tuple[List[Any], Dict[str, Any]]:
    """Merge non-advisory findings of the same type within the same graph connected component.

    Preserves all `advisory_only` findings, disconnected findings, and different `FindingType`s.
    Merged findings are recorded in `confidence_features["merged_findings"]` and `evidence`.
    """
    analysis = analyze_evidence_graph(graph)
    finding_to_comp: Dict[str, int] = analysis["finding_to_component"]

    groups: Dict[Tuple[int, str], List[Any]] = defaultdict(list)
    for finding in findings:
        if getattr(finding, "advisory_only", False):
            continue
        fid = str(getattr(finding, "finding_id", "") or "")
        comp_id = finding_to_comp.get(fid)
        if comp_id is None:
            continue
        ftype = str(getattr(getattr(finding, "type", ""), "value", getattr(finding, "type", "")))
        groups[(comp_id, ftype)].append(finding)

    dropped: Set[str] = set()
    merged_count = 0
    for (_comp_id, _ftype), members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=_finding_rank_key, reverse=True)
        primary, rest = members[0], members[1:]
        features = primary.confidence_features
        if features is None:
            primary.confidence_features = features = {}
        merged_list = features.setdefault("merged_findings", [])
        existing_ids = {str(m.get("finding_id")) for m in merged_list if isinstance(m, dict)}

        for other in rest:
            oid = str(getattr(other, "finding_id", "") or "")
            if oid and oid not in existing_ids:
                merged_list.append({
                    "finding_id": oid,
                    "type": str(getattr(other, "type", "")),
                    "status": str(getattr(other, "status", "")),
                    "grade": str(getattr(getattr(other, "evidence_grade", ""), "value", getattr(other, "evidence_grade", ""))),
                    "title": getattr(other, "title", ""),
                    "engine": getattr(other, "engine", ""),
                    "merged_by": "evidence_graph",
                })
                existing_ids.add(oid)

            try:
                from packages.common.schemas import Evidence
                primary.evidence.append(
                    Evidence.create(
                        description=f"증거 그래프 동일 원인 병합: {getattr(other, 'title', '')}"[:300],
                        grade=other.evidence_grade,
                        document_id=other.document_id,
                        page=other.page,
                        excerpt=(getattr(other, "detail", None) or "")[:300],
                        supports=True,
                    )
                )
            except Exception:  # pragma: no cover - defensive
                pass

            for tag in getattr(other, "tags", None) or []:
                if tag not in primary.tags:
                    primary.tags.append(tag)
            if oid:
                dropped.add(oid)
                merged_count += 1

        features["graph_deduplicated"] = True

    analysis["summary"]["merged_finding_count"] = merged_count
    kept = [f for f in findings if str(getattr(f, "finding_id", "") or "") not in dropped]
    return kept, analysis


def build_prerequisite_checklist(
    analysis: Dict[str, Any],
    *,
    citation_id: Optional[str] = None,
    finding_ids: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    """Return structured prerequisite/chain checklist items matching a ReviewItem."""
    fid_set = {str(x) for x in finding_ids if x}
    checklist: List[Dict[str, Any]] = []

    for item in analysis.get("broken_authority_chains") or []:
        item_fids = {str(x) for x in (item.get("finding_ids") or [])}
        if (citation_id and item.get("citation_id") == citation_id) or (fid_set & item_fids):
            checklist.append({
                "rule": "BROKEN_AUTHORITY_CHAIN",
                "status": "FAILED",
                "target": item.get("authority_label") or "",
                "detail": f"근거 법리·판례 상태 이상 ({item.get('reason')})",
            })

    for item in analysis.get("missing_prerequisite_elements") or []:
        item_fids = {str(x) for x in (item.get("finding_ids") or [])}
        if not item_fids or (fid_set & item_fids):
            checklist.append({
                "rule": "MISSING_PREREQUISITE_ELEMENT",
                "status": "MISSING",
                "target": item.get("element_label") or "",
                "detail": f"법적 주장 '{item.get('claim_label', '')[:40]}'의 필수 요건사실 서술 누락",
            })

    for item in analysis.get("unsupported_fact_elements") or []:
        item_fids = {str(x) for x in (item.get("finding_ids") or [])}
        if not item_fids or (fid_set & item_fids):
            checklist.append({
                "rule": "UNSUPPORTED_FACT_ELEMENT",
                "status": "FAILED",
                "target": item.get("exhibit_label") or "",
                "detail": f"사실 주장 뒷받침 서증 상태 이상 ({item.get('exhibit_status')})",
            })

    return checklist
