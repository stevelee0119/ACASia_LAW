# -*- coding: utf-8 -*-
"""날짜·요일 일치성 및 달력 유효성 검증 엔진 (DATE-WEEKDAY, DATE-INVALID, DAYS).

서면에 기재된 날짜(연·월·일)와 괄호 표기 요일(월~일)의 역법상 일치 여부,
평년 2월 29일이나 30일 등 달력상 존재하지 않는 날짜,
그리고 두 날짜 사이의 일수(경과일) 계산 오류를 검증한다.
"""
from __future__ import annotations

import calendar
import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from packages.common.confidence import score as confidence_score
from packages.common.enums import EvidenceGrade, FindingType, ForensicLevel, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument

ENGINE_NAME = "claim_engine.date_verifier"

# 요일 매핑 (0: 월요일, 6: 일요일)
KOREAN_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
WEEKDAY_MAP = {name: idx for idx, name in enumerate(KOREAN_WEEKDAYS)}

# 날짜 + 요일 병기 패턴: 예) 2026. 3. 20.(목), 2026년 3월 20일(목요일), 2025. 9. 1. 화요일에
# 요일 단어 뒤에 조사(에, 은, 는, 이, 가, 을, 를, 의, 로, 으로, 부터, 까지)가 붙는 서식도 허용
DATE_WEEKDAY_RE = re.compile(
    r"(?P<year>\d{4})[.\s년/-]+(?P<month>\d{1,2})[.\s월/-]+(?P<day>\d{1,2})(?:일)?[\s.]*"
    r"(?:\((?P<weekday>[월화수목금토일])(?:요일)?\)|(?P<weekday_word>[월화수목금토일])요일)"
    r"(?:[에은는이가을를의]|으로|로|부터|까지)?(?![가-힣])"
)

# 일반 날짜 패턴: 예) 2026. 2. 29., 2026년 2월 29일
DATE_GENERAL_RE = re.compile(
    r"(?P<year>\d{4})[.\s년/-]+(?P<month>\d{1,2})[.\s월/-]+(?P<day>\d{1,2})[일]?"
)

# 일수 경과 패턴: 예) "통지일로부터 N일이 지난 YYYY. M. D.", "YYYY. M. D.로부터 N일이 지난 YYYY. M. D."
DAYS_ELAPSED_RE = re.compile(
    r"(?:(?:(?P<from_y>\d{4})[.\s년/-]+(?P<from_m>\d{1,2})[.\s월/-]+(?P<from_d>\d{1,2})[일\s.]*)|(?:해고일|퇴사일|처분일|작성일|통지일))(?:로부터|부터|에서|이후|후)\s*"
    r"(?P<days>\d{1,4})\s*(?:일|日)\s*(?:이\s*지난|경과한|후의?|째\s*되는)?\s*"
    r"(?P<to_y>\d{4})[.\s년/-]+(?P<to_m>\d{1,2})[.\s월/-]+(?P<to_d>\d{1,2})[일\s.]*"
)

# 소제목/목차 번호 패턴 (한국 법률 서면의 일반적인 번호·기호 체계)
# 1. , 가. , (1) , (가) , 1) , [소제목] , 【소제목】 , <소제목> , 제1조 등
HEADING_LINE_RE = re.compile(
    r"^\s*(?:"
    r"(?:[0-9]{1,3}|[가나다라마바사아자차카타파하]|[ㄱ-ㅎ]|[IVXLCDM]+)\s*[\.\)]\s*|"  # 1. , 가. , 1) , I. 등
    r"\((?:[0-9]{1,3}|[가나다라마바사아자차카타파하]|[ㄱ-ㅎ])\)\s*|"                   # (1) , (가) 등 (교대 묶음 누락 수정)
    r"\[[^\]\n]{1,60}\]|"                                                            # [소제목]
    r"【[^】\n]{1,60}】|"                                                            # 【소제목】
    r"<[^>\n]{1,60}>|"                                                               # <소제목>
    r"제\s*[0-9]{1,3}\s*[조항]\s*"                                                   # 제1조 등 ([조항조] 중복 수정)
    r")\s*(?P<title>[^\n]{1,80})"
)

# 정정 서술 배제 표지 (~로 정정한다, ~가 아니라, 오기이다 등)
CORRECTION_EXCLUDE_RE = re.compile(
    r"(?:정정(?:합|한|합니|하|되)|아니라|오기(?:이|입|였)|착오(?:로|에)|바로잡)"
)

# 장래/예정/약정 배제 표지 (~할 예정, ~까지 변제하기로, 이행기 등)
FUTURE_EXCLUDE_RE = re.compile(
    r"(?:예정(?:입|이|으|된)|변제하기로|지급하기로|이행기|약정기한|추후|향후|계획(?:입|이|으)|기한을\s*[0-9가-힣\s.]+로|도래할)"
)

# 판례/법령 인용 배제 표지 (선고, 공포, 시행 등)
AUTHORITY_EXCLUDE_RE = re.compile(
    r"(?:선고|판결|공포|시행|법률|조례|규칙|대법원|헌법재판소)"
)

# 별개 주체 대립 표지 (원고와 피고가 각각 다른 절에서 분리된 행위를 할 때)
DIFFERENT_SUBJECTS_RE = re.compile(
    r"(?:원고(?:는|가|의)|신청인(?:은|이|의))\s*.*?(?:피고(?:는|가|의)|피신청인(?:은|이|의))|"
    r"(?:피고(?:는|가|의)|피신청인(?:은|이|의))\s*.*?(?:원고(?:는|가|의)|신청인(?:은|이|의))"
)

# 앞선 사건을 대상·근거·첨부로 삼는 정상 회고 서술 배제 표지
# (나중 서면이 앞선 처분을 다툼, '~에 따라' 참조, 나중 청구의 대상이 앞선 결정, 앞선 회신 첨부, '~를 거쳐' 회고 등)
RETROSPECTIVE_OBJECT_EXCLUDE_RE = re.compile(
    r"(?:취소를\s*구|무효(?:확인)?를\s*구|위법(?:성|함)?을\s*다투|다투(?:고자|며|는|었)|"
    r"대상으로\s*(?:하|삼|한)|별지로\s*첨부|첨부(?:하여|하였|했|함)|"
    r"거쳐\s*(?:제기|청구|신청|소송)|에\s*따라\s*(?:제출|청구|신청|첨부))"
)

# 재입사·별개 기간·선행 계약 예외 표지
SEPARATE_PERIOD_EXCLUDE_RE = re.compile(
    r"(?:재입사|별개(?:의)?\s*(?:기간|근로|계약)|이전\s*(?:근로)?계약과\s*별도)"
)

