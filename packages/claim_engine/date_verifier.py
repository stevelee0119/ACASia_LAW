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

# 구조적 패턴용 날짜 부분 정규식 (하이픈, 슬래시, 온점, 년월일, 요일 괄호 병기 허용)
_DATE_PAT = (
    r"(?:19|20)\d{2}\s*(?:[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2}\s*\.?|년\s*\d{1,2}\s*월\s*\d{1,2}\s*일)"
    r"(?:\s*\([월화수목금토일](?:요일)?\)|\s*[월화수목금토일]요일)?"
)

# A-4 1. 당사자 호칭 사전 (주체 범주)
PARTY_TITLES: Tuple[str, ...] = (
    "원고", "피고", "신청인", "피신청인",
    "채권자", "채무자", "임대인", "임차인",
    "근로자", "사용자", "청구인", "피청구인",
)

# A-4 2. 기관명 접미 규칙 (조건 6: 기관명 열거 금지, 접미 규칙으로 포착)
ORGAN_SUFFIX_RE = re.compile(
    r"[가-힣]{1,15}(?:법원|위원회|세무서|경찰서|소방서|관할청|처분청|행정청|검찰청|노동청|국세청|구청|시청|지청)"
)

# 주체 추출 정규식: 당사자 호칭 또는 기관명 접미 + 주격/보조사
SUBJECT_RE = re.compile(
    r"(?:(?P<party>" + "|".join(PARTY_TITLES) + r")|(?P<organ>[가-힣]{1,15}(?:법원|위원회|세무서|경찰서|소방서|관할청|처분청|행정청|검찰청|노동청|국세청|구청|시청|지청)))"
    r"(?P<particle>[은는이가의])"
)

# 절 분리 정규식: 쉼표, 세미콜론, 연결어미 (-고, -며, -나, -한 후, -한 뒤, -하여, -한바 등), 문장 종결어미 (조건 1)
CLAUSE_DELIMITER_RE = re.compile(
    r",\s*|;\s*|\n+|"
    r"(?<=[가-힣][다음함임것바기]\.)\s+|"
    r"(?:"
    r"(?<=[가-힣])(?:하고|했고|하고는|하며|했으나|하나|하지만|하였고|하였으나|하였으며|하여|한바|인바|"
    r"(?:한|된|받은|보낸|마친|끝난)\s*(?:후|뒤|다음)(?:에|는|,|\s)?)|"
    r"(?:(?<=\.)|(?<=\d)|\s+)이(?:고|며|나|지만|인데)|"
    r"(?:(?<=\.)|(?<=\d)|\s+)에\s*대한"
    r")\s*"
)

# A-4 3. 7대 사건 종류 표면형 닫힌 사전 (조건 2: 활용형·동의어 표면형 전체를 코드 상수로 정의)
EVENT_KIND_SURFACE_FORMS: Dict[str, Tuple[str, ...]] = {
    "신청": (
        "허가신청", "변경신청", "교부신청", "재심청구", "심판청구", "구제신청", "지급청구", "손해배상청구", "소송제기",
        "신청서제출", "청구서제출", "소장제출", "의견서제출",
        "손해배상 청구", "손해배상금 지급청구", "보험금 청구",
        "신청서", "청구서", "신청", "청구",
        "신청하", "청구하", "신청했", "청구했", "신청한", "청구한", "신청된", "청구된", "제출하", "제출했", "제기되었", "제기했",
    ),
    "처분": (
        "과징금부과처분", "영업정지처분", "직위해제처분", "거부처분", "불승인처분", "불허가처분",
        "기각결정", "각하결정", "인용결정", "승인처분", "인가처분", "보정명령",
        "처분", "결정", "고지", "통고", "명령", "판정", "의결",
        "처분하", "결정하", "고지하", "통고하", "명령하",
        "처분했", "결정했", "고지했", "통고했", "명령했",
        "처분된", "결정된", "내려진", "발령",
    ),
    "통지": (
        "해제통지", "해지통지", "결과통지", "최고서",
        "해제 통지", "해지 통지",
        "통지서", "통지", "회신", "통보", "안내", "공지",
        "통지하", "회신하", "통보하", "통지했", "회신했", "통보했", "통지된", "발송된통지",
    ),
    "발송": (
        "발송일", "발신일", "송부일", "발송일시", "발신일시",
        "발송", "송부", "발신",
        "발송하", "송부하", "발신하", "발송했", "송부했", "발신했",
        "보냈", "보낸", "부친", "부쳤", "발송한", "송부한",
    ),
    "도달": (
        "결정도달", "송달", "도달일", "수령일", "송달일", "도달일시", "수령일시", "송달일시",
        "도달", "수령", "송달받", "수임", "교부받",
        "도달하", "수령하", "도달했", "수령했", "도달한", "수령한",
        "받았", "받은", "교부", "인계",
    ),
    "체결": (
        "계약체결", "협약체결", "합의체결",
        "체결일", "계약체결일", "체결", "약정", "계약을맺",
        "체결하", "약정하", "체결했", "약정했", "체결한", "약정한",
        "맺었", "맺은",
    ),
    "이행": (
        "이행", "변제", "지급", "인도", "결제", "정산",
        "이행하", "변제하", "지급하", "인도하",
        "이행했", "변제했", "지급했", "인도했",
    ),
    "해지": (
        "계약해지", "계약해제", "합의해제", "해제통지", "해지통지", "해제 통지", "해지 통지",
        "해지일", "해제일", "해지", "해제",
        "해지하", "해제하", "해지했", "해제했", "해지한", "해제한",
        "해지된", "해제된",
    ),
    "입사": (
        "입사일", "근무시작일", "재직시작일", "채용일", "임용일",
        "입사", "채용", "취직", "근무시작", "재직시작", "임용",
        "입사하", "채용하", "입사했", "채용했", "입사한", "채용된",
    ),
    "퇴사": (
        "최종퇴사일", "최종퇴직일", "퇴사일", "퇴직일", "해고일", "사직일", "근무종료일",
        "사직통지", "사직 통지", "해고통지", "해고 통지",
        "퇴사", "퇴직", "해고", "사직", "근무종료", "최종퇴사", "최종퇴직",
        "퇴사하", "퇴직하", "해고하", "사직하",
        "퇴사했", "퇴직했", "해고했", "사직했", "퇴직한", "해고된",
    ),
    "접수": (
        "소장접수", "사건접수", "신청접수", "접수일",
        "접수", "접수하", "접수했", "접수한", "접수된", "접수되었", "접수되어", "접수되",
    ),
    "보정": (
        "보정명령", "보정권고", "보정명령일",
        "보정", "보정하", "보정했", "보정명령을내", "보정명령한",
    ),
    "발생": (
        "사고발생", "손해발생", "사건발생", "발생일", "사고발생일",
        "교통사고", "사고",
        "발생", "발생하", "발생했", "발생한",
    ),
    "기간시작": (
        "임대차개시일", "임대기간", "근무기간", "계약기간",
        "개시일", "시작일", "기산일",
        "개시", "시작", "기산", "부터",
    ),
    "기간종료": (
        "임대종료일", "계약종료일", "계약해지일", "만료일", "종료일", "종기일",
        "종료", "만료", "종기", "까지",
        "끝난뒤", "종료된후", "끝난후", "마친뒤",
    ),
    "작성": (
        "작성일", "발급일", "발행일", "산정일", "확인서",
        "작성", "발급", "발행", "산정",
        "작성하", "발급하", "발행하", "산정하",
        "작성했", "발급했", "발행했", "산정했", "작성한",
    ),
}

