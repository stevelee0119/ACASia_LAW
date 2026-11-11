"""TK-76 3주기 후속 D 묶음 — 날짜 검증 성능 P1(평가 측 공개 시험). 판정 결과는 바뀌지 않고 시간만 줄어야 한다."""
from __future__ import annotations

import time

from packages.claim_engine.date_verifier import verify_dates_in_document
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(text):
    b = Block(block_id="b1", text=text, page=1, visible=True, source_layer="visible_text")
    return NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                              pages=[Page(page_number=1, blocks=[b], width=595.0, height=842.0)])


def test_p1_long_hangul_run_without_spaces_is_linear():
    # 기준 Steve 3d54f77 약 34초(CONJUGATED_ORDER_RE 이차 시간) → 사본 0.2초 안팎. 여유를 크게 둔 상한
    text = "나" * 20000 + " 통지는 2024. 2. 5. 도달하였다. 피고는 2024. 2. 13. 원고에 대한 감급처분을 결정하였다."
    t0 = time.time()
    verify_dates_in_document(_doc(text))
    assert time.time() - t0 < 5.0


def test_p1_order_connective_still_read():
    # 동사 길이 제한 뒤에도 '-ㄴ 뒤/후' 순서 연결어 판정은 그대로(이 꼴의 결과가 비지 않음은 기존 시험이 본다 — 여기서는 예외 없이 끝나는지만)
    verify_dates_in_document(_doc("원고는 2024. 3. 2. 계약을 해지한 뒤 2024. 3. 1. 통지를 발송하였다."))
