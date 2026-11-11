"""TK-140: HWPX 이름공간 확인·문서 누적 상한·중첩 표 번호, 구형 HWP 셀 문단 대응의 내용 확인. 합성 자료만 쓴다."""
import time
import zipfile

import pytest

import test_tk132_hwpx_tables as hx
import test_tk133_hwp_tables as hw
from packages.document_engine.registry import parse_document


def raw_section(tmp_path, body, name="raw.hwpx"):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        z.writestr("Contents/section0.xml", f'<?xml version="1.0" encoding="UTF-8"?>{body}')
    return parse_document(str(path), document_id="d", filename=name, mime_type="", sha256="x")


# --- A. HWPX ----------------------------------------------------------------------------------------------------
def test_foreign_namespace_elements_are_not_read_as_body_or_table(tmp_path):
    foreign = ('<x:p xmlns:x="urn:example:other"><x:t>외부 조각 글자</x:t></x:p>'
               '<x:tbl xmlns:x="urn:example:other" rowCnt="1" colCnt="1"><x:tr><x:tc><x:cellAddr colAddr="0" rowAddr="0"/>'
               '</x:tc></x:tr></x:tbl>')
    doc = hx.hwpx(tmp_path, (0, hx.para("본문 문단") + foreign))
    assert "본문 문단" in hx.text_of(doc) and "외부 조각 글자" not in hx.text_of(doc)
    assert not doc.structure.get("tables") and not doc.structure.get("partial_tables")


def test_other_hwpml_year_namespace_and_no_namespace_are_still_read(tmp_path):
    newer = ('<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2016/section" '
             'xmlns:hp="http://www.hancom.co.kr/hwpml/2016/paragraph"><hp:p><hp:run><hp:t>신판 이름공간</hp:t>'
             '</hp:run></hp:p></hs:sec>')
    assert "신판 이름공간" in hx.text_of(raw_section(tmp_path, newer))
    plain = "<sec><p><run><t>이름공간 없음</t></run></p></sec>"
    assert "이름공간 없음" in hx.text_of(raw_section(tmp_path, plain, name="plain.hwpx"))


def test_document_node_budget_stops_reading_and_says_so(tmp_path, monkeypatch):
    import packages.document_engine.hwp_parser as hp
    monkeypatch.setattr(hp, "HWPX_MAX_DOC_NODES", 12)
    doc = hx.hwpx(tmp_path, (0, hx.para("첫 섹션")), (1, hx.para("둘째 섹션") * 5))
    assert "첫 섹션" in hx.text_of(doc) and "둘째 섹션" not in hx.text_of(doc)
    assert doc.structure["body_truncated"] is True and any("노드 누적 상한" in w for w in doc.parse_warnings)


def test_document_char_budget_stops_reading_and_skips_tables(tmp_path, monkeypatch):
    import packages.document_engine.hwp_parser as hp
    monkeypatch.setattr(hp, "HWPX_MAX_DOC_CHARS", 10)
    doc = hx.hwpx(tmp_path, (0, hx.para("열 글자 이내") + hx.para("상한을 넘는 문단") + hx.table(1, 1, [hx.cell(0, 0, "칸")])))
    assert "열 글자 이내" in hx.text_of(doc) and "상한을 넘는 문단" not in hx.text_of(doc)
    assert not doc.structure.get("tables") and any("글자 누적 상한" in w for w in doc.parse_warnings)


def test_many_nested_tables_get_parent_refs_without_rescanning(tmp_path):
    inner = hx.table(1, 1, [hx.cell(0, 0, "안쪽")])
    outer = hx.table(1, 1, [hx.cell(0, 0, "바깥", inner=inner)])
    started = time.perf_counter()
    doc = hx.hwpx(tmp_path, (0, outer * 400))
    elapsed = time.perf_counter() - started
    nested = [t for t in doc.structure["tables"] if t["nested"]]
    assert len(nested) == 400
    assert all(t["parent_table_ref"] == f"hwpx_s0t{t['table_index'] - 1}" for t in nested)
    assert elapsed < 10.0, elapsed


