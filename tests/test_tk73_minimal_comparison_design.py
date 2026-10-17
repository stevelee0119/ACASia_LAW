"""Synthetic public counterexamples for an unapproved design, no product patch."""
import copy
import importlib.util
from pathlib import Path

import pytest

from packages.claim_engine import evidence_consistency as engine
from packages.document_engine.registry import parse_document

SPEC = importlib.util.spec_from_file_location(
    "tk73_public_minimal_audit", Path(__file__).resolve().parents[1] /
    "docs/handoff/requests/TK73_minimal_comparison_audit.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


@pytest.fixture(scope="module")
def proposed():
    return audit.minimal_numbering(guarded=True)


def document(tmp_path, lines):
    path = tmp_path / "fabricated.txt"
    path.write_text("\n\n".join(lines), encoding="utf-8")
    return parse_document(str(path), document_id="synthetic", filename=path.name,
                          mime_type="text/plain", sha256="0" * 64)


@pytest.mark.parametrize("title,other", [("운송대장", "정비일지"), ("검수기록", "배치도면"), ("입고목록", "관측보고")])
@pytest.mark.parametrize("mode", ["plain", "date_suffix", "identifier_suffix", "third_occurrence", "both_colons"])
def test_synthetic_true_duplicates_keep_original_A(tmp_path, proposed, title, other, mode):
    first, second = f"{title}, 위치 4쪽", f"{other}: 설명."
    if mode == "date_suffix":
        first, second = f"{title}, 2023. 1. 3.", f"{title}: 2023. 1. 4."
    if mode == "identifier_suffix":
        first, second = f"{title}, REF-AA", f"{title}: REF-BB"
    if mode == "both_colons":
        first, second = f"{title}: 동쪽 기재", f"{title}: 서쪽 기재"
    lines = [f"갑 제1호증: {first}", f"갑 제1호증 {second}"]
    if mode == "third_occurrence":
        lines = [f"갑 제1호증: {title}, 위치 4쪽", f"갑 제1호증 {title}: 동쪽 기재", f"갑 제1호증 {title}: 서쪽 기재"]
    doc = document(tmp_path, lines)
    rows = engine.exhibit_rows(doc)
    frozen = copy.deepcopy(rows)
    before = audit.duplicate(engine._numbering(doc, rows))
    after = audit.duplicate(proposed(doc, rows))
    assert len(before) == len(after) == 1
    assert str(after[0].evidence_grade) == "A"
    assert audit.contract(before) == audit.contract(after)
    assert rows == frozen


@pytest.mark.parametrize("title", ["운송대장", "검수기록", "입고목록"])
@pytest.mark.parametrize("location", ["위치 4쪽", "위치 8행", "위치 12페이지"])
def test_synthetic_repeated_mentions_lose_only_false_duplicate(tmp_path, proposed, title, location):
    doc = document(tmp_path, [f"갑 제1호증: {title}, {location}", f"갑 제1호증 {title}: 설명."])
    rows = engine.exhibit_rows(doc)
    original = audit.contract(engine.check_exhibits(doc))
    assert len(audit.duplicate(engine._numbering(doc, rows))) == 1
    assert not audit.duplicate(proposed(doc, rows))
    # Compiling/calling a separate candidate never installs it in the engine.
    assert audit.contract(engine.check_exhibits(doc)) == original


@pytest.mark.parametrize("title", ["운송대장", "검수기록", "입고목록"])
def test_native_title_cells_are_not_trimmed(tmp_path, proposed, title):
    doc = document(tmp_path, ["합성 자료"])
    doc.structure["tables"] = [{"table_ref": "synthetic_table", "page": 1, "cells": [
        ["호증", "서증명", "작성일"],
        ["갑 제1호증", f"{title}: 동쪽 기재", "2023. 1. 3."],
        ["갑 제1호증", f"{title}: 서쪽 기재", "2023. 1. 3."]]}]
    rows = engine.exhibit_rows(doc)
    assert len(rows) == 2 and not any(row["from_lines"] for row in rows)
    assert len(audit.duplicate(audit.minimal_numbering()(doc, rows))) == 0
    assert len(audit.duplicate(proposed(doc, rows))) == 1
