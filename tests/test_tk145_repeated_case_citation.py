"""TK-145: 같은 판례를 같은 문단에서 다른 인용문으로 다시 인용하면 별도 인용으로 대조하고, '…하여서는 안 된다'를
부정으로 읽으며, 상대방 주장으로 밝힌 문장은 판시 방향 대조에서 뺀다. 합성 문장만 쓴다."""
from packages.common.enums import CitationType
from packages.common.schemas import Block, Citation, NormalizedDocument, Page
from packages.legal_engine.citation_extractor import extract_citations
from packages.legal_engine.opinion_attribution import _clause_negated

CASE = "대법원 2016. 3. 10. 선고 2015다12345 판결"
TEXT = (f"{CASE}은 “계약 해제의 의사표시는 상대방에게 도달한 때 효력이 생긴다.”라고 판시하였다. "
        "따라서 통지가 도달하기 전에는 해제의 효력이 없다. "
        f"원고는 {CASE}이 “해제 통지는 발송한 때 언제나 효력이 생긴다.”라고 판시하였다고 원용하면서, "
        "발송만으로 해제되었다고 주장한다.")


def one_block(text):
    p = Page(page_number=1)
    p.blocks.append(Block(block_id="b0", text=text, page=1, source_layer="visible_text", block_type="paragraph",
                          visible=True))
    return NormalizedDocument(document_id="d", filename="x.pdf", mime_type="application/pdf", sha256="1" * 64,
                              pages=[p], raw_layers={"raw_text": text})


def test_second_quote_of_same_case_in_same_block_is_kept():
    quotes = [c.quoted_text for c in extract_citations(one_block(TEXT))]
    assert quotes == ["계약 해제의 의사표시는 상대방에게 도달한 때 효력이 생긴다.",
                      "해제 통지는 발송한 때 언제나 효력이 생긴다."]


def test_same_case_same_quote_repeated_is_still_one_citation():
    text = (f"{CASE}은 “계약 해제의 의사표시는 상대방에게 도달한 때 효력이 생긴다.”라고 판시하였다. "
            f"같은 취지로 {CASE}은 “계약 해제의 의사표시는 상대방에게 도달한 때 효력이 생긴다.”라고 하였다.")
    assert len(extract_citations(one_block(text))) == 1


def test_prohibitive_ending_is_negative():
    assert _clause_negated("곧바로 그 요구를 협박이라고 단정하여서는 안 된다")
    assert _clause_negated("이를 근거로 삼아서는 안된다")
    assert not _clause_negated("곧바로 협박으로 보아야 한다")


def _direction(claim, holding):
    from packages.legal_engine.verifier import LegalVerifier
    c = Citation.create(type=CitationType.CASE, raw_text=CASE, document_id="d")
    c.attributes["case_claim"] = claim
    return [f for f in LegalVerifier._opinion_findings(c, {"holding": holding})
            if f.confidence_features["verdict_label"] == "HOLDING_DIRECTION_REVERSED"]


HOLDING = "[1] 해제의 의사표시가 발송만으로 효력이 생기는지 여부(소극)"


def test_opponent_claim_sentence_is_not_compared_with_holding():
    assert _direction("원고는 이 판결을 원용하면서, 해제의 의사표시는 발송만으로 효력이 생긴다고 주장한다.", HOLDING) == []


def test_document_own_reversed_claim_is_still_flagged():
    assert _direction("해제의 의사표시는 발송만으로 효력이 생긴다고 판시하였다.", HOLDING)
