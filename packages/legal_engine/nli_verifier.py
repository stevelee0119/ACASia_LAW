"""Sliding-window official passage alignment & Stage 2 Legal NLI auxiliary verifier (P1 PR-09).

Core safety invariants:
1. NLI is NEVER a standalone final legal decision-maker.
2. `CONTRADICTED` may only be proposed when an official `passage` is located AND
   either a structural inversion (`quote_diff` / polarity / modality / proviso) is confirmed
   or an external NLI scorer reaches high contradiction confidence with a located span.
3. Missing official source text always fails closed to `INSUFFICIENT`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from packages.document_engine.reading_text import sentence_bounds
from packages.legal_engine.quote_diff import quote_changes


_CONTENT_TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]{2,}")
_NEG_SURFACE_RE = re.compile(
    r"(?:않|아니하|아니라|아니다|아닙|없다|없고|없으며|없음|불허|금지|무효|부인|배척|부정)"
)
_OBLIGATION_RE = re.compile(r"(?:하여야\s*한다|해야\s*한다|의무가\s*있다|필수적이다)")
_DISCRETION_RE = re.compile(r"(?:할\s*수\s*있다|허용된다|가능하다|재량에\s*속한다|무방하다)")


@dataclass(frozen=True)
class PassageCandidate:
    start: int
    end: int
    text: str
    overlap_score: float


@dataclass(frozen=True)
class NLISignal:
    label: str                  # ENTAILMENT | CONTRADICTION | NEUTRAL
    entail_prob: float
    contradict_prob: float
    neutral_prob: float
    structural_reasons: List[str] = field(default_factory=list)


@dataclass
class Stage2VerificationResult:
    verdict: str                # SUPPORTED | CONTRADICTED | PENDING_REVIEW | INSUFFICIENT
    located_passage: Optional[PassageCandidate]
    nli_signal: Optional[NLISignal]
    structural_changes: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "located_passage": asdict(self.located_passage) if self.located_passage else None,
            "nli_signal": asdict(self.nli_signal) if self.nli_signal else None,
            "structural_changes": self.structural_changes,
            "reason": self.reason,
        }


def _token_set(text: str) -> set[str]:
    words = set(_CONTENT_TOKEN_RE.findall(text or ""))
    # Add 2-char Korean syllables for paraphrase/inflection resilience
    compact = re.sub(r"\s+", "", text or "")
    bigrams = {compact[i:i + 2] for i in range(max(0, len(compact) - 1))}
    return words | bigrams


def sliding_window_passages(
    official_text: str,
    claim_or_quote: str,
    *,
    window_sizes: Sequence[int] = (1, 2, 3),
    top_k: int = 3,
) -> List[PassageCandidate]:
    """Locate the highest-overlap 1..3 sentence windows in `official_text` for `claim_or_quote`."""
    src = official_text or ""
    hyp = (claim_or_quote or "").strip()
    if not src.strip() or not hyp:
        return []

    bounds = sentence_bounds(src)
    if not bounds:
        bounds = [(0, len(src))]

    hyp_tokens = _token_set(hyp)
    if not hyp_tokens:
        return []

    candidates: List[PassageCandidate] = []
    seen_spans: set[Tuple[int, int]] = set()
    for win in window_sizes:
        if win <= 0 or win > len(bounds):
            continue
        for idx in range(0, len(bounds) - win + 1):
            raw_start = bounds[idx][0]
            raw_end = bounds[idx + win - 1][1]
            raw_seg = src[raw_start:raw_end]
            segment = raw_seg.strip()
            if not segment:
                continue
            lead_ws = len(raw_seg) - len(raw_seg.lstrip())
            trail_ws = len(raw_seg) - len(raw_seg.rstrip())
            start = raw_start + lead_ws
            end = raw_end - trail_ws
            if (start, end) in seen_spans:
                continue
            seen_spans.add((start, end))
            seg_tokens = _token_set(segment)
            if not seg_tokens:
                continue
            inter = len(hyp_tokens & seg_tokens)
            # Recall-weighted overlap (how much of the hypothesis is grounded in this passage)
            score = inter / max(1, len(hyp_tokens))
            if score > 0.0:
                candidates.append(PassageCandidate(start=start, end=end, text=segment, overlap_score=round(score, 4)))

    candidates.sort(key=lambda c: (-c.overlap_score, len(c.text), c.start))
    return candidates[:top_k]


def _structural_inversion_reasons(premise: str, hypothesis: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    reasons: List[str] = []
    prem_neg = len(_NEG_SURFACE_RE.findall(premise)) % 2 == 1
    hyp_neg = len(_NEG_SURFACE_RE.findall(hypothesis)) % 2 == 1
    diff_res = quote_changes(hypothesis, premise) or {}
    changes = list(diff_res.get("changes") or [])
    for kind in diff_res.get("diff_categories") or []:
        if kind == "NEGATION" and prem_neg == hyp_neg:
            continue
        if kind in {"NEGATION", "MODALITY", "PARTY_SWAP", "PROVISO_OMISSION", "NUMERIC"}:
            reasons.append(f"QUOTE_DIFF_{kind}")

    if prem_neg != hyp_neg:
        reasons.append("POLARITY_INVERSION")

    prem_obl = bool(_OBLIGATION_RE.search(premise))
    hyp_obl = bool(_OBLIGATION_RE.search(hypothesis))
    prem_disc = bool(_DISCRETION_RE.search(premise))
    hyp_disc = bool(_DISCRETION_RE.search(hypothesis))
    if (prem_obl and hyp_disc) or (prem_disc and hyp_obl):
        reasons.append("MODALITY_OBLIGATION_DISCRETION_SWAP")

    # Deduplicate preserving order
    deduped = list(dict.fromkeys(reasons))
    return deduped, changes


def default_nli_scorer(premise: str, hypothesis: str) -> NLISignal:
    """Deterministic lexical/structural fallback NLI scorer when no neural NLI model is loaded."""
    reasons, _ = _structural_inversion_reasons(premise, hypothesis)
    p_toks = _token_set(premise)
    h_toks = _token_set(hypothesis)
    overlap = (len(p_toks & h_toks) / max(1, len(h_toks))) if h_toks else 0.0

    if reasons and overlap >= 0.25:
        return NLISignal(
            label="CONTRADICTION",
            entail_prob=0.05,
            contradict_prob=0.90,
            neutral_prob=0.05,
            structural_reasons=reasons,
        )
    if overlap >= 0.45 and not reasons:
        return NLISignal(
            label="ENTAILMENT",
            entail_prob=0.85,
            contradict_prob=0.05,
            neutral_prob=0.10,
            structural_reasons=[],
        )
    return NLISignal(
        label="NEUTRAL",
        entail_prob=0.20,
        contradict_prob=0.10,
        neutral_prob=0.70,
        structural_reasons=reasons,
    )


def evaluate_citation_nli_stage2(
    official_text: str,
    claim_or_quote: str,
    *,
    nli_scorer: Callable[[str, str], NLISignal] = default_nli_scorer,
    min_passage_overlap: float = 0.25,
    contradict_threshold: float = 0.85,
) -> Stage2VerificationResult:
    """Align `claim_or_quote` to `official_text` and compute a guarded Stage 2 NLI verdict."""
    if not (official_text or "").strip() or not (claim_or_quote or "").strip():
        return Stage2VerificationResult(
            verdict="INSUFFICIENT",
            located_passage=None,
            nli_signal=None,
            reason="공식 원문 또는 검증 대상 진술이 비어 있어 근거 부족(INSUFFICIENT)으로 처리합니다.",
        )

    passages = sliding_window_passages(official_text, claim_or_quote, top_k=3)
    if not passages or passages[0].overlap_score < min_passage_overlap:
        return Stage2VerificationResult(
            verdict="INSUFFICIENT",
            located_passage=passages[0] if passages else None,
            nli_signal=None,
            reason="공식 원문에서 충분한 어휘 중첩을 가진 대응 구간을 찾지 못해 근거 부족으로 유보합니다.",
        )

    best = passages[0]
    structural_reasons, changes = _structural_inversion_reasons(best.text, claim_or_quote)
    signal = nli_scorer(best.text, claim_or_quote)
    combined_reasons = list(dict.fromkeys(structural_reasons + list(signal.structural_reasons)))
    enriched_signal = NLISignal(
        label=signal.label,
        entail_prob=signal.entail_prob,
        contradict_prob=signal.contradict_prob,
        neutral_prob=signal.neutral_prob,
        structural_reasons=combined_reasons,
    )

    if signal.label == "CONTRADICTION" and signal.contradict_prob >= contradict_threshold:
        if structural_reasons:
            return Stage2VerificationResult(
                verdict="CONTRADICTED",
                located_passage=best,
                nli_signal=enriched_signal,
                structural_changes=changes,
                reason="공식 원문 대응 구간이 특정되었고 독립 검증된 구조적 반전 및 NLI 모순 신호가 함께 확인되었습니다.",
            )
        return Stage2VerificationResult(
            verdict="PENDING_REVIEW",
            located_passage=best,
            nli_signal=enriched_signal,
            structural_changes=changes,
            reason="NLI 모순 점수가 높으나 독립 확인된 구조적 반전 표지가 없어 전문가/LLM 교차 검토로 보류합니다.",
        )

    if signal.label == "ENTAILMENT" and not structural_reasons:
        return Stage2VerificationResult(
            verdict="SUPPORTED",
            located_passage=best,
            nli_signal=enriched_signal,
            structural_changes=changes,
            reason="공식 원문 대응 구간과 서면 인용의 취지가 부합합니다.",
        )

    return Stage2VerificationResult(
        verdict="INSUFFICIENT",
        located_passage=best,
        nli_signal=enriched_signal,
        structural_changes=changes,
        reason="공식 원문 구간과 서면 진술 간의 함의/모순 관계가 확정되지 않았습니다.",
    )
