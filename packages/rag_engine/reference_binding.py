"""Deterministic Drive reference binding; never changes official verification.

Keep the matching contract in sync with app.js (executed by Node parity tests).
Structural links express provenance, while identifier checks gate SUPPORTS.
"""
import re

EXPLICIT_WHITESPACE_RE = re.compile(
    r"[\u0009-\u000D\u001C-\u0020\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000\uFEFF]+"
)
NOTICE = "참고문헌·구속력 없음, 공식 확인 아님"
CASE_RE = re.compile(r"(?<![0-9])([0-9]{4}[가-힣]{1,4}[0-9]+)(?![0-9])")
ARTICLE_RE = re.compile(r"제[0-9]+조(?:의[0-9]+)?(?:제[0-9]+항)?(?:제[0-9]+호)?(?![0-9])")


def value(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def compact_text(text):
    return EXPLICIT_WHITESPACE_RE.sub("", str(text or ""))


def authority_text(text):
    return re.sub(r"[「」『』]", "", compact_text(text))


def identifier(citation):
    raw = authority_text(value(citation, "raw_text") or value(citation, "cited_authority") or "")
    case = authority_text(value(citation, "canonical_case_number") or value(citation, "case_number") or "")
    found = CASE_RE.search(case or raw)
    if found:
        return ("case", found.group(1), "")
    law = authority_text(value(citation, "law_name") or "")
    article = authority_text(value(citation, "article") or "")
    if article and not article.startswith("제"):
        article = "제" + article + "조"
    for field, suffix in (("paragraph", "항"), ("item", "호")):
        part = authority_text(value(citation, field) or "")
        if part:
            article += part if part.startswith("제") else "제" + part + suffix
    if not law:
        found = re.search(r"([가-힣A-Za-z·]+(?:법률|법|령|규정|조례))(제[0-9]+조(?:의[0-9]+)?(?:제[0-9]+항)?(?:제[0-9]+호)?)", raw)
        if found:
            law, article = found.groups()
    return ("law", law, article) if law and ARTICLE_RE.fullmatch(article) else None


def identifier_match(citation, excerpt):
    """Return full/proximate/conflict flags, with complete article boundaries."""
    ident = identifier(citation)
    text = authority_text(excerpt)
    if not ident:
        return {"full": False, "proximate": False, "conflict": False}
    kind, key, article = ident
    if kind == "case":
        cases = {m.group(1) for m in CASE_RE.finditer(text)}
        conflict = bool(cases - {key})
        full = key in cases and not conflict
        return {"full": full, "proximate": full, "conflict": conflict}
    # Preserve name boundaries before removing whitespace/brackets. A suffix of
    # a different law's name is not the complete law identifier.
    original = str(excerpt or "")
    separator = r"[\u0009-\u000D\u001C-\u0020\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000\uFEFF「」『』]*"
    law_pattern = (r"(?<![가-힣A-Za-z0-9])" + separator.join(re.escape(c) for c in key)
                   + r"(?:(?![가-힣A-Za-z0-9])|(?=제" + separator + r"[0-9]))")
    positions = [len(authority_text(original[:m.start()])) for m in re.finditer(law_pattern, original)]
    articles = list(ARTICLE_RE.finditer(text))
    conflict = any(m.group() != article and any(abs(m.start() - p - len(key)) <= 100 for p in positions)
                   for m in articles)
    full = bool(positions) and any(m.group() == article for m in articles) and not conflict
    near = full and any(m.group() == article and any(abs(m.start() - p - len(key)) <= 100 for p in positions)
                        for m in articles)
    return {"full": full, "proximate": bool(near), "conflict": conflict}


def citation_excerpt(citation, text):
    """Window of original text, preserving provenance and original whitespace."""
    ident = identifier(citation)
    if not ident:
        return ""
    normalized, offsets = [], []
    for index, char in enumerate(text):
        if authority_text(char):
            normalized.append(char)
            offsets.append(index)
    compact = "".join(normalized)
    anchor = ident[1] if ident[0] == "case" else ident[2]
    pos = compact.find(anchor)
    if pos < 0:
        return ""
    center = offsets[pos]
    size = 400 if ident[0] == "case" else 500
    start = max(0, center - 100)
    excerpt = text[start:start + size]
    return excerpt if identifier_match(citation, excerpt)["proximate"] else ""


def bind_observations(items, document):
    """Mutate only reference fields. Return unmatched entries in document order."""
    rag = value(document, "engine_data", {}).get("rag", {})
    sources = {s.get("source_id"): s for s in rag.get("sources", [])}
    citations = {value(c, "citation_id"): c for c in value(document, "citations", [])}
    claims = {value(c, "claim_id"): value(c, "citation_ids", []) for c in value(document, "claims", [])}
    for item in items:
        item["reference_observations"] = []
    unmatched = []
    for index, observation in enumerate(rag.get("observations", [])):
        entry = {**observation, "source": "google_drive", "official": False, "binding": False,
                 "notice": NOTICE, "source_detail": sources.get(observation.get("source_id")),
                 "observation_index": index}
        ids = claims.get(observation.get("claim_id"), [])
        target = next((i for i in items if i.get("citation_id") and i["citation_id"] in ids), None)
        candidates = []
        if target is None:
            fallback = []
            quote = compact_text(observation.get("claim_quote"))
            for item in items:
                match = identifier_match(citations.get(item.get("citation_id"), item), observation.get("source_quote"))
                if match["proximate"]:
                    candidates.append(item)
                elif match["full"]:
                    claim = compact_text(item.get("claim_text"))
                    if len(quote) >= 15 and len(claim) >= 15 and (quote in claim or claim in quote):
                        fallback.append(item)
            candidates = candidates or fallback
            if len(candidates) == 1:
                target = candidates[0]
        if target is None:
            unmatched.append(entry)
        else:
            target["reference_observations"].append(entry)
    for item in items:
        observations = item["reference_observations"]
        if not observations:
            continue
        supported = any(o.get("relationship") == "SUPPORTS" and identifier_match(
            citations.get(item.get("citation_id"), item), o.get("source_quote"))["full"] for o in observations)
        if item.get("reference_status") != "CONTRADICTED":
            item["reference_status"] = "SUPPORTED" if supported else "PENDING_REVIEW"
    return unmatched
