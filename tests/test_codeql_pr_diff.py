"""Steve 대상 PR CodeQL 새 경고 게이트(scripts/codeql_pr_diff.py) 시험. SARIF는 지어낸 합성 값이다."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("codeql_pr_diff", ROOT / "scripts" / "codeql_pr_diff.py")
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)

RULES = [
    {"id": "py/polynomial-redos", "shortDescription": {"text": "Polynomial ReDoS"},
     "properties": {"security-severity": "7.5"}},
    {"id": "py/clear-text-logging", "shortDescription": {"text": "Clear-text logging"},
     "properties": {"security-severity": "4.0"}},
    {"id": "py/unused-import", "defaultConfiguration": {"level": "note"}},
    {"id": "js/example-error", "defaultConfiguration": {"level": "error"}},
]


def _res(rule, uri, line, msg, **extra):
    return {"ruleId": rule, "message": {"text": msg}, **extra,
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}, "region": {"startLine": line}}}]}


def _sarif(path: Path, results, rules_in="driver"):
    tool = {"driver": {"name": "CodeQL", "rules": RULES if rules_in == "driver" else []}}
    if rules_in == "extension":
        tool["extensions"] = [{"name": "codeql/python-queries", "rules": RULES}]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": "2.1.0", "runs": [{"tool": tool, "results": results}]}), encoding="utf-8")
    return path


def test_new_high_result_fails_and_line_shift_is_not_new(tmp_path):
    old = _res("py/polynomial-redos", "packages/a.py", 10, "This regex may run slow.")
    base = _sarif(tmp_path / "base" / "python.sarif", [old])
    head = _sarif(tmp_path / "head" / "python.sarif", [
        _res("py/polynomial-redos", "packages/a.py", 14, "This regex may run slow."),   # 위 코드가 바뀌어 줄만 밀림
        _res("py/polynomial-redos", "packages/b.py", 3, "This regex may run slow."),    # 새 파일의 새 결과
    ])
    rows_b, _ = cd.load([base])
    rows_h, _ = cd.load([head])
    new = cd.new_results(rows_b, rows_h)
    assert [(r["uri"], r["line"]) for r in new] == [("packages/b.py", 3)]
    assert cd.main(["--base", str(base), "--head", str(head)]) == 1


def test_medium_and_note_results_are_reported_but_pass(tmp_path, capsys):
    base = _sarif(tmp_path / "base" / "python.sarif", [])
    head = _sarif(tmp_path / "head" / "python.sarif", [
        _res("py/clear-text-logging", "apps/x.py", 5, "Sensitive data logged."),
        _res("py/unused-import", "apps/x.py", 1, "Import unused."),
    ], rules_in="extension")
    assert cd.main(["--base", str(tmp_path / "base"), "--head", str(tmp_path / "head")]) == 0
    out = capsys.readouterr().out
    assert "새 결과 2건" in out and "실패 기준 해당 0건" in out


def test_error_level_without_security_severity_fails(tmp_path):
    base = _sarif(tmp_path / "base" / "js.sarif", [])
    head = _sarif(tmp_path / "head" / "js.sarif", [_res("js/example-error", "apps/w.js", 2, "Bad.")])
    assert cd.main(["--base", str(base), "--head", str(head)]) == 1


def test_duplicate_keys_count_by_difference_and_suppressed_ignored(tmp_path):
    same = ("py/polynomial-redos", "packages/a.py")
    base = _sarif(tmp_path / "b.sarif", [_res(*same, 1, "m")])
    head = _sarif(tmp_path / "h.sarif", [
        _res(*same, 1, "m"), _res(*same, 9, "m"),                                     # 같은 키 1 → 2: 1건 새것
        _res("py/polynomial-redos", "packages/c.py", 4, "m", suppressions=[{"kind": "inSource"}]),
    ])
    new = cd.new_results(cd.load([base])[0], cd.load([head])[0])
    assert len(new) == 1 and new[0]["uri"] == "packages/a.py"


def test_missing_sarif_is_not_a_pass(tmp_path):
    head = _sarif(tmp_path / "head" / "python.sarif", [])
    (tmp_path / "base").mkdir()
    assert cd.main(["--base", str(tmp_path / "base"), "--head", str(head)]) == 2


def test_unmatched_glob_path_is_missing_not_crash(tmp_path):
    head = _sarif(tmp_path / "head" / "python.sarif", [])
    assert cd.main(["--base", str(tmp_path / "sarif-base-*"), "--head", str(head)]) == 2
