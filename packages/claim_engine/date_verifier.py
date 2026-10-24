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

# A-4 2. 기관명 접미 규칙 (조건 6, R5: 기관명 열거 금지, 접미 규칙으로 포착, U3: 재판장·판사 포함)
ORGAN_SUFFIX_RE = re.compile(
    r"[가-힣]{0,15}(?:법원|위원회|세무서|경찰서|소방서|관할청|처분청|행정청|검찰청|노동청|국세청|구청|시청|지청|공단|사무소|공사|재판장|판사)"
)

# 주체 추출 정규식: 당사자 호칭 또는 기관명 접미 + 주격/보조사
SUBJECT_RE = re.compile(
    r"(?:(?P<party>" + "|".join(PARTY_TITLES) + r")|(?P<organ>[가-힣]{0,15}(?:법원|위원회|세무서|경찰서|소방서|관할청|처분청|행정청|검찰청|노동청|국세청|구청|시청|지청|공단|사무소|공사|재판장|판사)))"
    r"(?P<particle>[은는이가의])"
)

# 절 분리 정규식: 쉼표, 세미콜론, 연결어미 (-고, -며, -나, -한 후, -한 뒤, -하여, -한바 등), 관형절 경계, 문장 종결어미 (R2)
CLAUSE_DELIMITER_RE = re.compile(
    r",\s*|;\s*|\n+|"
    r"(?<=[가-힣][다음함임것바기]\.)\s+|"
    r"(?:"
    r"(?<=[가-힣])(?:하고|했고|하고는|하며|했으나|하나|하지만|하였고|하였으나|하였으며|(?<!대)(?<!관)(?<!의)하여|한바|인바|"
    r"하였는데|되었는데|했는데|한데|인데|였는데|았는데|었는데|은바|는바|"
    r"(?:한|된|받은|보낸|마친|끝난)\s*(?:후|뒤|다음)(?:에|는|,|\s)?)|"
    r"(?:(?<=\.)|(?<=\d)|\s+)이(?:고|며|나|지만|인데)|"
    r"(?:(?<=\.)|(?<=\d)|\s+)에\s*대한|"
    r"(?<=[가-힣])(?:내린|처분한|결정한|신청한|청구한|제출한|발송한|송부한|체결한|약정한|작성한)\s+(?=[가-힣]{2,})|"
    r"(?<=[가-힣])(?:다가|자마자|자)\s+"
    r")\s*"
)

# R3: 문서 명사는 사건이 아니라 대상(OBJECT) 사전으로 분리
DOCUMENT_OBJECT_NOUNS: Tuple[str, ...] = (
    "신청서", "청구서", "소장", "의견서", "답변서", "준비서면",
    "통지서", "최고서", "처분서", "결정서", "보정명령서", "결정문", "통지문",
    "확인서", "증명서", "산정서", "계약서", "합의서", "약정서", "공문",
    "임대차계약", "공급계약", "매매계약", "근로계약", "업무협약", "임대차", "근무기간", "임대기간", "계약기간",
)

# R6: 명확한 5대 제외 대상 정규식 (절 단위 검사)
EXCLUDE_CASE_LAW_RE = re.compile(
    r"(?:대법원|판결|판례|헌법재판소|결정례|선고|대판|선기)\s*(?:\d{2,4}[가-힣]+\d+|\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.|\([가-힣\s]+\))|"
    r"(?:법|령|규칙)\s*제\s*\d+\s*조"
)
EXCLUDE_FUTURE_RE = re.compile(
    r"(?:변제기|이행기|예정(?:이다|일|이며|이나)?|하기로\s*한다|하기로\s*약정|도래하지|기한이\s*도래)"
)
EXCLUDE_OPPONENT_CLAIM_RE = re.compile(
    r"(?:(?:라고|다고|라며|다며)\s*(?:(?:주장|진술|항변|번복)(?:하|합|했|하였|한)|다(?:투|툽|퉜|퉈))|"
    r"(?:라는|다는)\s*(?:피고|원고|신청인|상대방)?\s*(?:의\s*)?주장은)"
)
EXCLUDE_NEGATION_RE = re.compile(
    r"(?:하지\s*않았|하지\s*아니하였|한\s*사실이\s*없|한\s*바\s*없|되지\s*않았|아니하였다|없었다|아니다)"
)
# U2: 정정 서술 표지 통합 및 확장 ('착오이므로·오기이므로·바로잡는다' 포괄)
CORRECTION_MARKER_RE = re.compile(
    r"(?:(?:착오|오기)(?:이므로|이다|로|였|입)?|바로잡(?:는|는다면|는다|음|은|고자)?|정정(?:한다|합니다|하여|한|합니|되)?|이\s*아니라|가\s*아니라)"
)
EXCLUDE_CORRECTION_RE = CORRECTION_MARKER_RE

# 문장 종결자 정규식: 한글 뒤 마침표, 세미콜론, 개행 (날짜 마침표 오인 방지)
SENTENCE_DELIM_RE = re.compile(r"(?<=[가-힣])\.\s*|[;\n]+")