# A-4 4. 법률상 선후 관계 닫힌 쌍 및 근거 조문 (조건 3: 위험 쌍 축소 및 근거 조문 명시)
EVENT_ORDER_RULES: List[Dict[str, Any]] = [
    # 1. 신청 -> 처분 (행정절차법 제17조, 근로기준법 제28조)
    {
        "cause_kind": "신청",
        "effect_kinds": ("처분",),
        "rule_id": "TARGET_BOUND_DISPOSITION",
        "statute": "행정절차법 제17조·근로기준법 제28조",
        "require_target_match": False,  # 동일 블록 내 신청에 대한 처분
        "description": "선행 신청·청구보다 그에 대한 처분·결정이 앞서 기재됨",
    },
    # 1-2. 신청 -> 통지 (조건 3: 신청->통지는 통지의 대상이 그 신청일 때만!)
    {
        "cause_kind": "신청",
        "effect_kinds": ("통지",),
        "rule_id": "TARGET_BOUND_DISPOSITION",
        "statute": "행정절차법 제17조",
        "require_target_match": True,  # 통지의 대상이 그 신청일 때만 한정
        "description": "선행 신청보다 그 신청에 대한 통지가 앞서 기재됨",
    },
    # 2. 발송/통지 -> 도달/수령 (민법 제111조)
    {
        "cause_kind": "발송",
        "effect_kinds": ("도달",),
        "rule_id": "SEND_BEFORE_RECEIPT",
        "statute": "민법 제111조",
        "require_target_match": False,
        "description": "발송일시보다 도달·수령일시가 앞서 기재됨",
    },
    {
        "cause_kind": "통지",
        "effect_kinds": ("도달",),
        "rule_id": "SEND_BEFORE_RECEIPT",
        "statute": "민법 제111조",
        "require_target_match": False,
        "description": "통지·최고 발송일시보다 도달·수령일시가 앞서 기재됨",
    },
    # 3. 체결 -> 해지/해제/이행/통지/도달 (민법 제543조·제536조)
    {
        "cause_kind": "체결",
        "effect_kinds": ("해지", "이행", "통지", "도달"),
        "rule_id": "ANAPHORIC_TARGET_INVERSION",
        "statute": "민법 제543조·제536조",
        "require_target_match": True,
        "description": "계약 체결일보다 계약 해제·해지·이행 또는 해제 통지·도달일이 앞서 기재됨",
    },
    # 4. 입사/채용 -> 퇴사/해고 (근로기준법 제2조·제23조)
    {
        "cause_kind": "입사",
        "effect_kinds": ("퇴사",),
        "rule_id": "SAME_SUBJECT_LIFECYCLE",
        "statute": "근로기준법 제2조·제23조",
        "require_target_match": False,
        "require_same_subject": True,  # 동일 주체 한정
        "description": "동일 주체의 입사·채용일보다 퇴사·해고일이 앞서 기재됨",
    },
    # 5. 접수 -> 보정/결정 (민사소송법 제254조)
    # 조건 3: 접수->결정은 같은 대상 결합이 없으면 비교하지 않음
    {
        "cause_kind": "접수",
        "effect_kinds": ("보정", "처분"),
        "rule_id": "RECEIPT_BEFORE_AMENDMENT",
        "statute": "민사소송법 제254조",
        "require_target_match": False,  # 소장/사건/신청서 접수 후 보정명령·권고
        "description": "사건 접수일보다 보정명령·권고일이 앞서 기재됨",
    },
    # 6. 발생 -> 청구/신고 (상법 제724조·민법 제750조)
    # 조건 3: 발생->청구는 같은 대상 결합이 없으면 비교하지 않음
    {
        "cause_kind": "발생",
        "effect_kinds": ("신청",),
        "rule_id": "OCCURRENCE_BEFORE_CLAIM",
        "statute": "상법 제724조·민법 제750조",
        "require_target_match": True,
        "description": "사고·손해 발생일보다 청구·신고일이 앞서 기재됨",
    },
    # 7. 기간시작 -> 기간종료 (민법 제157조·제159조·제160조)
    {
        "cause_kind": "기간시작",
        "effect_kinds": ("기간종료",),
        "rule_id": "PERIOD_START_BEFORE_END",
        "statute": "민법 제157조·제159조·제160조",
        "require_target_match": False,
        "description": "기간 개시일보다 기간 종료일이 앞서 기재됨",
    },
    # 8. 기간종료 -> 작성/산정 (기간 만료 전 사후 확인서·정산서 작성 불가)
    {
        "cause_kind": "기간종료",
        "effect_kinds": ("작성",),
        "rule_id": "PERIOD_END_WRITE_INVERSION",
        "statute": "민법 제157조·제159조",
        "require_target_match": True,
        "description": "기간 종료일보다 그 종료 후 작성한 확인서·산정일이 앞서 기재됨",
    },
]



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


