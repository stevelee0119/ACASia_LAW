"""TK-185: repeated measurements must prove input and execution comparability."""
from copy import deepcopy
import json
from itertools import count

import pytest

from scripts import ai_repeat_summary as tool

_RUN_IDS = count(1)


def report():
    versions = {"rule": "rule-1", "prompt": "prompt-1", "model_config": "model-policy-1"}
    return {
        "started_at": "2026-11-15T10:00:00", "run_id": f"run-{next(_RUN_IDS)}",
        "run_manifest": {
            "implementation": {"git_commit": "a" * 40}, "versions": versions.copy(),
            "environment": {"fingerprint": "environment-1"},
            "reference_library": {"status": "READY", "folder_id": "private-folder", "snapshot_hash": "b" * 64},
        },
        "input_snapshot": {
            "documents": [{"document_id": "doc-1", "sha256": "c" * 64, "is_own_document": False,
                           "filename": "sample.pdf", "mime_type": "application/pdf"}],
            "context": {"project_id": "project-1", "profile": "STANDARD", "case_date": None,
                        "external_ai_policy": "MASKED", "issue_dates": {}, "requested_issues": [],
                        "counterparty_document": True},
            "security": {"external_ai_policy": "MASKED", "blocked_providers": [], "block_sealed_reveal": False},
            "execution": {"providers": {"a": {"model": "model-a", "enabled": True},
                                         "b": {"model": "model-b", "enabled": True}},
                          "pricing": {}, "budget": {},
                          "settings": {"allow_network": True, "llm_cross_check": "auto", "llm_efficient_routing": True,
                                       "llm_routing": {}, "llm_model_overrides": {}, "llm_default_models": {},
                                       "rag_drive_folder_id": "private-folder", "korean_law_review_profile": False,
                                       "rule_version": "rule-1", "prompt_version": "prompt-1"}},
            "versions": versions.copy(), "issues": [],
        },
        "documents": [{"document_id": "doc-1", "sha256": "c" * 64,
                       "ai_detector_result": {"model_opinions": [{"provider": "a", "verdict": "PARTIAL", "score": 0.6}]}}],
        "scores": {"axes": {"ai_authorship": {"documents": [{"document_id": "doc-1", "verdict": "AI_PARTIAL_GENERATION", "score": 0.6}]}}},
    }


def summary(*reports):
    return tool.summarize([tool.observe(r) for r in reports])


def test_complete_same_conditions_and_auto_routing_participation():
    a, b = report(), report()
    b["run_id"] = "run-2"
    b["started_at"] = "2026-11-15T11:00:00+00:00"
    b["documents"][0]["ai_detector_result"]["model_opinions"].append({"provider": "b", "verdict": "FULL", "score": 0.8})
    s = summary(a, b)
    assert s["same_condition"] and s["condition_status"] == "SAME"
    assert s["comparable_agreement"] == 1
    assert s["provider_score_range"]["b"] == [0.8, 0.8, 1]
    output = json.dumps(tool.observe(a))
    assert "private-folder" not in output and "MASKED" not in output


@pytest.mark.parametrize("path,value,field", [
    (("run_manifest", "implementation", "git_commit"), "a" * 12 + "d" * 28, "commit"),
    (("input_snapshot", "context", "profile"), "STRICT", "context"),
    (("input_snapshot", "context", "project_id"), "different-project", "context"),
    (("input_snapshot", "documents", 0, "filename"), "renamed.pdf", "input"),
    (("input_snapshot", "context", "case_date"), "2026-01-01", "context"),
    (("input_snapshot", "security", "external_ai_policy"), "LOCAL_ONLY", "security"),
    (("input_snapshot", "execution", "settings", "llm_cross_check"), "always", "execution.settings"),
    (("input_snapshot", "execution", "providers", "a", "model"), "other-model", "execution.providers"),
    (("run_manifest", "versions", "prompt"), "prompt-2", "versions"),
    (("run_manifest", "reference_library", "snapshot_hash"), "d" * 64, "reference_library"),
    (("run_manifest", "environment", "fingerprint"), "other-env", "environment"),
    (("started_at",), "2026-11-15T15:00:00Z", "reference_date"),
])
def test_changed_conditions_are_not_comparable(path, value, field):
    a, b = report(), report()
    node = b
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    s = summary(a, b)
    assert not s["same_condition"] and s["comparable_agreement"] is None
    assert field in s["different_conditions"]


