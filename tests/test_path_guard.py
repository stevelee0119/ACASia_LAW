"""평가 도구 경로 묶기(scripts/path_guard.py, CodeQL py/path-injection #285). 값은 합성이다."""
import os
from pathlib import Path

import pytest

from scripts.evaluation_v2 import dataset_identity
from scripts.path_guard import ROOT, contained_path


def test_paths_inside_the_repository_or_temp_folder_are_returned_resolved(tmp_path):
    assert contained_path(ROOT / "scripts" / ".." / "scripts") == (ROOT / "scripts").resolve()
    assert contained_path(tmp_path / "out.json") == Path(os.path.realpath(tmp_path / "out.json"))


@pytest.mark.parametrize("outside", ["/etc/passwd", "/", "/usr/bin/env"])
def test_paths_outside_the_allowed_folders_are_refused(outside):
    with pytest.raises(ValueError):
        contained_path(outside)


def test_the_allowed_folder_itself_is_refused(tmp_path):
    with pytest.raises(ValueError):
        contained_path(tmp_path, tmp_path)  # 허용 폴더 안의 경로만 받는다


def test_prefix_lookalike_and_dotdot_escape_are_refused(tmp_path):
    inner = tmp_path / "data"
    inner.mkdir()
    (tmp_path / "data_evil").mkdir()
    with pytest.raises(ValueError):
        contained_path(tmp_path / "data_evil" / "x", inner)  # 이름 앞부분만 같은 형제 폴더
    with pytest.raises(ValueError):
        contained_path(inner / ".." / "data_evil", inner)


def test_symlink_out_of_the_dataset_is_refused(tmp_path):
    data = tmp_path / "set"
    data.mkdir()
    (data / "ground_truth.json").write_text('{"documents": {"D1": {"file": "doc.txt"}}}', encoding="utf-8")
    (data / "match_spec.json").write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    (data / "doc.txt").symlink_to(outside)
    with pytest.raises(ValueError):
        dataset_identity(data)
