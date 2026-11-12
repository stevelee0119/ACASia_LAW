"""LV-03: 판례·법령 존재 및 서지 판정의 3단 체계화 (Three-tier authority verification).

3단 체계 및 사건번호 구조 판정:
1. 존재 확인 (VERIFIED): 공식 DB에서 일치 확인
2. 부존재 확인 (CONFIRMED_NONEXISTENT): 전수 수록 attestation이 검증된 출처에서 명시적 부존재가 확인된 경우 (CRITICAL)
3. 확인 불가 (UNCONFIRMED_SOURCE_LIMIT): 출처 한계 또는 미수록 가능성으로 인한 미확인은 가짜 판례(FABRICATION)로 단정하지 않고 '확인 불가'로 명시 (MEDIUM)
4. 오기 의심 (SUSPICIOUS): 성립 불가능한 사건번호(연도, 부호, 번호 구조)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from packages.common.enums import CitationType, Severity, StrEnum, VerificationStatus
from packages.legal_engine.citation_format import code_court_family, court_family
from packages.legal_engine.normalize import split_case_number, SUPREME_COURT_CODES


class LegalVerificationStatus(StrEnum):
    """법률 검증 3단 공용 판정 상태 열거형 (LV-03)."""
    VERIFIED = "VERIFIED"                                   # 확인됨: 공식 원문과 존재·서지·내용 일치
    CONTRADICTED = "CONTRADICTED"                           # 불일치/모순: 원문 또는 확립된 법리와 명백히 충돌
    CONFIRMED_NONEXISTENT = "CONFIRMED_NONEXISTENT"         # 부존재 확인: 전수 수록 attestation이 입증된 출처에서 부존재 확정 (CRITICAL)
    SUSPICIOUS = "SUSPICIOUS"                               # 존재의심/오기: 성립 불가능한 사건번호/조문 표기
    CONTEXT_CAUTION = "CONTEXT_CAUTION"                     # 맥락주의: 판례는 실재하나 취지 왜곡(변경된 판례, 반대의견 오인 등)
    UNCONFIRMED_SOURCE_LIMIT = "UNCONFIRMED_SOURCE_LIMIT"   # 확인 불가: 하급심·약칭 등 출처 미수록 가능성 (가짜 판례 단정 금지)
    SUSPENDED = "SUSPENDED"                                 # 판단/계산 보류: 소제기일/기산점 등 필수 전제 결여
    UNVERIFIED = "UNVERIFIED"                               # 미검증: 검증 미실시


def get_court_tier(citation: Any) -> str:
    """법원 위계 분류: SUPREME (대법원) / CONSTITUTIONAL (헌법재판소) / LOWER (하급법원) / UNKNOWN"""
    court_str = getattr(citation, "court", "") or ""
    cf = court_family(court_str)
    if cf == "대법원":
        return "SUPREME"
    if cf == "헌법재판소":
        return "CONSTITUTIONAL"

    case_no = getattr(citation, "canonical_case_number", None) or getattr(citation, "case_number", None) or ""
    parts = split_case_number(case_no)
    if parts:
        code = parts[1]
        if code.startswith("헌"):
            return "CONSTITUTIONAL"
        ccf = code_court_family(code)
        if ccf == "대법원" or code in SUPREME_COURT_CODES:
            return "SUPREME"
        if ccf == "헌법재판소":
            return "CONSTITUTIONAL"
        if ccf == "하급법원":
            return "LOWER"

    if cf == "하급법원":
        return "LOWER"
    return "UNKNOWN"


def make_authority_id(citation: Any) -> str:
    """공식/정규 기관 ID 생성 (KR_SC_{사건번호}, KR_CC_{사건번호}, KR_LOWER_{사건번호}, KR_ACT_{법령명}_{조문})."""
    c_type = getattr(citation, "type", None)
    case_no = getattr(citation, "canonical_case_number", None) or getattr(citation, "case_number", None) or ""

    if c_type in (CitationType.CASE, CitationType.CONSTITUTIONAL) or case_no:
        clean_case = re.sub(r"\s+", "", case_no)
        tier = get_court_tier(citation)
        if tier == "SUPREME":
            return f"KR_SC_{clean_case}" if clean_case else "KR_SC_UNKNOWN"
        elif tier == "CONSTITUTIONAL":
            return f"KR_CC_{clean_case}" if clean_case else "KR_CC_UNKNOWN"
        elif tier == "LOWER":
            court = getattr(citation, "court", "") or ""
            clean_court = re.sub(r"[^\w가-힣]", "", court)
            court_part = f"_{clean_court}" if clean_court else ""
            return f"KR_LOWER{court_part}_{clean_case}" if clean_case else f"KR_LOWER{court_part}_UNKNOWN"
        return f"KR_COURT_{clean_case}" if clean_case else "KR_COURT_UNKNOWN"

    if c_type in (CitationType.STATUTE, CitationType.ADMIN_RULE):
        law_name = getattr(citation, "law_name", "") or ""
        article = getattr(citation, "article", "") or ""
        clean_law = re.sub(r"[^\w가-힣]", "", law_name)
        clean_art = re.sub(r"[^\w가-힣\d]", "", str(article))
        base = f"KR_ACT_{clean_law}"
        return f"{base}_{clean_art}".rstrip("_")

    raw = getattr(citation, "raw_text", "") or "UNKNOWN"
    clean_raw = re.sub(r"[^\w가-힣]", "", raw)[:20]
    return f"KR_AUTH_{clean_raw}"


def is_covered_precedent_scope(citation: Any) -> bool:
    """공식 공개 DB(국가법령정보/종합법률정보)가 체계적 전수 수록을 보장하는 범위인지 여부.

    현재 어댑터 수준에서 전수 수록 여부(exhaustive coverage)에 대한
    서버측 검증 증명(attestation) 시스템이 부재하므로,
    클라이언트가 주입한 coverage_attestation 속성을 신뢰하지 않고
    일관되게 False(미확인)를 반환한다 (LV-03-R4).
    """
    return False


# 대법원 전원합의체 판결은 법원도서관 분류상 A급(전원합의체 및 대법원판례집 수록 대상)으로 판례공보에 실리고
# 종합법률정보에 등록된다(법원도서관 조사심의관, '판례공보와 종합법률정보', 2017. 8. 4.). 공보 게재(월 2회)·DB 등록·
# 국가법령정보 연계 지연을 넉넉히 두고, 그보다 오래된 전원합의체 판결을 찾지 못하면 '부존재 의심'(HIGH)으로 올린다
# (TK-154). 국가법령정보 판례 DB가 공보 판결 전부를 담는다는 공식 증명은 없으므로 부존재 확정(CRITICAL)은 아니다.
ENBANC_PUBLICATION_LAG_DAYS = 180


def enbanc_absence_suspected(citation: Any, current_date: Optional[str]) -> bool:
    """서면이 '전원합의체'라고 밝힌 대법원 판결이고, 선고일이 기준일보다 공개 지연 기간 이상 앞서는가."""
    from datetime import date, timedelta
    from packages.source_adapters.legal_history import legal_date

    if get_court_tier(citation) != "SUPREME":
        return False
    label = (getattr(citation, "case_kind", "") or "") + " " + (getattr(citation, "raw_text", "") or "")
    if not re.search(r"전원\s*합의체", label):
        return False
    decided, current = legal_date(getattr(citation, "decision_date", None)), legal_date(current_date)
    if not decided or not current:
        return False
    return date.fromisoformat(decided) <= date.fromisoformat(current) - timedelta(days=ENBANC_PUBLICATION_LAG_DAYS)


def classify_authority_status(
    citation: Any,
    official_record: Optional[Dict[str, Any]],
    format_valid: bool = True,
) -> Dict[str, Any]:
    """판례 또는 법령의 공식 확인 여부, 서지 형식 타당성, 법원 위계를 종합하여 3단 판정 정보를 도출한다."""
    auth_id = make_authority_id(citation)
    tier = get_court_tier(citation)
    is_covered = is_covered_precedent_scope(citation)

    # 1. 공식 원문 존재 확인 (VERIFIED)
    if official_record:
        return {
            "status": LegalVerificationStatus.VERIFIED,
            "tier": tier,
            "authority_id": auth_id,
            "severity": Severity.INFO,
            "title": f"공식 원문 일치 확인: {getattr(citation, 'raw_text', '')}",
            "reason": "공식 DB에서 일치하는 기록을 확인했습니다.",
            "is_covered": is_covered,
        }

    # 2. 성립 불가능한 서지 형식 / 오기 의심 (SUSPICIOUS)
    if not format_valid:
        return {
            "status": LegalVerificationStatus.SUSPICIOUS,
            "tier": tier,
            "authority_id": auth_id,
            "severity": Severity.HIGH,
            "title": f"성립할 수 없는 사건번호 형식(오기 의심): {getattr(citation, 'raw_text', '')}",
            "reason": "사건번호의 접수연도 또는 사건부호가 형식상 실재할 수 없어 오기(誤記)로 판단됩니다.",
            "is_covered": is_covered,
        }

    # 3. 공식 DB 미발견 (출처 한계 - 단순 미발견을 가짜 판례로 단정 금지)
    title = f"조회 범위 내에서 찾지 못한 판례 인용: {getattr(citation, 'raw_text', '')}"
    reason = (
        "미공개 판결이거나 DB 수록 범위 밖일 수 있으므로 '존재하지 않는 판례'라고 단정하지 않습니다. "
        "상대방에게 판결문 사본 제출을 요청하거나 다른 공식 경로를 통해 확인해야 합니다."
    )
    return {
        "status": LegalVerificationStatus.UNCONFIRMED_SOURCE_LIMIT,
        "tier": tier,
        "authority_id": auth_id,
        "severity": Severity.MEDIUM,
        "title": title,
        "reason": reason,
        "is_covered": False,
    }
