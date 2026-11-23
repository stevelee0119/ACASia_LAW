from __future__ import annotations

from pathlib import Path

from scripts.eval_cassette_track import has_cassettes, run_cassette_track
from scripts.eval_perturbation import perturb_text


def test_cassette_track_returns_not_measured_when_empty(tmp_path: Path):
    empty_dir = tmp_path / "cassettes"
    empty_dir.mkdir()
    assert not has_cassettes(empty_dir)
    res = run_cassette_track(tmp_path, empty_dir)
    assert res["status"] == "NOT_MEASURED"
    assert res["reason"] == "NO_CASSETTE_FILES"
    assert res["overall"] is None


def test_perturb_text_register_date_and_party_role():
    src = "원고는 2022. 3. 10. 피고에게 통지하였습니다. 계약이 성립합니다."
    out = perturb_text(src, ("register", "date_format", "party_role"))
    assert "신청인은" in out
    assert "피신청인에게" in out
    assert "2022년 3월 10일" in out
    assert "통지하였음." in out
    assert "성립함." in out


def test_perturb_text_noop_when_no_modes():
    src = "원고는 2022. 3. 10. 계약을 체결하였습니다."
    assert perturb_text(src, ()) == src
