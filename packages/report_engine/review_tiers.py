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


def tier3_review_item_entries(doc: Any, *, limit: int = 0) -> list[list[str]]:
    """인용 표(ai_hallucination_table)에 포함되지 않은 3단 검토 항목(계산 오류·무리한 법리 주장 등)을 보고서 4열 형식으로 변환한다."""
    from packages.common.display_text import readable

    existing_table = getattr(doc, "ai_hallucination_table", None) or []
    existing_keys = {
        (str(r.get("claim_text") or "").strip(), str(r.get("cited_authority") or "").strip())
        for r in existing_table if isinstance(r, dict)
    }
    existing_cids = {
        str(r.get("citation_id"))
        for r in existing_table if isinstance(r, dict) and r.get("citation_id")
    }

    entries: list[list[str]] = []
    filename = str(getattr(doc, "filename", "") or "").strip()
    for raw_item in getattr(doc, "review_items", None) or []:
        item = raw_item if isinstance(raw_item, dict) else (raw_item.to_dict() if hasattr(raw_item, "to_dict") else None)
        if not item:
            continue
        kind = str(item.get("kind") or "")
        if kind in ("CITATION", "CLAIM", "UNVERIFIED_SCOPE", "PROCESSING_QUALITY") or item.get("citation_id"):
            continue
        if item.get("citation_id") and str(item.get("citation_id")) in existing_cids:
            continue
        if classify_row_tier(item) != 3:
            continue

        claim = str(item.get("claim_text") or "").strip()
        authority = str(item.get("cited_authority") or "").strip()
        if (claim, authority) in existing_keys:
            continue

        loc = item.get("location") or {}
        if isinstance(loc, dict):
            loc_disp = str(loc.get("display") or (f"{loc['page']}쪽" if loc.get("page") is not None else "")).strip()
        else:
            loc_disp = str(loc).strip()
        cell_loc = f"{filename} {loc_disp}".strip() or filename or "-"

        claim_shown = claim[:limit] if limit and len(claim) > limit else claim
        cell_claim = readable(claim_shown + (f"\n({authority})" if authority else ""))

        verdict = readable(str(item.get("verdict_label") or "검토 필요").strip())
        basis_parts = [f"[평가] {verdict}"]
        basis_note = readable(str(item.get("ai_generation_basis") or "").strip())
        if basis_note and basis_note != verdict:
            basis_parts.append(basis_note)
        review_body = readable(
            str((item.get("reasoning_sections") or {}).get("review") or item.get("legal_reasoning") or "").strip()
        )
        if review_body and review_body != verdict and review_body != basis_note and review_body != cell_claim:
            if limit and len(review_body) > limit:
                review_body = review_body[:limit]
            basis_parts.append(review_body)
        sources = [
            readable(str(s).strip())
            for s in (item.get("evidence_sources") or [])
            if s and "구속력 없음" not in str(s)
        ]
        if sources:
            basis_parts.append("근거: " + " · ".join(sources[:3]))
        cell_basis = "\n".join(basis_parts)

        verif = readable(str(item.get("counteraction") or "").strip())
        if verif:
            cell_review = f"확인 필요 사항: {verif}"
        else:
            cell_review = "서면 주장 및 관련 계산·사실관계 근거를 원문·증빙과 대조하여 확인해야 합니다."

        entries.append([cell_loc, cell_claim, cell_basis, cell_review])
    return entries
