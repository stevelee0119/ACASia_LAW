"""TK-175: 평가 도구의 CodeQL 경고(경로 주입 10건·부분 SSRF 1건) 해소 — 입력 꼴 검사와 허용 폴더 묶기(평가 에이전트).

값은 모두 합성이다. 네트워크를 쓰지 않는다.
"""
from __future__ import annotations

import pytest

import scripts.ci_failed_tests as ci_failed
import scripts.export_security_alerts as export


@pytest.mark.parametrize("repo", ["evil.example/x?y", "a/b/c", "a b/c", "../x", ""])
def test_alert_export_refuses_a_repo_that_is_not_owner_slash_name(repo):
    with pytest.raises(SystemExit):
        export.fetch_alerts(repo, "token")


@pytest.mark.parametrize("ref", ["x;y", "refs/pull/1/merge?x=1", "https://evil.example/", "refs/other/1"])
def test_alert_export_refuses_a_ref_outside_heads_tags_pull(ref):
    with pytest.raises(SystemExit):
        export.fetch_alerts("owner/repo", "token", ref=ref)


def test_alert_export_refuses_an_unknown_state():
    with pytest.raises(SystemExit):
        export.fetch_alerts("owner/repo", "token", state="open&x=1")


def test_alert_export_builds_the_api_url_for_valid_inputs(monkeypatch):
    seen = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"[]"

    monkeypatch.setattr(export.urllib.request, "urlopen", lambda request, timeout: seen.append(request.full_url) or Response())
    assert export.fetch_alerts("owner/repo", "token", ref="refs/pull/7/merge") == []
    assert seen == ["https://api.github.com/repos/owner/repo/code-scanning/alerts?state=open&per_page=100&page=1"
                    "&ref=refs%2Fpull%2F7%2Fmerge"]


def test_failed_test_list_skips_files_outside_the_allowed_folders(tmp_path):
    inside = tmp_path / "pytest.txt"
    inside.write_text("FAILED tests/x.py::t - boom\n", encoding="utf-8")
    assert ci_failed.failures([str(inside), "/etc/hostname"]) == [("pytest.txt", "FAILED tests/x.py::t")]


def test_step_summary_outside_the_runner_temp_is_skipped(tmp_path, monkeypatch, capsys):
    report = tmp_path / "pytest.txt"
    report.write_text("FAILED tests/x.py::t\n", encoding="utf-8")
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path / "runner"))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "elsewhere.md"))
    assert ci_failed.main([str(report)]) == 0
    assert not (tmp_path / "elsewhere.md").exists() and "실패 시험 목록: 1건" in capsys.readouterr().out
