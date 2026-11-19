"""Unadjudicated alert extraction, deduplication clustering, and 3-way offline legal reachability analysis."""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import re
import unicodedata
from typing import Any, Iterable, Sequence

from .schemas import (
    AlertAdjudicationRecord,
    OfflineReachability,
    ReachabilityItemRecord,
    UnadjudicatedAlertCandidate,
)

# Defect categories that fundamentally require an external official text (judgment body,
# official case summary, or unindexed statute full text) when no local rule/range applies.
EXTERNAL_TEXT_DEPENDENT_TYPES = frozenset({
    "CIT-FAB-Q",
    "CIT-MIS",
    "CIT-META",
    "LAW-NX",
    "LAW-MIS",
    "OVR",
    "OVR / LAW-NX",
})

# Defect categories verifiable purely from deterministic format, range, or local consistency rules.
DETERMINISTIC_OFFLINE_TYPES = frozenset({
    "CIT-NX",
    "EVI-FAKECIT",
    "EVI-DATE",
    "EVI-NUM",
    "EVI-INCONS",
    "EVI-COPY",
    "EVI-FORM",
    "EVI-OVR",
    "INJ",
})


def _norm_token(text: str) -> str:
    cleaned = unicodedata.normalize("NFKC", str(text or "")).casefold()
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_subject_signature(finding: dict[str, Any]) -> str:
    """Extract a canonical subject key from a finding for same-document duplicate clustering.

    Uses confidence_features identifiers (citation_id, canonical_case_number, law_name,
    entity_id) when available; otherwise falls back to the normalized title prefix.
    """
    feats = finding.get("confidence_features")
    if isinstance(feats, dict):
        for key in ("canonical_case_number", "case_number", "citation_id", "law_name", "rule_id", "entity_id"):
            val = feats.get(key)
            if val and str(val).strip():
                return _norm_token(str(val))
    title = _norm_token(str(finding.get("title") or ""))
    # Strip trailing punctuation/whitespace while preserving structural prefix
    return title[:48] if title else "untitled"


def compute_alert_id(document_key: str, finding: dict[str, Any]) -> str:
    """Deterministic 16-hex identifier for an unadjudicated alert."""
    doc = _norm_token(document_key)
    ftype = _norm_token(str(finding.get("type") or "UNKNOWN"))
    page = str(finding.get("page") or "")
    span_raw = finding.get("span")
    if isinstance(span_raw, (list, tuple)) and len(span_raw) == 2:
        span_str = f"{span_raw[0]}:{span_raw[1]}"
    else:
        span_str = ""
    title = _norm_token(str(finding.get("title") or ""))
    detail_head = _norm_token(str(finding.get("detail") or ""))[:64]
    payload = f"{doc}|{ftype}|{page}|{span_str}|{title}|{detail_head}"
    return "ALT_" + sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_cluster_id(document_key: str, finding: dict[str, Any], *, group_by_type_only: bool = False) -> str:
    """Deterministic cluster identifier for grouping duplicate alerts in the same document."""
    doc = _norm_token(document_key)
    ftype = _norm_token(str(finding.get("type") or "UNKNOWN"))
    if group_by_type_only:
        payload = f"{doc}|{ftype}"
    else:
        subject = _extract_subject_signature(finding)
        payload = f"{doc}|{ftype}|{subject}"
    return "CLS_" + sha256(payload.encode("utf-8")).hexdigest()[:12]


def _extract_excerpt(finding: dict[str, Any]) -> str:
    evidence = finding.get("evidence")
    if isinstance(evidence, list):
        for ev in evidence:
            if isinstance(ev, dict):
                excerpt = str(ev.get("excerpt") or ev.get("description") or "").strip()
                if excerpt:
                    return excerpt[:240]
    detail = str(finding.get("detail") or "").strip()
    return detail[:240]


