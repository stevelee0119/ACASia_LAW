"""4-dimensional structured evaluation output contract (0.28.0 Task 4).

Builds PII-free, independent evaluation records for:
1. identity
2. quote
3. claim_applicability (SUPPORTS / CONTRADICTS / INSUFFICIENT + evidence_spans)
4. source_retrieval
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


def _sha256_json(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _span_length(span: Any) -> int:
    if isinstance(span, (list, tuple)) and len(span) == 2:
        try:
            return max(0, int(span[1]) - int(span[0]))
        except (TypeError, ValueError):
            return 0
    return 0


def _map_claim_judgment(status: str) -> str:
    st = str(status or "").upper()
    if st == "VERIFIED":
        return "SUPPORTS"
    if st in ("CONTRADICTED", "NOT_FOUND", "INVALID", "INVALID_FORMAT", "SUSPICIOUS"):
        return "CONTRADICTS"
    return "INSUFFICIENT"


def build_evaluation_dimensions(doc_result: Any, *, doc_sha256: str = "") -> Dict[str, List[Dict[str, Any]]]:
    """Extract 4 independent, PII-free evaluation dimensions from a DocumentResult."""
    sha = (
        doc_sha256
        or getattr(getattr(doc_result, "normalized", None), "sha256", "")
        or getattr(doc_result, "sha256", "")
        or ""
    )
    doc_id = str(getattr(doc_result, "document_id", "") or "")
    engine_data = getattr(doc_result, "engine_data", None) or {}
    citations_by_id = {
        str(c.get("citation_id")): c
        for c in (getattr(doc_result, "citations", None) or [])
        if isinstance(c, dict) and c.get("citation_id")
    }
    doc_source_by_id: Dict[str, Dict[str, Any]] = {}
    for sr in (getattr(doc_result, "source_records", None) or []):
        sr_dict = sr.to_dict() if hasattr(sr, "to_dict") else (sr if isinstance(sr, dict) else {})
        if sr_dict.get("source_record_id"):
            doc_source_by_id[str(sr_dict["source_record_id"])] = sr_dict

    verdicts = engine_data.get("legal_verdicts") or []
    applicability = engine_data.get("case_applicability_reviews") or []

    identity_items: List[Dict[str, Any]] = []
    quote_items: List[Dict[str, Any]] = []
    source_items: List[Dict[str, Any]] = []

    for v in verdicts:
        if not isinstance(v, dict):
            continue
        cid = str(v.get("citation_id") or "")
        cit = citations_by_id.get(cid, {})
        raw_text = str(cit.get("raw_text") or cid)
        page = cit.get("page")
        span = cit.get("span")
        levels = v.get("levels") or {}
        text_hash = _sha256_text(raw_text)

        id_anchor = {
            "document_sha256": sha,
            "page": page,
            "span": span,
            "text_sha256": text_hash,
            "dimension": "identity",
        }
        identity_items.append({
            "item_id": "identity-" + _sha256_json(id_anchor),
            "citation_id": cid,
            "page": page,
            "span": span,
            "status": str(levels.get("level1") or levels.get("existence") or v.get("status") or "UNVERIFIED"),
            "errors": [str(f.get("type")) for f in (v.get("findings") or []) if isinstance(f, dict) and f.get("type")],
        })

        if cit.get("quoted_text"):
            q_anchor = {
                "document_sha256": sha,
                "page": page,
                "span": span,
                "text_sha256": text_hash,
                "dimension": "quote",
            }
            quote_errors = [
                str(f.get("type"))
                for f in (v.get("findings") or [])
                if isinstance(f, dict) and f.get("type") in ("CASE_QUOTE_MISMATCH", "LAW_CITATION_ERROR")
            ]
            quote_items.append({
                "item_id": "quote-" + _sha256_json(q_anchor),
                "citation_id": cid,
                "page": page,
                "span": span,
                "status": str(levels.get("level3") or levels.get("content") or "UNVERIFIED"),
                "errors": quote_errors,
            })

        sl = v.get("source_lookup") or {}
        sl_reqs = sl.get("requests") if isinstance(sl.get("requests"), list) else []
        src_records = [
            doc_source_by_id[str(sid)]
            for sid in (v.get("source_record_ids") or [])
            if str(sid) in doc_source_by_id
        ] or (v.get("source_records") or [])
        first_src = src_records[0] if src_records and isinstance(src_records[0], dict) else {}
        first_req = sl_reqs[0] if sl_reqs and isinstance(sl_reqs[0], dict) else {}
        src_name = str(
            sl.get("source")
            or first_src.get("adapter")
            or first_req.get("adapter")
            or "unknown"
        )
        raw_src_status = str(
            sl.get("status")
            or first_src.get("status")
            or first_req.get("status")
            or v.get("status")
            or "UNVERIFIED"
        ).replace("AdapterStatus.", "")
        s_anchor = {
            "document_sha256": sha,
            "citation_id": cid,
            "source_name": src_name,
            "dimension": "source_retrieval",
        }
        source_items.append({
            "item_id": "source-" + _sha256_json(s_anchor),
            "citation_id": cid,
            "source_name": src_name,
            "status": raw_src_status,
            "matched_count": int(sl.get("matched_count") or (1 if v.get("official_record") else 0)),
            "cause": sl.get("cause"),
            "official_span": {
                "document_id": doc_id,
                "page": page,
                "span": span,
                "length": _span_length(span),
            },
        })

    verdict_by_cid = {str(v.get("citation_id")): v for v in verdicts if isinstance(v, dict) and v.get("citation_id")}
    app_by_cid = {str(a.get("citation_id")): a for a in applicability if isinstance(a, dict) and a.get("citation_id")}
    claim_items: List[Dict[str, Any]] = []
    claims = getattr(doc_result, "claims", None) or []
    for idx, cl in enumerate(claims):
        if not isinstance(cl, dict):
            continue
        claim_text = str(cl.get("text") or cl.get("claim") or "")
        page = cl.get("page")
        span = cl.get("span")
        c_anchor = {
            "document_sha256": sha,
            "page": page,
            "span": span,
            "claim_sha256": _sha256_text(claim_text or f"claim:{idx}"),
            "dimension": "claim_applicability",
        }
        linked_statuses: List[str] = []
        for cid in (cl.get("citation_ids") or []):
            cid_str = str(cid)
            if cid_str in app_by_cid and app_by_cid[cid_str].get("verdict"):
                linked_statuses.append(str(app_by_cid[cid_str]["verdict"]))
            elif cid_str in verdict_by_cid and verdict_by_cid[cid_str].get("status"):
                linked_statuses.append(str(verdict_by_cid[cid_str]["status"]))
        app_match = applicability[idx] if idx < len(applicability) and isinstance(applicability[idx], dict) else {}
        raw_claim_status = (
            app_match.get("verdict")
            or (linked_statuses[0] if linked_statuses else None)
            or cl.get("status")
            or "UNVERIFIED"
        )
        judgment = _map_claim_judgment(raw_claim_status)
        claim_items.append({
            "item_id": "claim-" + _sha256_json(c_anchor),
            "claim_id": str(cl.get("claim_id") or f"C_{idx}"),
            "judgment": judgment,
            "evidence_spans": [
                {
                    "document_id": doc_id,
                    "page": page,
                    "span": span,
                    "length": _span_length(span),
                }
            ],
        })

    return {
        "identity": identity_items,
        "quote": quote_items,
        "claim_applicability": claim_items,
        "source_retrieval": source_items,
    }
