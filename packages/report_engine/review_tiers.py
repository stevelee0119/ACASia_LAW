# -*- coding: utf-8 -*-
"""TK-88: 3단 체계(AI 작성·보안 / 인용 오류·미확인 / 법률적 무리 주장) 분류 유틸리티

설계 메모 docs/handoff/requests/94_tk88_three_tier_review_structure_design.md 기준
분류 원칙:
1. 인용 행(CITATION)은 출처 상태(basis, official_status) 및 판정 문장(validity_verdict)을 결과 유형보다 먼저 본다.
   - 성립 불가 사건번호(1번), 공식 DB 미확인(2번), 인용문 변형(3번)은 결과 유형(LEGAL_ARGUMENT_INVALID)과 무관하게 2단(출처 검토)에 배치.
   - 판례 취지 왜곡(6번), 사실관계 상이(7번) 등 명시적 부당 변론 항목만 3단(무리한 주장)에 배치.
2. 참고자료 모순(8번, RAG.REFERENCE_CONTRADICTION), AI 환각(9번, AI_HALLUCINATED_CONTENT)은 3단에 배치.
3. 공식 원문 일치(10번)는 2단에 배치.
"""
from typing import Any, Dict

# 3단 체계 표준 소제목 명칭
TIER1_HEADING = "1. AI 작성·보안 진단"
TIER2_HEADING = "2. 판례·법령·주요참고문헌 인용 오류·미확인 검토 (AI 작성 여부 판단과 별개)"
TIER3_HEADING = "3. 법률적으로 무리한 주장"

# 표준 판정 문장 상수 (argument_validity_verifier.py 일치)
VERDICT_INVALID_CASE_NUMBER = "근거 결여 (성립 불가한 사건번호)"
VERDICT_OFFICIAL_NOT_FOUND = "공식 DB 미확인 (원문 확인 필요)"
VERDICT_QUOTE_MODIFIED = "인용문 변형 (원문과 어절 차이)"
VERDICT_CONTENT_MISMATCH = "인용 내용 불일치 (원문 대조 필요)"
VERDICT_HOLDING_DISTORTION = "판례 취지 왜곡 (판시사항과 상반 / 부당)"
VERDICT_FACT_DISTINGUISHABLE = "적용 차이 (사실관계 상이 / 전문가 검토 필요)"
VERDICT_OFFICIAL_CONFIRMED = "공식 원문 일치 (사건 적용성 직접 검토 필요)"

# 2단 배정 표준 판정 문장 집합
TIER2_VERDICTS = {
    VERDICT_INVALID_CASE_NUMBER,
    VERDICT_OFFICIAL_NOT_FOUND,
    VERDICT_QUOTE_MODIFIED,
    VERDICT_CONTENT_MISMATCH,
    VERDICT_OFFICIAL_CONFIRMED,
}

# 3단 배정 표준 판정 문장 집합
TIER3_VERDICTS = {
    VERDICT_HOLDING_DISTORTION,
    VERDICT_FACT_DISTINGUISHABLE,
}


def classify_row_tier(row: Dict[str, Any]) -> int:
    """단일 hallucination_table 또는 review_item 행을 2단(출처/인용) 또는 3단(무리한 주장)으로 분류한다.

    Returns:
        2: 판례·법령·주요참고문헌 인용 오류·미확인 검토 (AI 작성 여부 판단과 별개)
        3: 법률적으로 무리한 주장
    """
    rule_id = str(row.get("rule_id") or "")
    finding_type = str(row.get("finding_type") or row.get("type") or "")
    basis = str(row.get("basis") or "")
    error_category = str(row.get("error_category") or "")
    official_status = str(row.get("official_status") or "")
    verdict = str(row.get("validity_verdict") or row.get("verdict_label") or "")
    cited_authority = str(row.get("cited_authority") or "")
    is_citation = bool(
        cited_authority
        or row.get("citation_id")
        or row.get("kind") == "CITATION"
        or "CITATION" in str(row.get("item_id") or "")
    )

    # 1. 고유 3단 전용 규칙 (출처 여부 불문 3단)
    # 8번 행: 참고자료 모순 (TK-70)
    if "REFERENCE_CONTRADICTION" in rule_id or "참고자료 모순" in verdict:
        return 3
    # 9번 행: 가짜 판례·조문 기반 법률 주장 (AI_HALLUCINATED_CONTENT)
    if "AI_HALLUCINATED_CONTENT" in finding_type or "AI_HALLUCINATED_CONTENT" in rule_id:
        return 3

    # 2. 인용 행(CITATION) 처리: basis와 판정 문장을 결과 유형보다 먼저 본다 (요구 2)
    if is_citation:
        # [표 1 3단 예외 항목 선제 판정]
        # 6번 행: 판례 취지 왜곡 (부당 원용)
        if verdict == VERDICT_HOLDING_DISTORTION or ("취지 왜곡" in verdict and "상반" in verdict):
            return 3
        # 7번 행: 적용 차이 (사실관계 상이)
        if (
            verdict == VERDICT_FACT_DISTINGUISHABLE
            or error_category == "APPLICATION_DIFFERENCE"
            or basis == "DISTINGUISHABLE"
            or "사실관계 상이" in verdict
        ):
            return 3

        # [표 1 2단 출처 오류/미확인 항목]
        # 1번 행: 성립 불가한 사건번호 (2단 고정)
        if (
            verdict == VERDICT_INVALID_CASE_NUMBER
            or basis == "FABRICATION_SUSPECTED"
            or "성립 불가" in verdict
        ):
            return 2
        # 2번 행: 공식 DB 미확인
        if (
            verdict == VERDICT_OFFICIAL_NOT_FOUND
            or basis == "UNCONFIRMED"
            or official_status in ("OFFICIAL_NOT_FOUND", "UNCONFIRMED")
            or "공식 DB 미확인" in verdict
            or "원문 확인 필요" in verdict
        ):
            return 2
        # 3번 행: 인용문 변형 / 내용 불일치
        if (
            verdict in (VERDICT_QUOTE_MODIFIED, VERDICT_CONTENT_MISMATCH)
            or error_category == "LEGAL_CITATION_ERROR"
            or "인용문 변형" in verdict
            or "인용 내용 불일치" in verdict
        ):
            return 2
        # 4번 행: 객관적 판시사항 왜곡 인용문
        if "CASE_HOLDING_DISTORTION" in finding_type or "CASE_HOLDING_DISTORTION" in rule_id:
            return 2
        # 5번 행: 시적 적용 오류
        if "TEMPORAL_LAW_MISMATCH" in finding_type or "TEMPORAL_LAW_MISMATCH" in rule_id:
            return 2
        # 10번 행: 공식 원문 일치
        if (
            verdict == VERDICT_OFFICIAL_CONFIRMED
            or basis == "OFFICIAL_CONFIRMED"
            or official_status == "OFFICIAL_CONFIRMED"
            or "공식 원문 일치" in verdict
        ):
            return 2
        # 기타 인용 검색 불일치
        if any(k in finding_type for k in ("CASE_NOT_FOUND", "LAW_NOT_FOUND", "CASE_METADATA_MISMATCH", "CITATION_TEXT_MISMATCH")):
            return 2

        # 인용 행의 기본값은 2단 (출처 검증)
        return 2

    # 3. 비인용 행(사실관계 불일치, 일자 모순 등) 처리
    # 사실관계 상이 및 모순 -> 3단
    if "FACT" in str(row.get("kind") or "") or "FACT_MISMATCH" in finding_type or "TIMELINE" in finding_type:
        return 3

    # 기본값: 3단
    return 3
