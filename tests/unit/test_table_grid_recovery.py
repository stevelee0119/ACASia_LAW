"""Unit tests for TableGrid recovery and column sum verification (P2 PR-10)."""
from __future__ import annotations

from packages.common.schemas import Block, NormalizedDocument, Page
from packages.document_engine.table_structure import (
    attach_table_grids,
    build_table_grid_from_rows,
    check_column_totals,
)


def test_build_table_grid_preserves_headers_and_row_labels():
    rows = [
        ["항목", "청구금액", "인정금액"],
        ["치료비", "1,000,000", "800,000"],
        ["위자료", "2,000,000", "1,500,000"],
        ["합계", "3,000,000", "2,300,000"],
    ]
    grid = build_table_grid_from_rows(rows, block_id="tbl_1", page=2)
    assert grid.num_rows == 4
    assert grid.num_cols == 3
    assert grid.headers == ["항목", "청구금액", "인정금액"]
    assert grid.total_row_indices == [3]
    c = grid.cell(1, 2)
    assert c is not None
    assert c.header_path == ["인정금액"]
    assert c.row_label == "치료비"
    assert check_column_totals(grid) == []


def test_attach_table_grids_and_detect_total_mismatch():
    table_text = (
        "구분 | 청구액 | 비고\n"
        "원금 | 1,000,000 | 약정\n"
        "이자 | 500,000 | 지연\n"
        "합계 | 2,000,000 | 오기"
    )
    doc = NormalizedDocument(
        document_id="doc_tbl_1",
        filename="claim.pdf",
        mime_type="application/pdf",
        sha256="b" * 64,
        pages=[
            Page(
                page_number=1,
                blocks=[
                    Block(block_id="b_tbl", text=table_text, page=1, block_type="table"),
                ],
            )
        ],
    )
    grids = attach_table_grids(doc)
    assert len(grids) == 1
    assert "table_grid" in doc.blocks[0].attributes
    mismatches = check_column_totals(grids[0])
    assert len(mismatches) == 1
    assert mismatches[0]["header"] == "청구액"
    assert mismatches[0]["sum_of_rows"] == 1_500_000
    assert mismatches[0]["stated_total"] == 2_000_000


def test_check_column_totals_detects_grand_total_mismatch_after_subtotal():
    rows = [
        ["항목", "금액"],
        ["항목A", "10"],
        ["소계", "10"],
        ["항목B", "20"],
        ["총계", "999"],
    ]
    grid = build_table_grid_from_rows(rows, block_id="tbl_sub", page=3)
    assert grid.total_row_indices == [2, 4]
    mismatches = check_column_totals(grid)
    assert len(mismatches) == 1
    assert mismatches[0]["row_label"] == "총계"
    assert mismatches[0]["sum_of_rows"] == 30
    assert mismatches[0]["stated_total"] == 999

