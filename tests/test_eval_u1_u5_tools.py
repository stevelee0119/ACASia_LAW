"""U1~U5(사용자 승인 11-14 'U-1~5 모두 반영') 평가 도구 시험. 값은 모두 합성이다."""
import json
from pathlib import Path

import pytest

from scripts import ai_repeat_summary, eval_testset, score_report, score_sealed_online

ROOT = Path(__file__).resolve().parents[1]


def _report(sources, observations, kinds=None, network=True):
    return {"run_id": "r", "run_manifest": {"environment": {"network": network},
                                            "implementation": {"git_commit": "abc1234567890"}},
            "documents": [{"filename": "SD-01_x.pdf", "findings": [], "masked_preview": {"kinds": kinds or {}},
                           "engine_data": {"rag": {"sources": sources, "observations": observations}}}]}


def _rag_rows(report, checks, tmp_path):
    path = tmp_path / "r.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps({"name": "t", "checks": checks}), encoding="utf-8")
    return {row["id"]: row["passed"] for row in score_report.score(path, spec)["rows"]}


def test_rag_source_controls_positive_and_negative(tmp_path):
    report = _report([{"source_id": "R1", "title": "야간사격훈련_지침.pdf"}, {"source_id": "R2", "title": "다른자료.pdf"}],
                     [{"source_id": "R1", "relationship": "SUPPORTS", "claim_quote": "가"},
                      {"source_id": "R2", "relationship": "CONTRADICTS", "claim_quote": "나"}])
    checks = [{"id": "S1", "kind": "rag_source_selected", "title": "야간사격훈련", "expect": True},
              {"id": "S2", "kind": "rag_source_relationship", "title": "야간사격훈련", "any_of": ["CONTRADICTS"], "expect": False},
              {"id": "S3", "kind": "rag_source_relationship", "title": "야간사격훈련", "any_of": ["SUPPORTS"], "expect": True},
              {"id": "N1", "kind": "rag_source_selected", "title": "학교급식", "expect": False},
              {"id": "N2", "kind": "rag_source_relationship", "title": "다른자료", "any_of": ["CONTRADICTS"], "expect": False}]
    assert _rag_rows(report, checks, tmp_path) == {"S1": True, "S2": True, "S3": True, "N1": True, "N2": False}


def test_rag_control_spec_loads():
    spec = score_report.load_spec(ROOT / "tests/fixtures/probes/case9_state_compensation_online_rag_controls.json")
    assert {c["kind"] for c in spec["checks"]} == {"rag_source_selected", "rag_source_relationship"}
    for name in ("rag_control_support_night_firing_safety.pdf", "rag_control_unrelated_school_meal.pdf"):
        assert (ROOT / "tests/fixtures/rag_controls" / name).is_file()


def test_scorer_new_defect_kinds_are_additive_and_resolvable():
    for kind in ("FOR-META", "FOR-HIDDEN", "FOR-SIG", "FOR-TRACK", "RHET", "CIT-INT", "CALC-INV", "DOC-QUAL"):
        assert eval_testset.allowed_types(kind)
    assert eval_testset.allowed_types("FOR-SIG / RHET") >= {"SIGNATURE_INVALID", "COERCIVE_LANGUAGE_SIGNAL"}
    assert "CASE_NOT_FOUND" in eval_testset.allowed_types("CIT-NX")   # 기존 유형 그대로


def test_pii_kind_score_counts_kinds_only():
    gt = {"SD-01": {"pii_kinds": ["PERSON", "PHONE", "ACCOUNT"]}, "SD-02": {}}
    result = _report([], [], kinds={"PERSON": 2, "PHONE": 1, "EMAIL": 1})
    assert eval_testset.pii_kind_score(result, gt) == {"expected_kinds": 3, "found_kinds": 2, "recall": 0.667}
    assert eval_testset.pii_kind_score(result, {"SD-01": {}}) is None


def test_sealed_online_refuses_repo_dirs_and_missing_files(tmp_path):
    report = tmp_path / "r.json"
    report.write_text("{}", encoding="utf-8")
    assert score_sealed_online.main(["--report", str(report), "--sealed-dir", str(ROOT / "tests")]) == 2
    assert score_sealed_online.main(["--report", str(report), "--sealed-dir", str(tmp_path)]) == 2


def test_ai_repeat_summary_agreement_and_condition():
    def run(commit, verdict, score, opinions):
        return {"run_manifest": {"implementation": {"git_commit": commit}},
                "scores": {"axes": {"ai_authorship": {"documents": [{"verdict": verdict, "score": score}]}}},
                "documents": [{"ai_detector_result": {"model_opinions": opinions}}]}
    runs = [ai_repeat_summary.observe(run("c1", "AI_PARTIAL_GENERATION", 0.6, [{"provider": "a", "verdict": "AI_X", "score": 0.6}])),
            ai_repeat_summary.observe(run("c1", "UNCERTAIN", 0.5, [{"provider": "a", "verdict": "UNCERTAIN", "score": 0.4}])),
            ai_repeat_summary.observe(run("c1", "AI_PARTIAL_GENERATION", 0.7, [{"provider": "a", "verdict": "AI_X", "score": 0.8}]))]
    summary = ai_repeat_summary.summarize(runs, ["AI_PARTIAL_GENERATION"])
    assert summary["same_condition"] and summary["agreement"] == 0.667 and summary["uncertain_runs"] == 1
    assert summary["expected_ratio"] == 0.667 and summary["provider_score_range"]["a"] == [0.4, 0.8, 3]
    runs[0]["commit"] = "c2"
    assert ai_repeat_summary.summarize(runs)["same_condition"] is False