def _is_holiday_or_weekend(d: datetime.date) -> bool:
    """토요일(5), 일요일(6) 또는 관공서 법정 공휴일 여부를 판정한다 (민법 제161조)."""
    if d.weekday() in (5, 6):
        return True
    fixed_holidays = {
        (1, 1),   # 신정
        (3, 1),   # 삼일절
        (5, 5),   # 어린이날
        (6, 6),   # 현충일
        (8, 15),  # 광복절
        (10, 3),  # 개천절
        (10, 9),  # 한글날
        (12, 25), # 기독탄신일
    }
    return (d.month, d.day) in fixed_holidays


def _adjust_for_holiday(d: datetime.date) -> datetime.date:
    """민법 제161조에 따라 말일이 토요일 또는 공휴일인 경우 익일(다음 영업일)로 순연한다."""
    cur = d
    while _is_holiday_or_weekend(cur):
        cur += datetime.timedelta(days=1)
    return cur


def _add_civil_period(
    start: datetime.date,
    n: int,
    unit: str,
    *,
    inclusive: bool = False,
    adjust_holiday: bool = False,
) -> datetime.date:
    """민법 제157조(초일 불산입 및 오전 0시 기산 초일 산입)·제159조·제160조(역에 의한 계산)·제161조(공휴일 익일 만료) 기간 만료일 산출.

    - 일 단위: 초일 불산입 시 start + n일, 초일 산입(오전 0시 시작 등 예외) 시 start + max(0, n - 1)일.
    - 월/달/개월·년 단위: 역에 의하여 계산하되 마지막 달에 해당 일이 없으면 그 달의 말일로 하며(민법 제160조 제3항),
      초일 불산입 시 전일(해당일)에 만료하고, 초일 산입 시 하루 앞선 날을 최소 만료 가능일로 반환한다.
    - adjust_holiday: 민법 제161조에 따라 말일이 토요일 또는 공휴일인 경우 익일 만료 순연 적용.
    """
    if unit == "일":
        offset = max(0, n - 1) if inclusive else n
        expiry = start + datetime.timedelta(days=offset)
    else:
        months = n * 12 if unit == "년" else n
        y, m = divmod(start.month - 1 + months, 12)
        year, month = start.year + y, m + 1
        last_day = calendar.monthrange(year, month)[1]
        expiry_excl = datetime.date(year, month, min(start.day, last_day))
        expiry = expiry_excl - datetime.timedelta(days=1) if inclusive else expiry_excl

    if adjust_holiday:
        expiry = _adjust_for_holiday(expiry)
    return expiry


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