# 한국어 고유어 수관형사 매핑 (민법 제157조·제160조 기간 산정용)
KOREAN_NUMERAL_MAP: Dict[str, int] = {
    "한": 1, "두": 2, "세": 3, "석": 3, "네": 4, "넉": 4,
    "다섯": 5, "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9,
    "열": 10, "열한": 11, "열두": 12,
}

# 구조적 패턴용 날짜 부분 정규식
_DATE_PAT = r"(?:19|20)\d{2}\s*(?:[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2}\s*\.?|년\s*\d{1,2}\s*월\s*\d{1,2}\s*일)"

# 규칙 1-A1: 동일 주체의 개시일(입사일 등)–종료일(최종 퇴사일 등) 명사구 역전
SAME_SUBJECT_LIFECYCLE_RE = re.compile(
    rf"(?P<start_label>입사일|근무\s*시작일|재직\s*시작일|계약\s*체결일|임대차\s*개시일)[은는이가을를]\s*"
    rf"(?P<d1>{_DATE_PAT})\s*(?:로\s*(?:적었|기재되었|정하였)[가-힣\s.,]*?|이고|이며|이나|인데|,)\s*"
    rf"(?:(?:같은|동일|위|그)\s*[가-힣]{{1,6}}의\s*)?"
    rf"(?P<end_label>(?:최종\s*)?(?:퇴사일|퇴직일|근무\s*종료일|해고일|계약\s*종료일|계약\s*해지일))[은는이가을를]\s*"
    rf"(?P<d2>{_DATE_PAT})"
)

# 규칙 1-A2: 동일 주체·근로관계의 개시일(입사일) 후 일정 기간(N개월/달/년/일) 근무 뒤 사직·퇴사 일자 역전
LIFECYCLE_DURATION_INVERSION_RE = re.compile(
    rf"(?P<start_label>입사일|근무\s*시작일|재직\s*시작일|계약\s*체결일)[은는이가을를]\s*(?P<d1>{_DATE_PAT})"
    rf"[^.!?]{{0,25}}?[.!?]?\s*(?:[가-힣\s]{{0,15}}?)?"
    rf"(?P<n>\d{{1,3}}|한|두|세|석|네|넉|다섯|여섯|일곱|여덟|아홉|열|열한|열두)\s*"
    rf"(?P<unit>개월|달|년|일)\s*(?:간|동안)?\s*(?:근무|재직|복무|사용|거주)한\s*(?:뒤|후|다음)"
    rf"[^.!?]{{0,40}}?(?:사직|퇴사|퇴직|해지|종료)[^.!?]{{0,25}}?"
    rf"(?:발송일|제출일|통지일|일자|날)[은는이가]\s*(?P<d2>{_DATE_PAT})"
)

# 규칙 1-B1: 선행 신청·청구를 직접 대상으로 삼은('~에 대한') 후행 처분·결정의 발령일 역전
TARGET_BOUND_DISPOSITION_RE = re.compile(
    rf"(?:(?P<cause_noun>(?:최초\s*|첫\s*)?[가-힣]{{0,8}}?(?:신청|청구|접수))\s*(?:일[은는이가]?\s*)?(?P<d1>{_DATE_PAT})|"
    rf"(?:최초\s*|첫\s*)?(?P<d1_alt>{_DATE_PAT})\s*(?:자\s*)?(?P<cause_noun_alt>[가-힣]{{0,8}}?(?:신청|청구|접수)))\s*"
    rf"에\s*대한\s*"
    rf"(?P<effect_noun>[가-힣\s]{{0,12}}?(?:거부\s*처분|불승인\s*처분|불허가\s*처분|처분|기각\s*결정|각하\s*결정|결정|승인\s*처분|인가\s*처분))[은는이가]\s*"
    rf"(?P<d2>{_DATE_PAT})\s*에\s*(?:발령|통지|고지|송달|내려|이루어)"
)

# 규칙 1-B2: 선행 행위(신청·계약·청구) D1 후 지시어('그/위/해당 <동일명사>')로 결합된 후행 처분·해제 D2 역전
ANAPHORIC_TARGET_INVERSION_RE = re.compile(
    rf"(?P<d1>{_DATE_PAT})\s*[에\s]*[가-힣\s]{{0,15}}?(?P<noun>신청|청구|계약|접수)"
    rf"(?:을\s*하|를\s*하|하였|했|을?\s*체결하|을?\s*체결했|을?\s*제출하|을?\s*제출했)[^.!?]{{0,30}}?"
    rf"(?:그|위|해당|동)\s*(?P=noun)\s*(?:에\s*대한|에\s*관한|의)\s*"
    rf"(?P<effect_noun>[가-힣\s]{{0,12}}?(?:거부\s*처분|불승인\s*처분|처분|기각\s*결정|결정|해제\s*통지|해지\s*통지|승인|인가|회신))"
    rf"[은는이가을를]?\s*(?P<d2>{_DATE_PAT})\s*[에\s]*(?:발령|통지|고지|송달|발송|수신|도달|내려)"
)

# 규칙 2: 동일 행위 기간(D1부터 D2까지) 종료('끝난 뒤') 후 최초 문서 작성·산정일(D3) 역전
PERIOD_END_WRITE_INVERSION_RE = re.compile(
    rf"(?P<act>[가-힣]{{2,6}})\s*기간[은는이가]?\s*(?P<d1>{_DATE_PAT})\s*(?:부터|~|∼)\s*(?P<d2>{_DATE_PAT})\s*까지"
    rf"[^.!?]{{0,20}}?(?:그\s*|위\s*)?(?P=act)[이가은는]?\s*(?:끝난|종료된|마친|완료된)\s*(?:뒤|후|다음)"
    rf"[^.!?]{{0,35}}?(?:처음|최초로?)?\s*[가-힣\s]{{1,15}}?(?:처음\s*|최초로?\s*)?(?:작성|발급|발행|산정)한\s*(?:날|일자)[은는이가]\s*(?P<d3>{_DATE_PAT})"
)

# 규칙 3: 동일 행위 명사 결합 상대 일자('다음 날/이튿날/N일 뒤') 역산 모순 (민법 제157조·제160조)
RELATIVE_NEXT_DAY_INVERSION_RE = re.compile(
    rf"(?P<d1>{_DATE_PAT})\s*[에\s]*(?:처음\s*|최초로?\s*)?(?P<act>[가-힣]{{2,6}})"
    rf"(?:하였|했|하고|했고|하였으며|한\s*뒤|한\s*후|되었|됐),?\s*"
    rf"(?:(?:그\s*|위\s*)?(?P=act)\s*(?:한\s*)?|그\s*)"
    rf"(?:(?P<next_day>다음\s*날|이튿날|익일)|"
    rf"(?P<n>\d{{1,3}}|한|두|세|석|네|넉|다섯|여섯|일곱|여덟|아홉|열)\s*(?P<unit>일|개월|달|년)\s*(?:뒤|후|경과\s*후|지난\s*뒤))인\s*"
    rf"(?P<d2>{_DATE_PAT})"
)

