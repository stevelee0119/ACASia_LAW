"""2026-11-14 평가 체계 감사 보완 도구 시험(평가 측). 값은 모두 합성이다.

- scorecard: 엔진 오류('단계:예외 종류')와 결함 유형별 집계를 성적표에 싣는다(봉인도 숫자만).
- score_gate: 알려진 목록에 없는 엔진 오류는 실패, 알려졌는데 더는 나지 않으면 경고.
- score_report: run_health로 실행 기록(엔진 오류·공식 DB·모델·Drive 동기화·커밋)을 본다.
"""
import json
from pathlib import Path

import pytest

from scripts import score_gate, score_report, scorecard

ROOT = Path(__file__).resolve().parents[1]


def _manifest(**over):
    manifest = {
        "implementation": {"git_commit": "abcdef1234567890"},
        "sources": {"law_go_kr": "READY"},
        "engines": {"legal_rules": {"executed": True, "errors": []},
                    "reference_sync": {"executed": True, "errors": []}},
        "source_lookup_summary": {"requests": 12, "retryable_failures": 0, "by_status": {"READY": 12}},
        "model_execution_summary": {"providers": {"a": {"calls": 10, "failed": 0, "errors": {}}}},
        "reference_library": {"status": "READY", "files_indexed": 3, "files_seen": 3,
                              "diagnostics": {"issue_counts": {}, "case_table_candidates": []}},
    }
    manifest.update(over)
    return manifest


def test_scorecard_counts_engine_errors_by_stage_and_exception_only():
    result = {"run_manifest": {"engines": {
        "legal_rules": {"errors": ["doc_1: NameError", "doc_2: NameError"]},
        "timeline": {"errors": ["doc_1: KeyError"]},
        "ocr": {"errors": []}, "note": "x"}}}
    assert scorecard.engine_errors(result) == {"legal_rules:NameError": 2, "timeline:KeyError": 1}
    assert scorecard.engine_errors({}) == {}


def test_scorecard_summary_has_per_type_numbers_even_when_sealed():
    report = {"overall": 50.0, "weighted_recall": 0.5, "defect_items": 4, "false_positives_total": 0,
              "fp_trap_false_positives": 0, "control_false_positives": 0, "a_grade_false_positives": 0,
              "duplicate_citation_verdicts": 0, "findings_without_document_id": 0, "injection_defense": None,
              "per_document": {"D1": {"recall": 0.5}},
              "per_type": {"LAW-NX": {"recall": 1.0, "items": 2}, "CIT-NX": {"recall": 0.0, "items": 2}}}
    sealed = scorecard.summarize(report, documents=1, sealed=True)
    assert sealed["per_type"] == {"CIT-NX": {"items": 2, "recall": 0.0}, "LAW-NX": {"items": 2, "recall": 1.0}}
    assert "per_document" not in sealed
    assert "per_document" in scorecard.summarize(report, documents=1, sealed=False)


def test_score_gate_fails_on_unknown_engine_error_and_warns_on_stale_known(tmp_path):
    card = {"sets": {"dev": {"engine_errors": {"legal_rules:NameError": 3, "timeline:KeyError": 1}}}}
    known = {"legal_rules:NameError": "TK-177"}
    failures, warnings = score_gate.engine_error_check(card, known)
    assert len(failures) == 1 and "timeline:KeyError" in failures[0]
    assert warnings == []
    failures, warnings = score_gate.engine_error_check({"sets": {"dev": {"engine_errors": {}}}}, known)
    assert failures == [] and "TK-177" in warnings[0]
    failures, _ = score_gate.engine_error_check({"sets": {"dev": {"engine_errors": {"legal_rules:NameError": 1}}}}, {})
    assert failures


def test_known_engine_errors_file_is_well_formed():
    known = score_gate.known_engine_errors()
    assert all(":" in key and ticket for key, ticket in known.items())
    assert score_gate.known_engine_errors(Path("/nonexistent/known.json")) == {}


