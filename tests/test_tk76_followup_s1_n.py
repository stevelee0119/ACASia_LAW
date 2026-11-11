# -*- coding: utf-8 -*-
"""TK-76 3주기 EVI-INCONS 후속: S1(문서 간 앵커 속성 경계)·N1~N3(산식 이름표·뺄셈 합계·나열 쉼표) 평가 측 시험.

문장은 평가 측 비공개 탐침과 다른 합성 낱말로 짓는다(2-2).
"""
from __future__ import annotations

from packages.claim_engine.calculation import CalculationEngine, _extract_formula_tokens
from packages.claim_engine.cross_document_entities import verify_cross_document_entities
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(i, text):
    d = NormalizedDocument(document_id=f"d{i}", filename=f"d{i}.pdf", mime_type="application/pdf", sha256=str(i) * 64)
    p = Page(page_number=1, width=595.0, height=842.0)
    p.blocks.append(Block(block_id=f"b{i}0", page=1, text="사건 2024가합10001 대여금"))
    p.blocks.append(Block(block_id=f"b{i}1", page=1, text=text))
    d.pages.append(p)
    return d


def _anchored(t1, t2):
    fs = verify_cross_document_entities([_doc(1, t1), _doc(2, t2)])
    return [f for f in fs if (f.confidence_features or {}).get("rule_id") == "XDOC.ANCHORED_ATTRIBUTE"]


def _calc(text):
    d = NormalizedDocument(document_id="c", filename="c.pdf", mime_type="application/pdf", sha256="0" * 64)
    p = Page(page_number=1, width=595.0, height=842.0)
    p.blocks.append(Block(block_id="b1", page=1, text=text, bbox=(50.0, 50.0, 500.0, 100.0), block_type="paragraph",
                          source_layer="visible_text"))
    d.pages.append(p)
    return [f for f in CalculationEngine().verify_document(d) if f.type == FindingType.ARITHMETIC_MISMATCH]


def test_s1_longer_attribute_after_money_suffix():
    # '…금' 뒤에 한글이 이어지면('…금일', '…금액') 더 긴 속성으로 읽는다
    assert _anchored("갑 제21호증의 지급금일은 2020. 2. 3.이다.", "갑 제21호증의 지급금일은 2020. 3. 2.이다.")
    assert _anchored("갑 제22호증의 반납금액은 금 1,100,000원이다.", "갑 제22호증의 반납금액은 금 1,010,000원이다.")
    assert not _anchored("갑 제21호증의 지급금일은 2020. 2. 3.이다.", "갑 제23호증의 지급금일은 2020. 3. 2.이다.")


def test_n1_period_label_is_not_operand():
    toks = [t["raw"].strip() for t in _extract_formula_tokens("물량: 2월분 300개 + 3월분 200개 = 500개")]
    assert "2월분" not in toks and "3월분" not in toks
    assert _calc("물량: 2월분 300개 + 3월분 200개 = 600개")
    assert not _calc("물량: 2월분 300개 + 3월분 200개 = 500개")
    # 기간의 양('2개월분')은 수량이므로 이름표가 아니다
    assert any(t["raw"].strip().startswith("2개월분") for t in _extract_formula_tokens("2개월분 사용료 1,000,000원"))


def test_n2_subtraction_sentence_is_not_a_sum_total():
    assert not _calc("보수 3,000,000원에서 수수료 200,000원을 빼면 실지급액은 2,800,000원이다.")
    assert _calc("보수 3,000,000원에서 수수료 200,000원을 빼면 실지급액은 2,700,000원이다.")


def test_n3_comma_list_is_not_clause_break():
    assert not _calc("사용료는 5월분 100,000원, 6월분 120,000원, 7월분 130,000원으로 합계 350,000원이다.")
    assert _calc("사용료는 5월분 100,000원, 6월분 120,000원, 7월분 130,000원으로 합계 360,000원이다.")


def test_s1_variants_order_connective_vocab():
    """S1 변형 시험: 어순, 연결 어미, 다른 속성 낱말(2-2 규약)."""
    # 1) 어순/조사 변형 ('기재', '의')
    assert _anchored("갑 제1호증 기재 입금일자는 2021. 5. 1.이다.", "갑 제1호증 기재 입금일자는 2021. 5. 2.이다.")
    # 2) 연결 어미 변형 ('-이고,')
    assert _anchored("을 제3호증의 출금일은 2022. 1. 10.이고,", "을 제3호증의 출금일은 2022. 1. 11.이다.")
    # 3) 다른 속성 낱말 (송금액, 환불금액)
    assert _anchored("갑 제5호증의 송금액은 500,000원이며,", "갑 제5호증의 송금액은 600,000원이다.")
    assert _anchored("을 제7호증의 환불금액은 2,000,000원이다.", "을 제7호증의 환불금액은 3,000,000원이다.")


def test_n1_variants_period_types_and_connectives():
    """N1 변형 시험: 분기분/반기분/년분 기간 표지 및 연산 연결(2-2 규약)."""
    toks_q = [t["raw"].strip() for t in _extract_formula_tokens("1분기분 40개 + 2분기분 60개 = 100개")]
    assert "1분기분" not in toks_q and "2분기분" not in toks_q
    assert not _calc("1분기분 40개 + 2분기분 60개 = 100개")
    assert _calc("1분기분 40개 + 2분기분 60개 = 110개")

    toks_y = [t["raw"].strip() for t in _extract_formula_tokens("2023년분 500원 + 2024년분 500원 = 1,000원")]
    assert "2023년분" not in toks_y and "2024년분" not in toks_y
    assert not _calc("2023년분 500원 + 2024년분 500원 = 1,000원")
    assert _calc("2023년분 500원 + 2024년분 500원 = 1,200원")


def test_n2_variants_subtraction_predicates_and_order():
    """N2 변형 시험: 공제/차감 등 다양한 뺄셈 술어 및 연결 표현(2-2 규약)."""
    # '공제하면'
    assert not _calc("총액 5,000,000원에서 세금 500,000원을 공제하면 실지급액은 4,500,000원이다.")
    assert _calc("총액 5,000,000원에서 세금 500,000원을 공제하면 실지급액은 4,000,000원이다.")
    # '차감하여'
    assert not _calc("원금 10,000,000원에서 분담금 1,000,000원을 차감하여 차인지급액은 9,000,000원이다.")
    assert _calc("원금 10,000,000원에서 분담금 1,000,000원을 차감하여 차인지급액은 8,000,000원이다.")


def test_n3_variants_comma_spacing_and_length():
    """N3 변형 시험: 쉼표 뒤 공백 유무 및 다항목 나열(2-2 규약)."""
    # 쉼표 뒤 공백 있는 나열
    assert not _calc("비용은 1월분 10원, 2월분 20원, 3월분 30원으로 합계 60원이다.")
    assert _calc("비용은 1월분 10원, 2월분 20원, 3월분 30원으로 합계 70원이다.")
    # 쉼표 뒤 숫자 바로 오는 나열
    assert not _calc("비용은 100원, 200원, 300원으로 합계 600원이다.")
    assert _calc("비용은 100원, 200원, 300원으로 합계 700원이다.")

