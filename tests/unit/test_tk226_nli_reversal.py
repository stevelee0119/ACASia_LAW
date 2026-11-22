"""TK-226: Legal NLI Stage 2 semantic-reversal classification and offset/reason diagnostics tests."""
from __future__ import annotations

from packages.legal_engine.nli_verifier import evaluate_citation_nli_stage2


# ---------------------------------------------------------------------------
# Positive cases: reversed / distorted citations must NOT be SUPPORTED
# ---------------------------------------------------------------------------


def test_tk226_pos1_double_negation_in_long_precedent_reversal_detected() -> None:
    """Reversing one negation in a multi-negation official precedent must yield CONTRADICTED (not SUPPORTED)."""
    official = (
        "이 사건의 경위를 보면 원심의 판단에는 법리오해가 없다. "
        "원칙적으로 임대차보증금 반환채권의 양수인은 특별한 사정이 없는 한 우선변제권을 행사할 수 없다. "
        "따라서 원고의 주장은 받아들이기 어렵다."
    )
    reversed_quote = "임대차보증금 반환채권의 양수인은 특별한 사정이 없는 한 우선변제권을 행사할 수 있다."
    res = evaluate_citation_nli_stage2(official, reversed_quote)
    d = res.to_dict()

    assert res.verdict == "CONTRADICTED"
    assert res.nli_signal is not None
    assert res.nli_signal.structural_reasons
    assert d["passage_offset"] is not None
    assert d["passage_offset"]["start"] >= 0
    assert d["passage_length"] > 0


def test_tk226_pos2_antonym_and_inflected_negation_reversal_detected() -> None:
    """Antonym/inflected negation reversal ('무효' <-> '유효', '없는' <-> '있는') yields CONTRADICTED."""
    official = "약관의 중요 내용에 관한 설명의무를 위반한 조항은 계약의 내용으로 주장할 수 없고 무효이다."
    reversed_quote = "약관의 중요 내용에 관한 설명의무를 위반한 조항도 계약의 내용으로 유효이다."
    res = evaluate_citation_nli_stage2(official, reversed_quote)

    assert res.verdict == "CONTRADICTED"
    assert res.nli_signal is not None
    assert any(r in res.nli_signal.structural_reasons for r in ("ANTONYM_POLARITY_SWAP", "POLARITY_INVERSION", "QUOTE_DIFF_NEGATION"))


def test_tk226_pos3_modality_obligation_discretion_swap_detected() -> None:
    """Swapping obligation ('하여야 한다') to discretion ('할 수 있다') yields CONTRADICTED."""
    official = "행정청은 처분에 앞서 당사자에게 사전통지를 하고 의견제출 기회를 부여하여야 한다."
    reversed_quote = "행정청은 처분에 앞서 당사자에게 사전통지를 하고 의견제출 기회를 부여할 수 있다."
    res = evaluate_citation_nli_stage2(official, reversed_quote)

    assert res.verdict == "CONTRADICTED"
    assert res.nli_signal is not None
    assert any("MODALITY" in r for r in res.nli_signal.structural_reasons)


# ---------------------------------------------------------------------------
# Control cases: accurate / missing / multi-sentence non-reversed controls
# ---------------------------------------------------------------------------


def test_tk226_ctrl1_accurate_quotation_remains_supported() -> None:
    """Accurate quotation with matching polarity and modality remains SUPPORTED."""
    official = (
        "법원은 변론 전체의 취지와 증거조사의 결과를 참작하여 자유심증으로 사회정의와 형평의 이념에 입각하여 "
        "논리와 경험의 법칙에 따라 사실 주장이 진실한지 아닌지를 판단한다."
    )
    accurate_quote = (
        "법원은 변론 전체의 취지와 증거조사의 결과를 참작하여 자유심증으로 논리와 경험의 법칙에 따라 "
        "사실 주장이 진실한지 아닌지를 판단한다."
    )
    res = evaluate_citation_nli_stage2(official, accurate_quote)

    assert res.verdict == "SUPPORTED"
    assert res.located_passage is not None
    assert res.to_dict()["passage_length"] == len(res.located_passage.text)


def test_tk226_ctrl2_multi_sentence_official_with_neighbor_negation_not_false_contradicted() -> None:
    """A negation in a neighboring sentence of a multi-sentence window must not falsely contradict an accurate quote."""
    official = (
        "매도인은 계약 목적물에 관한 하자를 담보할 책임을 부담한다. "
        "다만 매수인이 계약 당시 그 하자를 알았던 경우에는 그러하지 아니하다."
    )
    accurate_quote = "매도인은 계약 목적물에 관한 하자를 담보할 책임을 부담한다."
    res = evaluate_citation_nli_stage2(official, accurate_quote)

    assert res.verdict == "SUPPORTED"


def test_tk226_ctrl3_missing_official_text_fails_closed_to_insufficient() -> None:
    """Empty or missing official source text always fails closed to INSUFFICIENT."""
    res = evaluate_citation_nli_stage2("", "매도인은 담보책임을 부담한다.")
    assert res.verdict == "INSUFFICIENT"
    assert res.located_passage is None
    assert res.to_dict()["passage_length"] == 0