# 규칙 4-A: 동일 일자 내 지시어('그 <명사>보다 앞선') 결합 상대 시각(HH:MM) 역전
SAME_DAY_EARLIER_TIME_INVERSION_RE = re.compile(
    rf"(?P<act>[가-힣]{{2,8}})\s*(?:시각|시간)[은는이가]\s*(?P<d1>{_DATE_PAT})\s*(?P<t1>\d{{1,2}}:\d{{2}})\s*"
    rf"(?:이고|이며|,)\s*(?:그|위|해당)\s*(?P=act)보다\s*"
    rf"(?:(?P<offset>\d{{1,3}})\s*(?P<unit>분|시간)\s*)?"
    rf"(?P<rel>앞선|먼저\s*한|먼저\s*이루어진|이른)\s*[가-힣\s]{{1,15}}?[은는이가]\s*"
    rf"(?:같은\s*날|당일)\s*(?P<t2>\d{{1,2}}:\d{{2}})"
)

# 규칙 4-B: 동일 목적물('그 <목적물>')의 최초 회수·확보 시각(T1) vs 같은 날 이미 전달·인계된 시각(T2) 역전
SAME_OBJECT_FIRST_ACQUIRE_TIME_INVERSION_RE = re.compile(
    rf"(?P<d1>{_DATE_PAT})\s*(?P<t1>\d{{1,2}}:\d{{2}})\s*에\s*(?P<obj>[가-힣]{{2,10}})[을를]\s*"
    rf"(?:처음|최초로?)\s*(?:회수|확보|수령|입수|인수|작성)[가-힣\s.!?]{{1,35}}?"
    rf"(?:그|위|해당)\s*(?P<obj2>[가-힣]{{2,10}})[이가은는]\s*(?:같은\s*날|당일)\s*"
    rf"(?P<t2>\d{{1,2}}:\d{{2}})\s*에\s*(?:이미|벌써)\s*[가-힣\s]{{0,18}}?(?:전달|인계|교부|제출|반출|발송)되"
)



def _detect_heading(line: str) -> Optional[str]:
    """한 줄이 소제목/목차인지 검사하여 정리된 소제목 문자열을 반환한다."""
    line_s = line.strip()
    if not line_s or len(line_s) > 80:
        return None
    m = HEADING_LINE_RE.match(line_s)
    if m:
        return line_s
    return None


def _find_effective_heading(text: str, match_start: int, block_heading: Optional[str]) -> Optional[str]:
    """매칭 위치 이전의 텍스트 또는 블록/문서 흐름상 유효한 소제목을 반환한다."""
    prefix_text = text[:match_start]
    lines = prefix_text.splitlines()
    for line in reversed(lines):
        h = _detect_heading(line)
        if h:
            return h
    return block_heading


def _parse_valid_date(year: int, month: int, day: int) -> Optional[datetime.date]:
    """유효한 날짜인지 검사하고 date 객체를 반환한다. 유효하지 않으면 None."""
    try:
        return datetime.date(year, month, day)
    except (ValueError, OverflowError):
        return None


def _parse_date_str(text: str) -> Optional[datetime.date]:
    """날짜 문자열(YYYY. M. D., YYYY-MM-DD, YYYY년 M월 D일 등)에서 date 객체를 추출한다."""
    nums = [int(x) for x in re.findall(r"\d+", text)[:3]]
    if len(nums) != 3:
        return None
    return _parse_valid_date(nums[0], nums[1], nums[2])


def _parse_minutes(hhmm: str) -> Optional[int]:
    """HH:MM 문자열을 자정 기준 분(0~1440)으로 변환한다."""
    parts = hhmm.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 24 and 0 <= m < 60:
            return h * 60 + m
    except ValueError:
        pass
    return None


def _parse_numeral(val: str) -> Optional[int]:
    """숫자 또는 한국어 고유어 수관형사('한', '두', '세' 등)를 정수로 변환한다."""
    v = val.strip()
    if v.isdigit():
        return int(v)
    return KOREAN_NUMERAL_MAP.get(v)


def _add_civil_period(start: datetime.date, n: int, unit: str, *, inclusive: bool = False) -> datetime.date:
    """민법 제157조(초일 불산입 원칙)·제159조·제160조(역에 의한 계산, 말일 보정)에 따른 기간 만료일 산출.

    - 일 단위: 초일 불산입 시 start + n일, 초일 산입(오전 0시 시작 등 예외) 시 start + max(0, n - 1)일.
    - 월/달/개월·년 단위: 역에 의하여 계산하되 마지막 달에 해당 일이 없으면 그 달의 말일로 하며(민법 제160조 제3항),
      초일 불산입 시 전일(해당일)에 만료하고, 초일 산입 시 하루 앞선 날을 최소 만료 가능일로 반환한다.
    """
    if unit == "일":
        offset = max(0, n - 1) if inclusive else n
        return start + datetime.timedelta(days=offset)
    months = n * 12 if unit == "년" else n
    y, m = divmod(start.month - 1 + months, 12)
    year, month = start.year + y, m + 1
    last_day = calendar.monthrange(year, month)[1]
    expiry_excl = datetime.date(year, month, min(start.day, last_day))
    return expiry_excl - datetime.timedelta(days=1) if inclusive else expiry_excl


def _same_object_noun(left: str, right: str) -> bool:
    """두 목적물 명사가 동일하거나 핵심 접미 명사(2글자 이상, 예: '저장장치'와 '장치')를 공유하는지 판정한다."""
    a, b = re.sub(r"\s+", "", left), re.sub(r"\s+", "", right)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(b) >= 2 and a.endswith(b):
        return True
    if len(a) >= 2 and b.endswith(a):
        return True
    return False


