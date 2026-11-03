"""TK-144: DOCX 표를 structure["tables"]로 내어 표 검산이 DOCX에서도 동작하게 한다. 합성 문서만 쓴다."""
import docx
import pytest

from packages.claim_engine.calculation import CalculationEngine
from packages.document_engine.registry import parse_document


def build(tmp_path, tables, name="t.docx"):
    d = docx.Document()
    d.add_paragraph("가. 손해 정리")
    for rows in tables:
        t = d.add_table(rows=len(rows), cols=len(rows[0]))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                if value is not None:
                    t.cell(r, c).text = value
        d.add_paragraph("표 뒤 문단")
    path = tmp_path / name
    d.save(path)
    return path, d


def parse(path):
    return parse_document(str(path), document_id="d", filename=path.name, mime_type="", sha256="x")


def mismatches(doc):
    return [f for f in CalculationEngine().verify_document(doc) if f.type.value == "ARITHMETIC_MISMATCH"]


SUM_WRONG = [["항목", "금액(원)"], ["수리비", "1,250,000"], ["대여료", "480,000"], ["재검수 비용", "270,000"],
             ["합계", "2,100,000"]]
SUM_RIGHT = [["항목", "금액(원)"], ["교체비", "320,000"], ["운임", "180,000"], ["인건비", "250,000"],
             ["합계", "750,000"]]


def test_docx_table_is_exposed_with_cells_and_line_blocks(tmp_path):
    path, _ = build(tmp_path, [SUM_WRONG])
    doc = parse(path)
    [t] = doc.structure["tables"]
    assert t["table_ref"] == "docx_t0" and t["cells"][4] == ["합계", "2,100,000"]
    ids = {b.block_id for p in doc.pages for b in p.blocks if b.attributes.get("table_ref") == "docx_t0"}
    assert set(t["line_block_ids"]) == ids and len(ids) == 10


def test_wrong_table_total_is_found_once_and_right_total_is_not(tmp_path):
    path, _ = build(tmp_path, [SUM_WRONG, SUM_RIGHT])
    found = mismatches(parse(path))
    refs = [(f.confidence_features or {}).get("table_ref") for f in found]
    assert refs == ["docx_t0"]


def test_merged_header_and_two_paragraph_cell_are_preserved_without_false_finding(tmp_path):
    rows = [["구분", "비용(원)", None, "증빙"], [None, "직접비", "부대비", None],
            ["복구", "900,000", "100,000", "명세서"], ["회수", "400,000", "100,000", "확인서"],
            ["합계", "1,300,000", "200,000", "항목별 합산"]]
    path, d = build(tmp_path, [rows])
    t = d.tables[0]
    t.cell(0, 1).merge(t.cell(0, 2))                  # 가로 병합
    t.cell(0, 0).merge(t.cell(1, 0))                  # 세로 병합
    t.cell(0, 3).merge(t.cell(1, 3))
    t.cell(2, 3).add_paragraph("작업확인서")          # 한 칸 두 문단
    d.save(path)
    doc = parse(path)
    [table] = doc.structure["tables"]
    assert table["row_count"] == 5 and table["column_count"] == 4
    assert {(m["row"], m["col"], m["row_span"], m["col_span"]) for m in table["merges"]} >= {(0, 1, 1, 2), (0, 0, 2, 1)}
    assert table["cells"][2][3].split() == ["명세서", "작업확인서"]
    assert mismatches(doc) == []


def test_document_without_tables_is_unchanged(tmp_path):
    d = docx.Document()
    d.add_paragraph("첫째 문단이다.")
    path = tmp_path / "plain.docx"
    d.save(path)
    doc = parse(path)
    assert not doc.structure.get("tables") and not doc.structure.get("partial_tables")


def test_table_structure_failure_keeps_body_text(tmp_path, monkeypatch):
    import packages.document_engine.docx_parser as dp

    def boom(*args, **kwargs):
        raise ValueError("합성 실패")
    monkeypatch.setattr(dp, "_docx_table_structures", boom)
    path, _ = build(tmp_path, [SUM_WRONG])
    doc = parse(path)
    assert not doc.structure.get("tables") and any("표 구조 복원 실패" in w for w in doc.parse_warnings)
    assert any(b.text == "1,250,000" for p in doc.pages for b in p.blocks)
