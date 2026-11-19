"""TK-219: 기준 커밋 worktree에서도 같은 저장소의 시험 입력을 열 수 있어야 한다.

`regression_gate`는 기준 커밋을 임시 worktree에 펴고 그 안의 도구로 현재 저장소의 명세·입력을 읽는다.
worktree 안에서는 `path_guard.ROOT`가 임시 폴더라서, 저장소가 홈 밖에 있으면 현재 저장소의 입력이
어느 허용 폴더에도 들지 않아 전 항목이 '측정 못 함'이 됐다(검출 여부가 $HOME 위치에 달려 CI에서는
통과하고 로컬에서는 실패한다).
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_guard(path: Path, home: Path):
    """주어진 작업 폴더의 path_guard를 그 폴더 기준으로 새로 읽는다."""
    spec = importlib.util.spec_from_file_location(f"pg_{abs(hash(str(path)))}", path / "scripts" / "path_guard.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        spec.loader.exec_module(module)
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home
    return module


def test_main_checkout_is_this_repository():
    import scripts.path_guard as guard

    assert guard.MAIN_CHECKOUT is not None
    assert os.path.realpath(guard.MAIN_CHECKOUT) == os.path.realpath(ROOT)


def test_worktree_accepts_input_from_the_main_checkout(tmp_path):
    """worktree 안에서 돌아도 주 작업 폴더의 입력은 허용된다 — 홈이 저장소를 품지 않아도 그렇다."""
    tree = tmp_path / "tree"
    try:
        subprocess.run(["git", "worktree", "add", "--detach", "-q", str(tree), "HEAD"],
                       cwd=ROOT, check=True, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - git 없는 환경
        pytest.skip(f"worktree를 만들 수 없다: {exc}")
    try:
        # worktree에는 HEAD의 파일이 펴진다. 지금 작업 중인 path_guard를 진짜 worktree 안에서 재려면
        # 작업 폴더의 사본을 덮어쓴다(worktree 자체는 git이 만든 것 그대로다).
        shutil.copy2(ROOT / "scripts" / "path_guard.py", tree / "scripts" / "path_guard.py")
        far_home = tmp_path / "home"          # 저장소를 품지 않는 홈
        far_home.mkdir()
        guard = _load_guard(tree, far_home)
        assert Path(os.path.realpath(guard.ROOT)) == Path(os.path.realpath(tree))
        target = ROOT / "tests" / "fixtures" / "probes"
        probe = next(target.glob("*.json"), None)
        if probe is None:  # pragma: no cover - 명세가 없는 트리
            pytest.skip("탐침 명세가 없다")
        assert guard.contained_path(probe, *guard.INPUT_ROOTS) == Path(os.path.realpath(probe))
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=ROOT, capture_output=True)
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)


def test_paths_outside_every_allowed_root_are_still_refused():
    import scripts.path_guard as guard

    with pytest.raises(ValueError):
        guard.contained_path("/etc/passwd", *guard.INPUT_ROOTS)


def test_main_checkout_is_none_without_git(tmp_path, monkeypatch):
    """git을 쓸 수 없으면 허용 폴더를 넓히지 않고 None으로 둔다."""
    import scripts.path_guard as guard

    def boom(*args, **kwargs):
        raise OSError("git 없음")

    monkeypatch.setattr(subprocess, "run", boom)
    assert guard._main_checkout() is None
