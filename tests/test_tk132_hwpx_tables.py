"""TK-132: HWPX 표 구조 보존과 표 글자 중복 수집 제거.

합성 HWPX만 쓴다(시험 안에서 만든다). 표를 감싼 바깥 문단이 셀 글자를 한 번 더 모으던 결함과,
계산·사실 엔진이 쓰는 structure["tables"]가 HWPX에서 비어 있던 결함을 함께 본다.
"""
import zipfile

import pytest

from packages.claim_engine.calculation import CalculationEngine
from packages.document_engine.registry import parse_document

NS = ('xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
      'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"')


def para(text):
    return f"<hp:p><hp:run><hp:t>{text}</hp:t></hp:run></hp:p>"


def cell(row, col, *texts, row_span=1, col_span=1, inner=""):
    body = "".join(para(t) for t in texts) + inner
    return (f"<hp:tc><hp:subList>{body}</hp:subList><hp:cellAddr colAddr=\"{col}\" rowAddr=\"{row}\"/>"
            f"<hp:cellSpan colSpan=\"{col_span}\" rowSpan=\"{row_span}\"/></hp:tc>")


def table(rows, cols, *trs):
    body = "".join(f"<hp:tr>{''.join(tr)}</hp:tr>" for tr in trs)
    return f'<hp:p><hp:run><hp:tbl rowCnt="{rows}" colCnt="{cols}">{body}</hp:tbl></hp:run></hp:p>'


def hwpx(tmp_path, *sections, name="t.hwpx", manifest=None):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        for index, content in sections:
            z.writestr(f"Contents/section{index}.xml",
                       f'<?xml version="1.0" encoding="UTF-8"?><hs:sec {NS}>{content}</hs:sec>')
        if manifest:
            z.writestr("Contents/content.hpf", manifest)
    return parse_document(str(path), document_id="d", filename=name, mime_type="", sha256="x")


def visible(doc):
    return [b for p in doc.pages for b in p.blocks if b.source_layer == "visible_text"]


def text_of(doc):
    return "\n".join(b.text for b in visible(doc))


# --- 양성: 표 구조와 중복 제거 ------------------------------------------------------------------------------
def test_simple_table_is_structured_and_not_duplicated(tmp_path):
    doc = hwpx(tmp_path, (0, para("가. 손해배상 청구") + table(2, 2,
        [cell(0, 0, "항목"), cell(0, 1, "금액")], [cell(1, 0, "치료비"), cell(1, 1, "1,200,000원")])))
    [t] = doc.structure["tables"]
    assert t["cells"] == [["항목", "금액"], ["치료비", "1,200,000원"]]
    assert text_of(doc).count("1,200,000원") == 1          # 바깥 문단이 셀 글자를 다시 모으지 않는다
    assert any(b.block_type == "table" and b.attributes["table_ref"] == t["table_ref"] for b in visible(doc))


def test_merged_header_keeps_anchor_only(tmp_path):
    doc = hwpx(tmp_path, (0, table(3, 3,
        [cell(0, 0, "구분", row_span=2), cell(0, 1, "청구액", col_span=2)],
        [cell(1, 1, "원금"), cell(1, 2, "이자")],
        [cell(2, 0, "갑"), cell(2, 1, "500만원"), cell(2, 2, "30만원")])))
    [t] = doc.structure["tables"]
    assert t["cells"][0] == ["구분", "청구액", ""]           # 병합 값은 앵커 칸에만
    assert t["cells"][1][0] == ""                           # 세로 병합으로 덮인 칸은 빈칸
    assert {"row": 0, "col": 1, "row_span": 1, "col_span": 2} in t["merges"]
    assert [1, 0] in t["covered"] and [0, 2] in t["covered"]
    assert t["complete"] is True


def test_cell_with_several_paragraphs_and_nested_table(tmp_path):
    inner = table(1, 2, [cell(0, 0, "내부 표"), cell(0, 1, "7일")])
    doc = hwpx(tmp_path, (0, table(1, 2,
        [cell(0, 0, "첫 문단", "둘째 문단"), cell(0, 1, "바깥 칸", inner=inner)])))
    outer, nested = doc.structure["tables"]
    assert outer["cells"] == [["첫 문단 둘째 문단", "바깥 칸"]]  # 중첩 표 글자는 바깥 칸에 섞이지 않는다
    assert nested["nested"] is True and nested["parent_table_ref"] == outer["table_ref"]
    assert nested["cells"] == [["내부 표", "7일"]]
    assert text_of(doc).count("7일") == 1


