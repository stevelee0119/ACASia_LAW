"""평가 측 도구(티켓 지표·고정 벤치마크) 시험. 입력은 지어낸 합성 값이다."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ticket_metrics_counts_regression_and_open(tmp_path, monkeypatch):
    tm = _load("ticket_metrics")
    tickets = [
        {"id": "TK-1", "found_on": "2026-10-05", "kind_auto": "regression", "title": "a", "file": "x"},
        {"id": "TK-2", "found_on": "2026-10-06", "kind_auto": "existing", "title": "b", "file": "y"},
        {"id": "TK-3", "found_on": "2026-10-12", "kind_auto": "existing", "title": "c", "file": "z"},
    ]
    reg = {"TK-1": {"status": "deployed", "deployed_on": "2026-10-12"},
           "TK-2": {"status": "open", "kind": "regression"}}
    m = tm.build(tickets, reg)
    assert m["regression_total"] == 2            # 등록부 kind가 자동 분류를 덮어쓴다
    assert [r["id"] for r in m["open"]] == ["TK-2", "TK-3"]
    assert m["unregistered"] == ["TK-3"]
    assert m["weekly"]["2026-W41"] == {"found": 2, "regression": 2, "recurrence": 0}
    assert m["weekly"]["2026-W42"]["deployed"] == 1


def test_ticket_registry_covers_every_ticket():
    tm = _load("ticket_metrics")
    assert tm.main(["--check"]) == 0


def test_fixed_benchmark_fingerprint_and_combine(tmp_path):
    fb = _load("fixed_benchmark")
    for name in ("set01", "set02"):
        d = tmp_path / name
        d.mkdir()
        (d / "ground_truth.json").write_text("{}", encoding="utf-8")
        (d / "match_spec.json").write_text("{}", encoding="utf-8")
        (d / "SD-01.pdf").write_bytes(name.encode())
        (d / "notes.txt").write_text("무시", encoding="utf-8")
    first = fb.fingerprint(tmp_path)
    (tmp_path / "set01" / "notes.txt").write_text("바꿔도 지문 같음", encoding="utf-8")
    assert fb.fingerprint(tmp_path) == first
    (tmp_path / "set02" / "SD-01.pdf").write_bytes(b"changed")
    assert fb.fingerprint(tmp_path) != first
    row = lambda items, rec, ov, fp, inj: {"documents": 8, "defect_items": items, "weighted_recall": rec, "overall": ov,
                                           "false_positives": fp, "fp_trap": 0, "control_fp": fp, "a_grade_fp": fp,
                                           "injection_defended": inj}
    c = fb.combine([row(53, 0.302, 15.2, 3, True), row(46, 0.19, 19.0, 0, True)])
    assert c["weighted_recall"] == 0.25 and c["overall"] == 17.0 and c["false_positives"] == 3
    assert c["injection_defended"] is True
    assert fb.combine([row(10, 0.5, 50, 0, True), row(10, 0.5, 50, 0, False)])["injection_defended"] is False


def test_fixed_benchmark_fingerprint_order_is_codepoint_not_os(tmp_path):
    """지문은 OS와 무관하게 이름의 코드포인트 순서로 만든다(대문자 'SD-'가 소문자 json보다 앞). 2026-10-17 Windows·Linux 지문 불일치 재발 방지."""
    import hashlib
    fb = _load("fixed_benchmark")
    d = tmp_path / "set01"
    d.mkdir()
    files = {"ground_truth.json": b"{}", "match_spec.json": b"{\"tokens\": {}}", "SD-01.pdf": b"a", "SD-02.pdf": b"b"}
    for name, data in files.items():
        (d / name).write_bytes(data)
    digest = hashlib.sha256()
    digest.update(b"set01")
    for name in ("SD-01.pdf", "SD-02.pdf", "ground_truth.json", "match_spec.json"):
        digest.update(name.encode("utf-8"))
        digest.update(hashlib.sha256(files[name]).digest())
    assert fb.fingerprint(tmp_path) == digest.hexdigest()[:16]


def test_fixed_benchmark_refuses_folder_inside_repo():
    fb = _load("fixed_benchmark")
    assert fb.main(["--bench-dir", str(ROOT / "tests" / "fixtures" / "retired_sealed" / "sealed_20261010")]) == 2


def _retired(overall, fp, a, inj=True):
    return {"overall": overall, "weighted_recall": overall / 100, "false_positives": fp, "a_grade_fp": a,
            "injection_defended": inj}


def test_retired_compare_flags_only_regressions():
    rc = _load("retired_compare")
    base = {"s1": _retired(29.6, 0, 0), "s2": _retired(15.2, 3, 3), "s3": _retired(19.0, 0, 0)}
    same = {"s1": _retired(29.6, 0, 0), "s2": _retired(20.2, 2, 2), "s3": _retired(21.2, 0, 0)}
    assert rc.compare(base, same) == []
    worse = {"s1": _retired(27.8, 0, 0), "s2": _retired(15.2, 4, 4), "s3": _retired(19.0, 0, 0, inj=False)}
    problems = rc.compare(base, worse)
    assert any("s1: 종합점수 29.6 → 27.8" == p for p in problems)
    assert any(p.startswith("s2: 오탐 3 → 4") for p in problems)
    assert any(p.startswith("s2: A등급 오탐 3 → 4") for p in problems)
    assert any(p == "s3: 인젝션 방어 실패" for p in problems)


def test_retired_compare_failed_head_and_new_set():
    rc = _load("retired_compare")
    base = {"s1": _retired(29.6, 0, 0), "s2": None}
    head = {"s1": None, "s2": _retired(10.0, 0, 0), "s9": _retired(1.0, 5, 5)}
    assert rc.compare(base, head) == ["s1: 후보 채점 실패"]



def test_train_phrase_overlap_expands_regex_alternatives_into_word_windows():
    tp = _load("check_train_phrase_overlap")
    line = 'X_RE = re.compile(r"(?:완결\\s*(?:제출)?목록)\\s*[:：].*?외에는\\s*자료를\\s*제출하지\\s*않")  # 주석 낱말 무시'
    found = {p.replace(" ", "") for p in tp.phrases(line)}
    assert "외에는자료를제출하지" in found
    assert "주석낱말무시" not in found


def test_train_phrase_overlap_flags_only_long_multiword_hits(tmp_path, monkeypatch):
    tp = _load("check_train_phrase_overlap")
    (tmp_path / "a.txt").write_text("본문의 입증자료는 갑 제1호증 계약서이다. 서명 누락", encoding="utf-8")
    monkeypatch.setattr(tp, "added_lines", lambda base, head: [
        ("packages/x.py", 'A = re.compile(r"본문의\\s*입증자료는")'),
        ("packages/x.py", 'B = re.compile(r"서명\\s*누락")'),
    ])
    assert tp.main(["--base", "B", "--corpus-text", str(tmp_path)]) == 1
    monkeypatch.setattr(tp, "added_lines", lambda base, head: [("packages/x.py", 'B = re.compile(r"서명\\s*누락")')])
    assert tp.main(["--base", "B", "--corpus-text", str(tmp_path)]) == 0
