"""LV-04: 인용문 진위 정렬 및 차이 유형 구조화 단위 시험 (Public Synthetic Tests).

규칙 요구사항:
- 양성 예시 3건 (부정어 왜곡 NEGATION, 주어/객체 바뀜 PARTY_SWAP, 수치 불일치 NUMERIC / 단서 탈락 PROVISO_OMISSION)
- 대조군 3건 (본문 미확보 대조 불가 TEXT_UNAVAILABLE, 지어낸 인용문 FABRICATED_QUOTE, 완전 일치 EXACT_MATCH)
- 사건 고유 리터럴 미사용 (합성 문장 및 일반 법리 규정)
"""
from __future__ import annotations

from packages.legal_engine.quote_diff import (
    categorize_quote_diff,
    quote_changes,
    render_quote_diff,
)


def test_lv04_positive_negation_distortion():
    """양성 1: 부정어 삽입/탈락 왜곡 탐지 (NEGATION)."""
    official = "채무자의 이행지체로 인하여 발생한 손해에 대하여 채권자는 배상을 청구할 수 있고 그 책임을 면제하지 아니한다."
    quoted = "채무자의 이행지체로 인하여 발생한 손해에 대하여 채권자는 배상을 청구할 수 있고 그 책임을 면제한다."

    res = categorize_quote_diff(quoted, official, has_full_text=True)
    assert res["status"] == "MODIFIED_QUOTE"
    assert "NEGATION" in res["diff_categories"]
    assert res["meaningful"] is True
    assert "부정어 삽입/탈락" in res["category_labels"]


def test_lv04_positive_party_swap():
    """양성 2: 주어·객체 바뀜 왜곡 탐지 (PARTY_SWAP)."""
    official = "행정청은 침익적 행정처분을 함에 있어 당사자에게 의견제출의 기회를 부여하여야 한다."
    quoted = "당사자는 침익적 행정처분을 함에 있어 행정청에게 의견제출의 기회를 부여하여야 한다."

    res = categorize_quote_diff(quoted, official, has_full_text=True)
    assert res["status"] == "MODIFIED_QUOTE"
    assert "PARTY_SWAP" in res["diff_categories"]
    assert "주어·객체 바뀜" in res["category_labels"]


def test_lv04_positive_numeric_mismatch_and_proviso():
    """양성 3: 수치 불일치 탐지 (NUMERIC) 및 단서 탈락."""
    official = "취소소송은 처분등이 있음을 안 날부터 90일 이내에 제기하여야 하며 정당한 사유가 없는 한 이를 도과할 수 없다."
    quoted = "취소소송은 처분등이 있음을 안 날부터 60일 이내에 제기하여야 하며 정당한 사유가 없는 한 이를 도과할 수 없다."

    res = categorize_quote_diff(quoted, official, has_full_text=True)
    assert res["status"] == "MODIFIED_QUOTE"
    assert "NUMERIC" in res["diff_categories"]
    assert "수치 불일치" in res["category_labels"]


def test_lv04_contrast_text_unavailable():
    """대조군 1: 판결요지만 확보되고 본문이 미확보된 경우 인용 대조 불가 명시 (TEXT_UNAVAILABLE)."""
    quoted = "어떠한 손해도 인정되지 아니한다."

    # 1. official_text가 None인 경우
    res1 = categorize_quote_diff(quoted, None, has_full_text=False)
    assert res1["status"] == "TEXT_UNAVAILABLE"
    assert res1["can_compare"] is False
    assert "공식 판결문 본문 미확보" in res1["reason"]

    # 2. has_full_text가 False인 경우 (요약본만 확보)
    summary_only = "처분의 효력 정지에 관한 판결 요지입니다."
    res2 = categorize_quote_diff(quoted, summary_only, has_full_text=False)
    assert res2["status"] == "TEXT_UNAVAILABLE"
    assert res2["can_compare"] is False


def test_lv04_contrast_fabricated_quote():
    """대조군 2: 원문 어디에도 없는 지어낸 인용문 탐지 (FABRICATED_QUOTE, CIT-FAB-Q)."""
    official = "민법 제750조의 불법행위에 기한 손해배상청구권에 있어서 고의 또는 과실의 입증책임은 원고에게 있다."
    # 완전히 지어낸 인용문
    fabricated = "상대방의 계약 위반은 신의성실의 원칙상 결코 용인될 수 없으므로 무조건 계약 해제권이 발생한다."

    res = categorize_quote_diff(fabricated, official, has_full_text=True)
    assert res["status"] == "FABRICATED_QUOTE"
    assert "FABRICATED_QUOTE" in res["diff_categories"]
    assert "CIT-FAB-Q" in res["reason"]
    assert res["similarity"] < 0.50


def test_lv04_contrast_exact_match_and_minor_wording():
    """대조군 3: 완전 일치(EXACT_MATCH) 및 단순 자구·어미 차이(MINOR_WORDING)."""
    official = "불법행위로 인한 손해배상청구권의 단기소멸시효 기산점은 피해자나 그 법정대리인이 손해 및 가해자를 안 날이다."

    # 1. 완전 일치
    res_exact = categorize_quote_diff(official, official, has_full_text=True)
    assert res_exact["status"] == "EXACT_MATCH"
    assert res_exact["similarity"] >= 0.995

    # 2. 띄어쓰기 차이만 있는 경우 -> EXACT_MATCH
    spaced = "불법행위로  인한 손해배상청구권의  단기소멸시효 기산점은 피해자나 그 법정대리인이 손해 및 가해자를 안 날이다."
    res_spaced = categorize_quote_diff(spaced, official, has_full_text=True)
    assert res_spaced["status"] == "EXACT_MATCH"
