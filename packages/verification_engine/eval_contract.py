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
    sha = doc_sha256 or getattr(getattr(doc_result, "normalized", None), "sha256", "") or ""
    doc_id = str(getattr(doc_result, "document_id", "") or "")
    engine_data = getattr(doc_result, "engine_data", None) or {}
    citations_by_id = {
        str(c.get("citation_id")): c
        for c in (getattr(doc_result, "citations", None) or [])
        if isinstance(c, dict) and c.get("citation_id")
    }
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
            quote_items.append({
                "item_id": "quote-" + _sha256_json(q_anchor),
                "citation_id": cid,
                "page": page,
                "span": span,
                "status": str(levels.get("level3") or levels.get("content") or "UNVERIFIED"),
                "errors": [],
            })

        sl = v.get("source_lookup") or {}
        src_records = v.get("source_records") or []
        src_name = str(sl.get("source") or (src_records[0].get("adapter") if src_records and isinstance(src_records[0], dict) else "") or "unknown")
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
            "status": str(sl.get("status") or v.get("status") or "UNVERIFIED"),
            "matched_count": int(sl.get("matched_count") or (1 if v.get("official_record") else 0)),
            "cause": sl.get("cause"),
            "official_span": {
                "document_id": doc_id,
                "page": page,
                "span": span,
                "length": _span_length(span),
            },
        })

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
        app_match = applicability[idx] if idx < len(applicability) and isinstance(applicability[idx], dict) else {}
        judgment = _map_claim_judgment(app_match.get("verdict") or cl.get("status") or "UNVERIFIED")
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