# A-4 3. 7대 사건 종류 표면형 닫힌 사전 (R3: 행위 동사 및 파생어만 유지, 문서 명사 및 삭제 대상 제거)
EVENT_KIND_SURFACE_FORMS: Dict[str, Tuple[str, ...]] = {
    "신청": (
        "허가신청", "변경신청", "교부신청", "재심청구", "심판청구", "구제신청", "지급청구", "손해배상청구", "소송제기",
        "손해배상 청구", "손해배상금 지급청구", "보험금 청구",
        "신청", "청구", "제기", "제출",
        "신청하", "청구하", "제기하", "제출하",
        "신청했", "청구했", "제기했", "제출했",
        "신청한", "청구한", "제기한", "제출한",
        "신청된", "청구된", "제기된", "제출된",
        "신청되어", "청구되어", "제기되어", "제출되어",
    ),
    "처분": (
        "과징금부과처분", "영업정지처분", "직위해제처분", "거부처분", "불승인처분", "불허가처분",
        "기각결정", "각하결정", "인용결정", "승인처분", "인가처분",
        "처분", "결정", "명령", "판정", "의결",
        "처분하", "결정하", "명령하", "판정하", "의결하",
        "처분했", "결정했", "명령했", "판정했", "의결했",
        "처분한", "결정한", "명령한", "판정한", "의결한",
        "처분된", "결정된", "내려진", "발령", "발령된", "명령된",
        "처분되어", "결정되어", "발령되어",
    ),
    "통지": (
        "해제통지", "해지통지", "결과통지", "최고",
        "해제 통지", "해지 통지",
        "통지", "발령", "고지", "통고", "회신", "통보",
        "통지하", "발령하", "고지하", "통고하", "회신하", "통보하",
        "통지했", "발령했", "고지했", "통고했", "회신했", "통보했",
        "통지한", "발령한", "고지한", "통고한", "회신한", "통보한",
        "통지된", "발령된", "고지된", "통보된",
    ),
    "발송": (
        "발송일", "발신일", "송부일", "발송일시", "발신일시",
        "발송", "송부", "발신",
        "발송하", "송부하", "발신하",
        "발송했", "송부했", "발신했",
        "보냈", "보낸", "부친", "부쳤",
        "발송한", "송부한", "발신한",
        "발송된", "송부된", "발신된",
    ),
    "도달": (
        "결정도달", "송달", "도달일", "수령일", "송달일", "도달일시", "수령일시", "송달일시",
        "도달", "수령", "수신", "송달",
        "도달하", "수령하", "수신하", "송달하",
        "도달했", "수령했", "수신했", "송달했", "송달받", "송달받았",
        "도달한", "수령한", "수신한", "송달한", "송달받은",
        "도달된", "수령된", "수신된", "송달된",
    ),
    "체결": (
        "계약체결", "협약체결", "합의체결",
        "체결일", "계약체결일", "체결", "약정", "계약을맺",
        "체결하", "약정하", "체결했", "약정했",
        "체결한", "약정한", "맺었", "맺은",
        "체결된", "약정된",
    ),
    "이행": (
        "이행", "변제", "지급", "인도",
        "이행하", "변제하", "지급하", "인도하",
        "이행했", "변제했", "지급했", "인도했",
        "이행한", "변제한", "지급한", "인도한",
        "이행된", "변제된", "지급된", "인도된",
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
        "입사하", "채용하", "취직하", "임용하",
        "입사했", "채용했", "취직했", "임용했",
        "입사한", "채용된", "임용된",
    ),
    "퇴사": (
        "최종퇴사일", "최종퇴직일", "퇴사일", "퇴직일", "해고일", "사직일", "근무종료일",
        "사직통지", "사직 통지", "해고통지", "해고 통지",
        "퇴사", "퇴직", "해고", "사직", "근무종료", "최종퇴사", "최종퇴직",
        "퇴사하", "퇴직하", "해고하", "사직하",
        "퇴사했", "퇴직했", "해고했", "사직했", "퇴사한", "퇴직한", "해고된", "사직한",
    ),
    "접수": (
        "소장접수", "사건접수", "신청접수", "접수일",
        "접수", "접수하", "접수했", "접수한", "접수된", "접수되었", "접수되어", "접수되",
    ),
    "신고": (
        "신고일", "신고접수일", "사고신고",
        "신고",
        "신고하", "신고했", "신고한",
        "신고되", "신고된", "신고되었", "신고되어",
    ),
    "보정": (
        "보정",
        "보정하", "보정했", "보정한",
        "보정명령을내",
    ),
    "발생": (
        "사고발생", "손해발생", "사건발생", "발생일", "사고발생일",
        "교통사고", "사고", "손해",
        "발생", "성립", "발생하", "성립하", "발생했", "성립했", "발생한", "성립한",
    ),
    "기간시작": (
        "개시일", "시작일", "기산일", "개시", "시작", "기산", "부터",
    ),
    "기간종료": (
        "종료일", "만료일", "종기일", "종료", "만료", "종기", "까지", "끝난뒤", "종료된후", "끝난후", "마친뒤",
    ),
}

