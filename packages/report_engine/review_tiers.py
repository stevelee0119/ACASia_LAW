# -*- coding: utf-8 -*-
"""TK-88: 3단 체계(AI 작성·보안 / 인용 오류·미확인 / 법률적 무리 주장) 분류 유틸리티

설계 메모 docs/handoff/requests/94_tk88_three_tier_review_structure_design.md 기준
분류 우선순위:
1순위: 결과 유형 (FindingType / rule_id)
2순위: 공식 조회 및 출처 상태 (basis / error_category / official_status)
3순위: 법리 검토 판정 문장 (validity_verdict)
"""
from typing import Any, Dict

# 3단 체계 표준 소제목 명칭
TIER1_HEADING = "1. AI 작성·보안 진단"
TIER2_HEADING = "2. 판례·법령·주요참고문헌 인용 오류·미확인 검토 (AI 작성 여부 판단과 별개)"
TIER3_HEADING = "3. 법률적으로 무리한 주장"


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

    # 1순위: 결과 유형 (FindingType / rule_id)
    if "REFERENCE_CONTRADICTION" in rule_id or "참고자료 모순" in verdict:
        return 3
    if "AI_HALLUCINATED_CONTENT" in finding_type or "AI_HALLUCINATED_CONTENT" in rule_id:
        return 3
    if "LEGAL_ARGUMENT_INVALID" in finding_type or "LEGAL_ARGUMENT_INVALID" in rule_id:
        return 3
    if "FACT_MISMATCH" in finding_type or "FACT_MISMATCH" in rule_id:
        return 3
    if "CASE_HOLDING_DISTORTION" in finding_type or "CASE_HOLDING_DISTORTION" in rule_id:
        return 2  # 인용문 왜곡은 객관적 인용 대조이므로 2단 배치 (3단과 상호 참조)
    if "TEMPORAL_LAW_MISMATCH" in finding_type or "TEMPORAL_LAW_MISMATCH" in rule_id:
        return 2
    if any(k in finding_type for k in ("CASE_NOT_FOUND", "LAW_NOT_FOUND", "CASE_METADATA_MISMATCH", "CITATION_TEXT_MISMATCH")):
        return 2

    # 2순위: 공식 조회 및 출처 상태 (basis / error_category)
    if "FABRICATION_SUSPECTED" in basis or error_category == "LEGAL_CITATION_ERROR":
        return 2
    if "UNCONFIRMED" in basis or official_status == "OFFICIAL_NOT_FOUND":
        return 2

    # 3순위: 법리 검토 판정 문장 (validity_verdict)
    # 표 1 명시 항목:
    # 1번 행: "근거 결여 (성립 불가한 사건번호)" -> 2단
    if "성립 불가한 사건번호" in verdict or "성립 불가" in verdict:
        return 2
    # 2번 행: "공식 DB 미확인 (원문 확인 필요)" -> 2단
    if "공식 DB 미확인" in verdict or "원문 확인 필요" in verdict:
        return 2
    # 3번 행: "인용문 변형 (원문과 어절 차이)" 또는 "인용 내용 불일치 (원문 대조 필요)" -> 2단
    if "인용문 변형" in verdict or "인용 내용 불일치" in verdict:
        return 2
    # 6번 행: "판례 취지 왜곡 (판시사항과 상반 / 부당)" -> 3단
    if "취지 왜곡" in verdict or "부당" in verdict:
        return 3
    # 9번 행: "사실관계 상이" -> 3단
    if "사실관계 상이" in verdict:
        return 3

    # 기본값: 인용 정보가 있으면 2단, 그 외는 3단
    if cited_authority or row.get("citation_id") or row.get("kind") == "CITATION":
        return 2
    return 3