@pytest.mark.parametrize("which, manifest, expected", [
    ("engine_errors", _manifest(), True),
    ("engine_errors", _manifest(engines={"legal_rules": {"errors": ["d: NameError"]}}), False),
    ("law_db_ready", _manifest(), True),
    ("law_db_ready", _manifest(sources={"law_go_kr": "MISSING_KEY"}), False),
    ("source_lookups", _manifest(), True),
    ("source_lookups", _manifest(source_lookup_summary={"requests": 12, "retryable_failures": 2}), False),
    ("source_lookups", _manifest(source_lookup_summary={"requests": 0, "retryable_failures": 0}), False),
    ("models_ok", _manifest(), True),
    ("models_ok", _manifest(model_execution_summary={"providers": {"a": {"calls": 10, "failed": 5}}}), False),
    ("models_ok", _manifest(model_execution_summary={}), False),
    ("reference_sync", _manifest(), True),
    ("reference_sync", _manifest(reference_library={"status": "PARTIAL", "diagnostics": {}}), False),
    ("commit_present", _manifest(), True),
    ("commit_present", _manifest(implementation={}), False),
])
def test_run_health_checks(which, manifest, expected):
    check = {"id": "H", "kind": "run_health", "check": which, "min_requests": 1}
    passed, detail = score_report.run_health(check, manifest)
    assert passed is expected and detail


def test_run_health_engine_allow_and_partial_reference_options():
    manifest = _manifest(engines={"reference_sync": {"errors": ["project: 동기화 미완료"]},
                                  "legal_rules": {"errors": ["d: NameError"]}})
    assert score_report.run_health({"check": "engine_errors", "allow": ["reference_sync"]}, manifest)[0] is False
    assert score_report.run_health({"check": "engine_errors", "allow": ["reference_sync", "legal_rules:NameError"]},
                                   manifest)[0] is True
    partial = _manifest(reference_library={"status": "PARTIAL", "diagnostics": {
        "issue_counts": {"REFERENCE_QUARANTINED": 1},
        "case_table_candidates": [{"reason": "REFERENCE_QUARANTINED", "indexed_rows": 0}]}})
    check = {"check": "reference_sync", "allow_partial": True, "max_quarantined": 2}
    passed, detail = score_report.run_health(check, partial)
    assert passed is False and "격리 1" in detail   # 판례표가 격리되면 부분 허용이어도 실패


def test_health_specs_load_and_score_a_synthetic_report(tmp_path):
    report = {"documents": [], "run_manifest": _manifest(), "run_id": "r"}
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    for name in ("online_pipeline_health", "case9_state_compensation_online_health"):
        result = score_report.score(path, ROOT / "tests/fixtures/probes" / f"{name}.json")
        assert result["passed"] == result["total"], result["failed"]
    with pytest.raises(ValueError):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"name": "x", "checks": [{"id": "a", "kind": "run_health", "check": "nope"}]}),
                       encoding="utf-8")
        score_report.load_spec(bad)


def test_private_probe_overlap_reports_counts_only(tmp_path):
    from scripts import check_private_probe_overlap as overlap
    root = tmp_path / "repo"
    (root / "packages").mkdir(parents=True)
    phrase = "합성원고는합성피고에게합성물품대금을청구한다"
    (root / "packages" / "rule.py").write_text(
        f'PATTERN = r"{phrase}"\nCASE = "2099가합12345"\nAMOUNT = "123,456,789원"\n', encoding="utf-8")
    (root / "packages" / "clean.py").write_text('MESSAGE = "일반적인 안내 문구입니다"\n', encoding="utf-8")
    probe = f"서면 본문: {phrase} 사건 2099가합12345 금액 123,456,789원"
    hits = overlap.overlaps([probe], root=root)
    assert hits == {"packages/rule.py": {"values": 2, "phrases": 1}}
    assert overlap.overlaps(["전혀 다른 합성 문장으로 이루어진 탐침 본문입니다 2099가단1"], root=root) == {}


def test_private_probe_overlap_refuses_dirs_inside_repo(tmp_path):
    from scripts import check_private_probe_overlap as overlap
    assert overlap.main(["--probe-dir", str(ROOT / "tests")]) == 2
    assert overlap.main(["--probe-dir", str(tmp_path)]) == 2   # .txt 없음


def test_eval_coverage_counts_layers():
    from scripts import eval_coverage
    data = eval_coverage.build()
    summary = data["summary"]
    assert summary["total"] == len(data["rows"]) >= 90
    assert 0 < summary["offline_scorer"] <= summary["total"]
    assert {"offline_scorer", "online_spec", "dev_probe", "ci_tests"} <= set(data["rows"][0])
    assert "|" in eval_coverage.render(data)
