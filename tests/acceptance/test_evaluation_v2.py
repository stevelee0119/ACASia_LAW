"""Evaluator contracts: distinguish measurement failure, weak evidence and real progress."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts import evaluation_v2 as v2
from scripts import evaluation_dashboard as dashboard
from scripts import export_quality_predictions as exporter
from scripts import retired_compare as retired


def synthetic(tmp_path, items=1, kind="EVI-DATE"):
    (tmp_path / "T.pdf").write_bytes(b"synthetic only")
    (tmp_path / "ground_truth.json").write_text(json.dumps({"documents": {
        "T": {"file": "T.pdf", "expected": "FAIL", "items": [[kind, "page 1", "synthetic"]] * items}}}))
    (tmp_path / "match_spec.json").write_text(json.dumps({"tokens": {"T": [[["TOKEN"]]] * items}}))
    finding = {"finding_id": "f", "document_id": "d", "type": "EVIDENCE_DATE_INVALID", "title": "TOKEN",
               "status": "CONTRADICTED", "severity": "MEDIUM", "evidence_grade": "B", "evidence": []}
    payload = {"documents": [{"filename": "T.pdf", "document_id": "d", "findings": [finding]}]}
    return payload, finding


def test_one_finding_cannot_answer_two_gold_items(tmp_path):
    payload, _ = synthetic(tmp_path, items=2)
    assert v2.score(payload, tmp_path)["hits"] == 1
    assert len(v2.maximum_matching({0: [0, 1], 1: [0]})) == 2  # not greedy matching


@pytest.mark.parametrize("state,advisory", [("UNVERIFIED", False), ("CONTRADICTED", True), ("VERIFIED", False)])
def test_no_fractional_or_advisory_credit(tmp_path, state, advisory):
    payload, finding = synthetic(tmp_path)
    finding.update(status=state, advisory_only=advisory)
    assert v2.score(payload, tmp_path)["hits"] == 0


def test_metadata_only_keywords_do_not_earn_credit(tmp_path):
    payload, finding = synthetic(tmp_path)
    finding.update(title="different", confidence_features={"context": "TOKEN"})
    assert v2.score(payload, tmp_path)["hits"] == 0


def test_duplicate_finding_identity_is_not_extra_evidence(tmp_path):
    payload, finding = synthetic(tmp_path, items=2)
    payload["project_findings"] = [copy.deepcopy(finding)]
    assert v2.score(payload, tmp_path)["hits"] == 1


@pytest.mark.parametrize("state,expected", [("UNVERIFIED", 1), ("NOT_FOUND", 0), ("VERIFIED", 0)])
def test_uncertain_source_state_contract(tmp_path, state, expected):
    payload, finding = synthetic(tmp_path, kind="CIT-NX-DB")
    finding.update(type="CASE_NOT_FOUND", status=state)
    assert v2.score(payload, tmp_path)["hits"] == expected


def test_unmatched_warning_not_hidden_or_assumed_false(tmp_path):
    payload, _ = synthetic(tmp_path)
    payload["documents"][0]["findings"].append({"type": "EVIDENCE_DATE_INVALID", "status": "CONTRADICTED", "title": "OTHER"})
    result = v2.score(payload, tmp_path)
    assert result["known_false_positive_findings"] == 0
    assert result["unadjudicated_alerts"] == 1
    assert result["precision"] is None and result["legal_accuracy"] is None


@pytest.mark.parametrize("mutation", [lambda p: p.update(documents=[]), lambda p: p.update(errors=["failed"]),
                                    lambda p: p["documents"].append(copy.deepcopy(p["documents"][0]))])
def test_incomplete_execution_is_not_zero_score(tmp_path, mutation):
    payload, _ = synthetic(tmp_path)
    mutation(payload)
    with pytest.raises(ValueError):
        v2.score(payload, tmp_path)


def test_quarantine_is_a_decision_not_runner_failure(tmp_path):
    payload, _ = synthetic(tmp_path)
    payload["documents"][0]["quarantined"] = True
    assert v2.score(payload, tmp_path)["hits"] == 1


def test_empty_match_tokens_are_rejected(tmp_path):
    payload, _ = synthetic(tmp_path)
    (tmp_path / "match_spec.json").write_text(json.dumps({"tokens": {"T": [[[]]]}}))
    with pytest.raises(ValueError):
        v2.score(payload, tmp_path)


@pytest.mark.parametrize("mutation", [lambda x: x.update(items=999), lambda x: x.update(dataset_sha256="changed"),
                                    lambda x: x["by_type"]["EVI-DATE"].update(hits=0),
                                    lambda x: x["by_type"]["EVI-DATE"].update(hits=float("nan"))])
def test_count_hash_or_denominator_changes_fail_gate(tmp_path, mutation):
    payload, _ = synthetic(tmp_path)
    base = v2.score(payload, tmp_path)
    now = copy.deepcopy(base)
    mutation(now)
    assert v2.compare_sets({"s": now}, {"s": base})
    assert v2.compare_sets({}, {"s": base})


def test_failed_base_and_empty_inventory_fail_closed():
    assert retired.compare({"s": None}, {"s": None})
    assert retired.compare({}, {})


def test_retired_summary_contains_actual_counts():
    row = {"overall": 10, "false_positives": 0, "a_grade_fp": 0, "injection_defended": None,
           "regression_v2": {"hits": 1, "items": 5, "unadjudicated_alerts": 3}}
    rendered = retired._row("synthetic", row, row)
    assert "synthetic" in rendered and "1/5" in rendered and "미판정 3" in rendered


def test_retired_inventory_refuses_missing_set(tmp_path):
    with pytest.raises(ValueError):
        retired.check_inventory(tmp_path)


def product():
    return {"run_id": "run", "documents": [{"sha256": "a" * 64,
        "citations": [{"citation_id": "c", "raw_text": "synthetic citation", "quoted_text": "synthetic quotation", "page": 1, "span": [0, 18]}],
        "engine_data": {"legal_verdicts": [{"citation_id": "c", "status": "VERIFIED",
            "levels": {"level1": "VERIFIED", "level2": "VERIFIED", "level3": "UNVERIFIED"}, "findings": []}]}}]}


def test_export_separates_identity_and_quote_without_reading_gold():
    payload = product()
    index = exporter.inventory(payload)
    values = exporter.export(payload, index, "product-sha")
    decisions = {i["dimension"]: p.status for i, p in zip(index["items"], values)}
    assert decisions == {"identity": "VERIFIED", "quote": "UNVERIFIED"}
    assert all(p.cost is None for p in values)


def test_missing_extraction_abstains_with_same_denominator():
    payload = product(); index = exporter.inventory(payload)
    payload["documents"][0]["citations"] = []
    values = exporter.export(payload, index, "sha")
    assert len(values) == 2 and all(p.status == "ABSTAIN" for p in values)


def test_binding_does_not_use_transient_citation_ids():
    payload = product(); index = exporter.inventory(payload)
    payload["documents"][0]["citations"][0]["citation_id"] = "new"
    payload["documents"][0]["engine_data"]["legal_verdicts"][0]["citation_id"] = "new"
    assert exporter.inventory(payload) == index
    assert exporter.export(payload, index, "sha")[0].status == "VERIFIED"


def test_duplicate_binding_refused():
    payload = product()
    payload["documents"][0]["citations"] *= 2
    with pytest.raises(ValueError):
        exporter.inventory(payload)


def test_unknown_status_and_verified_error_conflict_refused():
    with pytest.raises(ValueError):
        exporter.decision({"levels": {"level3": "NEW_UNKNOWN_STATE"}}, "quote")
    with pytest.raises(ValueError):
        exporter.decision({"levels": {"level3": "VERIFIED"}, "findings": [
            {"type": "CASE_QUOTE_MISMATCH", "status": "CONTRADICTED"}]}, "quote")


def test_statute_dimensions_and_invalid_citation_format():
    verdict = {"levels": {"existence": "VERIFIED", "article": "VERIFIED", "content": "CONTRADICTED"}}
    assert exporter.decision(verdict, "identity")[0] == "VERIFIED"
    assert exporter.decision(verdict, "quote")[0] == "CONTRADICTED"
    assert exporter.decision({"levels": {"level1": "UNVERIFIED", "number_format": "IMPOSSIBLE"}}, "identity")[0] == "CONTRADICTED"


def test_new_unlabeled_outputs_are_reported(tmp_path):
    payload = product(); index = exporter.inventory(payload)
    extra = copy.deepcopy(payload["documents"][0]["citations"][0]); extra.update(citation_id="extra", page=2)
    payload["documents"][0]["citations"].append(extra)
    assert len(exporter.export(payload, index, "sha")) == 2
    assert exporter.unbound_count(payload, index) == 2


def test_compact_finding_reference_is_resolved_before_conflict_check():
    payload = product(); index = exporter.inventory(payload)
    doc = payload["documents"][0]
    doc["findings"] = [{"finding_id": "f", "type": "CASE_QUOTE_MISMATCH", "status": "CONTRADICTED"}]
    verdict = doc["engine_data"]["legal_verdicts"][0]
    verdict["levels"]["level3"] = "VERIFIED"
    verdict["findings"] = [{"finding_id": "f", "type": "CASE_QUOTE_MISMATCH"}]
    with pytest.raises(ValueError, match="conflicts"):
        exporter.export(payload, index, "sha")


def test_content_error_does_not_invalidate_statute_identity():
    verdict = {"levels": {"existence": "VERIFIED", "article": "VERIFIED", "content": "CONTRADICTED"},
               "findings": [{"type": "LAW_CITATION_ERROR", "status": "CONTRADICTED"}]}
    assert exporter.decision(verdict, "identity") == ("VERIFIED", [])
    assert exporter.decision(verdict, "quote") == ("CONTRADICTED", ["QUOTE_CONTENT_ERROR"])


def test_retired_cache_changes_when_frozen_bytes_change(tmp_path, monkeypatch):
    from scripts import scorecard
    folder = tmp_path / retired.RETIRED / "synthetic"
    folder.mkdir(parents=True)
    synthetic(folder)
    monkeypatch.setattr(retired, "ROOT", tmp_path)
    monkeypatch.setattr(scorecard, "tesseract_info", lambda: {"version": "synthetic", "langs": []})
    first = retired.cache_file("base", ["synthetic"])
    (folder / "T.pdf").write_bytes(b"different synthetic bytes")
    assert retired.cache_file("base", ["synthetic"]) != first


def test_dashboard_keeps_unknown_quality_unknown():
    base = json.loads((Path(dashboard.ROOT) / "docs/scorecards/regression_v2_baseline.json").read_text())
    card = {"sets": {k: {"regression_v2": v} for k, v in base["sets"].items()}}
    report = dashboard.build(card)
    assert report["regression"]["status"] == "MEASURED"
    assert report["legal_quality_approval"] == "NOT_ESTABLISHED"
    assert all(report[k]["status"] == "NOT_MEASURED" and report[k]["value"] is None
               for k in ["labeled_quality", "retrieval", "legal_argument_validity", "practice_utility"])
    # 외부 벤치마크는 미적용(사용자 결정 2026-11-13): 미측정과 구분해 NOT_APPLIED로 남고 값은 없다.
    assert report["public_benchmark"]["status"] == "NOT_APPLIED" and report["public_benchmark"]["value"] is None
    card["sets"].pop("holdout")
    assert dashboard.build(card)["regression"]["status"] == "FAILED"


def test_external_benchmark_is_not_applied_and_cannot_be_attached(tmp_path):
    # 외부 벤치마크 미적용(사용자 결정 2026-11-13): 보고서·성적표에 '미적용'으로 남고, 점수를 붙이는 입력 경로가 없다.
    base = json.loads((Path(dashboard.ROOT) / "docs/scorecards/regression_v2_baseline.json").read_text())
    card = {"git": {"sha": "current"}, "sets": {k: {"regression_v2": v} for k, v in base["sets"].items()}}
    report = dashboard.build(card)
    assert report["public_benchmark"] == dashboard.NOT_APPLIED_PUBLIC_BENCHMARK
    assert "| public_benchmark | NOT_APPLIED |" in dashboard.render(report)
    scorecard_text = (Path(dashboard.ROOT) / "scripts/scorecard.py").read_text(encoding="utf-8")
    assert '"public_benchmarks": {"status": "NOT_APPLIED"' in scorecard_text
    with pytest.raises(TypeError):
        dashboard.build(card, kbl_dataset=tmp_path, kbl_predictions=tmp_path)
    with pytest.raises(SystemExit):
        dashboard.main(["--scorecard", str(tmp_path / "s.json"), "--kbl-dataset", str(tmp_path), "--out", str(tmp_path / "o.json")])
    assert not (Path(dashboard.ROOT) / "scripts/evaluate_kbl.py").exists()


def test_dashboard_rejects_mismatched_labeled_prediction_version(tmp_path):
    # Synthetic schema exercise of declared attorney provenance, not actual attorney labels.
    label = {"item_id": "synthetic", "case_id": "synthetic", "case_family_id": "synthetic", "split": "TEST",
             "origin": "ATTORNEY_LABELED", "input_text": "synthetic example", "gold_status": "CONTRADICTED",
             "error_types": ["QUOTE_CONTENT_ERROR"], "annotation": {"reviewer_ids": ["mock1", "mock2"],
             "qualifications_confirmed": True, "adjudicated": True, "rationale": "SYNTHETIC SCHEMA TEST"}}
    pred = {"item_id": "synthetic", "run_id": "mock", "system_version": "old", "status": "CONTRADICTED", "error_types": ["QUOTE_CONTENT_ERROR"]}
    labels=tmp_path/"labels.jsonl"; predictions=tmp_path/"predictions.jsonl"
    labels.write_text(json.dumps(label)+"\n"); predictions.write_text(json.dumps(pred)+"\n")
    base = json.loads((Path(dashboard.ROOT) / "docs/scorecards/regression_v2_baseline.json").read_text())
    card = {"git": {"sha": "current"}, "sets": {k: {"regression_v2": v} for k, v in base["sets"].items()}}
    with pytest.raises(ValueError, match="exact scorecard product SHA"):
        dashboard.build(card, labels, predictions)


def test_workflow_preserves_legacy_gate_and_adds_v2():
    import yaml
    workflow = yaml.safe_load((Path(dashboard.ROOT) / ".github/workflows/score-gate.yml").read_text())
    steps = workflow["jobs"]["score-gate"]["steps"]
    assert any("score_gate.py" in s.get("run", "") for s in steps)
    assert any("evaluation_dashboard.py" in s.get("run", "") for s in steps)
    assert any("check_inventory" in s.get("run", "") for s in steps)