def extract_unadjudicated_alerts(
    unmatched_findings: Sequence[dict[str, Any]],
    *,
    group_by_type_only: bool = True,
) -> list[UnadjudicatedAlertCandidate]:
    """Convert raw unmatched defect findings into clustered UnadjudicatedAlertCandidate records.

    By default, `group_by_type_only=True` matches the scorecard audit convention
    ('같은 문서·유형 중복') so same-document, same-type duplicate alerts are flagged.
    """
    candidates: list[UnadjudicatedAlertCandidate] = []
    seen_clusters: set[str] = set()
    seen_alert_ids: dict[str, int] = {}

    for raw in unmatched_findings:
        if not isinstance(raw, dict):
            continue
        if raw.get("advisory_only"):
            continue
        doc_key = str(raw.get("document_key") or raw.get("document") or raw.get("document_id") or "UNKNOWN_DOC").strip()
        ftype = str(raw.get("type") or "UNKNOWN").strip()
        status = str(raw.get("status") or "UNKNOWN").strip()
        severity = str(raw.get("severity") or "MEDIUM").strip()
        grade = str(raw.get("evidence_grade") or "U").strip()
        engine = str(raw.get("engine") or "").strip()
        title = str(raw.get("title") or ftype).strip() or ftype

        page_val = raw.get("page")
        page = int(page_val) if isinstance(page_val, int) and page_val >= 1 else None

        span_raw = raw.get("span")
        span: tuple[int, int] | None = None
        if isinstance(span_raw, (list, tuple)) and len(span_raw) == 2:
            try:
                span = (int(span_raw[0]), int(span_raw[1]))
            except (TypeError, ValueError):
                span = None

        base_id = compute_alert_id(doc_key, raw)
        occ = seen_alert_ids.get(base_id, 0)
        seen_alert_ids[base_id] = occ + 1
        alert_id = base_id if occ == 0 else f"{base_id}_{occ}"

        cluster_id = compute_cluster_id(doc_key, raw, group_by_type_only=group_by_type_only)
        is_dup = cluster_id in seen_clusters
        seen_clusters.add(cluster_id)

        candidates.append(
            UnadjudicatedAlertCandidate(
                alert_id=alert_id,
                document_key=doc_key,
                finding_id=str(raw.get("finding_id") or ""),
                finding_type=ftype,
                status=status,
                severity=severity,
                evidence_grade=grade,
                engine=engine,
                page=page,
                block_id=str(raw.get("block_id")) if raw.get("block_id") else None,
                span=span,
                title=title,
                excerpt=_extract_excerpt(raw),
                cluster_id=cluster_id,
                is_duplicate_in_cluster=is_dup,
            )
        )
    return candidates


def summarize_unadjudicated_alerts(
    candidates: Sequence[UnadjudicatedAlertCandidate],
    *,
    total_documents: int | None = None,
    matched_true_positives: int = 0,
    known_false_positives: int = 0,
    adjudications: Sequence[AlertAdjudicationRecord] | None = None,
) -> dict[str, Any]:
    """Aggregate unadjudicated alerts by grade, type, engine, duplicate clusters, and adjudication labels."""
    total = len(candidates)
    duplicates = sum(1 for c in candidates if c.is_duplicate_in_cluster)
    unique_clusters = total - duplicates

    by_grade: dict[str, int] = defaultdict(int)
    by_type: dict[str, int] = defaultdict(int)
    by_engine: dict[str, int] = defaultdict(int)
    by_doc: dict[str, int] = defaultdict(int)

    for c in candidates:
        by_grade[c.evidence_grade] += 1
        by_type[c.finding_type] += 1
        by_engine[c.engine or "unknown"] += 1
        by_doc[c.document_key] += 1

    doc_denom = total_documents if (total_documents and total_documents > 0) else len(by_doc)
    alerts_per_doc = (total / doc_denom) if doc_denom else 0.0

    summary: dict[str, Any] = {
        "total_unadjudicated": total,
        "unique_clusters": unique_clusters,
        "duplicate_alerts": duplicates,
        "a_grade_alerts": by_grade.get("A", 0),
        "by_grade": dict(sorted(by_grade.items())),
        "by_type": dict(sorted(by_type.items())),
        "by_engine": dict(sorted(by_engine.items())),
        "documents_with_alerts": len(by_doc),
        "alerts_per_document": round(alerts_per_doc, 4),
        "adjudication_status": "UNADJUDICATED",
        "adjudicated_counts": None,
        "measured_alert_precision": None,
        "deduplicated_alert_precision": None,
    }

    if adjudications is not None:
        adj_map = {a.alert_id: a for a in adjudications}
        verdict_counts: dict[str, int] = {
            "TRUE_DEFECT_UNLISTED": 0,
            "TRUE_DEFECT_TOKEN_MISMATCH": 0,
            "DUPLICATE_FINDING": 0,
            "OVERREACH_FALSE_POSITIVE": 0,
            "ADVISORY_MISCLASSIFIED": 0,
        }
        unlabeled = 0
        for c in candidates:
            rec = adj_map.get(c.alert_id)
            if rec is None:
                unlabeled += 1
            else:
                verdict_counts[rec.verdict] += 1

        summary["adjudication_status"] = "COMPLETE" if unlabeled == 0 else "PARTIAL"
        summary["adjudicated_counts"] = {**verdict_counts, "UNLABELED": unlabeled}

        # Precision across all adjudicated findings (matched benchmark hits + adjudicated alerts + known FPs)
        tp_extra = verdict_counts["TRUE_DEFECT_UNLISTED"] + verdict_counts["TRUE_DEFECT_TOKEN_MISMATCH"]
        fp_extra = verdict_counts["OVERREACH_FALSE_POSITIVE"] + verdict_counts["ADVISORY_MISCLASSIFIED"]
        dup_count = verdict_counts["DUPLICATE_FINDING"]

        total_tp = matched_true_positives + tp_extra
        total_fp_raw = known_false_positives + fp_extra + dup_count
        total_fp_dedup = known_false_positives + fp_extra

        raw_denom = total_tp + total_fp_raw
        dedup_denom = total_tp + total_fp_dedup
        summary["measured_alert_precision"] = (total_tp / raw_denom) if raw_denom > 0 else None
        summary["deduplicated_alert_precision"] = (total_tp / dedup_denom) if dedup_denom > 0 else None

    return summary


