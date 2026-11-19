"""TK-215 — 시험 삭제·표시 승인이 적용 범위에 한정되는지.

문제: `approved_marks()`가 (경로::시험, 표시) 쌍만 읽어, 한 번 삭제 승인을 받은 이름이 나중에
다시 만들어진 뒤 또 지워져도 새 검토 없이 통과했다. 범위를 **시험 본문의 지문**으로 둔다.

축: (범위 있음/없음) × (지문 일치/불일치/없음) × (승인 날짜 경과 조치 이전/이후) × (항목 0·1·여럿)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_test_edits import (  # noqa: E402
    SCOPE_REQUIRED_FROM,
    body_digest,
    match_approval,
    signatures,
)

DIGEST = "0123456789abcdef"
OTHER = "fedcba9876543210"
OLD_DATE = "2026-10-04"
NEW_DATE = "2026-11-19"


def _entry(*, scope=None, approved=OLD_DATE, ticket="TK-x"):
    e = {"test": "tests/t.py::test_a", "mark": "delete", "ticket": ticket, "approved": approved}
    if scope is not None:
        e["scope"] = scope
    return e


# --- 축 1: 범위가 있으면 지문이 같을 때만 승인 -------------------------------

def test_scope_match_is_approved():
    entry, why = match_approval([_entry(scope={"body": DIGEST})], DIGEST)
    assert entry is not None and why == "범위 일치"


def test_scope_mismatch_is_not_approved():
    entry, why = match_approval([_entry(scope={"body": OTHER})], DIGEST)
    assert entry is None
    assert "적용 범위" in why


def test_scope_present_but_digest_unknown_is_not_approved():
    """본문을 읽을 수 없으면(지문 빈 문자열) 범위를 대조할 수 없으므로 승인하지 않는다."""
    entry, _ = match_approval([_entry(scope={"body": DIGEST})], "")
    assert entry is None


@pytest.mark.parametrize("scope", [{}, {"body": ""}, {"base": "deadbeef"}, "본문", 7, None])
def test_malformed_or_absent_scope_falls_back_to_date_rule(scope):
    """범위가 없거나 꼴이 틀리면 날짜 규칙으로 간다(옛 항목은 통과, 새 항목은 불통과)."""
    old, _ = match_approval([_entry(scope=scope, approved=OLD_DATE)], DIGEST)
    new, _ = match_approval([_entry(scope=scope, approved=NEW_DATE)], DIGEST)
    assert old is not None
    assert new is None


# --- 축 2: 경과 조치 (날짜) --------------------------------------------------

def test_legacy_entry_without_scope_passes_with_warning_reason():
    entry, why = match_approval([_entry(approved=OLD_DATE)], DIGEST)
    assert entry is not None
    assert why.startswith("범위 없는")


def test_entry_from_cutoff_date_without_scope_is_rejected():
    entry, _ = match_approval([_entry(approved=SCOPE_REQUIRED_FROM)], DIGEST)
    assert entry is None


def test_entry_after_cutoff_without_scope_is_rejected():
    entry, _ = match_approval([_entry(approved="2026-12-01")], DIGEST)
    assert entry is None


def test_entry_without_date_and_without_scope_is_treated_as_legacy():
    """날짜가 없는 옛 항목은 경과 조치로 통과시킨다(기존 CI를 깨지 않는다)."""
    entry, why = match_approval([_entry(approved="")], DIGEST)
    assert entry is not None and why.startswith("범위 없는")


# --- 축 3: 항목이 여럿일 때 --------------------------------------------------

def test_matching_scope_wins_over_other_entries():
    entries = [_entry(scope={"body": OTHER}), _entry(scope={"body": DIGEST})]
    entry, why = match_approval(entries, DIGEST)
    assert entry is not None and why == "범위 일치"


def test_scoped_mismatch_plus_legacy_falls_back_to_legacy():
    entries = [_entry(scope={"body": OTHER}), _entry(approved=OLD_DATE)]
    entry, why = match_approval(entries, DIGEST)
    assert entry is not None and why.startswith("범위 없는")


def test_all_entries_out_of_scope_is_rejected():
    entries = [_entry(scope={"body": OTHER}), _entry(scope={"body": "a" * 16}, approved=NEW_DATE)]
    entry, _ = match_approval(entries, DIGEST)
    assert entry is None


def test_no_entries_reports_absence():
    entry, why = match_approval([], DIGEST)
    assert entry is None and why == "승인 항목 없음"


# --- 축 4: 지문 자체 --------------------------------------------------------

SRC_A = "def test_a():\n    assert 1\n"
SRC_A_RENAMED = "def test_b():\n    assert 1\n"
SRC_A_CHANGED = "def test_a():\n    assert 2\n"


def test_digest_ignores_the_name_but_not_the_body():
    a = body_digest(signatures(SRC_A)["test_a"])
    renamed = body_digest(signatures(SRC_A_RENAMED)["test_b"])
    changed = body_digest(signatures(SRC_A_CHANGED)["test_a"])
    assert a == renamed      # 이름만 바뀐 시험은 같은 지문
    assert a != changed      # 본문이 바뀌면 다른 지문


def test_digest_is_stable_and_short():
    d = body_digest(signatures(SRC_A)["test_a"])
    assert d == body_digest(signatures(SRC_A)["test_a"])
    assert len(d) == 16 and all(c in "0123456789abcdef" for c in d)


def test_digest_of_missing_signature_is_empty():
    assert body_digest(None) == ""
    assert body_digest("") == ""


# --- 축 5: 저장소 끝에서 끝까지 (같은 이름 재사용을 실제로 막는지) -----------

GATE = Path(__file__).resolve().parents[1] / "scripts" / "check_test_edits.py"


def _run(cwd, *args):
    return subprocess.run([sys.executable, str(GATE), *args], cwd=cwd,
                          capture_output=True, text=True)


def _repo(tmp_path, approvals):
    """시험 하나를 만들고 지웠다가 다른 본문으로 다시 만들고 또 지우는 저장소."""
    r = tmp_path / "repo"
    (r / "tests").mkdir(parents=True)
    (r / "docs" / "scorecards").mkdir(parents=True)

    def git(*a):
        subprocess.run(["git", *a], cwd=r, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "e@x")
    git("config", "user.name", "n")

    (r / "docs/scorecards/approved_test_marks.json").write_text(
        json.dumps({"note": "시험용", "approved": approvals}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (r / "tests/t.py").write_text(SRC_A, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "c0\n\nAgent: evaluator")
    base_first = subprocess.run(["git", "rev-parse", "HEAD"], cwd=r, capture_output=True,
                                text=True, check=True).stdout.strip()

    # 같은 이름을 다른 본문으로 되살린 상태를 만든다
    (r / "tests/t.py").write_text(SRC_A_CHANGED, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "같은 이름을 다른 본문으로 되살림\n\nAgent: implementer")
    base_second = subprocess.run(["git", "rev-parse", "HEAD"], cwd=r, capture_output=True,
                                 text=True, check=True).stdout.strip()

    # 되살린 것을 또 지운다
    (r / "tests/t.py").write_text("def test_other():\n    assert 1\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "또 지움\n\nAgent: implementer")
    return r, base_first, base_second


def test_approval_scoped_to_first_body_does_not_cover_the_second_deletion(tmp_path):
    first_digest = body_digest(signatures(SRC_A)["test_a"])
    r, _, base_second = _repo(tmp_path, [{
        "test": "tests/t.py::test_a", "mark": "delete", "ticket": "TK-208",
        "approved": "2026-11-19", "reason": "시험용",
        "scope": {"body": first_digest},
    }])
    res = _run(r, "--base", base_second)
    assert res.returncode == 1, res.stdout
    assert "삭제된 시험" in res.stdout
    assert "적용 범위가 맞지 않는다" in res.stdout


def test_unscoped_new_approval_does_not_cover_any_deletion(tmp_path):
    r, _, base_second = _repo(tmp_path, [{
        "test": "tests/t.py::test_a", "mark": "delete", "ticket": "TK-208",
        "approved": "2026-11-19", "reason": "범위를 적지 않은 새 승인",
    }])
    res = _run(r, "--base", base_second)
    assert res.returncode == 1, res.stdout


def test_approval_scoped_to_second_body_covers_the_second_deletion(tmp_path):
    second_digest = body_digest(signatures(SRC_A_CHANGED)["test_a"])
    r, _, base_second = _repo(tmp_path, [{
        "test": "tests/t.py::test_a", "mark": "delete", "ticket": "TK-208",
        "approved": "2026-11-19", "reason": "시험용",
        "scope": {"body": second_digest},
    }])
    res = _run(r, "--base", base_second)
    assert res.returncode == 0, res.stdout
    assert "범위 일치" in res.stdout


def test_legacy_unscoped_approval_passes_but_is_warned(tmp_path):
    r, _, base_second = _repo(tmp_path, [{
        "test": "tests/t.py::test_a", "mark": "delete", "ticket": "TK-171",
        "approved": "2026-10-04", "reason": "옛 승인",
    }])
    res = _run(r, "--base", base_second)
    assert res.returncode == 0, res.stdout
    assert "적용 범위 없는 옛 승인" in res.stdout


def test_digest_subcommand_prints_the_body_digest(tmp_path):
    r, base_first, _ = _repo(tmp_path, [])
    res = _run(r, "--digest", "tests/t.py", "test_a", "--ref", base_first)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == body_digest(signatures(SRC_A)["test_a"])


def test_digest_subcommand_reports_missing_test(tmp_path):
    r, base_first, _ = _repo(tmp_path, [])
    res = _run(r, "--digest", "tests/t.py", "test_nope", "--ref", base_first)
    assert res.returncode == 2
    assert "없다" in res.stderr
