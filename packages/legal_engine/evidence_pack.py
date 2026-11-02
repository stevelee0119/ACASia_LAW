"""판례 의미 검토에 보낼 공식 원문 발췌(TK-131).

전문 앞부분을 자르는 대신, 전문 전체에서 먼저 관련 구간을 고른 뒤 예산에 맞춘다. 선택 순서:
1) 문서가 직접 인용한 문장과 같은 원문 구간 2) 문서 주장과 글자 겹침이 큰 원문 문장 3) 판시사항·판결요지
4) 전문 첫머리(사건 표시)·끝부분(결론). 각 구간은 문장 경계까지 넓히고, 겹치면 합친다.

offset은 마스킹 전 전문(official["full_text"]) 기준이다. 구간 글자는 원문 그대로다. 생략 표시 같은 시스템 문구는
구간 밖에 둔다. 근거 인용 확인은 구간마다 따로 한다(구간을 이어 붙인 인용은 받지 않는다).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCHEMA_VERSION = "evidence-pack-v1"
SELECTOR_VERSION = "tk131-1"
DEFAULT_BUDGET = 24000
HEAD_CHARS = 3000
TAIL_CHARS = 3000
SENTENCE_SLACK = 400        # 문장 경계를 찾으려고 더 넓힐 수 있는 최대 글자 수
CONTEXT_CHARS = 600         # 대응 구간 앞뒤로 함께 보낼 주변 글자 수
TOP_SENTENCES = 3
GAP_MARKER = "\n…(공식 원문 일부 생략)…\n"
_SENTENCE_END = re.compile(r"(?<=[.。])\s+|(?<=다\.)|\n+")


def _bigrams(text: str) -> set:
    compact = re.sub(r"\s+", "", text or "")
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def _snap(text: str, start: int, end: int) -> Tuple[int, int]:
    """[start, end)를 가까운 문장 경계까지 넓힌다. SENTENCE_SLACK 안에 경계가 없으면 그대로 둔다."""
    lo = max(0, start - SENTENCE_SLACK)
    before = [m.end() for m in _SENTENCE_END.finditer(text, lo, start)]
    start = before[-1] if before else (0 if start - lo < SENTENCE_SLACK else start)
    after = _SENTENCE_END.search(text, end, min(len(text), end + SENTENCE_SLACK))
    end = after.end() if after else (len(text) if len(text) - end <= SENTENCE_SLACK else end)
    return start, end


def _sentences(text: str) -> List[Tuple[int, int]]:
    spans, pos = [], 0
    for m in _SENTENCE_END.finditer(text):
        if m.start() > pos:
            spans.append((pos, m.start()))
        pos = m.end()
    if pos < len(text):
        spans.append((pos, len(text)))
    return spans


def _find_quote(text: str, quote: str) -> Optional[Tuple[int, int]]:
    quote = (quote or "").strip()
    if len(quote) < 4:
        return None
    at = text.find(quote)
    if at >= 0:
        return at, at + len(quote)
    # 띄어쓰기만 다른 인용: 공백을 \s*로 바꾼 한 번의 정규식 탐색(무제한 반복 대조를 하지 않는다)
    pattern = r"\s*".join(re.escape(ch) for ch in re.sub(r"\s+", "", quote)[:400])
    m = re.search(pattern, text)
    return (m.start(), m.end()) if m else None


def build_evidence_pack(full_text: str, *, quotes: Sequence[str] = (), claim: str = "",
                        structured: Sequence[str] = (), budget: int = DEFAULT_BUDGET) -> Dict[str, Any]:
    text = full_text or ""
    if len(text) <= budget:
        return _pack(text, [(0, len(text), "FULL_TEXT")], "FULL", [])
    candidates: List[Tuple[int, int, str]] = []
    unresolved = []
    for quote in quotes:
        span = _find_quote(text, quote)
        if span is None:
            unresolved.append("DIRECT_QUOTE_NOT_FOUND")
            continue
        candidates.append((span[0] - CONTEXT_CHARS, span[1] + CONTEXT_CHARS, "DIRECT_QUOTE"))
    claim_grams = _bigrams(claim)
    if claim_grams:
        scored = []
        for s, e in _sentences(text):
            grams = _bigrams(text[s:e])
            if len(grams) >= 4:
                scored.append((len(grams & claim_grams) / len(grams), s, e))
        for score, s, e in sorted(scored, reverse=True)[:TOP_SENTENCES]:
            if score > 0:
                candidates.append((s - CONTEXT_CHARS // 2, e + CONTEXT_CHARS // 2, "CLAIM_OVERLAP"))
    for part in structured:
        span = _find_quote(text, part[:200]) if part else None
        if span:
            candidates.append((span[0], span[0] + len(part), "STRUCTURED_FIELD"))
    candidates.append((0, HEAD_CHARS, "HEAD"))
    candidates.append((len(text) - TAIL_CHARS, len(text), "CONCLUSION"))

    chosen: List[Tuple[int, int, str]] = []
    reasons = list(unresolved)
    for start, end, reason in candidates:      # 우선순위 순서대로 예산을 채운다
        start, end = _snap(text, max(0, start), min(len(text), end))
        merged = _merge(chosen + [(start, end, reason)])
        cost = sum(e - s for s, e, _ in merged)
        if cost > budget:
            if reason == "DIRECT_QUOTE":
                reasons.append("INSUFFICIENT_CONTEXT")
            else:
                reasons.append(f"BUDGET_EXCEEDED:{reason}")
            continue
        chosen = merged
    coverage = "PARTIAL" if "INSUFFICIENT_CONTEXT" in reasons else "SELECTED"
    return _pack(text, chosen, coverage, reasons)


def _merge(spans: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
    out: List[Tuple[int, int, str]] = []
    for s, e, r in sorted(spans):
        if out and s <= out[-1][1]:
            ps, pe, pr = out[-1]
            out[-1] = (ps, max(pe, e), pr if r in pr.split("+") else f"{pr}+{r}")
        else:
            out.append((s, e, r))
    return out


def _pack(text: str, spans, coverage: str, reasons: List[str]) -> Dict[str, Any]:
    segments = [{"segment_id": f"S{i}", "original_start": s, "original_end": e, "selection_reason": r,
                 "text": text[s:e]} for i, (s, e, r) in enumerate(spans)]
    omitted, cursor = [], 0
    for seg in segments:
        if seg["original_start"] > cursor:
            omitted.append([cursor, seg["original_start"]])
        cursor = seg["original_end"]
    if cursor < len(text):
        omitted.append([cursor, len(text)])
    return {"schema_version": SCHEMA_VERSION, "selector_version": SELECTOR_VERSION, "source_length": len(text),
            "coverage_status": coverage, "segments": segments, "omitted_ranges": omitted,
            "truncation_reasons": reasons, "selected_chars": sum(len(s["text"]) for s in segments)}


def render(segments: Sequence[str]) -> str:
    """모델에 보낼 발췌 본문. 구간 사이에는 원문이 아닌 생략 표시를 넣는다."""
    return GAP_MARKER.join(segments)


def quote_in_one_segment(quote: str, segments: Sequence[str]) -> bool:
    """근거 인용이 보낸 구간 하나 안에 그대로 있는지. 구간을 이어 붙인 인용·생략 표시가 든 인용은 받지 않는다."""
    return isinstance(quote, str) and bool(quote.strip()) and any(quote in seg for seg in segments)


def project_masked(full_text: str, mask_result, segments: Sequence[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """원문 전체를 한 번 가린 결과(mask_result)로 구간을 옮긴다. 개인정보 탐지 범위를 가르는 구간 경계는 그 범위 전체로
    넓힌다. 돌려주는 값: (가린 전문, [{segment_id, masked_start, masked_end, text}]).

    구간을 따로 가리면 주변 문맥에 따른 탐지가 달라져, 뒤에서 전문 전체를 가려 근거를 다시 확인하는 경로
    (argument_validity_verifier._context_review)와 결과가 어긋난다(TK-131 설계 메모 4·5).
    """
    masked = mask_result.masked_text
    kept, cursor = [], 0
    for m in sorted(mask_result.matches, key=lambda m: (m.start, -(m.end - m.start))):
        if m.start < cursor:
            continue
        kept.append(m)
        cursor = m.end
    # 원문 위치 → 가린 위치 대응표(가린 글자 "[TOKEN]"은 원문 [m.start, m.end)를 대신한다)
    pieces, o, k = [], 0, 0
    for m in kept:
        pieces.append((o, m.start, k))                       # 그대로 옮긴 원문 구간
        k += m.start - o
        close = masked.index("]", k) + 1
        pieces.append((m.start, m.end, k, close))            # 가린 구간
        k, o = close, m.end
    pieces.append((o, len(full_text), k))

    def to_masked(pos: int, side: str) -> int:
        for piece in pieces:
            if len(piece) == 4:
                a, b, ms, me = piece
                if a < pos < b:                               # 넓힌 뒤에는 생기지 않는다(방어)
                    return me if side == "end" else ms
                continue
            a, b, ms = piece
            if a <= pos <= b:
                return ms + (pos - a)
        return len(masked)

    out = []
    for seg in segments:
        start, end = seg["original_start"], seg["original_end"]
        for m in kept:                                        # 경계가 가린 범위 안이면 범위 전체로 넓힌다
            if m.start < start < m.end:
                start = m.start
            if m.start < end < m.end:
                end = m.end
        ms, me = to_masked(start, "start"), to_masked(end, "end")
        out.append({"segment_id": seg["segment_id"], "masked_start": ms, "masked_end": me, "text": masked[ms:me]})
    return masked, out
