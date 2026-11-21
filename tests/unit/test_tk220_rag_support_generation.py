"""TK-220 RAG 지지 의견 미생성 해소(RAGC-S3) 일반화 양성/대조군 단위 시험."""
from __future__ import annotations

from packages.rag_engine.review import _contains_flexible, _deterministic_chunk_supports


def test_deterministic_chunk_supports_positives_and_controls() -> None:
    # 양성 3건: 서로 다른 법률·사실 영역에서 모델이 SUPPORTS를 누락한 전달 청크
    claims = [
        {
            "claim_id": "C1",
            "type": "FACT",
            "assertion_mode": "ASSERTED",
            "text": "피고는 2023년 4월 10일 물품대금 3500만원을 지정 계좌로 이체하여 전액 변제하였다.",
        },
        {
            "claim_id": "C2",
            "type": "LEGAL_ARGUMENT",
            "assertion_mode": "ASSERTED",
            "text": "행정처분에 대한 재결서 정본을 송달받은 날부터 90일 이내에 취소소송을 제기하여야 한다.",
        },
        {
            "claim_id": "C3",
            "type": "FACT",
            "assertion_mode": "ASSERTED",
            "text": "감정평가 보고서에 따르면 대상 토지의 기준시점 공시지가는 제곱미터당 120만원으로 산정되었다.",
        },
    ]
    sources = [
        {
            "source_id": "R1",
            "text": "금융거래 내역 확인서: 2023년 4월 10일 물품대금 3500만원이 지정 계좌로 이체되어 전액 변제 완료됨.",
        },
        {
            "source_id": "R2",
            "text": "절차 안내문: 행정심판 재결서 정본을 송달받은 날부터 90일 이내에 관할 행정법원에 취소소송을 제기하여야 한다.",
        },
        {
            "source_id": "R3",
            "text": "토지 감정평가 요약: 대상 토지의 기준시점 공시지가는 제곱미터당 120만원으로 산정되어 있다.",
        },
        # 대조군 1: 무관한 참고자료 (RAGC-N1/N2)
        {
            "source_id": "R4",
            "text": "임대차 계약 해지 통보 절차 및 보증금 반환 지연이자율 안내 사항입니다.",
        },
        # 대조군 2: 부정 극성 반전 (지지 근거로 억지 연결 금지)
        {
            "source_id": "R5",
            "text": "금융거래 내역 확인서: 2023년 4월 10일 물품대금 3500만원이 지정 계좌로 이체되지 않아 변제되지 않았다.",
        },
        # 대조군 3: 이미 SUPPORTS 관찰이 존재하는 source_id는 중복 생성하지 않음
        {
            "source_id": "R6",
            "text": "토지 감정평가 요약: 대상 토지의 기준시점 공시지가는 제곱미터당 120만원으로 산정되어 있다.",
        },
    ]
    existing = [{"source_id": "R6", "relationship": "SUPPORTS", "claim_quote": "a", "source_quote": "b"}]

    supports = _deterministic_chunk_supports(claims, sources, existing)
    supported_sids = {o["source_id"] for o in supports}
    assert supported_sids == {"R1", "R2", "R3"}
    assert all(o["relationship"] == "SUPPORTS" for o in supports)
    by_sid = {o["source_id"]: o for o in supports}
    assert by_sid["R1"]["claim_id"] == "C1"
    assert by_sid["R2"]["claim_id"] == "C2"
    assert by_sid["R3"]["claim_id"] == "C3"


def test_deterministic_chunk_supports_skips_hypothetical_and_quoted_claims() -> None:
    claims = [
        {
            "claim_id": "CH1",
            "type": "FACT",
            "assertion_mode": "HYPOTHETICAL",
            "text": "설령 2023년 4월 10일 물품대금 3500만원이 계좌로 이체되었다고 가정하더라도 효력이 없다.",
        },
        {
            "claim_id": "CH2",
            "type": "FACT",
            "assertion_mode": "QUOTED_OTHER",
            "text": "상대방은 2023년 4월 10일 물품대금 3500만원을 계좌로 이체하였다고 주장한다.",
        },
    ]
    sources = [
        {
            "source_id": "R1",
            "text": "2023년 4월 10일 물품대금 3500만원이 계좌로 이체된 사실이 확인된다.",
        }
    ]
    assert _deterministic_chunk_supports(claims, sources, []) == []


def test_contains_flexible_tolerates_minor_punctuation() -> None:
    haystack = "대법원 2020. 5. 14. 선고 2019다12345 판결(제1부)에 따르면 손해배상 책임이 인정된다."
    needle = "대법원 2020 5 14 선고 2019다12345 판결 제1부에 따르면 손해배상 책임이 인정된다"
    assert _contains_flexible(haystack, needle) is True
    assert _contains_flexible(haystack, "전혀 존재하지 않는 무관한 문장입니다") is False