def test_different_input_bytes_even_with_equal_commit():
    a, b = report(), report()
    b["documents"][0]["sha256"] = b["input_snapshot"]["documents"][0]["sha256"] = "d" * 64
    assert "input" in summary(a, b)["different_conditions"]


@pytest.mark.parametrize("path", [
    ("run_manifest", "implementation", "git_commit"), ("input_snapshot", "documents", 0, "sha256"),
    ("input_snapshot", "documents", 0, "filename"), ("input_snapshot", "documents", 0, "is_own_document"),
    ("input_snapshot", "context", "profile"), ("input_snapshot", "security", "external_ai_policy"),
    ("input_snapshot", "execution", "settings", "llm_cross_check"),
    ("input_snapshot", "execution", "providers", "a", "model"),
    ("run_manifest", "versions", "model_config"), ("input_snapshot", "issues"),
    ("run_manifest", "reference_library", "snapshot_hash"), ("started_at",),
])
def test_equal_missing_evidence_is_unknown(path):
    a = report()
    node = a
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    s = summary(a, deepcopy(a))
    assert s["condition_status"] == "UNKNOWN" and not s["same_condition"]
    assert s["missing_conditions"] and s["comparable_agreement"] is None


def test_multiple_documents_rejected_without_first_document_aggregation():
    a = report()
    a["documents"].append(deepcopy(a["documents"][0]))
    with pytest.raises(ValueError, match="문서별"):
        summary(a, a)


@pytest.mark.parametrize("path", [
    ("input_snapshot", "security", "external_ai_policy"),
    ("run_manifest", "versions", "prompt"), ("started_at",),
])
@pytest.mark.parametrize("value", [None, ""])
def test_empty_required_values_cannot_prove_equality(path, value):
    a = report()
    node = a
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    assert summary(a, a)["condition_status"] == "UNKNOWN"


def test_missing_or_mismatched_axis_document_is_not_comparable():
    a = report()
    a["scores"]["axes"]["ai_authorship"]["documents"][0]["document_id"] = "different-document"
    assert summary(a, a)["condition_status"] == "UNKNOWN"


def test_explicit_disabled_drive_and_single_run():
    a = report()
    a["run_manifest"]["reference_library"] = {"status": "DISABLED", "folder_id": "", "snapshot_hash": None}
    a["input_snapshot"]["execution"]["settings"]["rag_drive_folder_id"] = ""
    b = deepcopy(a)
    b["run_id"] = "another-run"
    assert summary(a, b)["same_condition"]
    assert not summary(a)["same_condition"]
    assert not summary()["same_condition"]


def test_duplicate_reports_are_not_independent_repetitions():
    a = report()
    s = summary(a, deepcopy(a))
    assert not s["same_condition"] and "distinct_run_ids" in s["missing_conditions"]
    assert s["comparable_agreement"] is None


def test_cli_unknown_conditions_exit_two_and_no_raw_context(tmp_path, capsys):
    a = report()
    a["input_snapshot"]["context"]["parties"] = ["private-name"]
    del a["run_manifest"]["implementation"]["git_commit"]
    path = tmp_path / "report.json"
    path.write_text(json.dumps(a))
    assert tool.main(["--reports", str(path), str(path), "--json"]) == 2
    output = capsys.readouterr().out
    assert "private-name" not in output and "private-folder" not in output
    assert json.loads(output)["summary"]["condition_status"] == "UNKNOWN"
