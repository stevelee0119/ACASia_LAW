"""TK-146: 표 비율 오류를 행 단위로 진단하고, 비율 열을 금액 합계로 검산하지 않는다. 합성 표만 쓴다."""
import pytest

from packages.claim_engine.calculation import CalculationEngine
from packages.common.schemas import Block, NormalizedDocument, Page


def run(cells):
    page = Page(page_number=1)
    text = "\n".join(" | ".join(r) for r in cells)
    page.blocks.append(Block(block_id="t", text=text, page=1, source_layer="visible_text", block_type="table",
                             visible=True, attributes={"table_ref": "x_t0", "cells": cells}))
    doc = NormalizedDocument(document_id="d", filename="x.hwpx", mime_type="", sha256="1" * 64, pages=[page],
                             raw_layers={"raw_text": text})
    doc.structure["tables"] = [{"table_ref": "x_t0", "page": 1, "cells": cells, "header": cells[0], "complete": True,
                                "representation": "TABLE_BLOCK"}]
    return [f for f in CalculationEngine().verify_document(doc) if f.type.value == "ARITHMETIC_MISMATCH"]


def table(pct):
    return [["구분", "금액(원)", "비율(%)"], ["가 항목", "900,000", "45"], ["나 항목", "700,000", pct],
            ["다 항목", "400,000", "20"], ["합계", "2,000,000", "100"]]


def test_wrong_row_percentage_is_named_once_without_percent_column_sum():
    [f] = run(table("30"))                                     # 나 항목은 35%
    assert f.title.startswith("비율(%)") and f.confidence_features["rows"] == ["나 항목: 기재 30% / 계산 35.00%"]
    assert "원" not in f.title


def test_correct_percentages_have_no_finding():
    assert run(table("35")) == []


@pytest.mark.parametrize("pct", ["35%", "35.0"])
def test_percent_sign_or_decimal_forms_are_read(pct):
    assert run(table(pct)) == []
