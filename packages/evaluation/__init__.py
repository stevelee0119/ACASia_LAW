"""Offline, case-separated evaluation of externally supplied predictions and alert adjudication."""
from .adjudication import (
    classify_offline_legal_reachability,
    compute_alert_id,
    compute_cluster_id,
    extract_unadjudicated_alerts,
    summarize_offline_reachability,
    summarize_unadjudicated_alerts,
)
from .quality import evaluate_quality, load_jsonl, validate_case_splits
from .schemas import (
    AdjudicationVerdict,
    AlertAdjudicationRecord,
    LabelRecord,
    OfflineReachability,
    PredictionRecord,
    ReachabilityItemRecord,
    UnadjudicatedAlertCandidate,
)

__all__ = [
    "AdjudicationVerdict",
    "AlertAdjudicationRecord",
    "LabelRecord",
    "OfflineReachability",
    "PredictionRecord",
    "ReachabilityItemRecord",
    "UnadjudicatedAlertCandidate",
    "classify_offline_legal_reachability",
    "compute_alert_id",
    "compute_cluster_id",
    "evaluate_quality",
    "extract_unadjudicated_alerts",
    "load_jsonl",
    "summarize_offline_reachability",
    "summarize_unadjudicated_alerts",
    "validate_case_splits",
]

