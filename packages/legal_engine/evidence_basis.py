"""TK-159(B1): 판정마다 근거로 쓴 공식 원문의 식별자·구간을 결과에 싣는다.

- 판단(일치·불일치)과 조회 실패·미발견을 상태로 구분한다(basis_status).
- 구간은 비교에 실제로 쓴 정규화 문자열(normalize_quote) 기준의 [start, end)와 그 문자열의 SHA-256으로 적는다.
  원문 자체는 다시 싣지 않고 짧은 발췌(최대 200자)만 둔다.
- 공식 원문 없이 형식·범위 규칙으로 정한 불일치는 RULE_BASED(근거=규칙 이름)로 적는다.
- 확인됨(VERIFIED)·불일치(CONTRADICTED) 판정인데 근거가 없으면 MISSING_BASIS로 드러낸다(판정은 바꾸지 않는다).
"""
from __future__ import annotations

import hashlib
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

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


ALIGN_LIMIT = 600      # 원문 대조 보기에 싣는 정규화 문자 수 상한(인용문·원문 각각)
ALIGN_MIN_SIMILARITY = 0.6  # 이보다 낮으면 같은 문장이라 보기 어렵다 — 나란히 보이지 않는다


_EDGE_PUNCT = "\"'.,;:!?)]}」』〉》”’"


def _key(token: str) -> str:
    """어절 비교 열쇠: 끝 문장부호·닫는 따옴표만 뗀다(조사·어미 차이는 그대로 차이로 본다)."""
    return token.rstrip(_EDGE_PUNCT).lstrip("\"'(「『〈《“‘") or token


