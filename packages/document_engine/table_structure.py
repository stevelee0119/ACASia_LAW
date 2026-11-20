"""Structured TableGrid recovery for legal documents (P2 PR-10).

Converts flat `" | "` table block text or raw 2D cell matrices into a normalized
`TableGrid` (`rows`, `cols`, `headers`, `cells`) stored in `Block.attributes["table_grid"]`,
preserving row/column header context and detecting total/summary rows for downstream
calculation and date verification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from packages.common.schemas import Block, NormalizedDocument


_TOTAL_ROW_RE = re.compile(r"^(?:합\s*계|총\s*계|소\s*계|계|합산|총액)\b")
_AMOUNT_RE = re.compile(r"[-+]?\d{1,3}(?:,\d{3})+|\d+")


@dataclass(frozen=True)
class TableCell:
    row_idx: int
    col_idx: int
    text: str
    row_span: int = 1
    col_span: int = 1
    is_header: bool = False
    header_path: List[str] = field(default_factory=list)
    row_label: str = ""
    bbox: Optional[Tuple[float, float, float, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TableGrid:
    block_id: str
    page: int
    num_rows: int
    num_cols: int
    headers: List[str] = field(default_factory=list)
    cells: List[TableCell] = field(default_factory=list)
    total_row_indices: List[int] = field(default_factory=list)

    def cell(self, row_idx: int, col_idx: int) -> Optional[TableCell]:
        for c in self.cells:
            if c.row_idx <= row_idx < c.row_idx + c.row_span and c.col_idx <= col_idx < c.col_idx + c.col_span:
                return c
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "page": self.page,
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "headers": self.headers,
            "total_row_indices": self.total_row_indices,
            "cells": [c.to_dict() for c in self.cells],
        }


def build_table_grid_from_rows(
    rows: Sequence[Sequence[str]],
    *,
    block_id: str = "",
    page: int = 1,
    header_rows: int = 1,
) -> TableGrid:
    """Build a normalized `TableGrid` from a 2D list of row/cell strings."""
    cleaned_rows = [[re.sub(r"\s+", " ", str(cell or "")).strip() for cell in row] for row in rows if any(str(c or "").strip() for c in row)]
    if not cleaned_rows:
        return TableGrid(block_id=block_id, page=page, num_rows=0, num_cols=0)

    num_rows = len(cleaned_rows)
    num_cols = max(len(r) for r in cleaned_rows)
    padded = [r + [""] * (num_cols - len(r)) for r in cleaned_rows]

    hdr_count = max(0, min(header_rows, num_rows))
    col_headers: List[str] = []
    for c_idx in range(num_cols):
        parts = [padded[r_idx][c_idx] for r_idx in range(hdr_count) if padded[r_idx][c_idx]]
        col_headers.append(" / ".join(parts) if parts else f"col_{c_idx}")

    cells: List[TableCell] = []
    total_rows: List[int] = []
    for r_idx, row in enumerate(padded):
        row_label = row[0] if row else ""
        if r_idx >= hdr_count and _TOTAL_ROW_RE.match(row_label):
            total_rows.append(r_idx)
        for c_idx, text in enumerate(row):
            is_hdr = r_idx < hdr_count
            cells.append(
                TableCell(
                    row_idx=r_idx,
                    col_idx=c_idx,
                    text=text,
                    is_header=is_hdr,
                    header_path=[col_headers[c_idx]] if not is_hdr else [],
                    row_label=row_label,
                )
            )

    return TableGrid(
        block_id=block_id,
        page=page,
        num_rows=num_rows,
        num_cols=num_cols,
        headers=col_headers,
        cells=cells,
        total_row_indices=total_rows,
    )


def parse_pipe_table_block(block: Block, *, header_rows: int = 1) -> Optional[TableGrid]:
    """Parse a `table` or `table_line` Block formatted with `" | "` cell separators."""
    text = (block.text or "").strip()
    if not text:
        return None
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows: List[List[str]] = []
    for line in raw_lines:
        stripped = line.strip("|").strip()
        parts = [p.strip() for p in stripped.split("|")]
        if parts:
            rows.append(parts)
    if not rows:
        return None
    return build_table_grid_from_rows(
        rows,
        block_id=block.block_id,
        page=block.page,
        header_rows=header_rows,
    )


def attach_table_grids(doc: NormalizedDocument) -> List[TableGrid]:
    """Attach structured `table_grid` metadata to all table blocks in `doc`."""
    grids: List[TableGrid] = []
    for block in doc.blocks:
        if block.block_type not in ("table", "table_line"):
            continue
        grid = parse_pipe_table_block(block)
        if grid and grid.num_rows > 0:
            block.attributes["table_grid"] = grid.to_dict()
            grids.append(grid)
    return grids


def check_column_totals(grid: TableGrid) -> List[Dict[str, Any]]:
    """Verify numeric column sums against any detected total/summary rows in `TableGrid`."""
    mismatches: List[Dict[str, Any]] = []
    if not grid.total_row_indices or grid.num_rows < 3:
        return mismatches

    first_total = min(grid.total_row_indices)
    for col_idx in range(1, grid.num_cols):
        total_cell = grid.cell(first_total, col_idx)
        if not total_cell:
            continue
        tot_match = _AMOUNT_RE.search(total_cell.text.replace(",", ""))
        if not tot_match:
            continue
        expected_total = int(tot_match.group(0))

        item_values: List[int] = []
        for r_idx in range(1, first_total):
            c = grid.cell(r_idx, col_idx)
            if not c or c.is_header:
                continue
            m = _AMOUNT_RE.search(c.text.replace(",", ""))
            if m:
                item_values.append(int(m.group(0)))

        if len(item_values) >= 2:
            actual_sum = sum(item_values)
            if actual_sum != expected_total:
                mismatches.append({
                    "block_id": grid.block_id,
                    "page": grid.page,
                    "col_idx": col_idx,
                    "header": grid.headers[col_idx] if col_idx < len(grid.headers) else f"col_{col_idx}",
                    "sum_of_rows": actual_sum,
                    "stated_total": expected_total,
                    "difference": actual_sum - expected_total,
                })
    return mismatches