# A-4 4. 법률상 선후 관계 닫힌 쌍 및 근거 조문 (R4: require_target_match 전면화, R5: 주체 관계 검증, R9: 규칙 8 삭제)
EVENT_ORDER_RULES: List[Dict[str, Any]] = [
    # 1. 신청 -> 처분 (행정절차법 제17조, 근로기준법 제28조)
    {
        "cause_kind": "신청",
        "effect_kinds": ("처분",),
        "rule_id": "TARGET_BOUND_DISPOSITION",
        "statute": "행정절차법 제17조·근로기준법 제28조",
        "require_target_match": True,
        "require_different_subject": True,  # R5: 신청인 vs 처분청 (주체 상이 필수)
        "description": "선행 신청·청구보다 그에 대한 처분·결정이 앞서 기재됨",
    },
    # 1-2. 신청 -> 통지 (조건 3: 신청->통지는 통지의 대상이 그 신청일 때만!)
    {
        "cause_kind": "신청",
        "effect_kinds": ("통지",),
        "rule_id": "TARGET_BOUND_DISPOSITION",
        "statute": "행정절차법 제17조",
        "require_target_match": True,
        "require_different_subject": True,
        "description": "선행 신청보다 그 신청에 대한 통지가 앞서 기재됨",
    },
    # 2. 발송/통지 -> 도달/수령 (민법 제111조)
    {
        "cause_kind": "발송",
        "effect_kinds": ("도달",),
        "rule_id": "SEND_BEFORE_RECEIPT",
        "statute": "민법 제111조",
        "require_target_match": True,
        "require_different_subject": True,  # R5: 발신자 vs 수신자 (주체 상이 필수)
        "description": "발송일시보다 도달·수령일시가 앞서 기재됨",
    },
    {
        "cause_kind": "통지",
        "effect_kinds": ("도달",),
        "rule_id": "SEND_BEFORE_RECEIPT",
        "statute": "민법 제111조",
        "require_target_match": True,
        "require_different_subject": True,
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
        "require_target_match": False,  # 입사-퇴사는 대상이 아니라 동일 주체 생애주기
        "require_same_subject": True,  # R5: 동일 주체 한정
        "description": "동일 주체의 입사·채용일보다 퇴사·해고일이 앞서 기재됨",
    },
    # 5. 접수 -> 보정/결정 (민사소송법 제254조)
    {
        "cause_kind": "접수",
        "effect_kinds": ("보정", "처분"),
        "rule_id": "RECEIPT_BEFORE_AMENDMENT",
        "statute": "민사소송법 제254조",
        "require_target_match": True,
        "require_different_subject": True,  # R5: 접수자 vs 법원
        "description": "사건 접수일보다 보정명령·권고일이 앞서 기재됨",
    },
    # 6. 발생 -> 청구/신고 (상법 제724조·민법 제750조)
    {
        "cause_kind": "발생",
        "effect_kinds": ("신청", "신고"),
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
        "require_target_match": True,
        "description": "기간 개시일보다 기간 종료일이 앞서 기재됨",
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


def _normalize_target(t: str) -> str:
    """대상 명사구에서 지시어('이 사건', '위', '해당', '동', '본건', '이', '그') 및 공백을 정규화하고,
    대상 끝에 붙은 사건 낱말(신청·청구·처분·통지·명령·결정·계약)을 분리한다 (W3, Z2).
    """
    if not t:
        return ""
    cleaned = re.sub(r"^(?:이\s*사건|위|해당|동|본건|이|그)\s*", "", t).strip()
    # 관형사형 용언 접두어(낸, 한, 제출한, 제기한, 내린, 받은, 보낸, 작성한, 송부한 등) 제거 (Z2)
    cleaned = re.sub(r"^(?:낸|한|제출한|제기한|내린|받은|보낸|작성한|송부한)\s*", "", cleaned)
    # 대상 끝에 사건 낱말이 붙어 있고 앞에 핵심 명사가 있는 경우(예: '인가 신청' -> '인가', '인가 처분' -> '인가') 분리
    m = re.match(r"^(?P<core>.+?)\s*(?:신청|청구|처분|통지|명령|결정|계약)(?:서|문)?$", cleaned)
    if m and m.group("core").strip():
        cleaned = m.group("core").strip()
    return re.sub(r"\s+", "", cleaned)


def _extract_target_modifier(t: str) -> Optional[str]:
    """대상 명사구 앞 수식어('1차', '2차', 'A', 'B' 등)를 추출한다 (R4)."""
    if not t:
        return None
    cleaned = re.sub(r"^(?:이\s*사건|위|해당|동|본건|이|그)\s*", "", t).strip()
    m = re.match(r"^((?:\d+차|[A-Za-z]))(?:\s+|$)", cleaned)
    return m.group(1) if m else None


def _same_object_noun(
    left: str,
    right: str,
    left_has_anaphora: bool = False,
    right_has_anaphora: bool = False,
) -> bool:
    """두 목적물 명사가 엄격히 일치하는지 판정한다 (R4, W3, Z4).

    핵심 명사와 수식어가 모두 같아야 하며, '1차 처분'과 '2차 처분'처럼 수식어가 다르면 다른 대상으로 본다.
    접미 일치는 짧은 쪽이 지시어로 해소된 대상(has_anaphora)이고, 긴 쪽이 바로 앞 대상일 때만 허용한다 (Z4).
    그 밖에는 핵심 명사 완전 일치만 인정한다.
    """
    mod_l = _extract_target_modifier(left)
    mod_r = _extract_target_modifier(right)
    if mod_l or mod_r:
        if mod_l != mod_r:
            return False

    a = _normalize_target(left)
    b = _normalize_target(right)
    if not a or not b:
        return False
    if a == b:
        return True
    # Z4: 접미 일치는 짧은 쪽이 지시어로 해소된 대상이고 긴 쪽의 접미어일 때만 허용
    if len(a) > len(b) and a.endswith(b) and len(b) >= 2 and right_has_anaphora:
        return True
    if len(b) > len(a) and b.endswith(a) and len(a) >= 2 and left_has_anaphora:
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
        is_new_cycle: bool = False,
        has_subsequent_order: bool = False,
        period_group_id: Optional[int] = None,
        subject: Optional[str] = None,
        target: Optional[str] = None,
        cause_target: Optional[str] = None,
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
        self.is_new_cycle = is_new_cycle
        self.has_subsequent_order = has_subsequent_order
        self.period_group_id = period_group_id
        self.subject = subject
        self.target = target
        self.cause_target = cause_target
        self.has_anaphora = has_anaphora
        self.span_in_block = span_in_block

    def __repr__(self) -> str:
        return f"<EventSlot kind={self.kind} date={self.date_obj} subj={self.subject} target={self.target} cause_tgt={self.cause_target}>"


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

# 대상 명사구 추출 정규식: 사건 표면형 앞 명사구 (최대 3개 명사, 날짜 앞뒤 유연화, 부사어 허용) (Z2)
TARGET_PRE_RE = re.compile(
    r"(?P<target>(?:[그위해당동이]\s*)?(?:(?:\d+차|[A-Za-z])\s+)?(?:[가-힣0-9]{1,15}\s+){0,2}[가-힣0-9]{1,15})"
    r"(?:\s*(?:\d{4}[.\s\-년]+\d{1,2}[.\s\-월]+\d{1,2}[일\s.]*|\d{1,2}[.\s\-월]+\d{1,2}[일\s.]*))?"
    r"(?:의|에\s*대한|에\s*대하여|에\s*관한|에\s*관하여|[을를]|자)"
    r"(?:\s*(?:\d{4}[.\s\-년]+\d{1,2}[.\s\-월]+\d{1,2}[일\s.]*|\d{1,2}[.\s\-월]+\d{1,2}[일\s.]*))?"
    r"(?:\s*[가-힣0-9]{1,10}(?:에|에게|으로|로))?"
    r"(?:\s*(?:기각|각하|인용|거부|불허|승인|취소|불승인|일체))?\s*$"
)

# U1: 순서 연결어 정규식 및 헬퍼
SUBSEQUENT_ORDER_RE = re.compile(r"(?:그\s*후|이후|그\s*뒤|뒤이어|다음에)")
CONJUGATED_ORDER_RE = re.compile(r"(?P<verb>[가-힣]+)\s*(?P<conn>뒤|후|다음)|다가")


def _has_jongseong_nieun(ch: str) -> bool:
    """한글 음절의 종성이 'ㄴ'인지 검사한다 (U1: -ㄴ 뒤, -ㄴ 후, -ㄴ 다음)."""
    if len(ch) != 1 or not ('가' <= ch <= '힣'):
        return False
    return (ord(ch) - 0xAC00) % 28 == 4


def _has_narrative_order_connective(text: str) -> bool:
    """두 슬롯 사이 또는 절에 순서 연결어(-ㄴ 뒤|-ㄴ 후|-ㄴ 다음|-다가|이후|그 후)가 있는지 검사한다 (U1)."""
    if SUBSEQUENT_ORDER_RE.search(text):
        return True
    for m in CONJUGATED_ORDER_RE.finditer(text):
        if "다가" in m.group(0):
            return True
        verb = m.group("verb")
        if verb:
            if verb.endswith(("은", "는", "던", "후", "뒤", "다음")):
                return True
            if _has_jongseong_nieun(verb[-1]):
                return True
    return False


def _is_passive_or_intransitive_event(kind: str, surf: str) -> bool:
    """피동·자동사 사건 낱말인지 판정한다 (U3: 접수되·발생하·도달하·송달되·해지되·체결되·발령되·결정되·내려지 등)."""
    if kind in ("접수", "발생", "도달"):
        return True
    return any(p in surf for p in ("접수", "발생", "도달", "송달", "해지되", "체결되", "발령되", "결정되", "내려지", "이루어지"))


def _apply_correction_slots(block_text: str, slots: List[EventSlot]) -> List[EventSlot]:
    """정정 문장 안에서는 정정 전 값(표지 앞 값)의 슬롯을 지우고, 정정 후 값('…로 바로잡/정정')만 남겨 반환한다 (U2)."""
    if not CORRECTION_MARKER_RE.search(block_text):
        return slots

    new_slots = list(slots)
    handled_sentences = set()

    for m_corr in CORRECTION_MARKER_RE.finditer(block_text):
        m_start = m_corr.start()
        sent_start = 0
        for delim in SENTENCE_DELIM_RE.finditer(block_text[:m_start]):
            sent_start = delim.end()
        sent_end = len(block_text)
        m_end_delim = SENTENCE_DELIM_RE.search(block_text[m_start:])
        if m_end_delim:
            sent_end = m_start + m_end_delim.start()

        sent_key = (sent_start, sent_end)
        if sent_key in handled_sentences:
            continue
        handled_sentences.add(sent_key)

        sent_text = block_text[sent_start:sent_end]
        m_first = CORRECTION_MARKER_RE.search(sent_text)
        split_pos = sent_start + (m_first.start() if m_first else 0)

        pre_corr_text = block_text[sent_start:split_pos]
        post_corr_text = block_text[split_pos:sent_end]

        pre_dates = []
        for m_pd in re.finditer(_DATE_PAT, pre_corr_text):
            p_obj = _parse_date_str(m_pd.group(0))
            if p_obj:
                pre_dates.append((p_obj, m_pd.group(0).strip()))

        post_dates = []
        for m_n in re.finditer(_DATE_PAT, post_corr_text):
            n_obj = _parse_date_str(m_n.group(0))
            if n_obj:
                post_dates.append((n_obj, m_n.group(0).strip()))

        pre_slots = [
            s for s in new_slots
            if s.span_in_block[0] >= sent_start and s.span_in_block[0] < split_pos
        ]

        if post_dates:
            post_date_obj, post_date_raw = post_dates[-1]
            if pre_slots:
                for s in pre_slots:
                    s.date_obj = post_date_obj
                    s.date_raw = post_date_raw
            else:
                if pre_dates:
                    target_old_obj = pre_dates[-1][0]
                    for s in new_slots:
                        if s.date_obj == target_old_obj and s.span_in_block[0] < split_pos:
                            s.date_obj = post_date_obj
                            s.date_raw = post_date_raw
                            break
        else:
            for s in pre_slots:
                if s in new_slots:
                    new_slots.remove(s)

    return new_slots

# 연도 생략 날짜 정규식 (R9: M월 D일 또는 M. D.)
_DATE_NO_YEAR_RE = re.compile(
    r"(?<!\d)(?:(?P<m1>[01]?\d)\s*월\s*(?P<d1>[0-3]?\d)\s*일|(?P<m2>[01]?\d)\s*[./-]\s*(?P<d2>[0-3]?\d)\s*\.?)"
    r"(?:\s*\([월화수목금토일](?:요일)?\)|\s*[월화수목금토일]요일)?"
)


def _is_clause_excluded(clause_text: str) -> bool:
    """해당 절이 4대 제외 대상(판례/법령, 장래/예정, 상대방 주장, 부정)에 해당하는지 검사한다 (R6, U2: 정정은 문장 단위 처리로 이전)."""
    if EXCLUDE_CASE_LAW_RE.search(clause_text):
        return True
    if EXCLUDE_FUTURE_RE.search(clause_text):
        return True
    if EXCLUDE_OPPONENT_CLAIM_RE.search(clause_text):
        return True
    if EXCLUDE_NEGATION_RE.search(clause_text):
        return True
    return False


def _extract_clause_slots(block_text: str) -> List[EventSlot]:
    """블록 텍스트를 절 단위로 결정적 분리하고 각 절마다 사건 슬롯을 추출한다 (R1~R9 전면 반영)."""
    slots: List[EventSlot] = []

    # 블록 내 기준 연도 추적 (기본값)
    m_yr_block = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", block_text)
    current_year = int(m_yr_block.group(0)) if m_yr_block else None

    # 절 분리
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
    last_topic_target: Optional[str] = None
    next_clause_has_anaphora = False
    period_counter = 0
    prev_delim = ""

    for clause_text, start_pos, end_pos, delim_str in clause_parts:
        # R6: 5대 제외 문맥 절 단위 필터링 (구분자 결합 형태 포함 검사)
        if _is_clause_excluded(clause_text) or _is_clause_excluded(clause_text + delim_str):
            prev_delim = delim_str
            continue

        # 연도 추적
        m_yr = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", clause_text)
        if m_yr:
            current_year = int(m_yr.group(0))

        # 주체 추출 (R5: 기관명 접미 규칙 적용, 피동형 아닌 경우 같은 문장 물려받기)
        subj = None
        subj_span: Optional[Tuple[int, int]] = None
        m_subj = SUBJECT_RE.search(clause_text)
        if m_subj:
            subj = (m_subj.group("party") or m_subj.group("organ") or "").strip()
            subj_span = m_subj.span()
            last_subject = subj
        else:
            is_passive = bool(re.search(r"(?:내려진|내려졌|발령되|처분되|결정되|송달되|도달되|지급되|이루어졌)", clause_text))
            if last_subject and not is_passive:
                subj = last_subject

        # 마침표가 있으면 문장 종결로 보아 주체 및 피동 주제 물려받기 초기화 (Z2-④)
        if "." in delim_str:
            last_subject = None
            last_topic_target = None

        # 기간 표현 (D1부터 D2까지) 검사: 기간시작 및 기간종료 슬롯 생성 (R8: period_group_id 부여)
        m_period = re.search(
            rf"(?P<d1>{_DATE_PAT})\s*(?:부터|~|∼)\s*(?P<d2>{_DATE_PAT})\s*까지",
            clause_text,
        )
        if m_period:
            period_counter += 1
            d1_raw = m_period.group("d1").strip()
            d2_raw = m_period.group("d2").strip()
            d1_obj = _parse_date_str(d1_raw)
            d2_obj = _parse_date_str(d2_raw)

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
                    period_group_id=period_counter,
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
                    period_group_id=period_counter,
                    subject=subj,
                    target=target_period,
                    span_in_block=(start_pos, end_pos),
                )
            )
            continue

        # 절 내 날짜 수집 (절대 일자 및 연도 생략 일자 복원, R9)
        date_entries: List[Tuple[int, int, datetime.date, str]] = []
        for m_d in re.finditer(_DATE_PAT, clause_text):
            d_raw = m_d.group(0).strip()
            d_obj = _parse_date_str(d_raw)
            if d_obj:
                date_entries.append((m_d.start(), m_d.end(), d_obj, d_raw))

        if current_year:
            for m_ny in _DATE_NO_YEAR_RE.finditer(clause_text):
                if not any(d[0] <= m_ny.start() < d[1] for d in date_entries):
                    m_val = int(m_ny.group("m1") or m_ny.group("m2"))
                    d_val = int(m_ny.group("d1") or m_ny.group("d2"))
                    d_obj = _parse_valid_date(current_year, m_val, d_val)
                    if d_obj:
                        date_entries.append((m_ny.start(), m_ny.end(), d_obj, m_ny.group(0).strip()))

        # R7, U1: 새 주기 및 글쓴이가 밝힌 순서 표지 ('새로' 포괄)
        is_new_cycle = bool(re.search(r"(?:다시|재차|새로운|새로)", clause_text))
        has_subsequent_order = bool(re.search(r"(?:그\s*후|이후|뒤이어|다음에|그\s*뒤)", clause_text))

        # 상대 일자 표지
        is_next = bool(RELATIVE_NEXT_DAY_RE.search(clause_text))
        is_zero = bool(ZERO_HOUR_RE.search(clause_text))

        # 대상 수식어 구간(예: '위 인가 신청에 대하여', '이 사건 신청에 대한' 등) 수집
        target_prep_spans = []
        for m_tp in re.finditer(r"(?:[그위해당동본이]\s*)?[가-힣0-9]{1,10}\s*(?:에\s*(?:대한|대하여|대해|관한|관하여|관해))", clause_text):
            pre_part = clause_text[:m_tp.start()].rstrip()
            if pre_part.endswith(("한", "낸", "제출한", "신청한", "청구한", "받은", "내린")):
                continue
            target_prep_spans.append(m_tp.span())

        # 절 안의 모든 사건 낱말 출현 위치 수집 (R2)
        event_matches: List[Tuple[int, int, str, str]] = []
        for kind, surfs in EVENT_KIND_SURFACE_FORMS.items():
            for s in surfs:
                idx = 0
                while True:
                    f_idx = clause_text.find(s, idx)
                    if f_idx == -1:
                        break
                    # 주체 매칭 구간(예: '신청인은'의 '신청')은 배제
                    if subj_span and subj_span[0] <= f_idx < subj_span[1]:
                        idx = f_idx + len(s)
                        continue
                    # 대상 수식어 구간(예: '인가 신청에 대하여') 안의 사건 낱말은 배제
                    if any(sp[0] <= f_idx < sp[1] for sp in target_prep_spans):
                        idx = f_idx + len(s)
                        continue
                    event_matches.append((f_idx, f_idx + len(s), kind, s))
                    idx = f_idx + len(s)

        # 겹치는 구간 중 가장 긴 표면형만 선택하여 정렬
        event_matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        filtered_events: List[Tuple[int, int, str, str]] = []
        last_e = -1
        for start, end, kind, s in event_matches:
            if start >= last_e:
                filtered_events.append((start, end, kind, s))
                last_e = end

        # R1: 사건 낱말이 없는 절은 슬롯을 만들지 않는다 (기본값 분기 완전 삭제)
        if not filtered_events:
            continue

        # 각 사건 낱말마다 가장 가까운 날짜 및 주체 매칭 및 슬롯 생성 (R2, R5)
        clause_slots: List[EventSlot] = []
        for e_start, e_end, kind, surf in filtered_events:
            pre_text = clause_text[:e_start].strip()

            # 사건 낱말 단위 선행 주체 추출 (R5)
            evt_subj = None
            subj_matches = list(SUBJECT_RE.finditer(pre_text))
            if subj_matches:
                last_m_subj = subj_matches[-1]
                evt_subj = (last_m_subj.group("party") or last_m_subj.group("organ") or "").strip()
            elif subj:
                evt_subj = subj

            # 선행(수식) 날짜 최우선 매칭: 사건 낱말 앞선 날짜 중 가장 가까운 날짜
            matched_date_obj: Optional[datetime.date] = None
            matched_date_raw: str = ""
            if date_entries:
                pre_dates = [d for d in date_entries if d[1] <= e_start]
                if pre_dates:
                    best_date = min(pre_dates, key=lambda d: e_start - d[1])
                else:
                    best_date = min(date_entries, key=lambda d: abs(d[0] - e_start))
                matched_date_obj = best_date[2]
                matched_date_raw = best_date[3]

            # 대상(target) 추출 (R3: 문서 명사 우선, TARGET_PRE_RE, 지시어 해소, U3: 피동·자동사 대상 포착)
            target: Optional[str] = None
            has_anaphora = False

            # 1) 사건 낱말 앞 문서 명사구 우선 채택 (R3)
            for doc_n in DOCUMENT_OBJECT_NOUNS:
                if doc_n in pre_text or doc_n in clause_text:
                    target = doc_n
                    if any(ana in (pre_text or clause_text) for ana in ("그 " + doc_n, "위 " + doc_n, "해당 " + doc_n, "동 " + doc_n, "본건 " + doc_n, "이 사건 " + doc_n, "위" + doc_n)):
                        has_anaphora = True
                    last_target = target
                    last_topic_target = target
                    break

            # 2) TARGET_PRE_RE 매칭 (Z2: 최대 3개 명사, 날짜 앞뒤 유연화, 부사어 허용 및 W3 끝 분리)
            if not target:
                m_target = TARGET_PRE_RE.search(pre_text)
                if m_target:
                    t_raw = m_target.group("target").strip()
                    is_actor = (
                        t_raw in PARTY_TITLES
                        or bool(ORGAN_SUFFIX_RE.search(t_raw))
                        or t_raw in ("관할청", "처분청", "행정청", "재판장", "법원", "회사", "담당 부서")
                    )
                    if not is_actor:
                        t_has_ana = any(t_raw.startswith(ana) for ana in ("그", "위", "해당", "동", "본건", "이 사건"))
                        cleaned = _normalize_target(t_raw)
                        if t_has_ana:
                            has_anaphora = True
                            target = cleaned or last_target
                        else:
                            target = cleaned
                        if target:
                            last_target = target
                            last_topic_target = target

            # 2-2) 후행 텍스트가 '...에 대한 것입니다/처분입니다' 꼴인 경우, 대상 신청을 찾아 target으로 채택 (W3)
            if not target:
                m_post = re.search(
                    r"(?P<post_target>(?:[그위해당동이]\s*)?(?:(?:\d+차|[A-Za-z])\s+)?(?:[가-힣0-9]{1,15}\s+){0,2}[가-힣0-9]{1,15})"
                    r"(?:에\s*(?:대한|대하여|따른))\s*(?:것(?:이다|입니다)|처분|결정|명령)",
                    clause_text[e_end:]
                )
                if m_post:
                    pt_raw = m_post.group("post_target").strip()
                    pt_clean = _normalize_target(pt_raw)
                    if pt_clean:
                        target = pt_clean
                        last_target = target
                        last_topic_target = target

            # 3) U3: 피동·자동사 사건 낱말일 때, 같은 절의 'X(은|는|이|가)'에서 X가 문서·계약·사건 명사이면 X를 대상으로 바인딩
            if not target and _is_passive_or_intransitive_event(kind, surf):
                for m_topic in re.finditer(r"(?:^|[\s,;])(?P<x>(?:[그위해당동본이]\s*)?(?:(?:\d+차|[A-Za-z])\s+)?[가-힣0-9]{1,15})(?P<p>은|는|이|가)(?!\S)", clause_text):
                    cand_raw = m_topic.group("x").strip()
                    is_actor = (
                        cand_raw in PARTY_TITLES
                        or bool(ORGAN_SUFFIX_RE.search(cand_raw))
                        or cand_raw in ("관할청", "처분청", "행정청", "재판장", "법원", "회사", "담당 부서")
                    )
                    if is_actor:
                        continue
                    cand_clean = re.sub(r"^(?:그|위|해당|동|본건|이\s*사건)\s*", "", cand_raw).strip()
                    is_valid_object = (
                        cand_clean in DOCUMENT_OBJECT_NOUNS
                        or any(cand_clean.endswith(k) for k in ("계약", "협약", "합의", "신청", "청구", "처분", "명령", "사건", "소장", "화재", "사고", "손해", "재해", "보정"))
                    )
                    if is_valid_object:
                        if any(cand_raw.startswith(ana) for ana in ("그", "위", "해당", "동", "본건", "이 사건")):
                            has_anaphora = True
                            target = cand_clean or last_target
                        else:
                            target = cand_clean
                        last_target = target
                        last_topic_target = target
                        break

            # 4) 사건 표면형(surf) 자체에 고유 대상 명사가 합성된 경우 (예: '허가신청' -> '허가', '변경신청' -> '변경', '재심청구' -> '재심', '공사계약' -> '공사')
            # 처분의 성격/종류 명사('거부', '불승인', '기각', '각하', '승인', '인용', '불허', '불허가')는 고유 대상이 아니므로 제외
            if not target:
                surf_core = _normalize_target(surf)
                if surf_core and surf_core != surf and surf_core not in (
                    "신청", "청구", "처분", "결정", "통지", "명령", "계약",
                    "거부", "불승인", "기각", "각하", "승인", "인용", "불허", "불허가",
                ):
                    target = surf_core
                    last_target = target
                    last_topic_target = target

            # 4-2) 수식어('1차', '2차', 'A', 'B' 등) + 사건 낱말인 경우 (예: 'A 신청' -> 'A 신청', 'B 처분' -> 'B 처분')
            if not target:
                m_mod = re.search(r"(?:(?:\d+차|[A-Za-z])\s*)$", pre_text)
                if m_mod:
                    target = f"{m_mod.group(0).strip()} {surf}".strip()
                    last_target = target
                    last_topic_target = target

            # 5) Z2-④: 같은 문장에서 주어가 생략되었거나 대상이 생략된 다음 절은 앞 절의 대상 승계
            if not target and (last_topic_target or last_target):
                if (
                    _is_passive_or_intransitive_event(kind, surf)
                    or kind in ("도달", "보정", "처분")
                    or any(conn in prev_delim for conn in ("으나", "는데", "한바", "고", "지만"))
                    or ("." not in prev_delim and prev_delim)
                ):
                    target = last_topic_target or last_target
                    has_anaphora = True

            # 6) 지시어 처리 (Z1: 풀리지 않은 지시어는 대상이 없는 것으로 봄)
            if any(ana in clause_text for ana in ("이에 대한", "그에 대한", "위 처분", "위 계약", "이 사건", "그 처분", "그 계약", "해당 계약")):
                if not target and last_target:
                    has_anaphora = True
                    target = last_target

            if next_clause_has_anaphora and not target and last_target:
                has_anaphora = True
                target = last_target

            if not target and last_target and has_anaphora:
                target = last_target

            # Z2-③: 청구·신고 사건의 원인 대상(cause_target) 추출
            cause_target: Optional[str] = None
            if kind in ("신청", "신고"):
                m_cause = re.search(
                    r"(?P<cx>(?:[그위해당동이]\s*)?(?:(?:\d+차|[A-Za-z])\s+)?(?:[가-힣0-9]{1,15}\s+){0,2}[가-힣0-9]{1,15})"
                    r"(?:으로\s*인한|로\s*인한|에\s*따른|에\s*관한)",
                    clause_text[:e_end]
                )
                if m_cause:
                    cx_raw = m_cause.group("cx").strip()
                    cx_has_ana = any(cx_raw.startswith(ana) for ana in ("그", "위", "해당", "동", "본건", "이 사건"))
                    cx_clean = _normalize_target(cx_raw)
                    if cx_has_ana:
                        has_anaphora = True
                        cause_target = cx_clean or last_target
                    else:
                        cause_target = cx_clean

            slot = EventSlot(
                clause_text=clause_text,
                kind=kind,
                surface_form=surf,
                date_obj=matched_date_obj,
                date_raw=matched_date_raw,
                is_next_day=is_next,
                is_zero_hour=is_zero,
                is_new_cycle=is_new_cycle,
                has_subsequent_order=has_subsequent_order,
                subject=evt_subj,
                target=target,
                cause_target=cause_target,
                has_anaphora=has_anaphora,
                span_in_block=(start_pos, end_pos),
            )
            clause_slots.append(slot)
        # 한 절 내 동일 kind & 동일 date_obj 중복 슬롯 제거 (가장 긴 표면형 유지)
        seen_clause_kinds: Dict[Tuple[str, Optional[datetime.date]], EventSlot] = {}
        for cs in clause_slots:
            k = (cs.kind, cs.date_obj)
            if k not in seen_clause_kinds or len(cs.surface_form) > len(seen_clause_kinds[k].surface_form):
                seen_clause_kinds[k] = cs
        slots.extend(seen_clause_kinds.values())

        if "에 대한" in delim_str or "에 대하여" in delim_str or "에 관한" in delim_str or "에 관하여" in delim_str:
            next_clause_has_anaphora = True
        else:
            next_clause_has_anaphora = False
        prev_delim = delim_str

    # 지시어 해소: 대상이 없거나 지시어가 있는데 아직 안 풀린 경우 앞선 슬롯에서 해소 (R4: 직전 대상 치환)
    for i in range(len(slots)):
        if slots[i].has_anaphora:
            for j in range(i - 1, -1, -1):
                if slots[j].target:
                    slots[i].target = slots[j].target
                    break

    # U2: 정정 문장 안에서는 정정 전 값(표지 앞 값)의 슬롯을 지우고, 정정 후 값('…로 바로잡/정정')만 남긴다
    slots = _apply_correction_slots(block_text, slots)

    # W2: 상대방 주장 문장 내 모든 슬롯 제외
    sent_spans = []
    last_s = 0
    for m_s in SENTENCE_DELIM_RE.finditer(block_text):
        sent_spans.append((last_s, m_s.end(), block_text[last_s:m_s.end()]))
        last_s = m_s.end()
    if last_s < len(block_text):
        sent_spans.append((last_s, len(block_text), block_text[last_s:]))

    for s_start, s_end, s_text in sent_spans:
        if EXCLUDE_OPPONENT_CLAIM_RE.search(s_text):
            slots = [s for s in slots if not (s_start <= s.span_in_block[0] < s_end)]

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

    # 5. 동일 주체·동일 대상 결합 기반 사건 일시·기간 선후 역전 검증 (TEMPORAL_EVENT_INVERSION, B/C등급) (R1~R9 전면 반영)
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
                and (
                    (
                        existing_f.confidence_features.get("cause_date") == extra_features.get("cause_date")
                        and existing_f.confidence_features.get("effect_date") == extra_features.get("effect_date")
                    )
                    or (
                        existing_f.confidence_features.get("sub_rule") == rule_sub_id
                        and existing_f.confidence_features.get("excerpt_key") == excerpt_text[:80]
                    )
                )
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

        norm_block = " ".join(text.split())
        if len(norm_block) < 15:
            continue

        # R6: 블록 전체 건너뛰기 완전 삭제 (절 단위 필터링으로 이전됨)

        # 5. A-4: 결정적 슬롯 추출 및 7대 선후 관계 쌍 기반 인과적 선후 역전 검증 (O(N) 묶음 비교)
        slots = _extract_clause_slots(norm_block)
        n_slots = len(slots)

        for i in range(n_slots):
            for j in range(i + 1, n_slots):
                if n_slots > 30 and j - i > 4:
                    break
                s1, s2 = slots[i], slots[j]

                # U1: 두 슬롯 사이에 순서 연결어('-ㄴ 뒤|-ㄴ 후|-ㄴ 다음|-다가|이후|그 후')가 있으면,
                # 글이 밝힌 순서(앞 절 s1 -> 뒤 절 s2)를 먼저 판정한다.
                between_text = norm_block[s1.span_in_block[0]:s2.span_in_block[1]]
                has_narrative_order = (
                    s2.has_subsequent_order
                    or _has_narrative_order_connective(between_text)
                    or _has_narrative_order_connective(s1.clause_text)
                    or _has_narrative_order_connective(s2.clause_text[:25])
                )

                if has_narrative_order and s1.date_obj and s2.date_obj:
                    if s2.date_obj < s1.date_obj:
                        _emit_temporal_inversion(
                            block_obj=block,
                            heading=eff_h,
                            rule_sub_id="NARRATIVE_TEMPORAL_ORDER_INVERSION",
                            evidence_grade=EvidenceGrade.B,
                            title=f"서술 순서와 일자 역전: 선행 사건({s1.date_raw}) 후속 서술이나 일자는 앞선 {s2.date_raw} 기재",
                            detail_body=(
                                f"선행 '{s1.surface_form}({s1.date_raw})' 이후의 후속 행위로 적으면서 "
                                f"일자는 그보다 앞선 {s2.date_raw}('{s2.surface_form}')로 기재하여 시간 선후 관계가 모순된다."
                            ),
                            excerpt_text=f"{s1.clause_text} ... {s2.clause_text}",
                            extra_features={
                                "cause_date": str(s1.date_obj),
                                "effect_date": str(s2.date_obj),
                            },
                        )
                        continue
                    else:
                        # 날짜가 그 순서와 맞으면(s2.date_obj >= s1.date_obj),
                        # 법률상 선후 사전의 역방향(결과→원인, 예: 퇴직한 뒤 새로 입사)이라도 새 주기로 보고 내지 않는다 (오탐 0).
                        continue

                # R7, U1: 새 주기 사건(다시/새로/새로운)은 이전 주기 사건과 비교하지 않음
                if s2.is_new_cycle:
                    continue

                # 1) 상대 일자 계산 불일치 검사 (민법 제157조 초일 불산입 기준 익일 불일치, C등급)
                cause_date_slot = s1 if (not s1.is_next_day and s1.date_obj) else (s2 if (not s2.is_next_day and s2.date_obj) else None)
                next_day_slot = s2 if s2.is_next_day else (s1 if s1.is_next_day else None)
                if cause_date_slot and next_day_slot and cause_date_slot != next_day_slot and cause_date_slot.date_obj:
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
                                evidence_grade=EvidenceGrade.C,
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

                # 2) 각 선후 규칙 검사 (절대 일자 2개 역전, B등급)
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

                    # R8: 기간 비교는 같은 기간 안에서만!
                    if rule["rule_id"] == "PERIOD_START_BEFORE_END":
                        if cause_slot.period_group_id is not None and effect_slot.period_group_id is not None:
                            if cause_slot.period_group_id != effect_slot.period_group_id:
                                continue
                        elif cause_slot.period_group_id is not None or effect_slot.period_group_id is not None:
                            continue
                        else:
                            c_t = cause_slot.target or ""
                            e_t = effect_slot.target or ""
                            if not c_t or not e_t or not _same_object_noun(c_t, e_t):
                                continue

                    # R5: 동일 주체 요구 검증 (입사 -> 퇴사 생애주기 등)
                    if rule.get("require_same_subject"):
                        if cause_slot.subject and effect_slot.subject and cause_slot.subject != effect_slot.subject:
                            continue

                    # R5: 상대방 관계 주체 상이 검증 (신청->처분, 발송->도달 등에서 동일 주체이면 오탐 제외)
                    if rule.get("require_different_subject"):
                        if cause_slot.subject and effect_slot.subject and cause_slot.subject == effect_slot.subject:
                            continue

                    # R4: 대상 엄격 일치 요구 검증 (Z1, Z4)
                    if rule.get("require_target_match"):
                        c_target = cause_slot.target or ""
                        e_target = effect_slot.target or ""

                        # Z1: 대상이 빈 슬롯끼리는 비교하지 않는다
                        if not c_target or not e_target:
                            continue

                        # 수식어(1차 vs 2차, A vs B)가 다르면 서로 다른 사건이므로 무조건 제외 (R4)
                        mod_c = _extract_target_modifier(c_target)
                        mod_e = _extract_target_modifier(e_target)
                        if (mod_c or mod_e) and mod_c != mod_e:
                            continue

                        # 대상 일치는 _same_object_noun(엄격 일치) 하나로만 정한다 (Z1)
                        # Z2-③: 발생->청구/신고 규칙은 발생 대상과 청구의 원인 대상(cause_target)을 비교한다
                        eff_comp_target = (
                            effect_slot.cause_target
                            if (rule["rule_id"] == "OCCURRENCE_BEFORE_CLAIM" and effect_slot.cause_target)
                            else e_target
                        )
                        matched_target = _same_object_noun(
                            c_target,
                            eff_comp_target,
                            left_has_anaphora=cause_slot.has_anaphora,
                            right_has_anaphora=effect_slot.has_anaphora,
                        )

                        if not matched_target:
                            continue

                    # 사후 불복/소송/심판 청구가 과거 결정을 대상으로 삼는 정상 회고 서술은 역전 판정에서 제외
                    if rule["rule_id"] in ("TARGET_BOUND_DISPOSITION", "RECEIPT_BEFORE_AMENDMENT"):
                        if re.search(r"(?:대상으로\s*(?:한다|삼고|삼는다|삼아|하고|지정한다)|(?:취소|위법|무효)[를을]?\s*(?:구하|다투)|소를\s*제기|소송을\s*제기)", norm_block):
                            continue
                        if cause_slot.target in ("소", "소송", "행정소송", "취소소송") or cause_slot.surface_form == "소송제기":
                            continue

                    # 두 슬롯 모두 절대 일자(date_obj)를 가진 경우 B등급 판정
                    if cause_slot.date_obj and effect_slot.date_obj:
                        d_cause = cause_slot.date_obj
                        d_effect = effect_slot.date_obj

                        if d_effect < d_cause:
                            excerpt = f"{cause_slot.surface_form}({cause_slot.date_raw}) <-> {effect_slot.surface_form}({effect_slot.date_raw})"
                            sub_id = rule["rule_id"]

                            _emit_temporal_inversion(
                                block_obj=block,
                                heading=eff_h,
                                rule_sub_id=sub_id,
                                evidence_grade=EvidenceGrade.B,
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
    return findings