def align_quote(quoted: str, official_text: str, limit: int = ALIGN_LIMIT) -> Optional[Dict[str, Any]]:
    """TK-163: 인용문과 공식 원문의 맞는 구간을 어절 단위로 맞대어 나란히 보일 자료를 만든다.

    반환: {"quoted": [[어절, 표지]], "official": [[어절, 표지]], "similarity", "truncated", "changed"}
    표지: same(같음) · changed(바뀜) · added(인용문에만 있음) · removed(원문에만 있음 — 인용에서 빠짐).
    - 원문 창은 인용문 길이보다 넉넉히 잡고, 인용 범위 밖(첫 일치 앞·마지막 일치 뒤)의 원문 어절은 버린다.
    - 인용이 어절 중간에서 시작·끝나는 경우(예: 인용 '경우' ↔ 원문 '경우에')는 같은 어절로 본다.
    원문 구간을 찾지 못했거나 유사도가 낮으면 None(판정은 바꾸지 않는다, 표시 자료일 뿐이다).
    """
    span = quote_span(quoted, official_text)
    if span is None or span["similarity"] < ALIGN_MIN_SIMILARITY:
        return None
    haystack, needle = normalize_quote(official_text or ""), normalize_quote(quoted or "")
    start = span["start"]
    end = min(len(haystack), span["end"] + len(needle) // 3 + 12)
    while start > 0 and haystack[start - 1] != " ":
        start -= 1
    while end < len(haystack) and haystack[end] != " ":
        end += 1
    truncated = len(needle) > limit
    a = needle[:limit].split()
    b = haystack[start:end][:limit + len(needle[:limit]) // 3 + 12].split()
    opcodes = SequenceMatcher(None, [_key(t) for t in a], [_key(t) for t in b], autojunk=False).get_opcodes()
    equal = [i for i, op in enumerate(opcodes) if op[0] == "equal"]
    if not equal:
        return None
    first, last = equal[0], equal[-1]
    # 조각(segment)마다 양쪽 어절과 표지를 모은다. 전문 보기는 조각을 이어 붙이고, 칸 요약은 다른 조각만 고른다.
    segments: List[Dict[str, List[List[str]]]] = []
    for index, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        qa, ob = a[i1:i2], b[j1:j2]
        if index < first or index > last:
            # 인용 범위 밖의 원문 어절은 맥락일 뿐이다. 인용 끝 어절이 원문 어절의 앞부분이면 같은 어절로 본다.
            if index == first - 1 and len(qa) == 1 and ob and _key(ob[-1]).endswith(_key(qa[0])):
                segments.append({"quoted": [[qa[0], "same"]], "official": [[ob[-1], "same"]]})
            elif index == last + 1 and len(qa) == 1 and ob and _key(ob[0]).startswith(_key(qa[0])):
                segments.append({"quoted": [[qa[0], "same"]], "official": [[ob[0], "same"]]})
            elif qa:
                segments.append({"quoted": [[t, "added"] for t in qa], "official": []})
            continue
        if tag == "equal":
            segments.append({"quoted": [[t, "same"] for t in qa], "official": [[t, "same"] for t in ob]})
        elif tag == "delete":
            segments.append({"quoted": [[t, "added"] for t in qa], "official": []})
        elif tag == "insert":
            segments.append({"quoted": [], "official": [[t, "removed"] for t in ob]})
        else:
            segments.append({"quoted": [[t, "changed"] for t in qa], "official": [[t, "changed"] for t in ob]})
    if truncated:
        while segments and any(m != "same" for _, m in segments[-1]["quoted"] + segments[-1]["official"]):
            segments.pop()
    quoted_tokens = [tok for seg in segments for tok in seg["quoted"]]
    official_tokens = [tok for seg in segments for tok in seg["official"]]
    changed = any(m != "same" for _, m in quoted_tokens + official_tokens)
    return {"quoted": quoted_tokens, "official": official_tokens, "hunks": _hunks(segments),
            "similarity": span["similarity"], "truncated": truncated, "changed": changed,
            "normalization": "normalize_quote"}


HUNK_CONTEXT = 2   # 칸 요약: 다른 곳 앞뒤로 보일 같은 어절 수
HUNK_MERGE_GAP = 4  # 다른 곳 사이의 같은 어절이 이 이하면 한 묶음으로 보인다


def _hunks(segments: List[Dict[str, List[List[str]]]]) -> List[Dict[str, Any]]:
    """다른 곳만 앞뒤 어절 조금과 함께 묶는다(TK-163 사용자 요청 11-14 '핵심내용만 칸에서 간략하게')."""
    is_diff = [any(m != "same" for _, m in seg["quoted"] + seg["official"]) for seg in segments]
    hunks: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for index, seg in enumerate(segments):
        if not is_diff[index]:
            continue
        before = segments[index - 1] if index > 0 and not is_diff[index - 1] else None
        if current is not None and before is not None and len(before["quoted"]) <= HUNK_MERGE_GAP \
                and current.get("_end") == index - 2:
            current["quoted"] += before["quoted"] + seg["quoted"]
            current["official"] += before["official"] + seg["official"]
        else:
            if current is not None:
                hunks.append(current)
            lead_q = before["quoted"][-HUNK_CONTEXT:] if before else []
            lead_o = before["official"][-HUNK_CONTEXT:] if before else []
            current = {"quoted": list(lead_q) + seg["quoted"], "official": list(lead_o) + seg["official"],
                       "lead": bool(before and len(before["quoted"]) > HUNK_CONTEXT)}
        current["_end"] = index
        after = segments[index + 1] if index + 1 < len(segments) and not is_diff[index + 1] else None
        current["_after"] = after
    if current is not None:
        hunks.append(current)
    out = []
    for hunk in hunks:
        after = hunk.pop("_after", None)
        hunk.pop("_end", None)
        if after:
            hunk["quoted"] = hunk["quoted"] + after["quoted"][:HUNK_CONTEXT]
            hunk["official"] = hunk["official"] + after["official"][:HUNK_CONTEXT]
        hunk["tail"] = bool(after and len(after["quoted"]) > HUNK_CONTEXT)
        out.append(hunk)
    return out


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
