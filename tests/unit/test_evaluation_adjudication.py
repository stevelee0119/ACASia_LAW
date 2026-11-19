"""Unit tests for packages/evaluation/adjudication.py (P0 PR-04)."""
from __future__ import annotations

import pytest

from packages.evaluation import (
    AlertAdjudicationRecord,
    ReachabilityItemRecord,
    classify_offline_legal_reachability,
    extract_unadjudicated_alerts,
    summarize_offline_reachability,
    summarize_unadjudicated_alerts,
)


def _sample_findings():
    return [
        {
            "finding_id": "F_1",
            "document_key": "doc_alpha",
            "type": "DATE_MISMATCH",
            "status": "CONTRADICTED",
            "severity": "HIGH",
            "evidence_grade": "A",
            "engine": "claim_engine.date_verifier",
            "page": 2,
            "span": [10, 40],
            "title": "계약 체결일과 이행기 날짜 순서 모순",
            "detail": "본문 제2면의 날짜 기재가 앞 문단과 다릅니다.",
            "evidence": [{"excerpt": "2024년 5월 1일 체결", "description": "날짜 대조"}],
        },
        {
            "finding_id": "F_2",
            "document_key": "doc_alpha",
            "type": "DATE_MISMATCH",
            "status": "CONTRADICTED",
            "severity": "MEDIUM",
            "evidence_grade": "A",
            "engine": "claim_engine.date_verifier",
            "page": 4,
            "span": [100, 130],
            "title": "계약 체결일과 이행기 날짜 순서 모순(재인용)",
            "detail": "동일 날짜 모순의 반복 인용입니다.",
        },
        {
            "finding_id": "F_3",
            "document_key": "doc_beta",
            "type": "LEGAL_ARGUMENT_INVALID",
            "status": "SUSPICIOUS",
            "severity": "HIGH",
            "evidence_grade": "B",
            "engine": "legal_engine.claim_review",
            "page": 1,
            "title": "예외 없는 전칭 일반화 주장",
            "detail": "근거 조문 없이 예외가 없다고 단정함.",
        },
        {
            "finding_id": "F_ADV",
            "document_key": "doc_beta",
            "type": "AUTHORSHIP_SIGNAL",
            "status": "SUSPICIOUS",
            "severity": "LOW",
            "evidence_grade": "D",
            "advisory_only": True,
            "title": "참고 신호는 미판정 결함 경고에서 제외",
        },
    ]


def test_extract_and_cluster_unadjudicated_alerts():
    candidates = extract_unadjudicated_alerts(_sample_findings())
    # advisory_only=True is excluded
    assert len(candidates) == 3
    assert candidates[0].is_duplicate_in_cluster is False
    assert candidates[1].is_duplicate_in_cluster is True
    assert candidates[0].cluster_id == candidates[1].cluster_id
    assert candidates[2].is_duplicate_in_cluster is False
    assert candidates[2].cluster_id != candidates[0].cluster_id


def test_summarize_unadjudicated_alerts_with_and_without_adjudication():
    candidates = extract_unadjudicated_alerts(_sample_findings())
    unlabeled_summary = summarize_unadjudicated_alerts(candidates, total_documents=2)
    assert unlabeled_summary["total_unadjudicated"] == 3
    assert unlabeled_summary["duplicate_alerts"] == 1
    assert unlabeled_summary["unique_clusters"] == 2
    assert unlabeled_summary["a_grade_alerts"] == 2
    assert unlabeled_summary["alerts_per_document"] == 1.5
    assert unlabeled_summary["adjudication_status"] == "UNADJUDICATED"
    assert unlabeled_summary["measured_alert_precision"] is None

    adjudications = [
        AlertAdjudicationRecord(
            alert_id=candidates[0].alert_id,
            document_key=candidates[0].document_key,
            finding_type=candidates[0].finding_type,
            verdict="TRUE_DEFECT_UNLISTED",
            cluster_id=candidates[0].cluster_id,
            reviewer_ids=["rev_1", "rev_2"],
            rationale="실제 날짜 모순 결함에 해당함",
        ),
        AlertAdjudicationRecord(
            alert_id=candidates[1].alert_id,
            document_key=candidates[1].document_key,
            finding_type=candidates[1].finding_type,
            verdict="DUPLICATE_FINDING",
            cluster_id=candidates[1].cluster_id,
            reviewer_ids=["rev_1"],
            rationale="첫 번째 경고와 동일 원인의 중복",
        ),
        AlertAdjudicationRecord(
            alert_id=candidates[2].alert_id,
            document_key=candidates[2].document_key,
            finding_type=candidates[2].finding_type,
            verdict="OVERREACH_FALSE_POSITIVE",
            cluster_id=candidates[2].cluster_id,
            reviewer_ids=["rev_1"],
            rationale="문맥상 정당한 법리 주장",
        ),
    ]
    labeled_summary = summarize_unadjudicated_alerts(
        candidates,
        total_documents=2,
        matched_true_positives=8,
        known_false_positives=0,
        adjudications=adjudications,
    )
    assert labeled_summary["adjudication_status"] == "COMPLETE"
    # TP = 8 + 1 = 9; raw FP = 0 + 1 (overreach) + 1 (dup) = 2 -> 9/11
    assert labeled_summary["measured_alert_precision"] == pytest.approx(9 / 11)
    # Deduplicated FP = 0 + 1 (overreach) -> 9/10
    assert labeled_summary["deduplicated_alert_precision"] == pytest.approx(0.9)


def test_offline_legal_reachability_three_way_split():
    items = [
        ReachabilityItemRecord(
            item_key="item_1",
            document_key="d1",
            defect_type="CIT-NX",
            hit=True,
            reachability=classify_offline_legal_reachability("CIT-NX", hit=True, format_impossible=True)[0],
            reason=classify_offline_legal_reachability("CIT-NX", hit=True, format_impossible=True)[1],
        ),
        ReachabilityItemRecord(
            item_key="item_2",
            document_key="d1",
            defect_type="CIT-FAB-Q",
            hit=False,
            reachability=classify_offline_legal_reachability("CIT-FAB-Q", hit=False)[0],
            reason=classify_offline_legal_reachability("CIT-FAB-Q", hit=False)[1],
        ),
        ReachabilityItemRecord(
            item_key="item_3",
            document_key="d2",
            defect_type="LAW-MIS",
            hit=False,
            reachability=classify_offline_legal_reachability("LAW-MIS", hit=False, has_local_rule_or_range=True)[0],
            reason=classify_offline_legal_reachability("LAW-MIS", hit=False, has_local_rule_or_range=True)[1],
        ),
    ]
    summary = summarize_offline_reachability(items)
    assert summary["total_items"] == 3
    assert summary["total_hits"] == 1
    assert summary["unseparated_recall"] == pytest.approx(1 / 3)
    assert summary["locally_reachable_items"] == 2
    assert summary["locally_reachable_hits"] == 1
    assert summary["locally_reachable_recall"] == pytest.approx(0.5)
    assert summary["external_source_required_items"] == 1
    assert summary["source_available_missed_items"] == 1