def verify_dates_in_document(doc: NormalizedDocument) -> List[Finding]:
    """문서 내 모든 텍스트 블록에서 날짜 유효성, 요일 정합성, 경과일수를 검증한다."""
    findings: List[Finding] = []

    # 서면의 기준 해고일/처분일 등 추출 시도 (문맥용)
    context_incident_date: Optional[datetime.date] = None
    for block in doc.body_blocks():
        t = block.text
        m_inc = re.search(r"(?:해고일|처분일|통지일)은?\s*(?:은|는|이|가)?\s*(\d{4})[.\s년/-]+(\d{1,2})[.\s월/-]+(\d{1,2})", t)
        if m_inc:
            y, m, d = int(m_inc.group(1)), int(m_inc.group(2)), int(m_inc.group(3))
            d_obj = _parse_valid_date(y, m, d)
            if d_obj:
                context_incident_date = d_obj
                break

    # 문서 흐름상 직전 소제목/목차 추적
    current_heading: Optional[str] = None

    for block in doc.body_blocks():
        text = block.text
        if not text:
            continue

        # 블록의 첫 번째 줄이 소제목인지 검사하여 현재 활성 소제목을 갱신한다
        first_line = text.splitlines()[0] if text.splitlines() else ""
        first_heading = _detect_heading(first_line)
        if first_heading:
            current_heading = first_heading

        # 1. 날짜 + 요일 불일치 검증 (DATE-WEEKDAY)
        for m in DATE_WEEKDAY_RE.finditer(text):
            y = int(m.group("year"))
            month = int(m.group("month"))
            day = int(m.group("day"))
            weekday_str = m.group("weekday") or m.group("weekday_word")

            d_obj = _parse_valid_date(y, month, day)
            if d_obj is not None:
                actual_weekday_idx = d_obj.weekday()
                actual_weekday_str = KOREAN_WEEKDAYS[actual_weekday_idx]

                if weekday_str != actual_weekday_str:
                    matched_str = m.group(0)
                    eff_h = _find_effective_heading(text, m.start(), current_heading)

                    features = {
                        "deterministic_rule": True,
                        "stated_date": f"{y}. {month}. {day}.",
                        "stated_weekday": weekday_str,
                        "actual_weekday": actual_weekday_str,
                        "rule_id": "claim_engine.date_verifier:DATE_WEEKDAY_MISMATCH",
                    }
                    if eff_h:
                        features["heading"] = eff_h

                    h_prefix = f"[{eff_h}] " if eff_h else ""

                    findings.append(
                        Finding.create(
                            type=FindingType.TIMELINE_CONTRADICTION,
                            status=VerificationStatus.CONTRADICTED,
                            severity=Severity.MEDIUM,
                            evidence_grade=EvidenceGrade.A,
                            title=f"날짜와 요일 불일치: {y}. {month}. {day}.({weekday_str}) → 실제 {actual_weekday_str}요일",
                            detail=(
                                f"{h_prefix}본문에 기재된 '{matched_str}'의 요일 표기가 달력과 일치하지 않는다. "
                                f"{y}년 {month}월 {day}일은 {actual_weekday_str}요일이나 본문에는 {weekday_str}요일로 기재되었다."
                            ),
                            confidence=1.0,
                            confidence_features=features,
                            document_id=doc.document_id,
                            block_id=block.block_id,
                            page=block.page,
                            engine=ENGINE_NAME,
                            tags=["TIMELINE", "DATE-WEEKDAY", "CALENDAR"],
                            evidence=[
                                Evidence.create(
                                    description=f"{h_prefix}달력 역법상 요일 불일치".strip(),
                                    grade=EvidenceGrade.A,
                                    document_id=doc.document_id,
                                    block_id=block.block_id,
                                    page=block.page,
                                    excerpt=matched_str,
                                    supports=True,
                                )
                            ],
                        )
                    )

        # 2. 존재하지 않는 날짜 검증 (DATE-INVALID)
        # 예: 2026. 2. 29. (2026년은 평년) 또는 "2026. 2." 아래 "2. 29." / "2월 29일"
        # 1) YYYY. MM. DD. 직접 매칭
        for m in DATE_GENERAL_RE.finditer(text):
            y = int(m.group("year"))
            month = int(m.group("month"))
            day = int(m.group("day"))

            # 1~12월 범위에서 일이 1~31 범위 내이나 달력상 존재하지 않는 경우 (예: 4월 31일, 평년 2월 29일 등)
            if 1 <= month <= 12 and 1 <= day <= 31:
                if _parse_valid_date(y, month, day) is None:
                    matched_str = m.group(0)
                    is_leap = calendar.isleap(y)
                    eff_h = _find_effective_heading(text, m.start(), current_heading)

                    features = {
                        "deterministic_rule": True,
                        "year": y,
                        "month": month,
                        "day": day,
                        "is_leap_year": is_leap,
                        "rule_id": "claim_engine.date_verifier:DATE_INVALID",
                    }
                    if eff_h:
                        features["heading"] = eff_h

                    h_prefix = f"[{eff_h}] " if eff_h else ""

                    findings.append(
                        Finding.create(
                            type=FindingType.EVIDENCE_DATE_INVALID,
                            status=VerificationStatus.CONTRADICTED,
                            severity=Severity.HIGH,
                            evidence_grade=EvidenceGrade.A,
                            title=f"달력상 존재하지 않는 날짜 기재: {matched_str}",
                            detail=(
                                f"{h_prefix}{y}년 {month}월에는 {day}일이 존재하지 않는다"
                                + (f" ({y}년은 평년으로 2월 28일까지 존재)." if month == 2 and not is_leap else ".")
                            ),
                            confidence=1.0,
                            confidence_features=features,
                            document_id=doc.document_id,
                            block_id=block.block_id,
                            page=block.page,
                            engine=ENGINE_NAME,
                            tags=["TIMELINE", "DATE-INVALID", "CALENDAR"],
                            evidence=[
                                Evidence.create(
                                    description=f"{h_prefix}존재하지 않는 날짜 표기".strip(),
                                    grade=EvidenceGrade.A,
                                    document_id=doc.document_id,
                                    block_id=block.block_id,
                                    page=block.page,
                                    excerpt=matched_str,
                                    supports=True,
                                )
                            ],
                        )
                    )

        # 2) 블록 내 선행 연도(예: 2026.) 아래 "2. 29." 또는 "2월 29일" 매칭
        m_feb29 = re.search(r"(?<!\d)(?:2|02)(?:\s*월\s*|[./-]\s*)29(?:일|(?=\D|$))", text)
        years = list(re.finditer(r"(?<!\d)([12]\d{3})(?:년|\s*\.)", text[:m_feb29.start()])) if m_feb29 else []
        block_year = int(years[-1].group(1)) if years else None
        if block_year is not None and not calendar.isleap(block_year):
            # 평년인데 2. 29. 또는 2월 29일이 있는 경우
            if m_feb29 and not any(m.start() <= m_feb29.start() < m.end() for m in DATE_GENERAL_RE.finditer(text)):
                # 이미 1)에서 찾은 것이 아닌 경우
                if not any(f.type == FindingType.EVIDENCE_DATE_INVALID and "29" in f.title for f in findings if f.block_id == block.block_id):
                    matched_str = m_feb29.group(0)
                    eff_h = _find_effective_heading(text, m_feb29.start(), current_heading)

                    features = {
                        "deterministic_rule": True,
                        "year": block_year,
                        "month": 2,
                        "day": 29,
                        "is_leap_year": False,
                        "rule_id": "claim_engine.date_verifier:DATE_INVALID_FEB29",
                    }
                    if eff_h:
                        features["heading"] = eff_h

                    h_prefix = f"[{eff_h}] " if eff_h else ""

                    findings.append(
                        Finding.create(
                            type=FindingType.EVIDENCE_DATE_INVALID,
                            status=VerificationStatus.CONTRADICTED,
                            severity=Severity.HIGH,
                            evidence_grade=EvidenceGrade.A,
                            title=f"달력상 존재하지 않는 날짜 기재: {block_year}년 2월 29일 ({matched_str})",
                            detail=(
                                f"{h_prefix}{block_year}년은 평년으로 2월 28일까지 존재하므로 2월 29일은 달력에 존재하지 않는다."
                            ),
                            confidence=1.0,
                            confidence_features=features,
                            document_id=doc.document_id,
                            block_id=block.block_id,
                            page=block.page,
                            engine=ENGINE_NAME,
                            tags=["TIMELINE", "DATE-INVALID", "CALENDAR"],
                            evidence=[
                                Evidence.create(
                                    description=f"{h_prefix}존재하지 않는 평년 2월 29일 표기".strip(),
                                    grade=EvidenceGrade.A,
                                    document_id=doc.document_id,
                                    block_id=block.block_id,
                                    page=block.page,
                                    excerpt=matched_str,
                                    supports=True,
                                )
                            ],
                        )
                    )

        # 3. 경과 일수 계산 검증 (DAYS)
        # 예: "기준일로부터 N일이 지난 날짜" → 두 날짜의 실제 일수와 N을 비교한다
        for m in DAYS_ELAPSED_RE.finditer(text):
            stated_days = int(m.group("days"))
            to_y = int(m.group("to_y"))
            to_m = int(m.group("to_m"))
            to_d = int(m.group("to_d"))
            to_date = _parse_valid_date(to_y, to_m, to_d)

            from_date = None
            if m.group("from_y"):
                from_date = _parse_valid_date(int(m.group("from_y")), int(m.group("from_m")), int(m.group("from_d")))
            elif context_incident_date:
                from_date = context_incident_date

            if from_date and to_date:
                actual_days = (to_date - from_date).days
                # 1일 차이는 초일 산입 여부(민법 제157조: 초일 불산입 원칙, 오전 0시부터 시작하면 산입)에 따라
                # 달라질 수 있으므로 계산 오류로 보지 않는다. 2일 이상 차이만 판정한다.
                if actual_days > 0 and abs(actual_days - stated_days) > 1:
                    matched_str = m.group(0)
                    eff_h = _find_effective_heading(text, m.start(), current_heading)

                    features = {
                        "deterministic_rule": True,
                        "from_date": str(from_date),
                        "to_date": str(to_date),
                        "stated_days": stated_days,
                        "actual_days": actual_days,
                        "difference": actual_days - stated_days,
                        "rule_id": "claim_engine.date_verifier:DAYS_ELAPSED_MISMATCH",
                    }
                    if eff_h:
                        features["heading"] = eff_h

                    h_prefix = f"[{eff_h}] " if eff_h else ""

                    findings.append(
                        Finding.create(
                            type=FindingType.TIMELINE_CONTRADICTION,
                            status=VerificationStatus.CONTRADICTED,
                            severity=Severity.MEDIUM,
                            evidence_grade=EvidenceGrade.A,
                            title=f"경과 일수 계산 오류: 기재 {stated_days}일 → 실제 {actual_days}일",
                            detail=(
                                f"{h_prefix}{from_date}부터 {to_date}까지의 실제 경과 일수는 {actual_days}일이나, "
                                f"본문에는 {stated_days}일로 기재되어 차이({abs(actual_days - stated_days)}일)가 발생한다."
                            ),
                            confidence=1.0,
                            confidence_features=features,
                            document_id=doc.document_id,
                            block_id=block.block_id,
                            page=block.page,
                            engine=ENGINE_NAME,
                            tags=["TIMELINE", "DAYS", "CALCULATION"],
                            evidence=[
                                Evidence.create(
                                    description=f"{h_prefix}일수 경과 계산 불일치".strip(),
                                    grade=EvidenceGrade.A,
                                    document_id=doc.document_id,
                                    block_id=block.block_id,
                                    page=block.page,
                                    excerpt=matched_str,
                                    supports=True,
                                )
                            ],
                        )
                    )

    # 4. 문서/통지 발송일시와 본문 과거 의결/사유일 선후 역전 검증 (DATE-INVERSION / TEMPORAL)
    # 예: 발송일시보다 뒤 날짜의 회의·의결을 "…에 개최된 …의 의결에 따라"처럼 이미 있었던 일로 인용하는 모순
    SEND_HEADER_RE = re.compile(
        r"(?:발송일시|발신일시|통지일시|작성일시|발송일|통지일|작성일)\s*[:\s]?\s*(?P<year>\d{4})[.\s년/-]+(?P<month>\d{1,2})[.\s월/-]+(?P<day>\d{1,2})"
    )
    PAST_EVENT_RE = re.compile(
        r"(?P<year>\d{4})[.\s년/-]+(?P<month>\d{1,2})[.\s월/-]+(?P<day>\d{1,2})[일\s.]*(?:개최된|열린|이루어진|의결에\s*따라|결의에\s*따라|처분에\s*따라|결정에\s*따라|실시된|자인한)"
    )

    for page in doc.pages:
        blocks = [b for b in page.blocks if b.visible and b.text.strip()]
        # 단일 블록 또는 인접 블록 결합 검사
        for i in range(len(blocks)):
            # 윈도우 텍스트 (현재 블록 + 다음 블록 최대 2개)
            window_blocks = blocks[i:min(i + 3, len(blocks))]
            window_text = " ".join(b.text for b in window_blocks)

            m_send = SEND_HEADER_RE.search(window_text)
            if m_send:
                sy, sm, sd = int(m_send.group("year")), int(m_send.group("month")), int(m_send.group("day"))
                send_date = _parse_valid_date(sy, sm, sd)

                if send_date:
                    for m_evt in PAST_EVENT_RE.finditer(window_text):
                        ey, em, ed = int(m_evt.group("year")), int(m_evt.group("month")), int(m_evt.group("day"))
                        evt_date = _parse_valid_date(ey, em, ed)

                        if evt_date and evt_date > send_date:
                            matched_send = m_send.group(0)
                            matched_evt = m_evt.group(0)
                            eff_h = _find_effective_heading(window_text, m_evt.start(), None)

                            features = {
                                "deterministic_rule": True,
                                "send_date": str(send_date),
                                "event_date": str(evt_date),
                                "rule_id": "claim_engine.date_verifier:DATE_INVERSION_EVENT_AFTER_SEND",
                            }
                            if eff_h:
                                features["heading"] = eff_h

                            h_prefix = f"[{eff_h}] " if eff_h else ""

                            # 중복 방지
                            if not any(f.title.startswith("발송/통지일 선후 역전") and f.page == window_blocks[0].page for f in findings):
                                findings.append(
                                    Finding.create(
                                        type=FindingType.TIMELINE_CONTRADICTION,
                                        status=VerificationStatus.CONTRADICTED,
                                        severity=Severity.HIGH,
                                        evidence_grade=EvidenceGrade.A,
                                        title=f"발송/통지일 선후 역전: 발송일({send_date})보다 미래의 사유·의결({evt_date})을 과거 사실로 인용",
                                        detail=(
                                            f"{h_prefix}발송/통지일시({send_date}) 시점에 아직 발생하지 않은 미래 일자({evt_date})를 "
                                            f"'{matched_evt}'와 같이 과거 완료된 사유로 인용하여 인과적 선후 관계가 모순된다."
                                        ),
                                        confidence=1.0,
                                        confidence_features=features,
                                        document_id=doc.document_id,
                                        block_id=window_blocks[0].block_id,
                                        page=window_blocks[0].page,
                                        engine=ENGINE_NAME,
                                        tags=["TIMELINE", "DATE-INVERSION", "TEMPORAL"],
                                        evidence=[
                                            Evidence.create(
                                                description=f"{h_prefix}발송일시 및 미래 의결 인용 선후 역전 구간".strip(),
                                                grade=EvidenceGrade.A,
                                                document_id=doc.document_id,
                                                block_id=window_blocks[0].block_id,
                                                page=window_blocks[0].page,
                                                excerpt=f"{matched_send} <-> {matched_evt}",
                                                supports=True,
                                            )
                                        ],
                                    )
                                )

    # 5. 동일 주체·동일 대상 결합 기반 사건 일시·기간 선후 역전 검증 (TEMPORAL_EVENT_INVERSION, B등급)
    # - 조건 ①: 은퇴 4세트 미득점 7항목 진단표의 4대 결합 구조에 한정하여 판정
    # - 조건 ②: 같은 주체·같은 대상 명사·지시어(그/위/해당/에 대한) 결합 필수, 앞선 사건을 대상·근거·첨부로 삼는 정상 회고 서술 제외
    # - 조건 ③: 기간·상대 일자 오차는 민법 제157조(초일 불산입 원칙)·제159조·제160조(역에 의한 월·년 계산, 말일 보정) 적용
    EXHIBIT_SECTION_RE = re.compile(r"(?:입증\s*방법|첨부\s*서류|증거\s*목록|서증\s*목록)")

    def _emit_temporal_inversion(
        *,
        block_obj: Any,
        heading: Optional[str],
        rule_sub_id: str,
        title: str,
        detail_body: str,
        excerpt_text: str,
        extra_features: Dict[str, Any],
    ) -> None:
        """인과·시간 선후 역전 Finding을 중복 없이 추가한다."""
        for existing_f in findings:
            if (
                existing_f.type == FindingType.TIMELINE_CONTRADICTION
                and existing_f.page == block_obj.page
                and existing_f.confidence_features.get("sub_rule") == rule_sub_id
                and existing_f.confidence_features.get("excerpt_key") == excerpt_text[:80]
            ):
                return
        h_pref = f"[{heading}] " if heading else ""
        features = {
            "deterministic_rule": True,
            "rule_id": "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION",
            "sub_rule": rule_sub_id,
            "excerpt_key": excerpt_text[:80],
            **extra_features,
        }
        if heading:
            features["heading"] = heading
        findings.append(
            Finding.create(
                type=FindingType.TIMELINE_CONTRADICTION,
                status=VerificationStatus.CONTRADICTED,
                severity=Severity.HIGH,
                evidence_grade=EvidenceGrade.B,
                title=title,
                detail=f"{h_pref}{detail_body}",
                confidence=0.9,
                confidence_features=features,
                document_id=doc.document_id,
                block_id=block_obj.block_id,
                page=block_obj.page,
                engine=ENGINE_NAME,
                tags=["TIMELINE", "DATE-INVERSION", "TEMPORAL"],
                evidence=[
                    Evidence.create(
                        description=f"{h_pref}동일 주체·대상 사건의 일시·기간 선후 역전".strip(),
                        grade=EvidenceGrade.B,
                        document_id=doc.document_id,
                        block_id=block_obj.block_id,
                        page=block_obj.page,
                        excerpt=excerpt_text[:240],
                        supports=True,
                    )
                ],
            )
        )

    for block in doc.body_blocks():
        if block.block_type in ("table", "table_line", "running_head"):
            continue

        text = block.text
        if not text:
            continue

        eff_h = _find_effective_heading(text, 0, current_heading)
        if eff_h and EXHIBIT_SECTION_RE.search(eff_h):
            continue
        if EXHIBIT_SECTION_RE.search(text[:60]):
            continue

        # 블록 전체를 공백 정규화한 단락 문자열 (인접 2문장 결합 구조 검사용)
        norm_block = " ".join(text.split())
        if len(norm_block) < 15:
            continue

        # 공통 배제 가드 검사 함수 (매칭 구간 및 직후 문맥 45자까지 포함하여 정정·장래·회고 표지 확인)
        def _is_excluded_context(m_obj: re.Match[str]) -> bool:
            start_idx = max(0, m_obj.start() - 15)
            end_idx = min(len(norm_block), m_obj.end() + 45)
            span_text = norm_block[start_idx:end_idx]
            if CORRECTION_EXCLUDE_RE.search(span_text):
                return True
            if FUTURE_EXCLUDE_RE.search(span_text):
                return True
            if AUTHORITY_EXCLUDE_RE.search(span_text):
                return True
            if DIFFERENT_SUBJECTS_RE.search(m_obj.group(0)):
                return True
            if RETROSPECTIVE_OBJECT_EXCLUDE_RE.search(span_text):
                return True
            if SEPARATE_PERIOD_EXCLUDE_RE.search(span_text):
                return True
            return False

        # (규칙 1-A1) 동일 주체의 개시일(입사일 등)–종료일(최종 퇴사일 등) 명사구 쌍 역전
        for m in SAME_SUBJECT_LIFECYCLE_RE.finditer(norm_block):
            matched = m.group(0)
            if _is_excluded_context(m):
                continue
            d1 = _parse_date_str(m.group("d1"))
            d2 = _parse_date_str(m.group("d2"))
            if d1 and d2 and d2 < d1:
                s_lbl, e_lbl = m.group("start_label"), m.group("end_label")
                _emit_temporal_inversion(
                    block_obj=block,
                    heading=eff_h,
                    rule_sub_id="SAME_SUBJECT_LIFECYCLE",
                    title=f"사건 일자 선후 모순: {s_lbl}({m.group('d1').strip()})보다 {e_lbl}({m.group('d2').strip()})이 앞섬",
                    detail_body=(
                        f"동일 주체의 '{s_lbl}({m.group('d1').strip()})'보다 종료 시점인 "
                        f"'{e_lbl}({m.group('d2').strip()})'이 시간상 앞서 기재되어 선후 관계가 모순된다."
                    ),
                    excerpt_text=matched,
                    extra_features={"cause_date": str(d1), "effect_date": str(d2)},
                )

        # (규칙 1-A2) 동일 주체 개시일(입사일) 후 일정 기간(N개월/달/년/일) 근무 뒤 사직·퇴사 발송일 역전 (민법 제157조·제160조)
        for m in LIFECYCLE_DURATION_INVERSION_RE.finditer(norm_block):
            matched = m.group(0)
            if _is_excluded_context(m):
                continue
            d1 = _parse_date_str(m.group("d1"))
            d2 = _parse_date_str(m.group("d2"))
            n_val = _parse_numeral(m.group("n"))
            unit = m.group("unit")
            if d1 and d2 and n_val:
                earliest_expiry = _add_civil_period(d1, n_val, unit, inclusive=True)
                expiry_excl = _add_civil_period(d1, n_val, unit, inclusive=False)
                if d2 < d1 or d2 < earliest_expiry:
                    s_lbl = m.group("start_label")
                    _emit_temporal_inversion(
                        block_obj=block,
                        heading=eff_h,
                        rule_sub_id="LIFECYCLE_DURATION_INVERSION",
                        title=(
                            f"사건 일자·기간 선후 모순: {s_lbl}({m.group('d1').strip()})로부터 "
                            f"{m.group('n')}{unit} 근무 뒤 일자가 {m.group('d2').strip()}로 기재"
                        ),
                        detail_body=(
                            f"'{s_lbl}'을 {m.group('d1').strip()}로 적으면서 {m.group('n')}{unit} 근무한 뒤의 "
                            f"사직·퇴사 관련 일자가 그보다 앞선 {m.group('d2').strip()}로 나타나 선후 관계가 모순된다 "
                            f"(민법 제157조·제160조상 최소 만료일: 초일 산입 {earliest_expiry}, 초일 불산입 {expiry_excl})."
                        ),
                        excerpt_text=matched,
                        extra_features={
                            "cause_date": str(d1),
                            "effect_date": str(d2),
                            "earliest_expiry": str(earliest_expiry),
                            "exclusive_expiry": str(expiry_excl),
                        },
                    )

        # (규칙 1-B1) 선행 신청·청구를 직접 대상으로 삼은('~에 대한') 후행 처분·결정의 발령일 역전
        for m in TARGET_BOUND_DISPOSITION_RE.finditer(norm_block):
            matched = m.group(0)
            if _is_excluded_context(m):
                continue
            d1_raw = (m.group("d1") or m.group("d1_alt") or "").strip()
            d2_raw = (m.group("d2") or "").strip()
            d1 = _parse_date_str(d1_raw)
            d2 = _parse_date_str(d2_raw)
            if d1 and d2 and d2 < d1:
                c_noun = (m.group("cause_noun") or m.group("cause_noun_alt") or "").strip()
                e_noun = m.group("effect_noun").strip()
                _emit_temporal_inversion(
                    block_obj=block,
                    heading=eff_h,
                    rule_sub_id="TARGET_BOUND_DISPOSITION",
                    title=f"사건 일자 선후 모순: {c_noun}({d1_raw})에 대한 {e_noun} 발령일({d2_raw})이 앞섬",
                    detail_body=(
                        f"선행 '{c_noun}({d1_raw})'을 대상으로 한 후행 '{e_noun}'의 발령일({d2_raw})이 "
                        f"신청·청구일보다 앞서 기재되어 인과적 선후 관계가 모순된다."
                    ),
                    excerpt_text=matched,
                    extra_features={"cause_date": str(d1), "effect_date": str(d2)},
                )

        # (규칙 1-B2) 선행 행위 D1 후 지시어('그/위/해당 <동일명사>')로 결합된 후행 처분·해제 D2 역전
        for m in ANAPHORIC_TARGET_INVERSION_RE.finditer(norm_block):
            matched = m.group(0)
            if _is_excluded_context(m):
                continue
            d1 = _parse_date_str(m.group("d1"))
            d2 = _parse_date_str(m.group("d2"))
            if d1 and d2 and d2 < d1:
                noun = m.group("noun").strip()
                e_noun = m.group("effect_noun").strip()
                _emit_temporal_inversion(
                    block_obj=block,
                    heading=eff_h,
                    rule_sub_id="ANAPHORIC_TARGET_INVERSION",
                    title=f"사건 일자 선후 모순: 선행 {noun}({m.group('d1').strip()})보다 그 {noun}에 대한 {e_noun}({m.group('d2').strip()})이 앞섬",
                    detail_body=(
                        f"선행 '{noun}({m.group('d1').strip()})'과 지시어로 결합된 동일 대상의 후행 '{e_noun}({m.group('d2').strip()})' 일자가 "
                        f"선행 행위일보다 앞서 기재되어 인과적 선후 관계가 모순된다."
                    ),
                    excerpt_text=matched,
                    extra_features={"cause_date": str(d1), "effect_date": str(d2)},
                )

        # (규칙 2) 동일 행위 기간(D1부터 D2까지) 종료('끝난 뒤') 후 최초 문서 작성·산정일(D3) 역전
        for m in PERIOD_END_WRITE_INVERSION_RE.finditer(norm_block):
            matched = m.group(0)
            if _is_excluded_context(m):
                continue
            d1 = _parse_date_str(m.group("d1"))
            d2 = _parse_date_str(m.group("d2"))
            d3 = _parse_date_str(m.group("d3"))
            if d1 and d2 and d3 and d1 <= d2 and d3 < d2:
                act = m.group("act").strip()
                _emit_temporal_inversion(
                    block_obj=block,
                    heading=eff_h,
                    rule_sub_id="PERIOD_END_WRITE_INVERSION",
                    title=f"사건 일자 선후 모순: {act} 종료일({m.group('d2').strip()}) 뒤 처음 작성한 날({m.group('d3').strip()})이 종료일보다 앞섬",
                    detail_body=(
                        f"{act}기간({m.group('d1').strip()} ~ {m.group('d2').strip()})의 {act}이 끝난 뒤 처음 작성·산정한 날을 "
                        f"종료일({m.group('d2').strip()})보다 앞선 {m.group('d3').strip()}로 기재하여 선후 관계가 모순된다."
                    ),
                    excerpt_text=matched,
                    extra_features={"period_start": str(d1), "cause_date": str(d2), "effect_date": str(d3)},
                )

        # (규칙 3) 동일 행위 명사 결합 상대 일자('다음 날/이튿날/N일 뒤') 역산 모순 (민법 제157조·제160조)
        for m in RELATIVE_NEXT_DAY_INVERSION_RE.finditer(norm_block):
            matched = m.group(0)
            if _is_excluded_context(m):
                continue
            d1 = _parse_date_str(m.group("d1"))
            d2 = _parse_date_str(m.group("d2"))
            if not d1 or not d2:
                continue
            act = m.group("act").strip()
            if m.group("next_day"):
                # 민법 제157조(초일 불산입): d1의 다음 날(익일/이튿날)은 d1 + 1일
                expected_d2 = d1 + datetime.timedelta(days=1)
                if d2 != expected_d2:
                    _emit_temporal_inversion(
                        block_obj=block,
                        heading=eff_h,
                        rule_sub_id="RELATIVE_NEXT_DAY_INVERSION",
                        title=f"상대 일자 계산·선후 모순: {act}일({m.group('d1').strip()})의 다음 날이 {m.group('d2').strip()}로 기재",
                        detail_body=(
                            f"{m.group('d1').strip()}에 '{act}'한 다음 날(민법 제157조 초일 불산입 기준 {expected_d2})을 "
                            f"그보다 앞선(또는 불일치하는) {m.group('d2').strip()}로 기재하여 달력 계산과 충돌한다."
                        ),
                        excerpt_text=matched,
                        extra_features={"cause_date": str(d1), "effect_date": str(d2), "expected_date": str(expected_d2)},
                    )
            elif m.group("n") and m.group("unit"):
                n_val = _parse_numeral(m.group("n"))
                unit = m.group("unit")
                if n_val:
                    earliest = _add_civil_period(d1, n_val, unit, inclusive=True)
                    if d2 < earliest:
                        _emit_temporal_inversion(
                            block_obj=block,
                            heading=eff_h,
                            rule_sub_id="RELATIVE_PERIOD_INVERSION",
                            title=f"상대 기간 선후 모순: {act}일({m.group('d1').strip()})로부터 {m.group('n')}{unit} 뒤가 {m.group('d2').strip()}로 기재",
                            detail_body=(
                                f"{m.group('d1').strip()} '{act}' 이후 {m.group('n')}{unit}이 지난 시점(민법 제157조·제160조 최소 만료일 {earliest})을 "
                                f"그보다 앞선 {m.group('d2').strip()}로 기재하여 선후 관계가 모순된다."
                            ),
                            excerpt_text=matched,
                            extra_features={"cause_date": str(d1), "effect_date": str(d2), "earliest_expiry": str(earliest)},
                        )

        # (규칙 4-A) 동일 일자 내 지시어('그 <명사>보다 앞선') 결합 상대 시각(HH:MM) 역전
        for m in SAME_DAY_EARLIER_TIME_INVERSION_RE.finditer(norm_block):
            matched = m.group(0)
            if _is_excluded_context(m):
                continue
            d1 = _parse_date_str(m.group("d1"))
            t1_min = _parse_minutes(m.group("t1"))
            t2_min = _parse_minutes(m.group("t2"))
            if d1 and t1_min is not None and t2_min is not None and t2_min >= t1_min:
                act = m.group("act").strip()
                _emit_temporal_inversion(
                    block_obj=block,
                    heading=eff_h,
                    rule_sub_id="SAME_DAY_EARLIER_TIME_INVERSION",
                    title=f"동일 일자 시각 선후 모순: {act} 시각({m.group('d1').strip()} {m.group('t1')})보다 앞선 시각이 같은 날 {m.group('t2')}로 기재",
                    detail_body=(
                        f"{act} 시각({m.group('d1').strip()} {m.group('t1')})보다 앞선 시점이라고 서술하면서 "
                        f"실제 시각은 그보다 늦은 같은 날 {m.group('t2')}로 기재하여 시간 선후 관계가 충돌한다."
                    ),
                    excerpt_text=matched,
                    extra_features={"date": str(d1), "time_1": m.group("t1"), "time_2": m.group("t2")},
                )

        # (규칙 4-B) 동일 목적물('그 <목적물>')의 최초 회수·확보 시각(T1) vs 같은 날 이미 전달·인계된 시각(T2) 역전
        for m in SAME_OBJECT_FIRST_ACQUIRE_TIME_INVERSION_RE.finditer(norm_block):
            matched = m.group(0)
            if _is_excluded_context(m):
                continue
            obj1, obj2 = m.group("obj").strip(), m.group("obj2").strip()
            if not _same_object_noun(obj1, obj2):
                continue
            d1 = _parse_date_str(m.group("d1"))
            t1_min = _parse_minutes(m.group("t1"))
            t2_min = _parse_minutes(m.group("t2"))
            if d1 and t1_min is not None and t2_min is not None and t2_min < t1_min:
                _emit_temporal_inversion(
                    block_obj=block,
                    heading=eff_h,
                    rule_sub_id="SAME_OBJECT_FIRST_ACQUIRE_TIME_INVERSION",
                    title=f"동일 목적물 시각 선후 모순: {obj1} 최초 확보({m.group('d1').strip()} {m.group('t1')})보다 앞서 같은 날 {m.group('t2')}에 인계·전달 기재",
                    detail_body=(
                        f"동일 목적물('{obj1}' / '그 {obj2}')을 {m.group('d1').strip()} {m.group('t1')}에 처음 회수·확보하였다고 하면서, "
                        f"그보다 앞선 같은 날 {m.group('t2')}에 이미 전달·인계되었다고 기재하여 시각 순서가 역전되었다."
                    ),
                    excerpt_text=matched,
                    extra_features={"date": str(d1), "acquire_time": m.group("t1"), "transfer_time": m.group("t2")},
                )

    return findings