class EventSlot:
    """결정적 절 분리를 통해 추출된 단일 사건 슬롯 구조체 (주체, 사건종류, 대상, 일시)."""

    def __init__(
        self,
        clause_text: str,
        kind: str,
        surface_form: str,
        date_obj: Optional[datetime.date] = None,
        date_raw: str = "",
        time_str: Optional[str] = None,
        time_min: Optional[int] = None,
        relative_duration: Optional[Tuple[int, str]] = None,
        is_next_day: bool = False,
        is_zero_hour: bool = False,
        subject: Optional[str] = None,
        target: Optional[str] = None,
        has_anaphora: bool = False,
        span_in_block: Tuple[int, int] = (0, 0),
    ):
        self.clause_text = clause_text
        self.kind = kind
        self.surface_form = surface_form
        self.date_obj = date_obj
        self.date_raw = date_raw
        self.time_str = time_str
        self.time_min = time_min
        self.relative_duration = relative_duration
        self.is_next_day = is_next_day
        self.is_zero_hour = is_zero_hour
        self.subject = subject
        self.target = target
        self.has_anaphora = has_anaphora
        self.span_in_block = span_in_block

    def __repr__(self) -> str:
        return f"<EventSlot kind={self.kind} date={self.date_obj} subj={self.subject} target={self.target}>"


# 상대 기간 정규식
RELATIVE_DURATION_RE = re.compile(
    r"(?P<n>\d{1,3}|한|두|세|석|네|넉|다섯|여섯|일곱|여덟|아홉|열|열한|열두)\s*"
    r"(?P<unit>개월|달|년|일)\s*(?:간|동안)?\s*(?:근무|재직|복무|사용|거주)?\s*(?:뒤|후|다음)?"
)

# 상대 일자 정규식
RELATIVE_NEXT_DAY_RE = re.compile(r"(?:다음\s*날|이튿날|익일)")

# 오전 0시 기산 정규식 (민법 제157조 단서)
ZERO_HOUR_RE = re.compile(r"(?:0시|오전\s*0시|자정|초일\s*산입)")

# 시각 정규식 (HH:MM)
TIME_RE = re.compile(r"(?<!\d)(?:(?:오전|오후)\s*)?(?P<time>[012]?\d:[0-5]\d)(?!\d)")

# 대상 명사구 추출 정규식: 사건 표면형 앞 ~의, ~에 대한, ~을/를, ~자 명사구
TARGET_PRE_RE = re.compile(
    r"(?P<target>(?:[그위해당동이]\s*)?[가-힣0-9]{1,15}?)(?:의|에\s*대한|에\s*관한|[을를]|자)\s*$"
)


