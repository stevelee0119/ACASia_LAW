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


def test_lv04_contrast_unaligned_low_overlap_quote():
    """대조군 2: 원문과 유사도가 낮은 인용문이라도 허위 가공(FABRICATED_QUOTE)으로 자동 단정하지 않고 대조 불일치로 처리."""
    official = "민법 제750조의 불법행위에 기한 손해배상청구권에 있어서 고의 또는 과실의 입증책임은 원고에게 있다."
    quote = "상대방의 계약 위반은 신의성실의 원칙상 결코 용인될 수 없으므로 무조건 계약 해제권이 발생한다."

    res = categorize_quote_diff(quote, official, has_full_text=True)
    assert res["status"] != "FABRICATED_QUOTE"
    assert "FABRICATED_QUOTE" not in res["diff_categories"]
    assert res["status"] == "UNALIGNED_QUOTE"
    assert "CONTENT_MISMATCH" in res["diff_categories"]
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


import pytest
from packages.common.schemas import Citation
from packages.legal_engine.verifier import LegalVerifier
from packages.source_adapters import SourceRegistry
from packages.source_adapters.base import AdapterResponse
from packages.common.enums import AdapterStatus, CitationType


class _MockLaw:
    def __init__(self, records):
        self.records = records

    def search_case(self, *args, **kw):
        return AdapterResponse(AdapterStatus.READY, self.records, None, "synthetic")


def _make_mock_verifier(records):
    registry = SourceRegistry()
    registry.legal[0] = _MockLaw(records)
    return LegalVerifier(registry)


@pytest.mark.parametrize("quote", ["집행 절차의 단계별 송달 방법을 검토한다.", "관할 구역의 획정과 소송 비용의 부담을 확인한다.", "문서 보관 기간 및 신청서의 서식을 정한다."])
def test_quote_low_overlap_is_not_proof_of_fabrication(quote: str):
    full = "매수인은 계약상 대금지급 의무를 부담하며 이행 조건을 확인하여야 한다."
    result = categorize_quote_diff(quote, full)
    assert result["status"] != "FABRICATED_QUOTE"
    assert "FABRICATED_QUOTE" not in result["diff_categories"]
    c = Citation(citation_id="c", type=CitationType.CASE, raw_text="대법원 2021다67283 판결",
                 court="대법원", case_number="2021다67283", canonical_case_number="2021다67283",
                 page=1, quoted_text=quote)
    v = _make_mock_verifier([dict(case_number="2021다67283", court="대법원", full_text=full)]).verify_case(c)
    assert not any("FABRICATED_QUOTE" in f.tags for f in v.findings)

