"""TK-76 EVI-INCONS C 후속 T1 — 결과 제목의 대상 표시에 같은 낱말이 겹치지 않는다(평가 측 공개 합성 문장)."""
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


def _target(title):
    m = re.search(r"동일 사건\(([^)]*)\)", title)
    return m.group(1) if m else ""


def test_no_repeated_word_when_head_nouns_differ():
    titles = _titles([
        "위원회는 2024. 3. 4. 처음이자 마지막으로 원고에 대한 해고를 의결하였습니다.",
        "위원회가 2024. 3. 18. 한 위 해고 의결은 정관상 정족수를 채우지 못하였습니다.",
    ])
    assert titles
    for t in titles:
        words = _target(t).split()
        assert len(words) == len(set(words)), t


def test_content_and_head_from_same_slot():
    titles = _titles([
        "원고는 2024. 5. 2. 단 한 차례 해지 통지를 발송하였습니다.",
        "원고는 2024. 5. 9. 위 해지 통지를 발송하였습니다.",
    ])
    assert titles and all(_target(t) == "해지 통지" for t in titles), titles
