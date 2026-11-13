"""TK-159(B1): 판정마다 근거로 쓴 공식 원문의 식별자·구간을 결과에 싣는다.

- 판단(일치·불일치)과 조회 실패·미발견을 상태로 구분한다(basis_status).
- 구간은 비교에 실제로 쓴 정규화 문자열(normalize_quote) 기준의 [start, end)와 그 문자열의 SHA-256으로 적는다.
  원문 자체는 다시 싣지 않고 짧은 발췌(최대 200자)만 둔다.
- 공식 원문 없이 형식·범위 규칙으로 정한 불일치는 RULE_BASED(근거=규칙 이름)로 적는다.
- 확인됨(VERIFIED)·불일치(CONTRADICTED) 판정인데 근거가 없으면 MISSING_BASIS로 드러낸다(판정은 바꾸지 않는다).
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from packages.common.textutil import locate_fuzzy_normalized, normalize_quote

EXCERPT_LIMIT = 200


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def quote_span(quoted: str, official_text: str) -> Optional[Dict[str, Any]]:
    """인용문이 공식 원문(정규화)에서 가장 가깝게 맞는 구간. 원문이 비면 None."""
    haystack, needle = normalize_quote(official_text or ""), normalize_quote(quoted or "")
    if not haystack or not needle:
        return None
    ratio, start = locate_fuzzy_normalized(haystack, needle)
    if start < 0:
        return None
    end = min(len(haystack), start + len(needle))
    return {"normalization": "normalize_quote", "start": start, "end": end, "similarity": round(ratio, 3),
            "text_sha256": sha256_text(haystack), "text_length": len(haystack),
            "excerpt": haystack[start:end][:EXCERPT_LIMIT]}


def _source(official: Dict[str, Any], kind: str) -> Optional[Dict[str, Any]]:
    if kind in ("CASE", "CONSTITUTIONAL"):
        ident = official.get("source_id") or official.get("case_number")
        if not ident:
            return None
        return {"kind": "OFFICIAL_CASE" if official.get("source_id") else "CASE_RECORD", "id": str(ident),
                "court": official.get("court"), "decision_date": official.get("decision_date"),
                "case_number": official.get("case_number"), "detail_link": official.get("detail_link"),
                "object_ref": official.get("source_object_ref")}
    if official.get("law_id"):
        return {"kind": "OFFICIAL_LAW", "id": str(official["law_id"]), "version_id": official.get("version_id"),
                "effective_from": official.get("effective_from"), "version_selection": official.get("version_selection"),
                "detail_link": official.get("detail_link"), "object_ref": official.get("source_object_ref")}
    if official.get("law_name"):
        # 내부 사본(mirror) 조문: 공식 응답이 아니므로 종류를 구분해 둔다.
        return {"kind": "MIRROR_LAW", "id": str(official.get("law_name")), "effective_from": official.get("effective_from"),
                "detail_link": official.get("detail_link")}
    return None


def build_basis(verdict) -> Dict[str, Any]:
    official = verdict.official_record or {}
    kind = str(verdict.citation.type)
    status = str(verdict.status)
    review = verdict.review or {}
    source = _source(official, kind) if official else None
    passage = None
    if kind in ("CASE", "CONSTITUTIONAL"):
        passage = review.get("quote_span")
    else:
        provision = review.get("provision") or {}
        if provision.get("status") in ("VERIFIED", "DELETED") and provision.get("text"):
            passage = {"path": provision.get("path"), "text_sha256": sha256_text(provision["text"]),
                       "text_length": len(provision["text"]), "excerpt": provision["text"][:EXCERPT_LIMIT]}
    if source is None:
        lookup_failed = any((f.confidence_features or {}).get("reason_code") for f in verdict.findings
                            if str(f.status) == "UNVERIFIED") if verdict.findings else False
        basis_status = "NOT_FOUND" if status == "NOT_FOUND" else "LOOKUP_FAILED" if (lookup_failed or status == "UNVERIFIED") \
            else "NO_SOURCE"
        rules = sorted({str((f.confidence_features or {}).get("rule_id") or f.type) for f in verdict.findings
                        if (f.confidence_features or {}).get("deterministic_rule")})
        if status in ("VERIFIED", "CONTRADICTED") and rules and status == "CONTRADICTED":
            # 공식 원문 대조가 아니라 형식·범위 규칙으로 정한 판정(예: 성립할 수 없는 사건번호). 근거는 규칙이다.
            basis_status, source = "RULE_BASED", {"kind": "DETERMINISTIC_RULE", "rules": rules}
        elif status in ("VERIFIED", "CONTRADICTED"):
            basis_status = "MISSING_BASIS"
    elif status == "CONTRADICTED":
        basis_status = "SOURCE_MISMATCHED"
    elif status in ("VERIFIED", "PARTIALLY_VERIFIED"):
        basis_status = "SOURCE_MATCHED"
    else:
        basis_status = "SOURCE_FOUND_NOT_DECIDED"
    return {"basis_status": basis_status, "source": source, "passage": passage}
