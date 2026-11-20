"""Legal applicability filter for retrieved RAG chunks (P1 PR-08 Tier 4).

Textual/semantic similarity alone does not establish legal applicability.
This filter evaluates temporal validity (effective/repealed dates against `target_date`),
authority status (overruled/unconstitutional precedents), and procedural domain alignment
before allowing a retrieved chunk to be used as affirmative legal support.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import re
from typing import Any, Dict, List, Optional, Sequence


_INVALID_AUTHORITY_STATUSES = frozenset({
    "OVERRULED",
    "SUPERSEDED",
    "REVERSED",
    "UNCONSTITUTIONAL",
    "REPEALED",
    "ABOLISHED",
})

_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


@dataclass(frozen=True)
class ApplicabilityVerdict:
    eligible_for_support: bool
    warnings: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    m = _ISO_DATE_RE.search(str(value).strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def check_chunk_applicability(
    chunk: Dict[str, Any],
    *,
    target_date: Optional[str] = None,
    case_type: Optional[str] = None,
) -> ApplicabilityVerdict:
    """Assess whether a retrieved chunk is legally applicable to the target case context."""
    meta = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    warnings: List[str] = []
    reasons: List[str] = []

    auth_status = str(meta.get("authority_status") or chunk.get("authority_status") or "").strip().upper()
    if auth_status in _INVALID_AUTHORITY_STATUSES:
        warnings.append("APPLICABILITY_WARNING:AUTHORITY_INVALIDATED")
        reasons.append(f"인용 권위의 효력이 상실·변경되었습니다({auth_status}).")

    ref_dt = _parse_iso_date(target_date)
    if ref_dt is not None:
        eff_from = _parse_iso_date(meta.get("effective_from") or chunk.get("effective_from"))
        repealed_at = _parse_iso_date(meta.get("repealed_at") or chunk.get("repealed_at"))
        if eff_from is not None and ref_dt < eff_from:
            warnings.append("APPLICABILITY_WARNING:NOT_YET_EFFECTIVE")
            reasons.append(f"기준일({ref_dt.isoformat()}) 당시 시행 전 규정입니다(시행일 {eff_from.isoformat()}).")
        if repealed_at is not None and ref_dt >= repealed_at:
            warnings.append("APPLICABILITY_WARNING:REPEALED_AT_TARGET_DATE")
            reasons.append(f"기준일({ref_dt.isoformat()}) 당시 이미 폐지된 규정입니다(폐지일 {repealed_at.isoformat()}).")

    req_proc = str(case_type or "").strip().upper()
    chunk_proc = str(meta.get("case_type") or chunk.get("case_type") or "").strip().upper()
    if req_proc and chunk_proc and chunk_proc != "GENERAL" and req_proc != chunk_proc:
        warnings.append("APPLICABILITY_WARNING:PROCEDURE_MISMATCH")
        reasons.append(f"사건 유형({req_proc})과 참고자료 절차 유형({chunk_proc})이 다릅니다.")

    return ApplicabilityVerdict(
        eligible_for_support=(len(warnings) == 0),
        warnings=warnings,
        reasons=reasons,
    )


def annotate_applicability(
    chunks: Sequence[Dict[str, Any]],
    *,
    target_date: Optional[str] = None,
    case_type: Optional[str] = None,
    exclude_inapplicable: bool = False,
) -> List[Dict[str, Any]]:
    """Annotate ranked chunks with applicability verdicts and optionally filter out invalid ones."""
    annotated: List[Dict[str, Any]] = []
    for ch in chunks:
        verdict = check_chunk_applicability(ch, target_date=target_date, case_type=case_type)
        if exclude_inapplicable and not verdict.eligible_for_support:
            continue
        annotated.append({
            **ch,
            "eligible_for_support": verdict.eligible_for_support,
            "applicability_warnings": verdict.warnings,
            "applicability_reasons": verdict.reasons,
        })
    return annotated
