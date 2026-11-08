"""TK-76 EVI-OVR 보완 — O4 의문·가정형 앎 제외, O5 전칭 부정 조사(가·도) 허용(평가 측 공개 합성 문장)."""
from __future__ import annotations

import pytest

from packages.claim_engine.evidence_consistency import INTENT_STATE_RE, check_evidence_overreach
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


def _hit(body: str, ev: str) -> bool:
    texts = ["청구원인", body, "입증방법", ev]
    blocks = [Block(block_id=f"b{i}", text=t, page=1, visible=True, source_layer="visible_text") for i, t in enumerate(texts)]
    doc = NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                             pages=[Page(page_number=1, blocks=blocks, width=595.0, height=842.0)])
    return any(f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH for f in check_evidence_overreach(doc))


@pytest.mark.parametrize("text", ["임대인임을 알았는지는", "도난품임을 알고 있었는지", "결함임을 알았다면", "하자임을 알고 있었다면"])
def test_question_or_condition_is_not_knowledge_assertion(text):
    assert not INTENT_STATE_RE.search(text)


@pytest.mark.parametrize("text", ["도난품임을 처음부터 알고 있었다", "그 사실을 알았다", "결함임을 알면서도"])
def test_knowledge_assertion_still_matches(text):
    assert INTENT_STATE_RE.search(text)


def test_question_form_in_document_is_not_flagged():
    assert not _hit("갑 제2호증 사진만으로 피고가 위 물건이 도난품임을 알았는지는 알 수 없습니다.", "1. 갑 제2호증 사진")


@pytest.mark.parametrize("text", ["전혀 점검을 누락한 바가 없다", "한 번도 연체한 적이 없다", "결코 그런 일도 없었다"])
def test_universal_negation_particles(text):
    # O5 보완: '바가·일도'처럼 조사 '가·도'가 붙어도 전칭 부정이다
    from packages.claim_engine.evidence_consistency import UNIVERSAL_NEGATION_RE
    assert UNIVERSAL_NEGATION_RE.search(text)
