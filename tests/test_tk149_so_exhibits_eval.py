"""TK-149 공용 호증 문법 — 신청 사건 부호 '소갑·소을' (평가 측 공개 합성 문장)."""
from __future__ import annotations

import pytest

from packages.claim_engine.evidence_consistency import check_document, exhibit_rows
from packages.claim_engine.exhibits import parse_exhibits
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(lines):
    blocks = [Block(block_id=f"b{i}", text=t, page=1, visible=True, source_layer="visible_text") for i, t in enumerate(lines)]
    return NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                              pages=[Page(page_number=1, blocks=blocks, width=595.0, height=842.0)])


@pytest.mark.parametrize("text,want", [
    ("이는 소을 제5호증의 기재로 소명됩니다", [("을", 5)]),
    ("(소을 제2, 3호증)", [("을", 2), ("을", 3)]),
    ("소을제7호증의 1", [("을", 7)]),
    ("소을 제1 내지 3호증", [("을", 1), ("을", 2), ("을", 3)]),
    ("소갑 제4호증 및 소을 제6호증", [("갑", 4), ("을", 6)]),
])
def test_so_eul_citation_parsed(text, want):
    got = [(r["party"], r["number"]) for r in parse_exhibits(text)]
    assert got == want


def test_so_label_keeps_prefix_and_party_key():
    ref = parse_exhibits("소을 제5호증의 2")[0]
    assert ref["party"] == "을" and ref["label"].startswith("소을") and ref["span"][0] == 0


@pytest.mark.parametrize("text", ["사실을 제3호증으로 증명합니다", "대소을 제2호증", "같은 법 제2조 제3호"])
def test_control_object_particle_not_party(text):
    assert not [r for r in parse_exhibits(text) if r["party"] == "을"]


@pytest.mark.parametrize("party", ["소갑", "소을"])
def test_so_list_lines_become_rows(party):
    rows = exhibit_rows(_doc(["소명방법", f"1. {party} 제1호증 확인서", f"2. {party} 제2호증 영수증"]))
    assert [(r["party"], r["number"]) for r in rows] == [(party[-1], 1), (party[-1], 2)]


def test_so_missing_from_list_detected_with_so_label():
    lines = ["답변서", "신청인 주식회사 해솔", "피신청인 문○○", "1. 피신청인은 계약을 해지하였습니다(소을 제4호증 해지통지서).",
             "소명방법", "1. 소을 제1호증 해지통지서", "2024. 10. 1.", "피신청인 대리인 변호사 ○○○"]
    titles = [f.title for f in check_document(_doc(lines)) if (f.confidence_features or {}).get("rule_id") == "EVI.EVIDENCE_LIST_MISMATCH"]
    assert titles and "소을 제4호증" in titles[0], titles


def test_control_consistent_so_document_no_list_finding():
    lines = ["가처분 신청서", "신청인 주식회사 해솔", "피신청인 문○○", "1. 신청인은 계약을 체결하였습니다(소갑 제1호증 계약서).",
             "소명방법", "1. 소갑 제1호증 계약서", "2024. 10. 1.", "신청인 대리인 변호사 ○○○"]
    assert not [f for f in check_document(_doc(lines)) if f.type.value == "EVIDENCE_LIST_MISMATCH"]
