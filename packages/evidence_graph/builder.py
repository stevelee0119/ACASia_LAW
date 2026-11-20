"""Legal Evidence Graph builder (P3 PR-12, Shadow Mode).

Connects extracted claims, statutory/precedent authorities, exhibits, findings,
and source spans into a unified `LegalEvidenceGraph`.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .schema import EdgeKind, GraphNode, LegalEvidenceGraph, NodeKind


_BROKEN_STATUSES = frozenset({
    "NOT_FOUND",
    "CONTRADICTED",
    "SUSPICIOUS",
    "INVALID_FORMAT",
    "INVALID",
    "OVERRULED",
})

_EXHIBIT_REF_RE = re.compile(r"([갑을병정])\s*제\s*(\d+)\s*호증(?:\s*의\s*(\d+))?")


def _span_node_id(doc_id: str, page: Any, block_id: Any, span: Any) -> str:
    raw = f"{doc_id}|{page or ''}|{block_id or ''}|{span or ''}"
    return "SPN_" + sha256(raw.encode("utf-8")).hexdigest()[:12]


def _attach_span(
    graph: LegalEvidenceGraph,
    owner_id: str,
    *,
    document_id: str,
    page: Optional[int] = None,
    block_id: Optional[str] = None,
    span: Optional[Sequence[int]] = None,
) -> None:
    if page is None and block_id is None and span is None:
        return
    spn_id = _span_node_id(document_id, page, block_id, list(span) if span else None)
    graph.add_node(
        GraphNode(
            node_id=spn_id,
            kind=NodeKind.SOURCE_SPAN,
            label=f"p.{page or '?'}" + (f" {list(span)}" if span else ""),
            document_id=document_id,
            status="LOCATED",
            attributes={
                "page": page,
                "block_id": block_id,
                "span": list(span) if span else None,
            },
        )
    )
    graph.add_edge(EdgeKind.LOCATED_AT, owner_id, spn_id)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def build_evidence_graph(
    document_id: str,
    *,
    claims: Sequence[Any] = (),
    citations: Sequence[Any] = (),
    exhibits: Sequence[Any] = (),
    findings: Sequence[Any] = (),
    requirement_rules: Optional[Dict[str, Sequence[str]]] = None,
) -> LegalEvidenceGraph:
    """Build a `LegalEvidenceGraph` for a single document from verification artifacts."""
    graph = LegalEvidenceGraph(document_id=document_id)

    # 1. Index Authority nodes from citations
    citation_node_by_id: Dict[str, str] = {}
    for idx, cit in enumerate(citations):
        cid = str(_get(cit, "citation_id") or f"CIT_{idx + 1}")
        raw_text = str(_get(cit, "raw_text") or _get(cit, "canonical_case_number") or cid)
        status = str(_get(cit, "status") or "UNVERIFIED").upper()
        node_id = f"AUTH_{cid}"
        graph.add_node(
            GraphNode(
                node_id=node_id,
                kind=NodeKind.AUTHORITY_SOURCE,
                label=raw_text,
                document_id=document_id,
                status=status,
                attributes={
                    "citation_id": cid,
                    "citation_type": str(_get(cit, "type") or ""),
                    "canonical_case_number": _get(cit, "canonical_case_number"),
                    "law_name": _get(cit, "law_name"),
                },
            )
        )
        citation_node_by_id[cid] = node_id
        _attach_span(
            graph,
            node_id,
            document_id=document_id,
            page=_get(cit, "page"),
            block_id=_get(cit, "block_id"),
            span=_get(cit, "span"),
        )

    # 2. Index Exhibit nodes
    exhibit_node_by_key: Dict[str, str] = {}
    for idx, exh in enumerate(exhibits):
        label = str(_get(exh, "label") or _get(exh, "exhibit_id") or f"EXH_{idx + 1}")
        canon = re.sub(r"\s+", "", label)
        status = str(_get(exh, "status") or "ATTACHED").upper()
        node_id = f"EXH_{canon}"
        graph.add_node(
            GraphNode(
                node_id=node_id,
                kind=NodeKind.EXHIBIT_EVIDENCE,
                label=label,
                document_id=document_id,
                status=status,
                attributes={"attached": bool(_get(exh, "attached", True))},
            )
        )
        exhibit_node_by_key[canon] = node_id

    # 3. Index Claim nodes (LEGAL_CLAIM vs FACT_ASSERTION) and link authorities/exhibits/elements
    fact_nodes: List[GraphNode] = []
    claim_nodes_by_id: Dict[str, List[str]] = {}
    req_rules = requirement_rules or {}

    for idx, clm in enumerate(claims):
        clm_id = str(_get(clm, "claim_id") or f"CLM_{idx + 1}")
        clm_type = str(_get(clm, "type") or "FACT").upper()
        text = str(_get(clm, "text") or "").strip()
        status = str(_get(clm, "status") or "UNVERIFIED").upper()
        is_legal = clm_type in ("LEGAL_ARGUMENT", "LEGAL_RULE", "CASE_HOLDING", "LEGAL_INTERPRETATION")
        kind = NodeKind.LEGAL_CLAIM if is_legal else NodeKind.FACT_ASSERTION

        base_nid = f"CLM_{clm_id}"
        node_id = base_nid
        occ = 2
        while node_id in graph.nodes:
            node_id = f"{base_nid}__{occ}"
            occ += 1

        node = graph.add_node(
            GraphNode(
                node_id=node_id,
                kind=kind,
                label=text[:120],
                document_id=document_id,
                status=status,
                attributes={
                    "claim_id": clm_id,
                    "claim_type": clm_type,
                    "full_text": text,
                },
            )
        )
        claim_nodes_by_id.setdefault(clm_id, []).append(node.node_id)
        _attach_span(
            graph,
            node.node_id,
            document_id=document_id,
            page=_get(clm, "page"),
            block_id=_get(clm, "block_id"),
            span=_get(clm, "span"),
        )
        if not is_legal:
            fact_nodes.append(node)

        for cit_id in _get(clm, "citation_ids") or []:
            auth_nid = citation_node_by_id.get(str(cit_id))
            if auth_nid:
                graph.add_edge(EdgeKind.GROUNDED_IN_AUTHORITY, node.node_id, auth_nid)
                auth_status = graph.nodes[auth_nid].status
                if auth_status in _BROKEN_STATUSES:
                    graph.add_edge(EdgeKind.UNDERMINES, auth_nid, node.node_id, reason=f"AUTHORITY_{auth_status}")
                    if auth_status == "CONTRADICTED":
                        graph.add_edge(EdgeKind.CONTRADICTS, auth_nid, node.node_id, reason="AUTHORITY_CONTRADICTED")

        for m in _EXHIBIT_REF_RE.finditer(text):
            canon = f"{m.group(1)}제{m.group(2)}호증" + (f"의{m.group(3)}" if m.group(3) else "")
            exh_nid = exhibit_node_by_key.get(canon)
            if exh_nid is None:
                exh_nid = f"EXH_{canon}"
                graph.add_node(
                    GraphNode(
                        node_id=exh_nid,
                        kind=NodeKind.EXHIBIT_EVIDENCE,
                        label=canon,
                        document_id=document_id,
                        status="UNATTACHED",
                        attributes={"attached": False},
                    )
                )
                exhibit_node_by_key[canon] = exh_nid
            graph.add_edge(EdgeKind.PROVED_BY_EXHIBIT, node.node_id, exh_nid)
            if graph.nodes[exh_nid].status in ("UNATTACHED", "MISSING", "CONTRADICTED"):
                graph.add_edge(EdgeKind.UNDERMINES, exh_nid, node.node_id, reason=f"EXHIBIT_{graph.nodes[exh_nid].status}")
                if graph.nodes[exh_nid].status == "CONTRADICTED":
                    graph.add_edge(EdgeKind.CONTRADICTS, exh_nid, node.node_id, reason="EXHIBIT_CONTRADICTED")

        if is_legal:
            for trigger_kw, elem_labels in req_rules.items():
                matched = (
                    bool(trigger_kw.search(text))
                    if isinstance(trigger_kw, re.Pattern)
                    else str(trigger_kw) in text
                )
                if matched:
                    for elem_spec in elem_labels:
                        if isinstance(elem_spec, tuple) and len(elem_spec) == 2:
                            elem_label, elem_pat = str(elem_spec[0]), elem_spec[1]
                        else:
                            elem_label, elem_pat = str(elem_spec), None
                        elem_id = "REQ_" + sha256(f"{node.node_id}|{elem_label}".encode("utf-8")).hexdigest()[:10]
                        attrs = {"pattern": elem_pat} if elem_pat is not None else {}
                        graph.add_node(
                            GraphNode(
                                node_id=elem_id,
                                kind=NodeKind.REQUIREMENT_ELEMENT,
                                label=elem_label,
                                document_id=document_id,
                                status="PENDING",
                                attributes=attrs,
                            )
                        )
                        graph.add_edge(EdgeKind.REQUIRES_ELEMENT, node.node_id, elem_id)

    # 4. Link FACT_ASSERTION nodes to REQUIREMENT_ELEMENT nodes by pattern or keyword overlap
    for req_node in [n for n in graph.nodes.values() if n.kind == NodeKind.REQUIREMENT_ELEMENT]:
        elem_pat = req_node.attributes.get("pattern")
        raw_toks = [re.sub(r"(?:은|는|이|가|을|를|의|에|도)$", "", tok) for tok in re.split(r"\s+", req_node.label)]
        kw_tokens = [tok for tok in raw_toks if len(tok) >= 2 and tok not in ("존재", "여부", "사실")]
        for f_node in fact_nodes:
            f_text = str(f_node.attributes.get("full_text") or f_node.label)
            satisfied = (
                bool(elem_pat.search(f_text))
                if isinstance(elem_pat, re.Pattern)
                else (bool(kw_tokens) and all(tok in f_text for tok in kw_tokens))
            )
            if satisfied:
                graph.add_edge(EdgeKind.ASSERTS_SATISFACTION, f_node.node_id, req_node.node_id)
                req_node.status = "ASSERTED"

    # 5. Annotate findings onto matching authority/claim nodes and link CONTRADICTS edges
    for fnd in findings:
        if _get(fnd, "advisory_only"):
            continue
        feats = _get(fnd, "confidence_features") or {}
        if not isinstance(feats, dict):
            feats = {}
        cit_id = feats.get("citation_id") or _get(fnd, "citation_id")
        f_status = str(_get(fnd, "status") or "").upper()
        f_id = str(_get(fnd, "finding_id") or "")

        if cit_id and str(cit_id) in citation_node_by_id:
            auth_nid = citation_node_by_id[str(cit_id)]
            if f_status in _BROKEN_STATUSES:
                graph.nodes[auth_nid].status = f_status
                for edge in graph.incoming(auth_nid, kind=EdgeKind.GROUNDED_IN_AUTHORITY):
                    graph.add_edge(EdgeKind.UNDERMINES, auth_nid, edge.source_id, finding_id=f_id, reason=f_status)
                    if f_status == "CONTRADICTED":
                        graph.add_edge(EdgeKind.CONTRADICTS, auth_nid, edge.source_id, finding_id=f_id, reason=f_status)
            attached_findings = graph.nodes[auth_nid].attributes.setdefault("finding_ids", [])
            if f_id:
                attached_findings.append(f_id)

        # Collect any claim_ids referenced by the finding (top-level or confidence_features)
        raw_cids: List[str] = []
        for key in ("claim_id", "target_claim_id", "contradicting_claim_id", "other_claim_id"):
            val = _get(fnd, key) or feats.get(key)
            if val:
                raw_cids.append(str(val))
        for container in (_get(fnd, "claim_ids"), feats.get("claim_ids")):
            if isinstance(container, (list, tuple)):
                raw_cids.extend(str(x) for x in container if x)

        matched_claim_nids: List[str] = []
        for cid in dict.fromkeys(raw_cids):
            matched_claim_nids.extend(claim_nodes_by_id.get(cid, []))

        if not matched_claim_nids:
            # Fallback: match by exact block_id + overlapping span if claim_id wasn't supplied
            f_block = _get(fnd, "block_id")
            if f_block:
                for nid, node in graph.nodes.items():
                    if node.kind in (NodeKind.LEGAL_CLAIM, NodeKind.FACT_ASSERTION):
                        for spn_edge in graph.outgoing(nid, kind=EdgeKind.LOCATED_AT):
                            spn_node = graph.nodes.get(spn_edge.target_id)
                            if spn_node and spn_node.attributes.get("block_id") == f_block:
                                matched_claim_nids.append(nid)

        for cnid in dict.fromkeys(matched_claim_nids):
            cnode = graph.nodes[cnid]
            cnode.attributes.setdefault("finding_ids", [])
            if f_id and f_id not in cnode.attributes["finding_ids"]:
                cnode.attributes["finding_ids"].append(f_id)
            if f_status in _BROKEN_STATUSES:
                cnode.status = f_status

        unique_cnids = list(dict.fromkeys(matched_claim_nids))
        if f_status == "CONTRADICTED" and len(unique_cnids) >= 2:
            src_nid = unique_cnids[0]
            for dst_nid in unique_cnids[1:]:
                graph.add_edge(EdgeKind.CONTRADICTS, src_nid, dst_nid, finding_id=f_id, reason="CLAIM_CONTRADICTION")

    return graph


def default_requirement_rules() -> Dict[Any, List[Any]]:
    """Build requirement_rules mapping from `CAUSE_OF_ACTION_RULES`."""
    try:
        from packages.legal_engine.actionable_guidance import CAUSE_OF_ACTION_RULES
    except Exception:  # pragma: no cover - defensive
        return {}
    rules: Dict[Any, List[Any]] = {}
    for rule in CAUSE_OF_ACTION_RULES:
        trigger = rule.get("trigger")
        elems = [(str(label), pat) for label, pat in (rule.get("elements") or []) if label]
        if trigger is not None and elems:
            rules[trigger] = elems
    return rules