def test_default_budgets_do_not_change_ordinary_documents(tmp_path):
    doc = hx.hwpx(tmp_path, (0, hx.para("가. 청구") + hx.table(2, 2, [hx.cell(0, 0, "항목"), hx.cell(0, 1, "금액")],
                                                        [hx.cell(1, 0, "치료비"), hx.cell(1, 1, "1,200,000원")])))
    assert not doc.structure.get("body_truncated") and len(doc.structure["tables"]) == 1


# --- B. 구형 HWP --------------------------------------------------------------------------------------------------
def test_same_count_but_different_paragraph_text_drops_tables(monkeypatch, tmp_path):
    import packages.document_engine.hwp_parser as hp
    original = hp._extract_hwp_text

    def shifted(raw, notes=None):
        texts = original(raw, notes)
        return texts[1:] + texts[:1]                       # 개수는 같고 순서만 어긋남
    monkeypatch.setattr(hp, "_extract_hwp_text", shifted)
    doc = hw.parse(monkeypatch, tmp_path, hw.sum_table("4,200,000원"))
    assert not doc.structure.get("tables")
    assert not any(b.attributes.get("table_ref") for p in doc.pages for b in p.blocks)
    assert any("순서가 맞지 않아" in w for w in doc.parse_warnings)


def test_aligned_paragraphs_still_link_cells(monkeypatch, tmp_path):
    doc = hw.parse(monkeypatch, tmp_path, hw.sum_table("4,200,000원"))
    [table] = doc.structure["tables"]
    assert len(table["line_block_ids"]) == 8


# --- B-2. 구형 HWP 중첩 표(사용자 승인 필요: 기존 test_nested_table_makes_outer_partial 단언 변경) ----------------------
def nested_doc(monkeypatch, tmp_path, inner_rows=1, inner_cols=2, inner_cells=None):
    inner_cells = inner_cells or [hw.cell(0, 0, "내부", level=5), hw.cell(1, 0, "7일", level=5)]
    inner = hw.tbl(inner_rows, inner_cols, level=4) + b"".join(inner_cells)
    body = (hw.tbl(1, 2) + hw.cell(0, 0, "바깥")
            + hw.rec(hw.LIST_HEADER, hw.struct.pack("<hIHHHHH", 1, 0, 0, 1, 0, 1, 1), 2) + inner + hw.text("표 뒤"))
    return hw.parse(monkeypatch, tmp_path, body)


def test_nested_table_gives_inner_table_and_outer_keeps_only_its_own_text(monkeypatch, tmp_path):
    doc = nested_doc(monkeypatch, tmp_path)
    outer, inner = doc.structure["tables"]
    assert outer["cells"] == [["바깥", ""]] and outer["nested"] is False
    assert inner["cells"] == [["내부", "7일"]] and inner["nested"] is True
    assert inner["parent_table_ref"] == outer["table_ref"] == "hwp_s0t0"
    by_id = {b.block_id: b for p in doc.pages for b in p.blocks}
    assert [by_id[i].text for i in inner["line_block_ids"]] == ["내부", "7일"]


def test_wrong_total_inside_inner_table_is_found_once(monkeypatch, tmp_path):
    cells = [hw.cell(0, 0, "항목", level=5), hw.cell(1, 0, "금액", level=5),
             hw.cell(0, 1, "치료비", level=5), hw.cell(1, 1, "1,200,000원", level=5),
             hw.cell(0, 2, "위자료", level=5), hw.cell(1, 2, "3,000,000원", level=5),
             hw.cell(0, 3, "합계", level=5), hw.cell(1, 3, "4,700,000원", level=5)]
    doc = nested_doc(monkeypatch, tmp_path, inner_rows=4, inner_cols=2, inner_cells=cells)
    found = hw.arithmetic(doc)
    assert len([f for f in found if (f.confidence_features or {}).get("table_ref") == "hwp_s0t1"]) == 1


def test_inner_table_that_cannot_be_built_makes_outer_partial(monkeypatch, tmp_path):
    doc = nested_doc(monkeypatch, tmp_path, inner_rows=2001, inner_cols=2)
    assert not doc.structure.get("tables")
    assert [t["table_ref"] for t in doc.structure["partial_tables"]] == ["hwp_s0t0"]
