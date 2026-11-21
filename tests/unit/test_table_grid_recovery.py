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


def test_check_column_totals_detects_single_detail_row_grand_total_mismatch():
    rows = [
        ["항목", "금액"],
        ["단일항목", "10"],
        ["총계", "999"],
    ]
    grid = build_table_grid_from_rows(rows, block_id="tbl_single", page=1)
    assert grid.total_row_indices == [2]
    mismatches = check_column_totals(grid)
    assert len(mismatches) == 1
    assert mismatches[0]["row_label"] == "총계"
    assert mismatches[0]["sum_of_rows"] == 10
    assert mismatches[0]["stated_total"] == 999


def test_calculation_engine_verifies_attached_table_grid_subtotal_and_grand_total():
    from packages.claim_engine.calculation import CalculationEngine
    from packages.common.enums import FindingType

    table_text = (
        "구분 | 손해액\n"
        "항목1 | 10\n"
        "소계 | 10\n"
        "항목2 | 20\n"
        "총계 | 999"
    )
    blk = Block(block_id="blk_tbl_1", text=table_text, page=1, block_type="table")
    doc = NormalizedDocument(
        document_id="doc_calc_grid",
        filename="calc.txt",
        mime_type="text/plain",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=[blk])],
    )
    attach_table_grids(doc)
    assert "table_grid" in blk.attributes

    findings = CalculationEngine().verify_document(doc)
    mismatches = [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert any((f.confidence_features or {}).get("stated") == 999 for f in mismatches)


def test_calculation_engine_control_valid_table_grid_emits_no_mismatch():
    from packages.claim_engine.calculation import CalculationEngine
    from packages.common.enums import FindingType

    table_text = (
        "구분 | 손해액\n"
        "항목1 | 10\n"
        "소계 | 10\n"
        "항목2 | 20\n"
        "총계 | 30"
    )
    blk = Block(block_id="blk_tbl_ok", text=table_text, page=1, block_type="table")
    doc = NormalizedDocument(
        document_id="doc_calc_grid_ok",
        filename="calc_ok.txt",
        mime_type="text/plain",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=[blk])],
    )
    attach_table_grids(doc)
    findings = CalculationEngine().verify_document(doc)
    mismatches = [f for f in findings if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert mismatches == []


def test_calculation_engine_preserves_same_wrong_total_across_tables_and_columns():
    from packages.claim_engine.calculation import CalculationEngine
    from packages.common.enums import FindingType

    # Two separate tables both misstating total as 999
    blk_1 = Block(
        block_id="blk_tbl_a",
        text="구분 | 손해액\n항목1 | 10\n항목2 | 20\n합계 | 999",
        page=1,
        block_type="table",
    )
    blk_2 = Block(
        block_id="blk_tbl_b",
        text="구분 | 지연손해금\n항목1 | 40\n항목2 | 50\n합계 | 999",
        page=2,
        block_type="table",
    )
    doc_two_tables = NormalizedDocument(
        document_id="doc_two_tbls",
        filename="two.txt",
        mime_type="text/plain",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=[blk_1]), Page(page_number=2, blocks=[blk_2])],
    )
    attach_table_grids(doc_two_tables)
    f_two = [f for f in CalculationEngine().verify_document(doc_two_tables) if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert {f.block_id for f in f_two} == {"blk_tbl_a", "blk_tbl_b"}

    # Single table with two columns both misstating total as 999
    blk_multi_col = Block(
        block_id="blk_tbl_cols",
        text="구분 | 원금 | 이자\n항목1 | 10 | 5\n항목2 | 20 | 15\n총계 | 999 | 999",
        page=1,
        block_type="table",
    )
    doc_multi_col = NormalizedDocument(
        document_id="doc_multi_col",
        filename="cols.txt",
        mime_type="text/plain",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=[blk_multi_col])],
    )
    attach_table_grids(doc_multi_col)
    f_cols = [f for f in CalculationEngine().verify_document(doc_multi_col) if f.type == FindingType.ARITHMETIC_MISMATCH]
    assert len(f_cols) == 2
    assert {f.confidence_features.get("col_idx") for f in f_cols} == {1, 2}


