"""TK-76 EVI-INCONS C 보완 D1 — 결과 제목·내용 수식에 날짜·번호 조각이 남지 않는다(평가 측 공개 합성 문장)."""
from __future__ import annotations

import re

from packages.claim_engine.internal_inconsistency import check_internal_inconsistency
from packages.common.schemas import Block, NormalizedDocument, Page


def _titles(lines):
    blocks = [Block(block_id=f"b{i}", text=t, page=1, visible=True, source_layer="visible_text") for i, t in enumerate(lines)]
    doc = NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                             pages=[Page(page_number=1, blocks=blocks, width=595.0, height=842.0)])
    return [f.title for f in check_internal_inconsistency(doc)
            if (f.confidence_features or {}).get("rule_id") == "EVI.INCONS_SAME_EVENT_DATETIME"]


def test_title_has_no_date_fragment():
    titles = _titles([
        "피고는 원고에게 2024. 5. 7. 유일한 이행최고서를 발송하였습니다.",
        "피고가 2024. 5. 13. 발송한 위 이행최고서에는 14일의 이행기간이 적혀 있었습니다.",
    ])
    assert titles, "같은 사건 두 날짜 모순을 내야 한다"
    for t in titles:
        inside = re.search(r"동일 사건\(([^)]*)\)", t)
        assert inside, t
        assert not re.search(r"\d", inside.group(1)), t
