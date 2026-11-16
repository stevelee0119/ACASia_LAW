"""제8장 PII 파이프라인.

Original → Rule-based PII + NER Detection → Context Validation
→ Project-stable Pseudonym → Masked Evidence View → External LLM
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from packages.common.enums import ExternalAIPolicy
from packages.common.schemas import NormalizedDocument

from .detector import PIIMatch, detect, is_lawyer_court_address_context
from .pseudonym import PseudonymStore, canonical_pseudonym_token

MIN_CONFIDENCE = 0.6
MAX_MASK_PASSES = 5


@dataclass
class MaskResult:
    masked_text: str
    matches: List[PIIMatch] = field(default_factory=list)
    replacements: Dict[str, str] = field(default_factory=dict)
    token_spans: Tuple[Tuple[int, int, str], ...] = field(default=(), compare=False, repr=False)

    @property
    def count(self) -> int:
        return len(self.matches)


def slice_token_spans(
    token_spans: Sequence[Tuple[int, int, str]],
    start: int,
    end: int,
) -> Tuple[Tuple[int, int, str], ...]:
    """Keep only complete token spans wholly contained within [start, end), rebased to start."""
    if not token_spans or start >= end:
        return ()
    return tuple(
        (ts - start, te - start, token)
        for ts, te, token in token_spans
        if start <= ts and te <= end
    )


@dataclass
class MaskedDocument:
    document_id: str
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    match_count: int = 0
    kinds: Dict[str, int] = field(default_factory=dict)
    replacements: Dict[str, str] = field(default_factory=dict)
    policy: str = ExternalAIPolicy.MASKED.value

    @property
    def text(self) -> str:
        return "\n".join(b["text"] for b in self.blocks)


def _unmasked_segments(
    orig_len: int, applied_orig: List[Tuple[PIIMatch, int]],
) -> List[Tuple[int, int, int]]:
    """Build (cur_start, cur_end, orig_start) intervals for unmasked gaps."""
    segments: List[Tuple[int, int, int]] = []
    cur_pos = 0
    orig_pos = 0
    for orig_match, tok_len in applied_orig:
        gap_len = orig_match.start - orig_pos
        if gap_len > 0:
            segments.append((cur_pos, cur_pos + gap_len, orig_pos))
        cur_pos += gap_len + tok_len
        orig_pos = orig_match.end
    tail_len = orig_len - orig_pos
    if tail_len > 0:
        segments.append((cur_pos, cur_pos + tail_len, orig_pos))
    return segments


def _applied_with_token_lengths(
    src_text: str, masked_text: str, applied_matches: List[PIIMatch],
) -> List[Tuple[PIIMatch, int]]:
    if not applied_matches:
        return []
    out: List[Tuple[PIIMatch, int]] = []
    masked_pos = 0
    src_pos = 0
    for idx, m in enumerate(applied_matches):
        gap = m.start - src_pos
        masked_pos += gap
        if idx + 1 < len(applied_matches):
            next_gap = applied_matches[idx + 1].start - m.end
            close = masked_text.find("]", masked_pos)
            while close != -1:
                cand_end = close + 1
                if next_gap == 0 and cand_end < len(masked_text) and masked_text[cand_end] == "[":
                    break
                if next_gap > 0 and masked_text.startswith(src_text[m.end:m.end + next_gap], cand_end):
                    break
                close = masked_text.find("]", close + 1)
            tok_len = (close + 1 - masked_pos) if close != -1 else 0
        else:
            tail_len = len(src_text) - m.end
            tok_len = len(masked_text) - masked_pos - tail_len
        out.append((m, tok_len))
        masked_pos += tok_len
        src_pos = m.end
    return out


_REAL_DETECT = detect


def _detect_matches(
    text: str,
    *,
    block_id: Optional[str] = None,
    page: Optional[int] = None,
    trusted_spans: Optional[frozenset[Tuple[int, int, str]]] = None,
) -> List[PIIMatch]:
    if trusted_spans is None:
        return detect(text, block_id=block_id, page=page)
    if detect is _REAL_DETECT:
        return detect(text, block_id=block_id, page=page, _trusted_spans=trusted_spans)
    import inspect

    if "_trusted_spans" in inspect.signature(detect).parameters:
        return detect(text, block_id=block_id, page=page, _trusted_spans=trusted_spans)
    return detect(text, block_id=block_id, page=page)


def _advance_token_spans(
    prev_spans: Sequence[Tuple[int, int, str]],
    pass_edits: Sequence[Tuple[int, int, int, int, Optional[str]]],
) -> List[Tuple[int, int, str]]:
    """Map prior pass token spans across non-overlapping edits and merge new spans."""
    updated: List[Tuple[int, int, str]] = []
    for ots, ote, otok in prev_spans:
        overlapped = any(ms < ote and ots < me for ms, me, _, _, _ in pass_edits)
        if overlapped:
            continue
        delta = sum((nte - nts) - (me - ms) for ms, me, nts, nte, _ in pass_edits if me <= ots)
        updated.append((ots + delta, ote + delta, otok))
    for _, _, nts, nte, ntok in pass_edits:
        if ntok is not None:
            updated.append((nts, nte, ntok))
    updated.sort(key=lambda item: (item[0], item[1]))
    return updated


class PIIEngine:
    def __init__(self, store: PseudonymStore) -> None:
        self.store = store

    def mask_text(self, text: str, *, block_id: Optional[str] = None, page: Optional[int] = None, _trace=None) -> MaskResult:
        matches = [m for m in _detect_matches(text, block_id=block_id, page=page) if m.confidence >= MIN_CONFIDENCE]
        first = self._mask_matches(text, matches) if _trace is None else self._mask_matches(text, matches, _trace=_trace)
        if (_trace is not None and type(text) is not str) or len(first.matches) >= len(matches) or first.masked_text == text:
            return first

        # 부분 중첩으로 1차 패스에서 건너뛴 후보가 남아 있을 때만 후속 패스로 잔여 PII를 마스킹한다.
        current_text = first.masked_text
        current_spans: List[Tuple[int, int, str]] = list(first.token_spans)
        applied_orig = _applied_with_token_lengths(text, current_text, first.matches)
        all_replacements: Dict[str, str] = dict(first.replacements)

        for _ in range(1, MAX_MASK_PASSES):
            next_matches = [
                m
                for m in _detect_matches(
                    current_text,
                    block_id=block_id,
                    page=page,
                    trusted_spans=frozenset(current_spans) if current_spans else None,
                )
                if m.confidence >= MIN_CONFIDENCE
            ]
            if not next_matches:
                break
            next_text, pass_applied, pass_replacements, pass_edits = (
                self._apply_matches_tracked(current_text, next_matches)
                if _trace is None
                else self._apply_matches_tracked(current_text, next_matches, _trace=_trace)
            )
            if not pass_applied or next_text == current_text:
                break
            all_replacements.update(pass_replacements)
            current_spans = _advance_token_spans(current_spans, pass_edits)
            segments = _unmasked_segments(len(text), applied_orig)
            seg_starts = [s[0] for s in segments]
            for cur_match, tok_len in pass_applied:
                idx = bisect_right(seg_starts, cur_match.start) - 1
                if idx < 0:
                    continue
                gap_cur_start, gap_cur_end, gap_orig_start = segments[idx]
                if gap_cur_start <= cur_match.start and cur_match.end <= gap_cur_end:
                    orig_start = gap_orig_start + (cur_match.start - gap_cur_start)
                    orig_end = gap_orig_start + (cur_match.end - gap_cur_start)
                    orig_match = replace(
                        cur_match,
                        start=orig_start,
                        end=orig_end,
                        text=text[orig_start:orig_end],
                    )
                    applied_orig.append((orig_match, tok_len))
            applied_orig.sort(key=lambda item: item[0].start)
            current_text = next_text
            if len(pass_applied) >= len(next_matches):
                break

        return MaskResult(
            current_text,
            [m for m, _ in applied_orig],
            all_replacements,
            token_spans=tuple(current_spans),
        )

    def _apply_matches_tracked(
        self, text: str, matches: List[PIIMatch], *, _trace=None,
    ) -> Tuple[str, List[Tuple[PIIMatch, int]], Dict[str, str], List[Tuple[int, int, int, int, Optional[str]]]]:
        if not matches:
            return text, [], {}, []
        replacements: Dict[str, str] = {}
        applied: List[Tuple[PIIMatch, int]] = []
        edits: List[Tuple[int, int, int, int, Optional[str]]] = []
        out: List[str] = []
        cursor = 0
        out_len = 0
        # 같은 위치에서 시작하면 긴 탐지를 먼저 쓴다(블록 경계를 넘는 문맥 탐지가 부분 탐지를 덮는다).
        for match in sorted(matches, key=lambda m: (m.start, -(m.end - m.start))):
            if match.start < cursor:
                continue
            token = self.store.pseudonym_for(match.kind, match.text)
            replacements[token] = match.kind
            rendered_token = f"[{token}]"
            canon = canonical_pseudonym_token(token, bracketed=False)
            tok_start = out_len + (match.start - cursor)
            tok_end = tok_start + len(rendered_token)
            out.append(text[cursor : match.start])
            out.append(rendered_token)
            if _trace is not None:
                _trace.keep(cursor, match.start)
                _trace.insert(len(rendered_token))
            applied.append((match, len(rendered_token)))
            edits.append((match.start, match.end, tok_start, tok_end, canon))
            out_len = tok_end
            cursor = match.end
        out.append(text[cursor:])
        if _trace is not None:
            _trace.keep(cursor, len(text))
            _trace.finish_mask()
        return "".join(out), applied, replacements, edits

    def _apply_matches(
        self, text: str, matches: List[PIIMatch], *, _trace=None,
    ) -> Tuple[str, List[Tuple[PIIMatch, int]], Dict[str, str]]:
        masked_text, applied, replacements, _ = self._apply_matches_tracked(text, matches, _trace=_trace)
        return masked_text, applied, replacements

    def _mask_matches(self, text, matches, *, _trace=None):
        masked_text, applied, replacements, edits = self._apply_matches_tracked(text, matches, _trace=_trace)
        if not applied:
            return MaskResult(text, [], {}, token_spans=())
        spans = tuple((nts, nte, ntok) for _, _, nts, nte, ntok in edits if ntok is not None)
        return MaskResult(masked_text, [m for m, _ in applied], replacements, token_spans=spans)

    def mask_document(self, doc: NormalizedDocument, *, policy: ExternalAIPolicy = ExternalAIPolicy.MASKED) -> MaskedDocument:
        """외부 LLM에 보낼 Masked Evidence View를 만든다."""
        masked = MaskedDocument(document_id=doc.document_id, policy=policy.value)
        if policy == ExternalAIPolicy.ORIGINAL:
            masked.blocks = [
                {"block_id": b.block_id, "page": b.page, "text": b.text, "layer": b.source_layer}
                for b in doc.body_blocks()
            ]
            return masked

        blocks = doc.body_blocks()
        # Labels and their values may be different table cells. Detect across the
        # assembled text, then map contained matches back to unchanged block spans.
        assembled_text = "\n".join(b.text for b in blocks)
        contextual = [m for m in detect(assembled_text) if m.confidence >= MIN_CONFIDENCE]
        offset = 0
        for block in blocks:
            raw_matches = [m for m in detect(block.text, block_id=block.block_id, page=block.page)
                           if m.confidence >= MIN_CONFIDENCE]
            # 블록 경계를 넘는 문맥 확인: 블록 단위로 탐지된 주소가 전체 문서 문맥상 소송대리인/법원 주소인 경우 보존
            matches = []
            for m in raw_matches:
                if m.kind == "ADDRESS" and is_lawyer_court_address_context(assembled_text, offset + m.start, offset + m.end):
                    continue
                matches.append(m)
            spans = {(m.start, m.end) for m in matches}
            end_of_block = offset + len(block.text)
            for match in contextual:
                if match.end <= offset or match.start >= end_of_block:
                    continue
                # 줄바꿈으로 여러 블록에 걸친 값("생년월일: 1985. 11." / "24.")은 블록마다 해당 조각을 가린다.
                # 한 블록 안에 든 값만 옮기면 나머지 조각이 그대로 외부 모델로 나간다.
                span = (max(match.start, offset) - offset, min(match.end, end_of_block) - offset)
                if not block.text[span[0]:span[1]].strip():
                    continue
                piece = replace(match, start=span[0], end=span[1], block_id=block.block_id, page=block.page)
                if span not in spans:
                    matches.append(piece)
                    spans.add(span)
                elif match.start < offset or match.end > end_of_block:
                    # 블록 안의 부분 탐지(지역명 없는 면허번호 등)보다 경계를 넘는 전체 값의 가명을 쓴다.
                    matches = [piece if (m.start, m.end) == span else m for m in matches]
            offset += len(block.text) + 1
            result = self._mask_matches(block.text, matches)
            masked.blocks.append(
                {"block_id": block.block_id, "page": block.page, "text": result.masked_text,
                 "layer": block.source_layer}
            )
            masked.match_count += result.count
            for match in result.matches:
                masked.kinds[match.kind] = masked.kinds.get(match.kind, 0) + 1
            masked.replacements.update(result.replacements)
        self.store.save()
        return masked