def classify_offline_legal_reachability(
    defect_type: str,
    *,
    hit: bool,
    has_local_rule_or_range: bool = False,
    format_impossible: bool = False,
) -> tuple[OfflineReachability, str]:
    """Classify a single offline legal benchmark item into one of the 3 reachability buckets.

    1. OFFLINE_VERIFIABLE: Either hit offline, or belongs to a deterministic format/local category
       and was hit.
    2. SOURCE_AVAILABLE_MISSED: Missed (`hit=False`), even though deterministic format rules,
       statute article range tables, or local legal rules (`config/legal_rules/rules.json`) cover it.
    3. EXTERNAL_SOURCE_REQUIRED: Missed (`hit=False`) in offline mode because official case/statute
       full text is required to verify the quote or holding without guessing.
    """
    dtype = str(defect_type or "").strip()
    locally_verifiable = (
        has_local_rule_or_range
        or format_impossible
        or dtype in DETERMINISTIC_OFFLINE_TYPES
    )
    if hit:
        return ("OFFLINE_VERIFIABLE", "오프라인 결정론 규칙·형식·내장 법리표로 적중 확인됨")
    if locally_verifiable:
        return ("SOURCE_AVAILABLE_MISSED", "오프라인 검증 가능 근거(형식·대역·내장 법리표)가 있으나 미탐됨")
    if dtype in EXTERNAL_TEXT_DEPENDENT_TYPES:
        return ("EXTERNAL_SOURCE_REQUIRED", "공식 판결문·법령 본문 조회 또는 스냅샷 리플레이가 필수인 항목")
    return ("SOURCE_AVAILABLE_MISSED", "로컬 문서 내 대조 규칙으로 판정 가능하나 미탐됨")


def summarize_offline_reachability(items: Iterable[ReachabilityItemRecord]) -> dict[str, Any]:
    """Compute separate denominators and recall metrics for the 3 offline reachability categories."""
    records = list(items)
    total = len(records)
    hits = sum(1 for r in records if r.hit)

    buckets: dict[str, list[ReachabilityItemRecord]] = {
        "OFFLINE_VERIFIABLE": [],
        "EXTERNAL_SOURCE_REQUIRED": [],
        "SOURCE_AVAILABLE_MISSED": [],
    }
    by_type: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "hits": 0,
            "OFFLINE_VERIFIABLE": 0,
            "EXTERNAL_SOURCE_REQUIRED": 0,
            "SOURCE_AVAILABLE_MISSED": 0,
        }
    )

    for rec in records:
        buckets[rec.reachability].append(rec)
        row = by_type[rec.defect_type]
        row["total"] += 1
        row["hits"] += int(rec.hit)
        row[rec.reachability] += 1

    # All locally reachable items = OFFLINE_VERIFIABLE (hits) + SOURCE_AVAILABLE_MISSED (misses with local basis)
    locally_reachable_total = len(buckets["OFFLINE_VERIFIABLE"]) + len(buckets["SOURCE_AVAILABLE_MISSED"])
    locally_reachable_hits = sum(1 for r in buckets["OFFLINE_VERIFIABLE"] if r.hit)

    return {
        "total_items": total,
        "total_hits": hits,
        "unseparated_recall": (hits / total) if total > 0 else None,
        "locally_reachable_items": locally_reachable_total,
        "locally_reachable_hits": locally_reachable_hits,
        "locally_reachable_recall": (
            locally_reachable_hits / locally_reachable_total if locally_reachable_total > 0 else None
        ),
        "external_source_required_items": len(buckets["EXTERNAL_SOURCE_REQUIRED"]),
        "source_available_missed_items": len(buckets["SOURCE_AVAILABLE_MISSED"]),
        "by_reachability": {
            key: {
                "items": len(group),
                "hits": sum(1 for r in group if r.hit),
            }
            for key, group in buckets.items()
        },
        "by_defect_type": dict(sorted(by_type.items())),
    }
