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


@pytest.mark.parametrize("title", ["운송대장", "검수기록", "입고목록"])
@pytest.mark.parametrize("description", [
    "차례를 설명하며 묶음번호 7을 다시 언급한다.",
    "비교 내용을 정리하고 갑 제9호증과 대조한다.",
    "관측 경로를 기록하며 REF-ZZ 및 14행을 함께 설명한다.",
    "순서를 설명하며 " + "8" * 128 + " 같은 긴 숫자도 인용한다.",
    "(설명 순서를 검토하고 묶음 7을 다시 언급한다.)",
    "[경로 정보를 정리하고 갑 제9호증을 인용한다.]",
    "{관측 부분을 비교하며 REF-ZZ를 뒤에 덧붙인다.}",
])
def test_later_narrative_numbers_never_become_identifier_suffixes(tmp_path, proposed, title, description):
    doc = document(tmp_path, [f"갑 제1호증: {title}, {description}",
                              f"갑 제1호증 {title}: 같은 자료를 설명한다."])
    rows = engine.exhibit_rows(doc)
    frozen = copy.deepcopy(rows)
    before = engine._numbering(doc, rows)
    after = proposed(doc, rows)
    assert len(audit.duplicate(before)) == 1
    assert not audit.duplicate(after)
    assert audit.contract([f for f in before if f not in audit.duplicate(before)]) == audit.contract(after)
    assert rows == frozen


@pytest.mark.parametrize("title", ["운송대장", "검수기록", "입고목록"])
@pytest.mark.parametrize("first,second", [("23", "24"), ("DOC-AA", "DOC-BB"),
                                         ("[R/31]", "[R/32]"), ("A", "B"),
                                         ("AB_17.", "AB_18."), ("(R-7", "(R-8")])
def test_different_immediate_identifiers_preserve_complete_original_A(tmp_path, proposed, title, first, second):
    doc = document(tmp_path, [f"갑 제1호증: {title}, {first} 뒤 설명을 붙인다.",
                              f"갑 제1호증 {title}: {second} 뒤 내용을 정리한다."])
    rows = engine.exhibit_rows(doc)
    before = engine._numbering(doc, rows)
    after = proposed(doc, rows)
    assert len(audit.duplicate(before)) == len(audit.duplicate(after)) == 1
    assert audit.contract(before) == audit.contract(after)


@pytest.mark.parametrize("tail", ["0" * 16000, "REF-AA", "제8호증", "[R/77]"])
def test_only_first_token_is_classified_even_with_long_later_identifier(tail):
    assert not audit.first_token_identifier("  설명 " + tail)
    assert audit.first_token_identifier("  REF-BB " + tail)


@pytest.mark.parametrize("title,date", [("운송대장", "2023. 8. 12."),
                                        ("검수기록", "2022. 7. 19."),
                                        ("입고목록", "2021. 6. 24.")])
def test_missing_vs_observed_date_remains_the_original_protected_residual(tmp_path, proposed, title, date):
    doc = document(tmp_path, [f"갑 제1호증: {title}, 설명 부분을 가리킨다.",
                              f"갑 제1호증 {title}: 순서를 기록하고 {date} 내용을 덧붙인다."])
    rows = engine.exhibit_rows(doc)
    assert [bool(row.get("date")) for row in rows] == [False, True]
    assert not audit.first_token_identifier(" 설명 부분을 가리킨다.")
    assert not audit.first_token_identifier(" 순서를 기록하고")
    before = engine._numbering(doc, rows)
    after = proposed(doc, rows)
    assert len(audit.duplicate(before)) == len(audit.duplicate(after)) == 1
    assert audit.contract(before) == audit.contract(after)