def _extract_clause_slots(block_text: str) -> List[EventSlot]:
    """블록 텍스트를 절 단위로 결정적 분리하고 각 절마다 단일 사건 슬롯을 추출한다 (조건 1)."""
    slots: List[EventSlot] = []

    # 절 분리 (쉼표, 연결어미, 문장 종결어미 등 및 구분자 추적)
    clause_parts: List[Tuple[str, int, int, str]] = []
    last_end = 0
    for m_del in CLAUSE_DELIMITER_RE.finditer(block_text):
        part = block_text[last_end:m_del.start()].strip()
        if part:
            clause_parts.append((part, last_end, m_del.start(), m_del.group(0)))
        last_end = m_del.end()
    rem = block_text[last_end:].strip()
    if rem:
        clause_parts.append((rem, last_end, len(block_text), ""))

    last_subject: Optional[str] = None
    last_target: Optional[str] = None

    for clause_text, start_pos, end_pos, delim_str in clause_parts:
        # 주체 추출 (같은 절 내 '은/는/이/가' 앞 당사자 호칭/기관명)
        subj = None
        subj_span: Optional[Tuple[int, int]] = None
        m_subj = SUBJECT_RE.search(clause_text)
        if m_subj:
            subj = (m_subj.group("party") or m_subj.group("organ") or "").strip()
            subj_span = m_subj.span()
            last_subject = subj
        elif last_subject:
            subj = last_subject

        # 기간 표현 (D1부터 D2까지) 검사: 기간시작 및 기간종료 2개 슬롯 동시 생성
        m_period = re.search(
            rf"(?P<d1>{_DATE_PAT})\s*(?:부터|~|∼)\s*(?P<d2>{_DATE_PAT})\s*까지",
            clause_text,
        )
        if m_period:
            d1_raw = m_period.group("d1").strip()
            d2_raw = m_period.group("d2").strip()
            d1_obj = _parse_date_str(d1_raw)
            d2_obj = _parse_date_str(d2_raw)

            # 대상 추출
            target_period = "기간"
            for comp in ("임대", "근로", "계약", "재직"):
                if comp in clause_text:
                    target_period = comp
                    break
            last_target = target_period

            slots.append(
                EventSlot(
                    clause_text=clause_text,
                    kind="기간시작",
                    surface_form="시작",
                    date_obj=d1_obj,
                    date_raw=d1_raw,
                    subject=subj,
                    target=target_period,
                    span_in_block=(start_pos, end_pos),
                )
            )
            slots.append(
                EventSlot(
                    clause_text=clause_text,
                    kind="기간종료",
                    surface_form="종료",
                    date_obj=d2_obj,
                    date_raw=d2_raw,
                    subject=subj,
                    target=target_period,
                    span_in_block=(start_pos, end_pos),
                )
            )
            continue

        # 사건 낱말 탐색 (EVENT_KIND_SURFACE_FORMS)
        # 주체 매칭 구간(예: '신청인은'의 '신청')은 사건 낱말 탐색에서 배제
        best_kind: Optional[str] = None
        best_surf: Optional[str] = None
        best_m_span: Optional[Tuple[int, int]] = None

        for kind, surfs in EVENT_KIND_SURFACE_FORMS.items():
            for s in surfs:
                idx = 0
                while True:
                    f_idx = clause_text.find(s, idx)
                    if f_idx == -1:
                        break
                    if subj_span and subj_span[0] <= f_idx < subj_span[1]:
                        idx = f_idx + len(s)
                        continue
                    if best_surf is None or len(s) > len(best_surf):
                        best_kind = kind
                        best_surf = s
                        best_m_span = (f_idx, f_idx + len(s))
                    break

        # 상대 기간 추출
        rel_dur: Optional[Tuple[int, str]] = None
        m_dur = RELATIVE_DURATION_RE.search(clause_text)
        if m_dur:
            nv = _parse_numeral(m_dur.group("n"))
            if nv:
                rel_dur = (nv, m_dur.group("unit"))

        # 상대 일자 추출
        is_next = bool(RELATIVE_NEXT_DAY_RE.search(clause_text))

        # 날짜 추출 (같은 절의 날짜만 붙임 - 조건 1)
        date_obj: Optional[datetime.date] = None
        date_raw: str = ""
        m_date = re.search(_DATE_PAT, clause_text)
        if m_date:
            date_raw = m_date.group(0).strip()
            date_obj = _parse_date_str(date_raw)

        # 시각 추출
        time_str: Optional[str] = None
        time_min: Optional[int] = None
        m_time = TIME_RE.search(clause_text)
        if m_time:
            time_str = m_time.group("time")
            time_min = _parse_minutes(time_str)

        if not best_kind and not rel_dur and not is_next and not date_obj and not time_str:
            continue

        if not best_kind:
            if is_next:
                best_kind = "신청"
                best_surf = "신청"
            elif rel_dur:
                best_kind = "퇴사"
                best_surf = "퇴사"
            elif time_str:
                best_kind = "시각"
                best_surf = "시각"
            elif date_obj:
                best_kind = "사건"
                best_surf = "사건"
            else:
                continue

        # 0시 기산 표지
        is_zero = bool(ZERO_HOUR_RE.search(clause_text))

        # 대상 추출: 사건 표면형 앞 명사구
        target: Optional[str] = None
        has_anaphora = False
        pre_text = clause_text[:best_m_span[0]].strip() if best_m_span else clause_text
        m_target = TARGET_PRE_RE.search(pre_text)
        if m_target:
            t_raw = m_target.group("target").strip()
            is_actor = (
                t_raw in PARTY_TITLES
                or bool(ORGAN_SUFFIX_RE.search(t_raw))
                or t_raw in ("관할청", "처분청", "행정청", "재판장", "법원")
            )
            if not is_actor:
                if any(t_raw.startswith(ana) for ana in ("그", "위", "해당", "동", "본건", "이 사건", "이")):
                    has_anaphora = True
                    target = re.sub(r"^(?:그|위|해당|동|본건|이\s*사건|이)\s*", "", t_raw).strip()
                    if not target:
                        target = last_target
                else:
                    target = t_raw
                last_target = target
        elif any(pre_text.endswith(ana) for ana in ("그", "위", "해당", "동")):
            has_anaphora = True
            target = last_target
        elif any(ana in clause_text for ana in ("이에 대한", "그에 대한", "그 매체", "그 계약", "그 결제", "그 처분", "위 계약", "그 협약")):
            has_anaphora = True
            m_ana = re.search(r"(?:그|위|해당|동)\s*([가-힣]{2,10})", clause_text)
            target = m_ana.group(1).strip() if m_ana else last_target
        elif last_target and has_anaphora:
            target = last_target

        if not target and best_surf:
            for comp in ("계약", "협약", "신청", "청구", "처분", "결정", "임대", "통지", "기록매체", "매체", "확인서", "결제", "안내", "사고", "손해", "보정"):
                if comp in best_surf or comp in clause_text:
                    target = comp
                    break

        slot = EventSlot(
            clause_text=clause_text,
            kind=best_kind,
            surface_form=best_surf or "",
            date_obj=date_obj,
            date_raw=date_raw,
            time_str=time_str,
            time_min=time_min,
            relative_duration=rel_dur,
            is_next_day=is_next,
            is_zero_hour=is_zero,
            subject=subj,
            target=target,
            has_anaphora=has_anaphora,
            span_in_block=(start_pos, end_pos),
        )
        slots.append(slot)

    # 에 대한 연결어미로 앞선 절의 사건을 후행 절의 대상으로 자동 바인딩
    for i in range(len(clause_parts) - 1):
        if "에 대한" in clause_parts[i][3]:
            if i < len(slots) and i + 1 < len(slots):
                slots[i + 1].target = slots[i].target or slots[i].surface_form

    # 지시어 해소: 대상이 없거나 지시어가 있는데 아직 안 풀린 경우 앞선 슬롯에서 해소
    for i in range(len(slots)):
        if slots[i].has_anaphora:
            for j in range(i - 1, -1, -1):
                if slots[j].target and _same_object_noun(slots[j].target, slots[i].target or ""):
                    slots[i].target = slots[j].target
                    break
                elif slots[j].target:
                    slots[i].target = slots[j].target
                    break

    return slots


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

    # 5. 동일 주체·동일 대상 결합 기반 사건 일시·기간 선후 역전 검증 (TEMPORAL_EVENT_INVERSION, B/C등급)
    # - 조건 ①: 7대 법률상 선후 관계 닫힌 쌍 및 민법 기간 계산에 한정하여 판정 (규약 2-2)
    # - 조건 ②: 같은 주체·같은 대상 명사·지시어 결합 필수, 앞선 사건을 대상·근거·첨부로 삼는 정상 회고 서술 제외
    # - 조건 ③: 기간·상대 일자 오차는 민법 제157조(초일 불산입 및 오전 0시 기산)·제159/160조·제161조(공휴일 익일 만료) 적용
    # - 조건 ④: 절대 일자 2개 역전은 B등급, 상대 기간 계산 불일치는 C등급 분기 (조건 5)
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
        evidence_grade: EvidenceGrade = EvidenceGrade.B,
    ) -> None:
        """인과·시간 선후 역전 Finding을 중복 없이 추가한다 (B/C등급 지원)."""
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
                severity=Severity.HIGH if evidence_grade == EvidenceGrade.B else Severity.MEDIUM,
                evidence_grade=evidence_grade,
                title=title,
                detail=f"{h_pref}{detail_body}",
                confidence=0.9 if evidence_grade == EvidenceGrade.B else 0.8,
                confidence_features=features,
                document_id=doc.document_id,
                block_id=block_obj.block_id,
                page=block_obj.page,
                engine=ENGINE_NAME,
                tags=["TIMELINE", "DATE-INVERSION", "TEMPORAL"],
                evidence=[
                    Evidence.create(
                        description=f"{h_pref}동일 주체·대상 사건의 일시·기간 선후 역전".strip(),
                        grade=evidence_grade,
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

        # 블록 전체를 공백 정규화한 단락 문자열
        norm_block = " ".join(text.split())
        if len(norm_block) < 15:
            continue

        # 공통 배제 가드 검사 (정정, 장래, 판례, 회고, 별개 기간 표지 확인)
        if (
            CORRECTION_EXCLUDE_RE.search(norm_block)
            or FUTURE_EXCLUDE_RE.search(norm_block)
            or AUTHORITY_EXCLUDE_RE.search(norm_block)
            or RETROSPECTIVE_OBJECT_EXCLUDE_RE.search(norm_block)
            or SEPARATE_PERIOD_EXCLUDE_RE.search(norm_block)
        ):
            continue

        # 5. A-4: 결정적 슬롯 추출 및 7대 선후 관계 쌍 기반 인과적 선후 역전 검증 (O(N) 묶음 비교)
        slots = _extract_clause_slots(norm_block)
        n_slots = len(slots)

        for i in range(n_slots):
            for j in range(i + 1, n_slots):
                if n_slots > 30 and j - i > 4:
                    break
                s1, s2 = slots[i], slots[j]

                # 1) 상대 일자 계산 불일치 검사 (민법 제157조 초일 불산입 기준 익일 불일치)
                cause_date_slot = s1 if s1.date_obj else (s2 if s2.date_obj else None)
                next_day_slot = s2 if s2.is_next_day else (s1 if s1.is_next_day else None)
                if cause_date_slot and next_day_slot and cause_date_slot != next_day_slot:
                    d_stated = next_day_slot.date_obj
                    if not d_stated:
                        m_st = re.search(_DATE_PAT, next_day_slot.clause_text)
                        if m_st:
                            d_stated = _parse_date_str(m_st.group(0))
                    if d_stated:
                        expected_d = cause_date_slot.date_obj + datetime.timedelta(days=1)
                        if d_stated != expected_d:
                            _emit_temporal_inversion(
                                block_obj=block,
                                heading=eff_h,
                                rule_sub_id="RELATIVE_NEXT_DAY_INVERSION",
                                evidence_grade=EvidenceGrade.C,  # 조건 5: 상대 일자 계산 불일치는 C등급
                                title=f"상대 일자 계산·선후 모순: {cause_date_slot.surface_form}({cause_date_slot.date_raw})의 다음 날이 {d_stated}로 기재",
                                detail_body=(
                                    f"{cause_date_slot.date_raw} '{cause_date_slot.surface_form}'의 다음 날(민법 제157조 초일 불산입 기준 {expected_d})을 "
                                    f"불일치하는 {d_stated}로 기재하여 달력 계산과 충돌한다."
                                ),
                                excerpt_text=f"{cause_date_slot.clause_text} ... {next_day_slot.clause_text}",
                                extra_features={
                                    "cause_date": str(cause_date_slot.date_obj),
                                    "effect_date": str(d_stated),
                                    "expected_date": str(expected_d),
                                },
                            )

                # 2) 상대 기간 근무 후 사직·퇴사 또는 일자 불일치 검사 (민법 제157조·제160조)
                dur_slot = s2 if s2.relative_duration else (s1 if s1.relative_duration else None)
                base_slot = s1 if s1.kind == "입사" or (s1.date_obj and s1 != dur_slot) else (s2 if s2.date_obj and s2 != dur_slot else None)
                if base_slot and dur_slot and base_slot.date_obj and dur_slot.relative_duration:
                    n_val, unit = dur_slot.relative_duration
                    d_stated = dur_slot.date_obj
                    if not d_stated:
                        m_st = re.search(_DATE_PAT, dur_slot.clause_text)
                        if m_st:
                            d_stated = _parse_date_str(m_st.group(0))
                    if d_stated:
                        earliest_expiry = _add_civil_period(
                            base_slot.date_obj,
                            n_val,
                            unit,
                            inclusive=base_slot.is_zero_hour,
                            adjust_holiday=False,
                        )
                        exclusive_expiry = _add_civil_period(
                            base_slot.date_obj,
                            n_val,
                            unit,
                            inclusive=False,
                            adjust_holiday=True,
                        )
                        if d_stated < base_slot.date_obj:
                            _emit_temporal_inversion(
                                block_obj=block,
                                heading=eff_h,
                                rule_sub_id="LIFECYCLE_DURATION_INVERSION",
                                evidence_grade=EvidenceGrade.B,  # 개시일 자체보다 앞선 날짜는 절대 일자 모순으로 B등급
                                title=f"사건 일자·기간 선후 모순: {base_slot.surface_form}({base_slot.date_raw})로부터 {n_val}{unit} 근무 뒤 일자가 {d_stated}로 기재",
                                detail_body=(
                                    f"'{base_slot.surface_form}'을 {base_slot.date_raw}로 적으면서 {n_val}{unit} 근무한 뒤의 "
                                    f"사직·퇴사 관련 일자가 그보다 앞선 {d_stated}로 나타나 선후 관계가 모순된다 "
                                    f"(민법 제157조·제160조상 최소 만료일: 초일 산입 {earliest_expiry}, 초일 불산입 {exclusive_expiry})."
                                ),
                                excerpt_text=f"{base_slot.clause_text} ... {dur_slot.clause_text}",
                                extra_features={
                                    "cause_date": str(base_slot.date_obj),
                                    "effect_date": str(d_stated),
                                    "earliest_expiry": str(earliest_expiry),
                                    "exclusive_expiry": str(exclusive_expiry),
                                },
                            )
                        elif d_stated < earliest_expiry:
                            _emit_temporal_inversion(
                                block_obj=block,
                                heading=eff_h,
                                rule_sub_id="RELATIVE_PERIOD_INVERSION",
                                evidence_grade=EvidenceGrade.C,  # 상대 기간 만료일 불일치는 C등급
                                title=f"상대 기간 선후 모순: {base_slot.surface_form}({base_slot.date_raw})로부터 {n_val}{unit} 뒤가 {d_stated}로 기재",
                                detail_body=(
                                    f"{base_slot.date_raw} '{base_slot.surface_form}' 이후 {n_val}{unit}이 지난 시점(민법 제157조·제160조·제161조 최소 만료일 {earliest_expiry})을 "
                                    f"그보다 앞선 {d_stated}로 기재하여 선후 관계가 모순된다."
                                ),
                                excerpt_text=f"{base_slot.clause_text} ... {dur_slot.clause_text}",
                                extra_features={
                                    "cause_date": str(base_slot.date_obj),
                                    "effect_date": str(d_stated),
                                    "earliest_expiry": str(earliest_expiry),
                                },
                            )

                # 3) 각 선후 규칙 검사 (절대 일자 2개 역전)
                for rule in EVENT_ORDER_RULES:
                    c_kind = rule["cause_kind"]
                    e_kinds = rule["effect_kinds"]

                    cause_slot: Optional[EventSlot] = None
                    effect_slot: Optional[EventSlot] = None

                    if s1.kind == c_kind and s2.kind in e_kinds:
                        cause_slot, effect_slot = s1, s2
                    elif s2.kind == c_kind and s1.kind in e_kinds:
                        cause_slot, effect_slot = s2, s1

                    if not cause_slot or not effect_slot:
                        continue

                    # 조건 4: 동일 주체 요구 검증 (입사 -> 퇴사 생애주기 등)
                    if rule.get("require_same_subject"):
                        if cause_slot.subject and effect_slot.subject and cause_slot.subject != effect_slot.subject:
                            continue

                    # 조건 3: 대상 일치 요구 검증
                    if rule.get("require_target_match"):
                        c_target = cause_slot.target or cause_slot.kind
                        e_target = effect_slot.target or effect_slot.kind
                        if not e_target and effect_slot.has_anaphora:
                            e_target = c_target
                        matched_target = False
                        if e_target and (
                            _same_object_noun(c_target, e_target)
                            or c_target in e_target
                            or e_target in c_target
                            or c_target in effect_slot.clause_text
                            or e_target in cause_slot.clause_text
                        ):
                            matched_target = True
                        elif c_target and (c_target in effect_slot.clause_text or e_target in cause_slot.clause_text):
                            matched_target = True

                        # 발생 -> 청구 대상 결합: 사고/손해 <-> 보험금/손해배상/청구
                        if not matched_target and rule["rule_id"] == "OCCURRENCE_BEFORE_CLAIM":
                            acc_words = ("사고", "교통사고", "손해", "사건")
                            claim_words = ("보험금", "손해배상", "손해배상금", "청구", "지급", "배상", "치료비")
                            c_is_acc = any(w in c_target for w in acc_words) or any(w in cause_slot.clause_text for w in acc_words)
                            e_is_claim = any(w in e_target for w in claim_words) or any(w in effect_slot.clause_text for w in claim_words)
                            if c_is_acc and e_is_claim:
                                matched_target = True

                        if not matched_target:
                            continue

                    # 두 슬롯 모두 절대 일자(date_obj)를 가진 경우
                    if cause_slot.date_obj and effect_slot.date_obj:
                        d_cause = cause_slot.date_obj
                        d_effect = effect_slot.date_obj

                        if d_effect < d_cause:
                            excerpt = f"{cause_slot.surface_form}({cause_slot.date_raw}) <-> {effect_slot.surface_form}({effect_slot.date_raw})"
                            sub_id = rule["rule_id"]
                            if sub_id == "SAME_SUBJECT_LIFECYCLE" and (
                                cause_slot.relative_duration
                                or effect_slot.relative_duration
                                or any(k in norm_block for k in ("근무한", "재직한", "복무한", "거주한"))
                            ):
                                sub_id = "LIFECYCLE_DURATION_INVERSION"

                            _emit_temporal_inversion(
                                block_obj=block,
                                heading=eff_h,
                                rule_sub_id=sub_id,
                                evidence_grade=EvidenceGrade.B,  # 조건 5: 절대 일자 2개 역전은 B등급
                                title=f"사건 일자 선후 모순: {cause_slot.surface_form}({cause_slot.date_raw})보다 {effect_slot.surface_form}({effect_slot.date_raw})이 앞섬",
                                detail_body=(
                                    f"선행 '{cause_slot.surface_form}({cause_slot.date_raw})'보다 후행 "
                                    f"'{effect_slot.surface_form}({effect_slot.date_raw})'이 시간상 앞서 기재되어 "
                                    f"인과적 선후 관계가 모순된다 ({rule['statute']})."
                                ),
                                excerpt_text=excerpt,
                                extra_features={
                                    "cause_date": str(d_cause),
                                    "effect_date": str(d_effect),
                                    "statute": rule["statute"],
                                },
                            )

                # 4) 동일 일자 내 시각 역전 및 상대 시각 역전 검사
                if (
                    s1.time_min is not None
                    and s2.time_min is not None
                    and (
                        (s1.date_obj and s2.date_obj and s1.date_obj == s2.date_obj)
                        or ("같은 날" in s2.clause_text or "당일" in s2.clause_text)
                        or ("같은 날" in s1.clause_text or "당일" in s1.clause_text)
                    )
                ):
                    # 상대 시각 표지 ("앞선", "이른") 검사
                    is_rel_earlier = bool(re.search(r"(?:앞선|먼저|이른)", s2.clause_text))
                    if is_rel_earlier:
                        if s2.time_min >= s1.time_min:
                            excerpt = f"{s1.surface_form}({s1.time_str}) <-> {s2.surface_form}({s2.time_str})"
                            _emit_temporal_inversion(
                                block_obj=block,
                                heading=eff_h,
                                rule_sub_id="SAME_DAY_EARLIER_TIME_INVERSION",
                                evidence_grade=EvidenceGrade.B,
                                title=f"동일 일자 시각 선후 모순: {s1.surface_form} 시각({s1.time_str})보다 앞선 시각이 같은 날 {s2.time_str}로 기재",
                                detail_body=(
                                    f"{s1.surface_form} 시각({s1.time_str})보다 앞선 시점이라고 서술하면서 "
                                    f"실제 시각은 그보다 늦은 같은 날 {s2.time_str}로 기재하여 시간 선후 관계가 충돌한다."
                                ),
                                excerpt_text=excerpt,
                                extra_features={
                                    "cause_time": s1.time_str,
                                    "effect_time": s2.time_str,
                                },
                            )
                    # 동일 목적물 최초 확보 후 전달/인계 시각 역전
                    elif s1.target and s2.target and _same_object_noun(s1.target, s2.target):
                        if (
                            any(k in s1.surface_form or k in s1.clause_text for k in ("확보", "수령", "회수", "입수"))
                            and any(k in s2.surface_form or k in s2.clause_text for k in ("인계", "전달", "교부", "제출", "반출"))
                        ):
                            if s2.time_min < s1.time_min:
                                excerpt = f"{s1.surface_form}({s1.time_str}) <-> {s2.surface_form}({s2.time_str})"
                                _emit_temporal_inversion(
                                    block_obj=block,
                                    heading=eff_h,
                                    rule_sub_id="SAME_OBJECT_FIRST_ACQUIRE_TIME_INVERSION",
                                    evidence_grade=EvidenceGrade.B,
                                    title=f"동일 목적물 시각 선후 모순: {s1.target} 최초 확보({s1.time_str})보다 앞서 같은 날 {s2.time_str}에 인계·전달 기재",
                                    detail_body=(
                                        f"동일 목적물('{s1.target}')을 {s1.time_str}에 처음 확보하였다고 하면서, "
                                        f"그보다 앞선 같은 날 {s2.time_str}에 이미 전달·인계되었다고 기재하여 시각 순서가 역전되었다."
                                    ),
                                    excerpt_text=excerpt,
                                    extra_features={
                                        "acquire_time": s1.time_str,
                                        "transfer_time": s2.time_str,
                                    },
                                )

    return findings