def test_sections_follow_numeric_order(tmp_path):
    doc = hwpx(tmp_path, (10, para("열 번째 구역")), (2, para("두 번째 구역")), (1, para("첫 구역")))
    text = doc.raw_layers["rendered_text"]           # 문단 복원이 짧은 문단을 합칠 수 있어 원문 층으로 순서를 본다
    assert text.index("첫 구역") < text.index("두 번째 구역") < text.index("열 번째 구역")


# --- 계산 엔진 연결(실제 진입점 parse_document → CalculationEngine) -------------------------------------------
def sum_table(total):
    return table(4, 2,
        [cell(0, 0, "항목"), cell(0, 1, "금액")],
        [cell(1, 0, "치료비"), cell(1, 1, "1,200,000원")],
        [cell(2, 0, "위자료"), cell(2, 1, "3,000,000원")],
        [cell(3, 0, "합계"), cell(3, 1, total)])


def arithmetic(doc):
    return [f for f in CalculationEngine().verify_document(doc) if f.type.value == "ARITHMETIC_MISMATCH"]


def test_wrong_table_total_is_found_through_parse_document(tmp_path):
    found = arithmetic(hwpx(tmp_path, (0, sum_table("4,500,000원"))))
    # 표 행 단위 검산(_verify_table_totals)이 잡아야 한다. 예전에는 중복된 줄 글자에서 우연히 잡혔다.
    assert [f.confidence_features.get("table_ref") for f in found] == ["hwpx_s0t0"]


def test_correct_table_total_has_no_arithmetic_finding(tmp_path):
    assert arithmetic(hwpx(tmp_path, (0, sum_table("4,200,000원")))) == []


# --- 대조: 손상·과대 구조 ----------------------------------------------------------------------------------
def test_span_outside_table_is_partial_and_not_given_to_consumers(tmp_path):
    doc = hwpx(tmp_path, (0, table(1, 2, [cell(0, 0, "가"), cell(0, 1, "나", col_span=3)])))
    assert not doc.structure.get("tables")                    # 불완전한 표는 계산·사실·첨부 소비자에 넘기지 않는다
    [partial] = doc.structure["partial_tables"]
    assert partial["reason"] == "INCOMPLETE_STRUCTURE" and "cells" not in partial
    assert any("범위를 벗어나" in w for w in doc.parse_warnings)


@pytest.mark.parametrize("rows,cols", [(999999, 2), (2, 999), (1000, 101)])
def test_oversized_table_is_not_built(tmp_path, rows, cols):
    doc = hwpx(tmp_path, (0, f'<hp:p><hp:run><hp:tbl rowCnt="{rows}" colCnt="{cols}"><hp:tr>'
                             + cell(0, 0, "가") + "</hp:tr></hp:tbl></hp:run></hp:p>"))
    assert not doc.structure.get("tables")
    assert any("상한" in w for w in doc.parse_warnings)


def test_overlapping_cells_make_table_partial(tmp_path):
    doc = hwpx(tmp_path, (0, table(1, 2, [cell(0, 0, "앞", col_span=2), cell(0, 1, "겹침")])))
    assert not doc.structure.get("tables") and doc.structure["partial_tables"]
    assert "앞" in text_of(doc)                                # 글자는 일반 문단으로 남는다


def test_partial_total_table_creates_no_arithmetic_finding(tmp_path):
    # 합계가 틀린 표라도 셀 주소가 깨진 불완전한 표면 계산 근거로 쓰지 않는다
    broken = table(3, 2, [cell(0, 0, "항목"), cell(0, 1, "금액")],
                   [cell(1, 0, "치료비"), cell(1, 1, "1,200,000원", col_span=4)],
                   [cell(2, 0, "합계"), cell(2, 1, "9,999,999원")])
    assert [f for f in arithmetic(hwpx(tmp_path, (0, broken)))
            if (f.confidence_features or {}).get("table_ref")] == []


def test_manifest_spine_relative_href_sets_section_order(tmp_path):
    manifest = ('<?xml version="1.0"?><opf:package xmlns:opf="http://www.idpf.org/2007/opf/"><opf:manifest>'
                '<opf:item id="a" href="section1.xml"/><opf:item id="b" href="section0.xml"/></opf:manifest>'
                '<opf:spine><opf:itemref idref="a"/><opf:itemref idref="b"/></opf:spine></opf:package>')
    doc = hwpx(tmp_path, (0, para("영 번 구역")), (1, para("일 번 구역")), manifest=manifest)
    text = doc.raw_layers["rendered_text"]
    assert text.index("일 번 구역") < text.index("영 번 구역")     # spine 순서(상대 href)를 따른다


def test_document_without_table_unchanged(tmp_path):
    doc = hwpx(tmp_path, (0, para("첫째 문단이다.") + para("둘째 문단이다.")))
    assert not doc.structure.get("tables")
    assert "첫째 문단이다." in text_of(doc) and "둘째 문단이다." in text_of(doc)
