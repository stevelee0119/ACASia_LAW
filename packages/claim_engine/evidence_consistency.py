"""증거 정합성 점검(v2 R9·Phase 7).

증거설명서·입증방법의 호증 목록과 본문, 같은 사건의 다른 서면을 서로 대조한다. 모두 문서 자체만으로
확인되는 형식·논리 사항이며, 법률 판단(증명력·채부)은 하지 않는다.

- 작성일이 달력에 없는 날짜 → EVIDENCE_DATE_INVALID (A)
- 작성일이 제출 서면 작성일보다 뒤 → EVIDENCE_TIMELINE_INVERSION (A: 제출 시점에 있을 수 없는 문서)
- 분석·보고·진술 자료의 작성일이 그 대상 사건일보다 앞 → EVIDENCE_TIMELINE_INVERSION (B)
- 호증 번호 결번, 본문이 언급한 호증이 목록에 없음 → EVIDENCE_NUMBERING_GAP / EVIDENCE_LIST_MISMATCH (B)
- 같은 사람의 계급·소속 기재가 증거 목록과 진술서에서 다름 → EVIDENCE_PERSON_INCONSISTENT (B)
- 진술서 서명 생략 → EVIDENCE_FORM_DEFECT (B)
- 지각하지 못했다면서 단정하는 진술 → STATEMENT_BEYOND_PERCEPTION (C, 사람 확인)
- 진단서·소견서로 의료와 무관한 사실을 입증하려 함 → EVIDENCE_PURPOSE_MISMATCH (C, 사람 확인)
- 서로 다른 서면에 같은 문장(인용문 제외)이 그대로 있음 → CROSS_DOC_COPY (B)
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument
from packages.document_engine.reading_text import build_reading_text, join_separator, sentence_bounds

from .exhibits import exhibit_keys, parse_exhibits, split_items

ENGINE_NAME = "claim_engine.evidence_consistency"


DATE_RE = re.compile(r"(?P<y>(?:19|20)\d{2})\s*[.\-년]\s*(?P<m>\d{1,2})\s*[.\-월]\s*(?P<d>\d{1,2})\s*[.일]?")
STANDALONE_DATE_RE = re.compile(r"^\s*(?:19|20)\d{2}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}\s*\.?\s*$")
HEADER_KEYS = {
    "id": ("호증", "증거번호", "증번", "번호", "순번"),
    "name": ("서증명", "증거명", "자료명", "문서명", "표목", "증거방법", "제출자료", "자료"),
    "date": ("작성일", "작성일자", "발급일", "발행일", "일자", "날짜"),
    "author": ("작성자", "작성명의인", "발행", "발급기관", "발급처", "제출자"),
    "purpose": ("입증취지", "입증 취지", "증명취지", "입증사항", "요지"),
    "amount": ("금액", "액수"),
}
MIN_ID_SHARE = 0.6  # 열 내용으로 증거표를 찾을 때: 호증 참조가 있는 행의 비율
# 사건 이후에 작성될 수밖에 없는 자료(그 사건을 분석·보고·진술한 문서)
AFTER_EVENT_KINDS = re.compile(r"분석|보고서|감정|진술|확인서|소견|조사")
MEDICAL_KINDS = re.compile(r"진단서|소견서|의무기록|진료기록")
MEDICAL_TERMS = re.compile(r"상해|부상|질병|질환|진단|치료|증상|건강|병명|장애|수술|통증|정신|심리|입원|외상")
# 계급(군). 법률 사실이 아니라 직급 명칭 목록이다.
RANKS = ("이병", "일병", "상병", "병장", "하사", "중사", "상사", "원사", "준위", "소위", "중위", "대위",
         "소령", "중령", "대령", "준장", "소장", "중장", "대장")
RANK_RE = re.compile("|".join(RANKS))
UNIT_RE = re.compile(r"제\s*(\d+)\s*(대대|중대|연대|여단|소대)")
NAME_FIELD_RE = re.compile(r"성\s*명\s*[:：]?\s*(?P<name>[가-힣][가-힣○△□＊*]{1,4})")
AFFILIATION_FIELD_RE = re.compile(r"소\s*속\s*[·ㆍ・]?\s*(?:계\s*급)?\s*[:：]?\s*(?P<value>[^\n]{2,60})")
SIGNATURE_OMITTED_RE = re.compile(r"(서명|날인|기명날인)\s*(생략|없음|미기재)")
LIMITATION_RE = re.compile(r"(들을\s*수\s*(는\s*)?없|듣지\s*못|보지\s*못|볼\s*수\s*(는\s*)?없|알\s*수\s*(는\s*)?없|"
                           r"기억(하지|나지)\s*(못|않)|확인하지\s*못)")
CERTAINTY_RE = re.compile(r"확실|분명|틀림없|단언|명백")
# 진술인의 위치: 가까이 있었다는 표현과 떨어져 있었다는 표현
PROXIMITY_RE = re.compile(r"같은\s*테이블|바로\s*옆|옆\s*자리|함께\s*앉|맞은\s*편|곁에")
DISTANCE_RE = re.compile(r"\d+\s*(?:미터|m|M)\s*(?:가량|정도|쯤)?\s*떨어진|다른\s*테이블|멀리\s*떨어")
# 진술인 명의 문서의 제목 줄(문단 전체가 제목). 증거 목록 속 "각 진술서"는 제목이 아니다.
STATEMENT_HEADING_RE = re.compile(r"(?:^|\n)\s*(?:진\s*술\s*서|사\s*실\s*확\s*인\s*서|확\s*인\s*서)\s*(?:\n|$)")
# 복사 문장 탐지 최소 길이 (24자 이상 문장 대상, 짧은 확인 문장 누락 방지)
COPY_MIN_CHARS = 24
COPY_SIMILARITY = 0.9

# 서증 형식 결함(EVI-FORM) 구조 기반 검출 정규식 (4대 축 및 정상 실무 보호)
# 서증 형식 결함(EVI-FORM) 구조 기반 검출 정규식 (4대 축 및 정상 실무 보호)
# 정상 실무 보호 1: 추후 제출/보완 예정(입증 계획) 및 기일 지참 서술문은 결함 제외
_NORMAL_FUTURE_SUBMISSION_RE = re.compile(
    r"(?:제출|보완|신청|제시|지참)\s*(?:할\s*)?예정(?:입니다|임|이며|이고|할\s*계획|에\s*있)"
)

# 정상 실무 보호 2: 물리 매체(USB, CD 등) 별도 제출 표기는 정상 실무이므로 제외
_EVI_FORM_SEPARATE_MEDIA_RE = re.compile(
    r"(?:USB|CD|DVD|외장하드|저장매체|디스크)\s*(?:등)?\s*(?:추후\s*)?(?:별도\s*)?(?:제출|송부|첨부)"
)

# 정상 실무 보호 3: 결함 해소·추완 진술, 이중 부정 반박, 상대방 주장/인용 반박, 부정의 부정(결손 부존재), 제출 철회 제외 (대조군 보호)
_EVI_FORM_NON_DEFECT_CONTEXT_RE = re.compile(
    r"(?:보완하여|추후\s*보완|금일\s*다시|기일에\s*지참|다시\s*제출|추완)"
    r"|(?:볼\s*수\s*없|이유\s*없|단정할\s*수\s*없|아니다)"
    r"|(?:주장하나|주장하지만|주장과\s*달리|주장에\s*불과|주장도\s*이유|주장은\s*이유)"
    # TK-81: 주어 없는 (다고|라고)...(지만|나...) 제거(상대방 배제 블록의 주어 조건 규칙만 남김)
    # TK-81 잔여 보완: 상대방 주장 관형형('-다는/-라는 + 주장/지적') + 부정 평가 반박 결함 제외 (부정어 결합 수긍 문장 차단 룩어헤드 및 단독 틀립니다·잘못입니다 보강)
    r"|(?:다는|라는)\s*(?:피고|원고|상대방|상대측)?\s*(?:의\s*)?(?:주장|지적|항변|진술|의견|말|의혹)(?:은|는|이|가|도)?[^\n.]{0,25}?"
    r"(?:"
    r"사실과\s*(?:다르|다릅|달라|달랐)(?!\s*(?:지\s*(?:않|아니)|않|아니|아닙))"
    r"|사실이\s*(?:아닙|아니|아님)(?!\s*(?:지\s*(?:않|아니)|않|아니))"
    r"|(?:사실과\s*)?(?:틀립[니시]|틀렸[다습음으]|틀려[서야도]|틀리다|틀린\s*(?:것|주장|지적)(?:이|입|으))(?!\s*(?:지\s*(?:않|아니)|않|아니|아닙|없))"
    r"|(?:명백한\s*)?잘못(?:입니다|이다|임|되었[다습음으]|되어\b|된\s*(?:것|주장|지적|판단)(?:이|입|으)|(?:\s*(?:알|파악|이해|해석|판단)(?:하고|한|하였)))(?!\s*(?:지\s*(?:않|아니)|않|아니|아닙|없))"
    r"|그릇된"
    r"|착오에\s*기인"
    r"|이유\s*(?:없|아닙|아니)(?!\s*(?:지\s*않|지\s*아니))"
    r"|근거\s*(?:없|부족)(?!\s*(?:지\s*않|지\s*아니))"
    r"|부당"
    r"|터무니\s*없"
    r"|어불성설"
    r"|받아들일\s*수\s*없"
    r")"
    r"|(?:빠진|누락(?:된)?|공란(?:인)?|흠결(?:이)?|결여(?:된)?)[^\n.]{0,20}?(?:이|가|은|는|도|사항이)?\s*(?:전혀\s*)?(?:없|아니|아닙|아님)"
    r"|(?:제출\s*철회|신청\s*철회|철회(?:합니다|함|하였음|된|사유)?)"
)

# 정상 실무 보호 4: 절차 사유 (추가 제출 부존재, 중복 첨부 생략, 공적 전산 확인, 촉탁·제출명령 사유) 결함 제외 (전달문 17 조건 1, TK-81)
_EVI_FORM_PROCEDURAL_JUSTIFICATION_RE = re.compile(
    # (가) 이 증거 외에 다른·그 밖의·추가 증거를 내지 않겠다는 진술 (TK-81: 단독 '밖에'를 제외하고 '이 밖에'·'그 밖에'만 유지)
    r"(?:이|본|위|해당)?\s*(?:증거|서증|자료|호증)?[^\n.]{0,10}?(?:외에|이외에|이\s*밖에|그\s*밖에)(?:는)?\s*[^\n.]{0,25}?"
    r"(?:다른|그\s*밖의|별도의|추가의|추가적인|추가로?|더\s*이상의)?\s*(?:증거|서증|자료|서류|입증방법)?(?:를|을|는|은|가|이)?\s*"
    r"(?:"
    r"(?:제출|신청|제시|입증|첨부)(?:하지|되지)\s*(?:않|못|아니|아닙|아님)"
    r"|내지\s*(?:않|못|아니|아닙|아님)"
    r"|(?:제출|신청|제시|입증|첨부|내)(?:할|하지|되지|하고\s*있지)?\s*(?:계획|생각|예정|의사|것)(?:이|은)?\s*(?:전혀\s*)?(?:없|아니|아닙|아님)"
    r"|(?:제출|신청|제시|입증|첨부|낼)\s*수가?\s*(?:전혀\s*)?없"
    r"|(?:다른|그\s*밖의|별도의|추가의|추가적인|더\s*이상의)\s*(?:증거|서증|자료|서류|입증방법)?(?:가|는|이|은)?\s*(?:전혀\s*)?(?:없|아니|아닙|아님)"
    r")"
    r"|더\s*이상(?:의)?\s*(?:증거|자료|서류|입증방법)?(?:를|는|가)?\s*(?:제출하지|내지)\s*(?:않|못|아니|아닙|아님)"
    r"|추가(?:로)?\s*(?:제출|제시|신청)(?:하지|할)\s*(?:않|계획이\s*없|것은\s*(?:아니|아닙))"
    # (나) 앞 서면에 이미 낸 증거를 중복 첨부하지 않는다는 진술
    r"|(?:기왕에|종전에|이미|앞선\s*서면에|종전\s*서면에|전의\s*서면에|기존에|앞서)\s*(?:이미\s*)?(?:제출|첨부)(?:하였|했|한\s*바\s*있|되었|된)"
    r"|중복\s*(?:제출|첨부)\s*(?:방지|생략|을\s*피하기)|별도로\s*중복\s*제출하지"
    # (다) 공적 전산으로 확인할 수 있어 첨부하지 않는다는 진술
    r"|(?:전자소송|전산망|대법원|등기부|가족관계|공적\s*장부|공적\s*전산|시스템)\s*(?:등?을\s*통해|에서)?\s*(?:확인\s*(?:가능|할\s*수\s*있)|조회\s*(?:가능|할\s*수\s*있)|열람\s*(?:가능|할\s*수\s*있))"
    r"|(?:전자적으로|전산으로)\s*(?:확인|조회|열람)"
    # (라) 문서송부촉탁·제출명령 신청 사유로 원본을 갖고 있지 않다고 적은 진술
    r"|(?:문서송부촉탁|문서제출명령|사실조회|법원촉탁|검찰청촉탁|과세정보제출명령)\s*(?:등?을\s*)?(?:통해|신청|구하|신청하였|신청할|결과를\s*기다려)"
    r"|(?:촉탁|사실조회|제출명령)\s*(?:신청\s*사유|신청에\s*따라)"
)

# 축 1: 서증 자리표시 기호/마크업 또는 내용 없이 파일명 단독 (SUSPICIOUS · B)
_EVI_FORM_PLACEHOLDER_RE = re.compile(
    r"\[\s*[^\]]{1,30}?(?:준비|삽입|첨부|입력|누락|공란|미완성|별도)[^\]]*\]"
    r"|<\s*[^>]{1,30}?(?:준비|삽입|첨부|입력|누락|공란|미완성|별도|사진|이미지|화면|캡처|내용)[^>]*>"
    r"|\(\s*[^)]{1,30}?(?:준비\s*중|준비중|삽입\s*예정|첨부\s*예정|추후\s*삽입|추후\s*첨부|별도\s*삽입)[^)]*?\)"
    r"|(?:화면|이미지|사진|캡처|사본|내용)\s*[:：]\s*(?:준비\s*중|준비중|삽입|첨부|누락|공란)"
    r"|\b[a-zA-Z0-9_\-]+\.(?:wav|mp3|mp4|avi|pdf|hwp|jpg|png|zip)\b[^\n.]{0,30}(?:내용\s*없음|본문\s*생략|사본\s*없음|내용이?\s*비어)"
)

# 축 2: 실물·원본·파일의 부재·미제출·분실·미확보·미보관 자인 (CONTRADICTED · B)
# 문법적 술어 형태 확장: 행위 부정(~하지 않/못), 행위 불능(할 수 없/하기 곤란), 상실(분실/망실), 존재 부정(없/아니)
_EVI_FORM_UNSUBMITTED_RE = re.compile(
    r"(?:영문\s*|국문\s*|한글\s*|스캔\s*|전자\s*|위\s*|이\s*|해당\s*|동\s*)?"
    r"(?:원본|실물|파일|음성|영상|녹음|원문|증거물|(?:위\s*|이\s*|해당\s*|동\s*)(?:자료|서류|문서))"
    r"[^\n.]{0,25}?"
    r"(?:"
    r"(?:회수|복구|발급|확보|수집|입수|취득|교부|출력|제출|첨부|보관|소지)(?:하지|받지|되지|하고\s*있지|되어\s*있지)\s*(?:않|못|아니)"
    r"|(?:회수|복구|발급|확보|수집|입수|취득|교부|출력|제출|첨부|보관|소지)(?:할\s*수\s*없|하기\s*어렵|하기\s*곤란|에\s*실패)"
    r"|내지\s*(?:않|못|아니)"
    r"|가지고\s*있지\s*(?:않|못|아니)"
    r"|찾지\s*(?:않|못|아니)"
    r"|미제출|미첨부|미확보|미보관|미소지"
    r"|분실|유실|망실|소실"
    r"|(?:이|가|은|는)\s*(?:전혀\s*)?(?:없|아니)"
    r")"
    r"|(?:제출|첨부|내)(?:하지|되지|지)\s*(?:않|못|아니)[^\n.]{0,25}(?:요지|메모|내용|녹취|번역문|번역본|사본)(?:만|를|을)?"
    r"|(?:원문|외국어\s*문서|원본)[^\n.]{0,25}?(?:제출|첨부|확보|내)(?:하지|되지|지)\s*(?:않|못|아니)[^\n.]{0,25}?(?:번역문|번역본|사본)(?:만|를|을)?"
    r"|(?:원문|외국어\s*문서|원본)\s*(?:미제출|미첨부)[^\n.]{0,25}?(?:번역문|번역본|사본)(?:만)?"
)

# 축 2 보강: 호증 표지 자체가 주어인 미제출 자인 (CONTRADICTED · B)
_EVI_FORM_EXHIBIT_UNSUBMITTED_RE = re.compile(
    r"(?:갑|을|병|정|소갑|소을)\s*제?\s*\d+\s*호증(?:의\s*\d+)?"
    r"[^\n.]{0,25}?"
    r"(?:은|는|을|를|의\s*경우|자체는|에\s*대하여는)?"
    r"[^\n.]{0,15}?"
    r"(?:"
    r"(?:회수|복구|발급|확보|수집|입수|취득|교부|출력|제출|첨부|보관|소지)(?:하지|받지|되지|하고\s*있지|되어\s*있지)\s*(?:않|못|아니)"
    r"|(?:회수|복구|발급|확보|수집|입수|취득|교부|출력|제출|첨부|보관|소지)(?:할\s*수\s*없|하기\s*어렵|하기\s*곤란|에\s*실패)"
    r"|내지\s*(?:않|못|아니)"
    r"|가지고\s*있지\s*(?:않|못|아니)"
    r"|찾지\s*(?:않|못|아니)"
    r"|미제출|미첨부|미확보|미보관|미소지"
    r"|분실|유실|망실|소실"
    r")"
)

# 축 3: 필수 기재(작성자·서명·날인·날짜)의 부재 (SUSPICIOUS · B)
# 문법적 술어 형태 확장: 상태 부정 일반형(~되어 있지 않/못), 결손 술어(공란/누락/빠져), 주어 존재 부정(없/아니)
_EVI_FORM_BLANK_RE = re.compile(
    r"(?:작성자|명의인|작성명의인|진술인|작성인|본인|서명자|서명|날인|기명날인|서명날인|도장|인영|자필서명|작성일자|작성일|날짜|일자)(?:란)?"
    r"(?:\s*(?:성명|서명|날인|도장))?"
    r"[^\n.]{0,25}?"
    r"(?:"
    r"(?:되어|찍혀|들어가|남아|붙어|이루어져)\s*있지\s*(?:않|못|아니)"
    r"|공란|빈칸|비어(?:\s*있)?|누락|미기재|미날인|미서명|미작성|빠져(?:\s*있)?|결여|흠결"
    r"|(?:이|가|은|는|도)\s*(?:전혀\s*)?(?:없|아니)"
    r")"
    r"|(?:작성자|명의인|진술인|성명|서명|날인|기명날인|작성일자|일자)\s*[:：]\s*(?:\(\s*(?:공란|미기재|빈칸|없음)\s*\)|공란|미기재|누락|빈칸)"
)

# 축 4: 내용 일부의 판독·식별 불가 자인 또는 일부 장·면 누락 + 증명 주장 (CONTRADICTED · B)
_EVI_FORM_UNIDENTIFIABLE_RE = re.compile(
    # 어순 1: 대상 명사 + 훼손 상태 + 불능 술어
    r"(?:금액|숫자|글자|문구|스캔|사본|화면|(?:위\s*|이\s*|해당\s*|동\s*)(?:내용|항목|부분|칸|하단|상단))"
    r"[^\n.]{0,25}?"
    r"(?:잘리|잘려|절단|흐리|흐려|어두워|번지|번져|번짐|지워|삭제|훼손|얼룩|깨져|불명확)"
    r"[^\n.]{0,25}?"
    r"(?:"
    r"(?:판독|식별|확인|읽|알)(?:하기|할|을|기|어보기|아보기)?(?:\s*(?:이|가|은|는|도|을|를))?\s*(?:수\s*없|불가|불가능|어렵|곤란|힘들|못)"
    r"|보이지\s*(?:않|못|아니)|확인되지\s*(?:않|못|아니)|나타나지\s*(?:않|못|아니)|나오지\s*(?:않|못|아니)"
    r")"
    # 어순 2: 훼손 상태 + 대상 명사 + 불능 술어 (예: 잉크 번짐으로 인해 금액 판독이 곤란)
    r"|(?:잘리|잘려|절단|흐리|흐려|어두워|번지|번져|번짐|지워|삭제|훼손|얼룩|깨져|불명확)"
    r"[^\n.]{0,25}?"
    r"(?:금액|숫자|글자|문구|스캔|사본|화면|(?:위\s*|이\s*|해당\s*|동\s*)(?:내용|항목|부분|칸|하단|상단))"
    r"[^\n.]{0,25}?"
    r"(?:"
    r"(?:판독|식별|확인|읽|알)(?:하기|할|을|기|어보기|아보기)?(?:\s*(?:이|가|은|는|도|을|를))?\s*(?:수\s*없|불가|불가능|어렵|곤란|힘들|못)"
    r"|보이지\s*(?:않|못|아니)|확인되지\s*(?:않|못|아니)|나타나지\s*(?:않|못|아니)|나오지\s*(?:않|못|아니)"
    r")"
    # 어순 3: 식별 불가 / 판독 불가 직결
    r"|(?:금액|숫자|글자|문구|스캔|사본|화면|(?:위\s*|이\s*|해당\s*|동\s*)(?:내용|항목|부분|칸))[^\n.]{0,15}?(?:식별\s*불가|판독\s*불가)"
    # 어순 4: 일부 장·면·쪽 누락
    r"|(?:일부|앞\s*면|뒷\s*면|마지막\s*(?:쪽|면|장|페이지)|특정\s*(?:쪽|면|장|페이지)|하단|상단|중간)\s*(?:쪽|면|장|페이지|내용)?\s*(?:이|가|은|는)?\s*(?:누락|빠져|잘려|결손)"
    r"|(?:쪽|면|장|페이지|매수)\s*(?:중\s*일부가?|가)?\s*(?:누락|빠져|잘려|부족)"
)

# 상대방 증거 탄핵 배제 (결함 제외)
_EVI_FORM_OPPONENT_CHALLENGE_RE = re.compile(
    r"(?:피고|원고|상대방|피고인|고소인)(?:가|는|이|의|를|을)?\s*(?:제출|주장|인용|원용|작성)"
    r"|신빙성(?:이|은)?\s*(?:없|의심|떨어|배척)|진정성립(?:이|은)?\s*(?:인정될\s*수\s*없|부인|다투)|입증하기에?\s*부족"
)
EXHIBIT_LABEL_RE = re.compile(r"(?:갑|을|병|정|소갑|소을)\s*제?\s*\d+\s*호증(?:의\s*\d+)?")


# --- 날짜 --------------------------------------------------------------------------
def _k(value: date) -> str:
    return f"{value.year}. {value.month}. {value.day}."


def calendar_date(text: str) -> Tuple[Optional[date], Optional[str]]:
    """문자열의 첫 날짜를 읽는다. 반환 (날짜, 오류). 달력에 없는 날짜면 (None, "2026. 4. 31.")."""
    m = DATE_RE.search(text or "")
    if not m:
        return None, None
    y, mo, d = int(m.group("y")), int(m.group("m")), int(m.group("d"))
    try:
        return date(y, mo, d), None
    except ValueError:
        return None, m.group(0).strip()


def _all_dates(text: str) -> List[date]:
    out = []
    for m in DATE_RE.finditer(text or ""):
        try:
            out.append(date(int(m.group("y")), int(m.group("m")), int(m.group("d"))))
        except ValueError:
            continue
    return out


SIGNATURE_LINE_RE = re.compile(r"\(\s*인\s*\)|귀\s*중|대\s*리\s*인|서\s*명|날\s*인")


def document_date(doc: NormalizedDocument) -> Optional[date]:
    """서면의 작성일: 날짜만 있는 줄 가운데 바로 뒤(3줄 안)에 서명·귀중 줄이 오는 첫 날짜.

    증거설명서 뒤에 진술서 등이 붙어 있으면 뒤쪽 날짜는 첨부 문서의 작성일이므로 첫 서명 날짜를 쓴다.
    서명 줄이 바닥글(대리인 표시)에만 있는 서면은 같은 쪽 바닥글까지 본다.
    """
    blocks = [b for b in doc.body_blocks(include_running_heads=True) if b.block_type not in ("table", "table_line")]
    for index, block in enumerate(blocks):
        if block.block_type == "running_head" or not STANDALONE_DATE_RE.match(block.text or ""):
            continue
        following = [b for b in blocks[index + 1:index + 6] if b.page == block.page]
        prose = [b for b in following if b.block_type != "running_head"][:3]
        heads = [b for b in following if b.block_type == "running_head"]
        if any(SIGNATURE_LINE_RE.search(b.text or "") for b in prose) or (
                len(prose) == 0 and any(SIGNATURE_LINE_RE.search(b.text or "") for b in heads)):
            parsed, _ = calendar_date(block.text)
            if parsed:
                return parsed
    return None


# --- 호증 목록 ---------------------------------------------------------------------
def _cell(value: Any) -> str:
    text = ""
    for line in str(value or "").splitlines():
        line = line.strip()
        if line:
            text = (text + join_separator(text, line) + line) if text else line
    return " ".join(text.split())


def _row(values: Dict[str, Any], ref: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    branches = ref.get("branches") or []
    return {**values, "party": ref["party"], "number": ref["number"], "branches": branches,
            "branch": str(branches[0]) if len(branches) == 1 else None,
            "label": f"{ref['party']} 제{ref['number']}호증" + (f"의 {branches[0]}" if len(branches) == 1 else
                                                              f"의 {branches[0]} 내지 {branches[-1]}" if branches else ""),
            **extra}


def exhibit_rows(doc: NormalizedDocument) -> List[Dict[str, Any]]:
    """문서의 호증 목록을 증거마다 한 행으로 읽는다: {id, party, number, branches, name, date, author, purpose}.

    표는 머리글 칸(호증·서증명·작성일…)으로 찾는다. 한 칸에 여러 증거가 묶인 표기('갑 제2, 3호증',
    '갑 제5호증의 1 내지 3')는 호증 문법(exhibits.py)으로 풀어 증거마다 행을 만든다(v5 3-1).
    """
    rows: List[Dict[str, Any]] = []
    for table in doc.structure.get("tables") or []:
        cells = table.get("cells") or []
        if len(cells) < 2:
            continue
        header = [_cell(h) for h in cells[0]]
        columns = {}
        for key, names in HEADER_KEYS.items():
            for index, title in enumerate(header):
                if any(name in title.replace(" ", "") for name in names) and index not in columns.values():
                    columns[key] = index
                    break
        body = cells[1:]
        if "id" not in columns or len(columns) < 3:
            # 표 제목·머리글이 표준과 달라도(양형자료 제출서 등) 열 내용으로 증거표를 알아본다(v5 3-3)
            columns, body = _columns_by_content(cells), cells
            if not columns:
                continue
        for row in body:
            values = {key: _cell(row[index]) if index < len(row) else "" for key, index in columns.items()}
            for ref in parse_exhibits(values.get("id", "")):
                rows.append(_row(values, ref, table_ref=table.get("table_ref"), page=table.get("page"), from_lines=False, in_section=True))
    return rows or _exhibit_lines(doc)


def _columns_by_content(cells: List[List[Any]]) -> Dict[str, int]:
    """머리글 없이 열 내용으로 증거표 열을 정한다. 호증 참조가 칸 첫머리에 오는 행이 60% 이상인 열을 번호 열로,
    날짜가 가장 많은 열을 작성일 열로, 번호 열 뒤 첫 글 열을 서증명, 마지막 글 열을 입증취지로 본다."""
    rows = [[_cell(c) for c in row] for row in cells if any(str(c or "").strip() for c in row)]
    if len(rows) < 2:
        return {}
    width = max(len(r) for r in rows)

    def share(index, test):
        values = [r[index] for r in rows if index < len(r) and r[index]]
        return (sum(1 for v in values if test(v)) / len(rows)) if values else 0.0

    def is_ref(value):
        refs = parse_exhibits(value)
        return bool(refs) and refs[0]["span"][0] == 0

    id_col = max(range(width), key=lambda i: share(i, is_ref))
    if share(id_col, is_ref) < MIN_ID_SHARE:
        return {}
    columns = {"id": id_col}
    dates = [(share(i, lambda v: bool(DATE_RE.search(v))), i) for i in range(width) if i != id_col]
    if dates and max(dates)[0] >= 0.5:
        columns["date"] = max(dates)[1]
    text_cols = [i for i in range(width) if i not in columns.values()
                 and share(i, lambda v: bool(re.search(r"[가-힣]{2,}", v))) >= 0.5]
    if not text_cols:
        return {}
    columns["name"] = text_cols[0]
    if len(text_cols) >= 2:
        columns["purpose"] = text_cols[-1]
    if len(text_cols) >= 3:
        columns["author"] = text_cols[1]
    amount = [i for i in range(width) if i not in columns.values() and share(i, lambda v: bool(re.search(r"\d[\d,]{3,}\s*원", v))) >= 0.5]
    if amount:
        columns["amount"] = amount[0]
    return columns


# 목록 줄이 아닌 것: 날짜만 있는 줄, 서명·첨부·당사자 줄, 번호 머리말로 시작하는 새 항목
_NOT_CONTINUATION_RE = re.compile(r"^\s*(?:(?:19|20)\d{2}\s*\.|첨\s*부|위\s|원\s*고|피\s*고|대\s*리\s*인|귀\s*중|"
                                  r"\d{1,2}\s*[.)]|[가-하]\s*[.)]|[①-⑳]|[■□▶-]|입\s*증\s*방\s*법|증\s*거\s*목\s*록)")

# 증거 목록 섹션 시작 헤더 (앞의 번호·기호 허용, 제목 뒤 괄호·쌍점 부연 허용, TK-64·TK-66 ReDoS 방지)
_EXHIBIT_SECTION_HEAD_RE = re.compile(
    r"^\s*(?:(?:(?:\d{1,2}|[가-하])\s*[.)]|\(\s*(?:\d{1,2}|[가-하])\s*\)|[①-⑳]|\[(?:\s*(?:\d{1,2}|[가-하]))?\s*\]?)\s*){0,3}"
    r"(?:입\s*증\s*방\s*법|첨\s*부\s*서\s*류|증\s*거\s*목\s*록|소\s*명\s*방\s*법)"
    r"(?:\s*(?:및|·|,)\s*(?:입\s*증\s*방\s*법|첨\s*부\s*서\s*류|증\s*거\s*목\s*록|소\s*명\s*방\s*법))?"
    r"(?:\s*\])?"
    r"(?:\s*\([^\)]*\))*"
    r"(?:\s*[:：\-–—]\s*.*)?\s*$"
)

# 본문 서술 문맥의 단순 인용·참조 표기 (예: '중 발췌하여', '참조바람', '보더라도' 등)
_EXHIBIT_REF_SENTENCE_RE = re.compile(
    r"(?:중\s*발췌(?:하여|한|해|하더라도)?|참조(?:\b|(?=[,.\s]))|\(참조\)|앞서\s*제출한|에서\s*확인되는|에\s*비추어)"
)


def _exhibit_lines(doc: NormalizedDocument) -> List[Dict[str, Any]]:
    """표가 없을 때: 문단 첫머리가 호증 번호인 목록(입증방법·증거설명 목록)을 행으로 읽는다.

    - 입증방법/첨부서류 구역(Section) 안의 항목은 제목에 '일부 발췌', '발췌본'이 있더라도
      정식 증거 목록으로 인정한다(FP-01 정밀화).
    - 본문 서술 구역에서 문장 중간에 참조되는 호증('중 발췌하여', '참조' 등)만 목록 정의에서 제외한다.
    """
    rows: List[Dict[str, Any]] = []
    reading = build_reading_text(doc)
    previous_was_item = False
    in_exhibit_section = False

    for paragraph_index, paragraph in enumerate(reading.text.split("\n")):
        stripped = paragraph.strip()
        if not stripped:
            continue

        # 입증방법 / 첨부서류 / 증거목록 섹션 진입 감지 (번호 붙은 제목 및 괄호·쌍점 부연 포함, TK-64)
        if _EXHIBIT_SECTION_HEAD_RE.search(stripped):
            in_exhibit_section = True
            previous_was_item = False
            continue

        # 앞머리의 번호/불릿(예: '1. ', '5. ', '- ', '가. ')을 정규화하여 호증 시작 판별
        bullet_m = re.match(r"^(\d{1,2}\s*[.)]|[-*•·]\s*|[가-하]\s*[.)]|[①-⑳]\s*)", stripped)
        cand_text = stripped[bullet_m.end():].strip() if bullet_m else stripped
        cand_refs = parse_exhibits(cand_text[:24]) if cand_text else []
        is_leading_exhibit = bool(cand_refs and cand_refs[0]["span"][0] == 0)

        raw_items = split_items(cand_text) if is_leading_exhibit else []
        items = []
        for ref, rest in raw_items:
            # 입증방법 구역 안이면 제목에 '발췌'가 있어도 정식 목록으로 수용
            if in_exhibit_section:
                items.append((ref, rest))
            else:
                # 본문 서술 영역에서는 서술형 참조 표현이 있으면 목록 정의에서 제외
                if _EXHIBIT_REF_SENTENCE_RE.search(rest) or _EXHIBIT_REF_SENTENCE_RE.search(stripped):
                    continue
                # 날짜가 있거나 번호형 목록 구조(예: '1. 갑 제5호증')이면 본문 영역이라도 수용
                if DATE_RE.search(rest) or re.match(r"^\d+[\.\)]", stripped):
                    items.append((ref, rest))
                else:
                    # 명백한 서술 문장이 이어지는 경우 본문 참조로 간주
                    if len(rest) > 20 and any(v in rest for v in ("하였다", "바와 같이", "살피건대", "주장한다")):
                        continue
                    items.append((ref, rest))

        if not items:
            if (previous_was_item and rows and stripped and len(stripped) <= 40 and not DATE_RE.search(stripped)
                    and not _NOT_CONTINUATION_RE.match(stripped) and not parse_exhibits(stripped)):
                group = rows[-1].get("line_group")
                for row in rows:
                    if row.get("line_group") == group and not row.get("date"):
                        row["name"] = (row["name"] + join_separator(row["name"], stripped) + stripped).strip()
                continue
            previous_was_item = False
            continue
        previous_was_item = True
        for index, (ref, rest) in enumerate(items):
            found = DATE_RE.search(rest)
            name = rest[:found.start()].strip() if found else rest
            tail = rest[found.end():].strip() if found else ""
            rows.append(_row({"id": ref["label"], "name": name, "date": found.group(0) if found else "",
                              "author": tail, "purpose": tail}, ref, table_ref=None, page=None, from_lines=True,
                             in_section=in_exhibit_section,
                             line_group=(paragraph_index, ref["span"])))
    return rows


def _finding(doc: NormalizedDocument, kind: FindingType, grade: EvidenceGrade, severity: Severity, title: str,
             detail: str, excerpt: str = "", *, page: Optional[int] = None, features: Optional[Dict] = None,
             status: VerificationStatus = VerificationStatus.CONTRADICTED) -> Finding:
    features = {"deterministic_rule": True, "rule_id": f"EVI.{kind}", **(features or {})}
    return Finding.create(
        type=kind, status=status, severity=severity, evidence_grade=grade, title=title, detail=detail,
        confidence=0.9 if grade == EvidenceGrade.A else 0.7 if grade == EvidenceGrade.B else 0.5,
        confidence_features=features, document_id=doc.document_id, page=page, engine=ENGINE_NAME,
        tags=["EVIDENCE"],
        evidence=[Evidence.create(description="문서 기재", grade=grade, document_id=doc.document_id, page=page,
                                  excerpt=excerpt[:300])] if excerpt else [])


def check_exhibits(doc: NormalizedDocument) -> List[Finding]:
    rows = exhibit_rows(doc)
    if not rows:
        return []
    out: List[Finding] = []
    filed = document_date(doc)
    for row in rows:
        parsed, invalid = calendar_date(row.get("date", ""))
        where = f"{row['label']} {row.get('name', '')}".strip()
        if invalid:
            out.append(_finding(doc, FindingType.EVIDENCE_DATE_INVALID, EvidenceGrade.A, Severity.HIGH,
                                f"증거 작성일이 달력에 없는 날짜다: {where} 작성일 {invalid}",
                                "달력에 없는 날짜이므로 그 날짜로는 문서가 작성될 수 없다. 오기인지 원본을 확인해야 한다.",
                                f"{where} | {row.get('date')}", page=row.get("page"),
                                features={"exhibit": row["label"], "written_date": invalid}))
            continue
        if parsed is None:
            continue
        if filed and parsed > filed:
            out.append(_finding(doc, FindingType.EVIDENCE_TIMELINE_INVERSION, EvidenceGrade.A, Severity.HIGH,
                                f"증거 작성일이 이 서면의 작성일보다 뒤다: {where} 작성일 {_k(parsed)} "
                                f"(서면 작성일 {_k(filed)})",
                                "서면을 작성·제출한 시점에는 존재할 수 없는 문서를 증거로 적었다.",
                                f"{where} | {row.get('date')}", page=row.get("page"),
                                features={"exhibit": row["label"], "written": parsed.isoformat(),
                                          "filed": filed.isoformat()}))
            continue
        described = f"{row.get('name', '')} {row.get('purpose', '')}"
        # 사건을 기록·증명하는 서증(분석·보고·진술·확인·의료·조서 등)은 그 사건보다 먼저 작성될 수 없다(G5).
        # 사건일은 입증취지·서증명의 날짜, 없으면 본문의 사고·사건 날짜를 쓴다.
        if EVENT_RECORD_KINDS.search(row.get("name", "")):
            later = [d for d in _all_dates(described) if d > parsed]
            if not later and EVENT_WORDS.search(described):
                later = [d for d in incident_dates(doc) if d > parsed]
            if later:
                event = max(later) if _all_dates(described) else min(later)
                out.append(_finding(doc, FindingType.EVIDENCE_TIMELINE_INVERSION, EvidenceGrade.B, Severity.HIGH,
                                    f"사건을 기록·증명하는 서증의 작성일이 그 사건보다 앞선다: {where} 작성일 "
                                    f"{_k(parsed)}, 대상 {_k(event)}",
                                    "입증하려는 사건이 일어나기 전에 그 사건을 기록·증명한 문서가 작성되었다고 적혀 있다.",
                                    f"{where} | {row.get('date')} | {row.get('purpose')}", page=row.get("page"),
                                    features={"exhibit": row["label"], "written": parsed.isoformat(),
                                              "event": event.isoformat()}))
        if MEDICAL_KINDS.search(row.get("name", "")) and row.get("purpose") and not MEDICAL_TERMS.search(row["purpose"]):
            out.append(_finding(doc, FindingType.EVIDENCE_PURPOSE_MISMATCH, EvidenceGrade.C, Severity.MEDIUM,
                                f"입증취지가 서증 성격 범위를 벗어날 수 있다: {where} → '{row['purpose']}'",
                                "의료 문서로 의료와 무관한 사실을 입증하려 한다. 증명력은 법원이 판단하므로 사람이 확인한다.",
                                f"{where} | {row.get('purpose')}", page=row.get("page"),
                                status=VerificationStatus.UNVERIFIED,
                                features={"exhibit": row["label"], "human_review": True}))
    out.extend(_numbering(doc, rows))
    out.extend(_attached_originals(doc, rows))
    out.extend(_attached_amounts(doc, rows))
    return out


def _attached_amounts(doc: NormalizedDocument, rows: List[Dict[str, Any]]) -> List[Finding]:
    """증거목록의 금액과 같은 파일에 붙은 원문 사본(첨부 … 사본)의 금액을 대조한다(v4 P4)."""
    from .calculation import parse_amounts
    from .fact_store import digit_transposition, segments

    copies = [(re.sub(r"\s|첨부|사본|원본|[()\[\]【】]", "", name), blocks) for name, blocks in segments(doc)[1:]]
    out: List[Finding] = []
    for row in rows:
        listed = parse_amounts(row.get("amount") or "")
        name = re.sub(r"\s", "", row.get("name") or "")
        if not listed or not name:
            continue
        for title, blocks in copies:
            if not title or (title not in name and name not in title):
                continue
            original = parse_amounts(build_reading_text(doc, blocks).text)
            if not original or any(a.value == listed[0].value for a in original):
                break
            where = f"{row['label']} {row.get('name', '')}".strip()
            transposed = any(digit_transposition(str(listed[0].value), str(a.value)) for a in original)
            out.append(_finding(doc, FindingType.EVIDENCE_LIST_MISMATCH, EvidenceGrade.A, Severity.HIGH,
                                f"증거목록 금액과 첨부 원문의 금액이 다르다: {where} — 목록 {listed[0].raw}, 원문 "
                                f"{original[0].raw}" + (" (자릿수 뒤바뀜 의심)" if transposed else ""),
                                "같은 파일 안의 증거목록과 첨부 원문 사본이 금액을 다르게 적었다. 원본을 확인해야 한다.",
                                f"{where} | 목록: {listed[0].raw} | 원문: {original[0].raw}", page=row.get("page"),
                                features={"rule_id": "EVI.LIST_AMOUNT_MISMATCH", "defect_code": "LIST_AMOUNT_MISMATCH",
                                          "exhibit": row["label"], "list_amount": str(listed[0].value),
                                          "original_amounts": [str(a.value) for a in original[:5]],
                                          "digit_transposition": transposed}))
            break
    return out


EVENT_RECORD_KINDS = re.compile(r"분석|보고서|감정|진술|확인서|경위서|소견|조사|진단서|의무기록|진료기록|진료비|영수증|"
                                r"조서|증명서|사실조회|사고\s*사실")
EVENT_WORDS = re.compile(r"사고|사건|폭행|상해|부상|피해|경위|치료|입원|발생")
ORG_RE = re.compile(r"[가-힣○△□A-Za-z]{1,20}(?:대학교병원|병원|의원|한의원|치과|보건소|경찰서|검찰청|법원|청|구청|시청|군청|"
                    r"센터|공단|공사|위원회|협회|주식회사|은행|보험)")
ISSUER_LINE_RE = re.compile(r"(?:발행|발급|작성)\s*(?:기관|처|자)?\s*[:：]\s*(?P<org>[^\n]{2,40})|(?P<head>[^\n]{2,30}(?:병원|의원)장)")


def incident_dates(doc: NormalizedDocument) -> List[date]:
    """본문이 사고·사건이 일어난 날로 적은 날짜(사실 저장소의 추출 기준과 같다).

    '사고' 낱말이 든 문장의 모든 날짜를 쓰면 시효 만료일·사고경위서 작성일까지 사건일로 잡힌다. 날짜 바로 뒤에
    사고 서술이 오거나 '사고일·범행일' 바로 뒤에 온 날짜만 쓴다.
    """
    from .fact_store import incident_dates as stated_incident_dates
    return [date.fromisoformat(value) for value in stated_incident_dates(doc)]


def _org_key(text: str) -> str:
    return re.sub(r"[\s○△□()（）㈜]|주식회사", "", text or "")


def _attached_originals(doc: NormalizedDocument, rows: List[Dict[str, Any]]) -> List[Finding]:
    """같은 파일에 붙은 원문(진단서 등)의 발급기관을 증거목록의 작성자와 대조한다(G5)."""
    text = build_reading_text(doc).text
    lines = text.split("\n")
    out: List[Finding] = []
    for row in rows:
        author, name = row.get("author") or "", re.sub(r"\s", "", row.get("name") or "")
        if not name or not ORG_RE.search(author):
            continue
        for index, line in enumerate(lines):
            if re.sub(r"\s", "", line) != name:
                continue  # 원문 첫머리의 제목 줄(예: '진 단 서')
            window = "\n".join(lines[index + 1:index + 25])
            issuers = [m.group("org") or m.group("head") for m in ISSUER_LINE_RE.finditer(window)]
            issuers = [ORG_RE.search(i).group(0) for i in issuers if i and ORG_RE.search(i)]
            if issuers and not any(_org_key(i) in _org_key(author) or _org_key(author) in _org_key(i)
                                   for i in issuers):
                where = f"{row['label']} {row.get('name', '')}".strip()
                out.append(_finding(doc, FindingType.EVIDENCE_LIST_MISMATCH, EvidenceGrade.B, Severity.MEDIUM,
                                    f"증거목록의 작성자와 첨부 원문의 발급기관이 다르다: {where} — 목록 '{author}', "
                                    f"원문 '{issuers[0]}'",
                                    "같은 파일 안의 증거목록과 첨부 원문이 발급기관을 다르게 적었다. 원본을 확인해야 한다.",
                                    f"{where} | 목록: {author} | 원문: {issuers[0]}", page=row.get("page"),
                                    features={"exhibit": row["label"], "list_author": author,
                                              "original_issuer": issuers[0]}))
            break
    return out


def _numbering(doc: NormalizedDocument, rows: List[Dict[str, Any]]) -> List[Finding]:
    def first_token_identifier(suffix):
        match = re.match(r"\s*(\S+)", suffix)
        if match is None:
            return False
        token = match.group(1).rstrip(".,;:")
        wrappers = {"(": ")", "[": "]", "{": "}", "<": ">"}
        if token[:1] in wrappers:
            closing = wrappers[token[0]]
            token = token[1:-1] if token.endswith(closing) else token[1:]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", token):
            return False
        return bool(re.search(r"[0-9_/-]", token) or re.fullmatch(r"[A-Z]+", token))

    def comparison_keys(same):
        original = {re.sub(r"\s", "", row.get("name") or "") for row in same}
        if len(same) != 2 or not all(row.get("from_lines") for row in same):
            return original
        pairs = [re.split(r"([,:])", row.get("name") or "", maxsplit=1) for row in same]
        if any(len(pair) != 3 or not pair[0].strip() for pair in pairs):
            return original
        if {pair[1] for pair in pairs} != {",", ":"}:
            return original
        prefixes = {re.sub(r"\s", "", pair[0]) for pair in pairs}
        if len(prefixes) != 1:
            return original
        # Keep the approved date-availability residual and native/GLOBAL guards.
        if len({re.sub(r"\s", "", row.get("date") or "") for row in same}) != 1:
            return original
        if any(first_token_identifier(pair[2]) for pair in pairs):
            return original
        return prefixes

    out: List[Finding] = []
    # 같은 호증 번호(가지번호까지 같음)가 목록에 두 번 이상 나온다(v4 P4)
    # 목록 구역(표 또는 번호 붙은 입증방법 섹션)에 존재하는 호증 번호는 본문 언급을 중복 판단에서 제외 (TK-64)
    section_keys = {
        (r["party"], r["number"])
        for r in rows
        if r.get("in_section", not r.get("from_lines", False))
    }

    seen: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        is_in_section = bool(row.get("in_section", not row.get("from_lines", False)))
        # 목록 구역이 존재하는 서면에서, 해당 목록 구역에 이미 등록된 번호의 본문 행은 중복 집계에서 제외
        if section_keys and not is_in_section and (row["party"], row["number"]) in section_keys:
            continue
        # 호증 중복 검사는 정식 증거 목록 행끼리만 비교한다.
        # 본문 서술 영역(not is_in_section)에서 추출된 행 중:
        # 1) 호증 번호 직후 조사가 결합되어 주어·목적어로 쓰인 본문 문장(예: '갑 제3호증을', '갑 제1호증은')
        #    (단, '갑 제1호증의 1' 등 가지번호는 조사가 아니므로 보존)
        # 2) 서증명 없이 단순 본문 인용·참조 표기만 있는 행
        # 은 목록 행이 아닌 본문 서술문이므로 중복 호증 집계에서 제외한다 (은퇴 10 A등급 오탐 방지 및 입증취지 포함 진짜 목록 보존).
        if not is_in_section:
            name = (row.get("name") or "").strip()
            # 가지번호(예: '의 1', '의 2')는 조사가 아니므로 보존
            if not re.match(r"^의\s*\d+", name):
                if re.match(r"^(?:[이가은는을를에와과]|에서|으로|부터|까지|보다)(?:\s|$)", name):
                    continue
            # 단순 인용·참조 표기
            if _EXHIBIT_REF_SENTENCE_RE.search(name):
                continue
        keys = [(row["party"], row["number"], b) for b in row.get("branches") or []] or [(row["party"], row["number"], None)]
        for key in keys:
            seen.setdefault(key, []).append(row)
    for (party, number, branch), same in seen.items():
        if len(same) < 2:
            continue
        # 서증명이 실질적으로 상이한 증거에 부여된 경우만 중복 번호로 확정 (단순 반복 기재 제외, FP-01)
        distinct_names = comparison_keys(same)
        distinct_names.discard("")
        if len(distinct_names) < 2 and len(same) >= 2 and all(r.get("name") for r in same):
            continue
        label = f"{party} 제{number}호증" + (f"의 {branch}" if branch else "")
        names = ", ".join(r.get("name") or "(이름 없음)" for r in same)
        out.append(_finding(doc, FindingType.EVIDENCE_LIST_MISMATCH, EvidenceGrade.A, Severity.MEDIUM,
                            f"같은 호증 번호가 두 번 쓰였다: {label} — {names}",
                            "증거 목록에서 한 번호를 서로 다른 증거에 두 번 붙였다. 어느 증거를 가리키는지 "
                            "특정할 수 없으므로 번호를 바로잡아야 한다.", f"{label}: {names}",
                            features={"rule_id": "EVI.EVIDENCE_NUMBER_DUPLICATE",
                                      "defect_code": "EVIDENCE_NUMBER_DUPLICATE", "exhibit": label,
                                      "names": [r.get("name") for r in same]}))
    listed: Dict[str, set] = {}
    for row in rows:
        listed.setdefault(row["party"], set()).add(row["number"])
    # 가지번호: '의 2'만 있고 '의 1'이 없으면 결번이다(G5). 범위 표기('의 1 내지 3')는 모두 있는 것으로 본다.
    branches: Dict[tuple, set] = {}
    for row in rows:
        if row.get("branches"):
            branches.setdefault((row["party"], row["number"]), set()).update(row["branches"])
    for (party, number), present in sorted(branches.items()):
        missing = [b for b in range(1, max(present) + 1) if b not in present]
        if missing:
            labels = ", ".join(f"{party} 제{number}호증의 {b}" for b in missing)
            out.append(_finding(doc, FindingType.EVIDENCE_NUMBERING_GAP, EvidenceGrade.B, Severity.MEDIUM,
                                f"가지번호가 비어 있다: {labels} 결번",
                                "같은 호증의 가지번호가 1부터 이어지지 않는다. 누락된 증거가 있는지 확인해야 한다.",
                                ", ".join(f"{party} 제{number}호증의 {b}" for b in sorted(present)),
                                features={"party": party, "number": number, "missing_branches": missing}))
    # 당사자별 결번 판정: 목록 구역이 있으면 구역 번호로만, 구역 최소 번호부터 결번 산출 (TK-67)
    has_any_section = any(r.get("in_section", not r.get("from_lines", False)) for r in rows)
    for party, numbers in listed.items():
        sec_nums = {
            r["number"] for r in rows
            if r["party"] == party and r.get("in_section", not r.get("from_lines", False))
        }
        if has_any_section:
            if not sec_nums:
                # 서면에 목록 구역이 존재하나 해당 당사자는 본문 언급만 있는 경우 결번 판정 제외
                continue
            target_nums = sec_nums
            start_num = min(sec_nums)
        else:
            # 목록 구역이 없는 서면은 기존 동작 유지 (1번부터 결번 산출)
            target_nums = numbers
            start_num = 1
        gaps = [n for n in range(start_num, max(target_nums) + 1) if n not in target_nums]
        if gaps:
            out.append(_finding(doc, FindingType.EVIDENCE_NUMBERING_GAP, EvidenceGrade.B, Severity.MEDIUM,
                                f"호증 번호가 비어 있다: {party} 제{', '.join(map(str, gaps))}호증 결번",
                                "증거 목록의 번호가 연속하지 않는다. 누락된 증거가 있는지 확인해야 한다.",
                                ", ".join(f"{party} 제{n}호증" for n in sorted(target_nums)),
                                features={"party": party, "missing": gaps}))
    text = build_reading_text(doc).text
    mentioned = exhibit_keys(text)
    missing = sorted((p, n) for p, n in mentioned if p in listed and n not in listed[p])
    if missing:
        labels = ", ".join(f"{p} 제{n}호증" for p, n in missing)
        out.append(_finding(doc, FindingType.EVIDENCE_LIST_MISMATCH, EvidenceGrade.B, Severity.MEDIUM,
                            f"본문이 언급한 증거가 증거 목록에 없다: {labels}",
                            "본문에서 입증 근거로 든 호증이 증거 목록에 없다.", labels,
                            features={"missing_from_list": [f"{p} 제{n}호증" for p, n in missing]}))
    return out


# --- 진술서 ------------------------------------------------------------------------
# 사람 이름: 가명 표기(성 + ○○) 또는 2~4글자 실명. 목록의 작성자 칸에서 사람 이름 하나만 있을 때 쓴다.
PERSON_NAME_RE = re.compile(r"(?<![가-힣])([가-힣])([○△□＊*]{1,3})(?![가-힣○△□＊*])")


def _statement_fields(text: str) -> List[Dict[str, Any]]:
    out = []
    for m in NAME_FIELD_RE.finditer(text):
        window = text[m.end():m.end() + 160]
        affiliation = AFFILIATION_FIELD_RE.search(window)
        value = affiliation.group("value") if affiliation else ""
        # 진술서 앞 300자 안의 가장 가까운 호증 표시('[갑 제6호증]')로 목록의 어느 행인지 정한다
        before = parse_exhibits(text[max(0, m.start() - 300):m.start()])
        out.append({"name": m.group("name"), "ranks": set(RANK_RE.findall(value)),
                    "units": {(n, u) for n, u in UNIT_RE.findall(value)}, "raw": value.strip(),
                    "exhibit": (before[-1]["party"], before[-1]["number"]) if before else None})
    return out


def _surname_conflict(listed_author: str, stated_name: str) -> Optional[str]:
    """목록 작성자 칸의 가명(성 + ○○)과 진술서 성명의 성이 다르면 두 표기를 돌려준다. 같은 가림 길이만 비교한다."""
    listed = PERSON_NAME_RE.findall(listed_author or "")
    stated = PERSON_NAME_RE.fullmatch(stated_name or "")
    if len(listed) != 1 or not stated:
        return None
    surname, mask = listed[0]
    if len(mask) != len(stated.group(2)) or surname == stated.group(1):
        return None
    return f"{surname}{mask} ↔ {stated_name}"


def check_statements(doc: NormalizedDocument, exhibits: Sequence[Dict[str, Any]] = ()) -> List[Finding]:
    """진술서의 형식·지각 범위와, 증거 목록 기재와의 인적사항 일치."""
    out: List[Finding] = []
    reading = build_reading_text(doc, [b for b in doc.body_blocks() if b.block_type != "running_head"])
    text = reading.text
    if SIGNATURE_OMITTED_RE.search(text) and re.search(r"진\s*술\s*서|확\s*인\s*서", text):
        m = SIGNATURE_OMITTED_RE.search(text)
        local = text[max(0, m.start() - 120):m.end() + 40]
        pleading = bool(re.search(r"소\s*장|청\s*구\s*취\s*지", text[:1500]) and
                        re.search(r"원고|피고|대리인", local))
        out.append(_finding(doc, FindingType.EVIDENCE_FORM_DEFECT, EvidenceGrade.B, Severity.MEDIUM,
                            "소장 작성자 기명날인 확인 필요" if pleading else f"진술서에 서명이 없다: '{m.group(0)}'",
                            "소장 작성자란에 서명 생략이 기재되어 있다. 제출본의 기명날인을 확인해야 한다. 진술서의 서명 누락이나 위조 판정이 아니다."
                            if pleading else "진술인의 서명·날인이 생략되어 작성 명의를 확인할 수 없다.",
                            text[max(0, m.start() - 40):m.end() + 20],
                            status=VerificationStatus.UNVERIFIED if pleading else VerificationStatus.CONTRADICTED))
    statement_start = _statement_start(doc, text)
    proximity: List[str] = []
    distance: List[str] = []
    for start, end in sentence_bounds(text):
        sentence = text[start:end]
        # 발췌는 원래 줄 글자를 띄어 이어 붙인다(읽기 본문은 줄바꿈 자리를 붙여 쓴다).
        shown = " ".join(b.text.strip() for b in reading.blocks_between(start, end)) or sentence.strip()
        if LIMITATION_RE.search(sentence) and CERTAINTY_RE.search(sentence):
            out.append(_finding(doc, FindingType.STATEMENT_BEYOND_PERCEPTION, EvidenceGrade.C, Severity.MEDIUM,
                                "지각 범위를 넘는 단정: 지각하지 못했다고 하면서 사실을 확실하다고 한다",
                                "같은 문장에서 보거나 듣지 못했다고 하면서 그 사실을 확실하다고 한다. "
                                "진술의 신빙성은 사람이 판단한다.",
                                shown, status=VerificationStatus.UNVERIFIED,
                                features={"human_review": True, "rule_id": "EVI.BEYOND_PERCEPTION"}))
        if statement_start is not None and start >= statement_start:
            if PROXIMITY_RE.search(sentence):
                proximity.append(shown)
            if DISTANCE_RE.search(sentence):
                distance.append(shown)
    if proximity and distance and proximity[0] != distance[0]:
        out.append(_finding(doc, FindingType.FACT_CONTRADICTION, EvidenceGrade.B, Severity.MEDIUM,
                            "진술 내부 모순: 가까이 있었다는 진술과 떨어져 있었다는 진술이 함께 있다",
                            "같은 진술서 안에서 진술인의 위치를 서로 다르게 적었다. 어느 쪽이 맞는지 사람이 확인한다.",
                            f"{proximity[0]} ↔ {distance[0]}",
                            features={"rule_id": "EVI.STATEMENT_LOCATION_CONFLICT",
                                      "statements": [proximity[0][:200], distance[0][:200]]}))
    for fields in _statement_fields(text):
        for row in exhibits:
            # 같은 호증(진술서 앞 호증 표시)인데 성이 다르면 작성 명의가 다르다(v5 3-3)
            if fields.get("exhibit") == (row["party"], row["number"]):
                conflict = _surname_conflict(row.get("author", ""), fields["name"])
                if conflict:
                    out.append(_finding(doc, FindingType.EVIDENCE_PERSON_INCONSISTENT, EvidenceGrade.B, Severity.HIGH,
                                        f"증거 목록의 작성자와 첨부 문서의 성명이 다르다({row['label']}): {conflict}",
                                        "같은 호증의 작성자를 증거 목록과 첨부 문서가 서로 다른 사람으로 적었다(성이 다름).",
                                        f"목록: {row.get('author')} / 첨부: 성명 {fields['name']}",
                                        features={"rule_id": "EVI.PERSON_NAME_MISMATCH", "exhibit": row["label"],
                                                  "listed": row.get("author"), "stated": fields["name"]}))
                    continue
            if fields["name"] not in row.get("author", "") or not re.search(r"진술|확인서", row.get("name", "")):
                continue
            listed_ranks = set(RANK_RE.findall(row.get("author", "")))
            listed_units = {(n, u) for n, u in UNIT_RE.findall(row.get("author", ""))}
            differences = []
            if listed_ranks and fields["ranks"] and not (listed_ranks & fields["ranks"]):
                differences.append(f"계급 {'/'.join(sorted(listed_ranks))} ↔ {'/'.join(sorted(fields['ranks']))}")
            same_kind = {u for _, u in listed_units} & {u for _, u in fields["units"]}
            for kind in same_kind:
                left = {n for n, u in listed_units if u == kind}
                right = {n for n, u in fields["units"] if u == kind}
                if left and right and not (left & right):
                    differences.append(f"소속 제{'/'.join(sorted(left))}{kind} ↔ 제{'/'.join(sorted(right))}{kind}")
            if differences:
                out.append(_finding(doc, FindingType.EVIDENCE_PERSON_INCONSISTENT, EvidenceGrade.B, Severity.HIGH,
                                    f"같은 진술인의 인적사항이 다르다({row['label']} {fields['name']}): "
                                    + "; ".join(differences),
                                    "증거 목록의 작성자 기재와 진술서의 소속·계급 기재가 서로 다르다.",
                                    f"목록: {row.get('author')} / 진술서: {fields['raw']}",
                                    features={"exhibit": row["label"], "differences": differences}))
    return out


# --- 서증 번호 및 목록 불일치(EVI-NUM) 구조 기반 검출 ----------------------------------

_PRIOR_SUBMISSION_RE = re.compile(r"(?:이미|앞서|종전(?:\s*에)?|기|제?\s*\d+\s*차\s*준비서면에서?)\s*제출(?:한|된|하여)?")
_CONTINUOUS_RANGE_RE = re.compile(
    r"(?P<p1>[가-힣])\s*제\s*(?P<n1>\d+)\s*호증부터\s*(?:(?P<p2>[가-힣])\s*제\s*)?(?P<n2>\d+)\s*호증까지"
    r"(?:\s*(?P<mod>빠짐없이|모두|전부|일체|연속|결번\s*없이))?"
)
_CONTINUOUS_KEYWORD_RE = re.compile(r"(?:연속\s*(?:번호|제출|서증)|누락이\s*(?:전혀\s*)?없)")
_COMPLETE_DECLARATION_RE = re.compile(
    r"(?:(?:최종\s*)?(?:제출\s*)?증거목록|입증방법|제출\s*증거(?:\s*목록)?|제출목록|별지\s*(?:증거|제출)?목록|첨부\s*목록)"
    r"[^.\n]{0,60}?(?:전부|모두|일체|빠짐없이|추가\s*제출\s*없음|확정|전체|최종|이것이\s*전부|만\s*있다|만\s*포함)"
    r"|(?:(?:최종\s*)?(?:제출\s*)?증거목록|입증방법|제출\s*증거(?:\s*목록)?|제출목록|별지\s*(?:증거|제출)?목록|첨부\s*목록)\s*\([^)\n]{0,60}?(?:전부|모두|일체|빠짐없이|추가\s*제출\s*없음|확정|전체|최종|이것이\s*전부|만\s*있다|만\s*포함)\)"
    r"|(?:별지\s*증거목록\s*전부|별지\s*제출목록\s*전부|이\s*(?:세|두|\d+)\s*자료만\s*제출)"
    r"|본문에\s*적힌\s*내용이\s*해당\s*발췌의\s*전부"
    r"|추가\s*(?:증거|자료|서증|호증)(?:를|은|가)?\s*(?:제출(?:하지\s*않|한\s*사실은\s*없|이\s*없)|없습니다)"
    r"|추가\s*(?:증거|제출|자료)?\s*목록은\s*없"
    r"|위\s*목록이\s*[^.\n]{0,60}(?:증거|자료)의\s*전부"
)
_COUNT_DECLARATION_RE = re.compile(
    r"(?:증거목록|입증방법|제출\s*증거|제출목록)[^.\n]{0,30}(?:총|모두)\s*(?P<count>\d+)\s*개"
    r"|(?P<count2>\d+)\s*개의\s*(?:서증|증거)(?:를|을)?\s*제출"
)


def check_evidence_numbering_mismatches(
    doc: NormalizedDocument, exhibits: Optional[Sequence[Dict[str, Any]]] = None
) -> List[Finding]:
    """서증 목록 구역(exhibit_rows)과 본문 호증 인용(parse_exhibits) 사이의 구조적 불일치를 검출한다 (EVI-NUM).

    1. 완결 선언 목록에 없는 자기 호증 번호 인용 (축 1) -> CONTRADICTED·B
    2. 연속 범위 선언 후 중간 호증 누락 (축 2) -> CONTRADICTED·B
    3. 본문과 목록에서 동일 서증명에 서로 다른 호증 번호 부여 (축 3) -> SUSPICIOUS·B (4자 이상)
    4. 선언 개수와 실제 목록 수 불일치 (축 4) -> CONTRADICTED·B
    """
    if exhibits is None:
        exhibits = exhibit_rows(doc)
    text = build_reading_text(doc).text
    out: List[Finding] = []

    # 정식 증거목록 구역(in_section=True 또는 table) 존재 여부 확인
    has_formal_section = any(r.get("in_section") or not r.get("from_lines") for r in exhibits)

    # EVI-NUM 전용 필터링: 긴 본문 서술 행(40자 초과 + 마침표)이나 조사 뒤 서술어가 이어지는 행은 목록 대조에서 제외
    filtered_exhibits = []
    for r in exhibits:
        # 정식 구역/표가 존재할 때 본문 문맥(in_section=False)에서 유출된 행은 목록에서 제외
        if has_formal_section and (not r.get("in_section") and r.get("from_lines")):
            continue
        name = (r.get("name") or "").strip()
        purpose = (r.get("purpose") or "").strip()
        full_desc = f"{name} {purpose}".strip()
        clean_desc = re.sub(r"\([^)]*\)", " ", full_desc)
        clean_desc = DATE_RE.sub(" ", clean_desc).strip()
        if len(clean_desc) > 40 and re.search(r"[다음습]\s*\.\s*$", clean_desc):
            continue
        if re.match(r"^[이가은는을를에로의]\s*(?:[가-힣A-Za-z0-9_]{1,30}\s+){0,6}(?:설명|주장|확인|보여|나타|제출|인용|바와|살피|따라|원용)", name):
            continue
        filtered_exhibits.append(r)

    # 목록의 호증 정보 집합 구성
    list_keys = set()
    list_name_by_key = {}
    for row in filtered_exhibits:
        party = row.get("party")
        num = row.get("number")
        if party and num is not None:
            key = (party, num)
            list_keys.add(key)
            name = (row.get("name") or "").strip()
            if name:
                norm_name = re.sub(r"\s+", "", name)
                list_name_by_key[key] = (name, norm_name)

    # 인라인/한 줄 증거목록 및 범위 표기 보강 (수, 행, 고, 설, 갑, 을 등)
    for line in text.split("\n"):
        if re.search(r"(?:최종\s*)?(?:증거목록|입증방법|제출\s*증거|제출목록|별지\s*(?:증거|제출)?목록|첨부\s*목록)", line):
            m_list_part = re.search(
                r"(?:최종\s*)?(?:증거목록|입증방법|제출\s*증거|제출목록|별지\s*(?:증거|제출)?목록|첨부\s*목록)(?:에는|은|:)?\s*(?P<part>[^\n.]+)",
                line,
            )
            target_str = m_list_part.group("part") if m_list_part else line
            for rm in re.finditer(
                r"(?P<p>[가-힣])\s*제\s*(?P<n1>\d+)\s*호증\s*(?:~|내지|-)\s*(?:[가-힣]\s*제\s*)?(?P<n2>\d+)\s*호증",
                target_str,
            ):
                p = rm.group("p")
                n1 = int(rm.group("n1"))
                n2 = int(rm.group("n2"))
                for k in range(n1, n2 + 1):
                    list_keys.add((p, k))
            for ref in parse_exhibits(target_str):
                k = (ref.get("party"), ref.get("number"))
                if k[0] and k[1] is not None:
                    list_keys.add(k)
                    span = ref["span"]
                    rest = target_str[span[1]:].strip()
                    m_name = re.match(
                        r"^([가-힣A-Za-z0-9_]+(?:\s+[가-힣A-Za-z0-9_]+)*?)(?=[,.]|\s*(?:피고인\s*증|[가-힣])\s*제\s*\d|$)",
                        rest,
                    )
                    if m_name:
                        nm = m_name.group(1).strip()
                        list_name_by_key[k] = (nm, re.sub(r"\s+", "", nm))

    # 자기 당사자 부호 집합 (상대방 증거 판단 배제용)
    listed_parties = {k[0] for k in list_keys if k[0]}
    if not listed_parties:
        return out

    # 본문 텍스트 분리: 입증방법/첨부서류/증거목록 섹션 헤더 이전의 순수 본문만 분리 (목록 내 기재 오인 방지)
    m_sec = re.search(
        r"(?:^|\n|[.!?]\s*)\s*(?:(?:(?:\d{1,2}|[가-하])\s*[.)]|\(\s*(?:\d{1,2}|[가-하])\s*\)|[①-⑳]|\[(?:\s*(?:\d{1,2}|[가-하]))?\s*\]?)\s*){0,3}"
        r"(?:입\s*증\s*방\s*법|첨\s*부\s*서\s*류|증\s*거\s*목\s*록|소\s*명\s*방\s*법)",
        text,
    )
    body_text = text[:m_sec.start()] if m_sec else text

    # 1. 완결 선언 목록과 본문 번호 대조 (축 1)
    # 목록 머리글 괄호 안의 완결 선언이 괄호 제거 등으로 유실되지 않도록 원문 text 전체에서 최우선 판정
    has_completion = bool(_COMPLETE_DECLARATION_RE.search(text))

    if has_completion:
        for raw_sentence in re.split(r"[.\n]+", body_text):
            sentence = raw_sentence
            # 이전 제출 호증 재인용 제외 (규칙 레벨 제외)
            if _PRIOR_SUBMISSION_RE.search(sentence):
                continue
            # 서증 목록/입증방법 자체 문장은 목록 앞부분만 취하여 인용 대조
            if any(h in sentence for h in ("증거목록", "입증방법", "제출 증거", "첨부서류", "첨부 목록")):
                m_sep = re.search(r"(?:최종\s*)?(?:증거목록|입증방법|제출\s*증거|첨부서류|첨부\s*목록)", sentence)
                if m_sep:
                    sentence = sentence[:m_sep.start()]
                else:
                    continue
            for ref in parse_exhibits(sentence):
                party = ref.get("party")
                num = ref.get("number")
                # 중요: 자기 당사자 부호의 호증만 판단 (상대방 호증 배제)
                if not party or party not in listed_parties or num is None:
                    continue
                key = (party, num)
                if key not in list_keys:
                    lbl = ref["label"]
                    if not any(f.confidence_features.get("exhibit") == lbl for f in out):
                        out.append(
                            _finding(
                                doc,
                                FindingType.EVIDENCE_LIST_MISMATCH,
                                EvidenceGrade.B,
                                Severity.MEDIUM,
                                f"완결 목록에 없는 호증 번호가 인용되었다: {lbl}",
                                f"증거 목록의 완결을 선언하였으나, 목록에 포함되지 않은 {lbl}이 본문에 원용되었다.",
                                sentence.strip()[:200],
                                features={
                                    "rule_id": "EVI.EVIDENCE_REFERENCE_MISSING",
                                    "defect_code": "EVIDENCE_REFERENCE_MISSING",
                                    "exhibit": lbl,
                                },
                            )
                        )

    # 2. 연속 범위 선언과 중간 번호 누락 (축 2)
    has_range_finding = False
    for m in _CONTINUOUS_RANGE_RE.finditer(text):
        p1 = m.group("p1")
        p2 = m.group("p2") or p1
        if p1 != p2 or p1 not in listed_parties:
            continue
        n1 = int(m.group("n1"))
        n2 = int(m.group("n2"))
        if n2 > n1 + 1:
            missing_nums = [k for k in range(n1 + 1, n2) if (p1, k) not in list_keys]
            if missing_nums:
                missing_lbl = f"{p1} 제{missing_nums[0]}호증"
                ctx_start = max(0, text.rfind(".", 0, m.start()) + 1)
                ctx_end = text.find(".", m.end())
                ctx_end = len(text) if ctx_end == -1 else ctx_end + 1
                excerpt = text[ctx_start:ctx_end].strip()
                if not any(
                    f.confidence_features.get("defect_code") == "CONTINUOUS_RANGE_GAP"
                    and f.confidence_features.get("exhibit") == missing_lbl
                    for f in out
                ):
                    has_range_finding = True
                    out.append(
                        _finding(
                            doc,
                            FindingType.EVIDENCE_LIST_MISMATCH,
                            EvidenceGrade.B,
                            Severity.MEDIUM,
                            f"연속 제출 선언 내 중간 호증이 목록에서 누락되었다: {missing_lbl}",
                            f"{p1} 제{n1}호증부터 제{n2}호증까지 연속 제출을 선언하였으나 중간의 {missing_lbl}이 목록에 없다.",
                            excerpt or missing_lbl,
                            features={
                                "rule_id": "EVI.CONTINUOUS_RANGE_GAP",
                                "defect_code": "CONTINUOUS_RANGE_GAP",
                                "exhibit": missing_lbl,
                                "range": f"{p1} 제{n1}호증 ~ 제{n2}호증",
                            },
                        )
                    )

    # 범위 선언이 없더라도 연속 키워드 선언이 명시된 경우 목록 순번 간격 확인
    if not has_range_finding and _CONTINUOUS_KEYWORD_RE.search(text):
        m_kw = _CONTINUOUS_KEYWORD_RE.search(text)
        ctx_start = max(0, text.rfind(".", 0, m_kw.start()) + 1)
        ctx_end = text.find(".", m_kw.end())
        ctx_end = len(text) if ctx_end == -1 else ctx_end + 1
        kw_excerpt = text[ctx_start:ctx_end].strip()

        for p in listed_parties:
            p_nums = sorted([k[1] for k in list_keys if k[0] == p])
            if len(p_nums) >= 2:
                missing_in_p = [k for k in range(p_nums[0], p_nums[-1] + 1) if (p, k) not in list_keys]
                if missing_in_p:
                    m_lbl = f"{p} 제{missing_in_p[0]}호증"
                    if not any(
                        f.confidence_features.get("defect_code") == "CONTINUOUS_RANGE_GAP"
                        and f.confidence_features.get("exhibit") == m_lbl
                        for f in out
                    ):
                        out.append(
                            _finding(
                                doc,
                                FindingType.EVIDENCE_LIST_MISMATCH,
                                EvidenceGrade.B,
                                Severity.MEDIUM,
                                f"연속 제출 선언 내 중간 호증이 목록에서 누락되었다: {m_lbl}",
                                f"연속 번호 제출을 선언하였으나 목록에서 {m_lbl}이 빠져 있다.",
                                kw_excerpt or m_lbl,
                                features={
                                    "rule_id": "EVI.CONTINUOUS_RANGE_GAP",
                                    "defect_code": "CONTINUOUS_RANGE_GAP",
                                    "exhibit": m_lbl,
                                },
                            )
                        )

    # 3. 본문·목록 동일 자료명의 호증 번호 불일치 (축 3, SUSPICIOUS·B, 4자 이상)
    # 평가 측 지침 준수:
    # 1) '지정' 구조에서만 판정 (따옴표 서증명, 괄호 호증, 서술형 지정, 직결 호증)
    #    - 조사 '와·과·및·이나' 등 병렬 나열 구조 및 일반 서술절 조사 결합은 철저히 제외.
    # 2) 자기 번호 우선: 본문 번호가 목록에 있고 그 목록 자료명이 본문 자료명과 부합하면
    #    다른 번호와의 불일치를 판정하지 않는다.

    def _is_self_match(body_k: tuple, test_norm: str) -> bool:
        """본문 번호의 목록 자료명이 본문 자료명과 같거나 부합하는지 확인 (자기 번호 우선)."""
        if body_k not in list_name_by_key:
            return False
        _, my_norm = list_name_by_key[body_k]
        if not my_norm or not test_norm:
            return False
        # 완전 일치, 또는 수식어 결합('변경/추가/2차 + 자료명') 접미/포함 일치
        if test_norm == my_norm:
            return True
        if len(my_norm) >= 3 and (test_norm.endswith(my_norm) or my_norm.endswith(test_norm)):
            return True
        if len(test_norm) >= 4 and len(my_norm) >= 4 and (test_norm in my_norm or my_norm in test_norm):
            return True
        return False

    # 패턴 1: 호증 뒤 자료명 (예: 갑 제22호증 운반 사진)
    pat1 = re.compile(
        r"(?P<label>(?:피고인\s*증|[가-힣])\s*제\s*\d+\s*호증(?:의\s*\d+)?)\s*(?P<rest>[^\n.,;:]{2,40})"
    )
    for m in pat1.finditer(body_text):
        lbl = m.group("label")
        rest = m.group("rest").strip()
        window = body_text[max(0, m.start() - 30) : min(len(body_text), m.end() + 30)]
        if _PRIOR_SUBMISSION_RE.search(window):
            continue
        body_refs = parse_exhibits(lbl)
        if not body_refs:
            continue
        body_key = (body_refs[0]["party"], body_refs[0]["number"])
        if body_key[0] not in listed_parties:
            continue

        rest_norm = re.sub(r"\s+", "", rest)
        # 자기 번호 우선: 본문 번호의 목록 자료명과 이미 부합하면 건너뜀
        if _is_self_match(body_key, rest_norm):
            continue

        for list_key, (l_name, l_norm) in list_name_by_key.items():
            if body_key != list_key and body_key[0] == list_key[0] and len(l_norm) >= 4:
                chars = [re.escape(c) for c in l_norm]
                name_pat = r"^\s*" + r"\s*".join(chars) + r"(?:에서|으로|부터|까지|[이가은는을를의에로와과도만등])?(?=[\s.,;:~!?]|$)"
                if re.match(name_pat, rest):
                    list_lbl = f"{list_key[0]} 제{list_key[1]}호증"
                    dup = any(
                        f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"
                        and f.confidence_features.get("body_exhibit") == lbl
                        for f in out
                    )
                    if not dup:
                        out.append(
                            _finding(
                                doc,
                                FindingType.EVIDENCE_LIST_MISMATCH,
                                EvidenceGrade.B,
                                Severity.MEDIUM,
                                f"본문과 증거목록의 호증 번호가 일치하지 않는다: 본문 '{lbl} {l_name}', 목록 '{list_lbl} {l_name}'",
                                f"같은 서증명 '{l_name}'에 대해 본문에서는 {lbl}, 증거목록에서는 {list_lbl}으로 서로 다른 번호를 기재하였다.",
                                f"본문: {lbl} {l_name} ↔ 목록: {list_lbl} {l_name}",
                                status=VerificationStatus.SUSPICIOUS,
                                features={
                                    "rule_id": "EVI.EXHIBIT_NUMBER_NAME_MISMATCH",
                                    "defect_code": "EXHIBIT_NUMBER_NAME_MISMATCH",
                                    "body_exhibit": lbl,
                                    "list_exhibit": list_lbl,
                                    "name": l_name,
                                },
                            )
                        )

    # 패턴 2: 자료명 뒤 호증 - 지정 구조 한정 수집
    pat2_candidates = []

    # (1) 따옴표 서증명: 「계약서」(갑 제1호증), '합의서' 갑 제2호증
    for m in re.finditer(
        r"[「‘'\"](?P<qname>[^」’'\"]{2,30})[」’'\"]\s*(?:\(\s*)?(?P<lbl>(?:피고인\s*증|[가-힣])\s*제\s*\d+\s*호증(?:의\s*\d+)?)(?:\s*\))?",
        body_text,
    ):
        pat2_candidates.append((m.group("qname").strip(), m.group("lbl"), m.start(), m.end(), False))

    # (2) 괄호 묶임: 서증명(갑 제N호증), 변경계약서 (갑 제2호증)
    for m in re.finditer(
        r"(?P<name>[가-힣A-Za-z0-9_]{2,25}(?:\s+[가-힣A-Za-z0-9_]{2,20})?)\s*\(\s*(?P<lbl>(?:피고인\s*증|[가-힣])\s*제\s*\d+\s*호증(?:의\s*\d+)?)\s*\)",
        body_text,
    ):
        pat2_candidates.append((m.group("name").strip(), m.group("lbl"), m.start(), m.end(), True))

    # (3) 서술형 지정: 서증명(을/를) 갑 제N호증으로 제출/원용/지정
    for m in re.finditer(
        r"(?P<name>[가-힣A-Za-z0-9_]{2,25}(?:\s+[가-힣A-Za-z0-9_]{2,20})?)\s*(?P<lbl>(?:피고인\s*증|[가-힣])\s*제\s*\d+\s*호증(?:의\s*\d+)?)(?:으로|로)\s*(?:제출|원용|지정|신청|제시|증명)",
        body_text,
    ):
        raw = m.group("name").strip()
        cleaned = re.sub(r"[을를]$", "", raw).strip()
        pat2_candidates.append((cleaned, m.group("lbl"), m.start(), m.end(), False))

    # (4) 직결 호증: 서증명 갑 제N호증 (공백 1개 이상 연결)
    for m in re.finditer(
        r"(?P<name>[가-힣A-Za-z0-9_]{2,20}(?:\s+[가-힣A-Za-z0-9_]{2,20})?)\s+(?P<lbl>(?:피고인\s*증|[가-힣])\s*제\s*\d+\s*호증(?:의\s*\d+)?)",
        body_text,
    ):
        pat2_candidates.append((m.group("name").strip(), m.group("lbl"), m.start(), m.end(), True))

    for nm_raw, lbl, start_pos, end_pos, check_particle in pat2_candidates:
        window = body_text[max(0, start_pos - 30) : min(len(body_text), end_pos + 30)]
        if _PRIOR_SUBMISSION_RE.search(window):
            continue

        # 조사 '와·과·및·이나' 등 병렬 나열 구조 및 일반 서술절 조사 결합 제외
        if check_particle:
            # 자료명 끝에 병렬 조사(와/과/및/이나 등)나 서술격 조사가 붙은 경우 제외
            if re.search(r"(?:와|과|및|이나|도|은|는|이|가|에|의|로|에서|부터|까지)$", nm_raw):
                continue
            # 자료명 직전 문맥에 '및', '또는', '와', '과' 병렬 접속사가 위치한 경우 제외
            pre_window = body_text[max(0, start_pos - 5) : start_pos]
            if re.search(r"(?:및|또는|와|과)\s*$", pre_window):
                continue

        nm_clean = nm_raw
        nm_norm = re.sub(r"\s+", "", nm_clean)
        if len(nm_norm) < 4:
            continue

        # 일반 서술 어휘 배제
        if re.search(r"(?:주장|지적|사실|내용|기재|경우|사항|이유|취지|부분|서면|준비서면|답변서|소장|신청서)$", nm_norm):
            continue

        body_refs = parse_exhibits(lbl)
        if not body_refs:
            continue
        body_key = (body_refs[0]["party"], body_refs[0]["number"])
        if body_key[0] not in listed_parties:
            continue

        # 자기 번호 우선: 본문 번호의 목록 자료명이 본문 자료명과 부합하면 판정 제외
        if _is_self_match(body_key, nm_norm):
            continue

        for list_key, (l_name, l_norm) in list_name_by_key.items():
            is_match = (nm_norm == l_norm) or (len(l_norm) >= 4 and nm_norm.endswith(l_norm) and not any(nm_norm.endswith(c + l_norm) for c in ("와", "과", "및")))
            if body_key != list_key and body_key[0] == list_key[0] and is_match:
                list_lbl = f"{list_key[0]} 제{list_key[1]}호증"
                dup = any(
                    f.confidence_features.get("defect_code") == "EXHIBIT_NUMBER_NAME_MISMATCH"
                    and f.confidence_features.get("body_exhibit") == lbl
                    for f in out
                )
                if not dup:
                    out.append(
                        _finding(
                            doc,
                            FindingType.EVIDENCE_LIST_MISMATCH,
                            EvidenceGrade.B,
                            Severity.MEDIUM,
                            f"본문과 증거목록의 호증 번호가 일치하지 않는다: 본문 '{nm_clean} {lbl}', 목록 '{list_lbl} {l_name}'",
                            f"같은 서증명 '{l_name}'에 대해 본문에서는 {lbl}, 증거목록에서는 {list_lbl}으로 서로 다른 번호를 기재하였다.",
                            f"본문: {nm_clean} {lbl} ↔ 목록: {list_lbl} {l_name}",
                            status=VerificationStatus.SUSPICIOUS,
                            features={
                                "rule_id": "EVI.EXHIBIT_NUMBER_NAME_MISMATCH",
                                "defect_code": "EXHIBIT_NUMBER_NAME_MISMATCH",
                                "body_exhibit": lbl,
                                "list_exhibit": list_lbl,
                                "name": l_name,
                            },
                        )
                    )

    # 4. 선언 개수와 실제 목록 수 불일치 (축 4)
    # 목록 구역 헤더 또는 목록 완결 선언 줄에서만 개수 선언 검사 (상대방 진술 배제)
    for line in text.split("\n"):
        # 상대방 주어가 있으면 제외
        if re.search(r"(?:피고|원고|상대방|피고인|고소인)는\s*(?:[^\n]*?)?(?:제출|주장)", line):
            continue
        if re.search(r"(?:증거목록|입증방법|제출\s*증거|제출목록)", line):
            m_count = _COUNT_DECLARATION_RE.search(line)
            if m_count and exhibits:
                declared_str = m_count.group("count") or m_count.group("count2")
                if declared_str:
                    declared_cnt = int(declared_str)
                    actual_cnt = len(list_keys)
                    if declared_cnt != actual_cnt and declared_cnt > 0 and actual_cnt > 0:
                        ctx_start = max(0, text.rfind(".", 0, m_count.start()) + 1)
                        ctx_end = text.find(".", m_count.end())
                        ctx_end = len(text) if ctx_end == -1 else ctx_end + 1
                        excerpt = text[ctx_start:ctx_end].strip()
                        out.append(
                            _finding(
                                doc,
                                FindingType.EVIDENCE_LIST_MISMATCH,
                                EvidenceGrade.B,
                                Severity.MEDIUM,
                                f"증거 목록 선언 개수({declared_cnt}개)와 실제 서증 수({actual_cnt}개)가 일치하지 않는다",
                                f"증거 목록에서 총 {declared_cnt}개 제출을 선언하였으나 실제 목록에는 {actual_cnt}개만 기재되었다.",
                                excerpt or f"선언 {declared_cnt}개 ↔ 실제 {actual_cnt}개",
                                features={
                                    "rule_id": "EVI.EXHIBIT_COUNT_MISMATCH",
                                    "defect_code": "EXHIBIT_COUNT_MISMATCH",
                                    "declared_count": declared_cnt,
                                    "actual_count": actual_cnt,
                                },
                            )
                        )
                        break

    return out


# --- 서증 형식 결함(EVI-FORM) 구조 기반 검출 ----------------------------------

def _detect_author_party(
    doc: NormalizedDocument, exhibits: Sequence[Dict[str, Any]]
) -> Tuple[Optional[str], set]:
    """서면의 작성 당사자(원고/피고)와 자기 당사자 호증 부호 집합을 결정한다.

    1순위: 문서 후반부 서명·제출인 줄 (... 소송대리인, ... 원고, ... 피고)
           - 피고 답변서 끝에 흔히 오는 '원고의 청구를 기각하여...'와 같은
             신청취지/주문 문구를 오인하지 않도록 서명·제출 줄 형식을 엄격히 확인한다.
    2순위: 문서 표제부/서두 (소장, 답변서, 준비서면(원고/피고) 등)
    3순위: 증거목록(exhibits)에 기재된 부호
    """
    author_party = None
    blocks = [b for b in doc.body_blocks() if b.block_type != "running_head"]

    # 1순위: 문서 후반부 서명/제출인 줄 검사 (뒤에서부터 탐색, 블록 내 줄 단위 분할)
    tail_blocks = blocks[-15:] if blocks else []
    for b in reversed(tail_blocks):
        b_text = (b.text or "").strip()
        lines = [ln.strip() for ln in b_text.splitlines() if ln.strip()]
        for line in reversed(lines):
            # 피고 답변서 끝에 흔히 오는 주문/신청취지 문맥("원고의 청구를 기각...") 제외
            if any(k in line for k in ("청구를 기각", "소송비용은", "판결을 구합니다", "결정을 구합니다")):
                continue
            # 피고 제출인/서명 줄
            if re.search(
                r"(?:^|\s)(?:피\s*고|피\s*신\s*청\s*인|채\s*무\s*자|피\s*고\s*인)"
                r"(?:\s*(?:들\s*)?(?:소\s*송\s*)?대\s*리\s*인|\s+[가-힣]{2,4})?"
                r"(?:\s*\(?\s*인\s*\)?|\s*印|\s*법무법인|\s*변호사|\s*$)",
                line,
            ):
                author_party = "피고"
                break
            # 원고 제출인/서명 줄
            if re.search(
                r"(?:^|\s)(?:원\s*고|신\s*청\s*인|채\s*권\s*자|고\s*소\s*인|청\s*구\s*인)"
                r"(?:\s*(?:들\s*)?(?:소\s*송\s*)?대\s*리\s*인|\s+[가-힣]{2,4})?"
                r"(?:\s*\(?\s*인\s*\)?|\s*印|\s*법무법인|\s*변호사|\s*$)",
                line,
            ):
                author_party = "원고"
                break
        if author_party:
            break

    # 2순위: 문서 표제부/서두 검사
    if not author_party and blocks:
        head_text = "\n".join((b.text or "").strip() for b in blocks[:8])
        if re.search(r"(?:^|\n)\s*(?:답\s*변\s*서|준비서면\s*\(피고\)|피고\s+준비서면)", head_text):
            author_party = "피고"
        elif re.search(r"(?:^|\n)\s*(?:소\s*장|신\s*청\s*서|고\s*소\s*장|준비서면\s*\(원고\)|원고\s+준비서면)", head_text):
            author_party = "원고"

    # 목록에 실제 등장하는 부호 수집 (#126 호환)
    listed_parties = {r.get("party") for r in exhibits if r.get("party")}

    if author_party == "원고":
        my_party_chars = {"갑", "소갑"}
    elif author_party == "피고":
        my_party_chars = {"을", "소을"}
    elif listed_parties:
        my_party_chars = set(listed_parties)
    else:
        my_party_chars = {"갑", "을"}

    return author_party, my_party_chars


def _has_defect_suffix_from_refutation(
    sentence: str, match: re.Match, my_party_chars: Sequence[str]
) -> bool:
    """반박 절 매칭 뒤(연결어미 -며·-고·-나·-지만 등 뒤)에 자기 측 원본 분실·미제출 자인 등 진짜 결함이 있는지 확인."""
    suffix = sentence[match.end():].strip()
    if suffix and len(suffix) >= 4:
        if (
            _EVI_FORM_UNSUBMITTED_RE.search(suffix)
            or _EVI_FORM_EXHIBIT_UNSUBMITTED_RE.search(suffix)
            or _EVI_FORM_BLANK_RE.search(suffix)
            or _EVI_FORM_UNIDENTIFIABLE_RE.search(suffix)
        ):
            refs = parse_exhibits(suffix) or parse_exhibits(sentence)
            if refs and any(r.get("party") in my_party_chars for r in refs):
                return True
    return False


def check_evidence_form_defects(
    doc: NormalizedDocument, exhibits: Optional[Sequence[Dict[str, Any]]] = None
) -> List[Finding]:
    """서면이 자기 증거로 원용하는 서증의 소송법상 형식적 결함을 구조적으로 판별한다 (EVI-FORM).

    1. 축 1: 서증 자리표시 기호/마크업 또는 내용 없이 파일명 단독 (SUSPICIOUS · B)
       - 정상 물리 매체(USB, CD 등) 별도 제출 표기는 보호(제외)
       - 추후 제출/보완 예정 등 입증 계획 서술문은 보호(제외)
    2. 축 2: 서면 스스로 실물/원본/파일 부재 또는 호증 자체 미제출 자인 (CONTRADICTED · B)
    3. 축 3: 필수 기재사항(작성자, 서명, 날짜) 공란/누락 양식 (SUSPICIOUS · B)
       - 본안 서면 자체의 전자서명 생략은 보호(제외)
       - 결손의 부존재(부정의 부정) 진술은 보호(제외)
    4. 축 4: 중요 내용(금액, 글자 등) 식별 불가/잘림 자인 + 증명 주장 (CONTRADICTED · B)

    * 주체 구분 및 정상 실무 보호:
      - 서면의 증거목록에 실린 자기 호증만 판단.
      - 상대방 증거 탄핵 주장(신빙성, 진정성립 다툼 등)은 결함에서 원천 배제.
      - 결함 해소·추완 진술, 이중 부정 반박, 상대방 주장 인용 반박, 부정의 부정은 결함에서 원천 제외.
      - 단락 내 선행 호증 인접 문장 결속 및 목록 행 괄호 첨부 예정 검사 지원.
    """
    if exhibits is None:
        exhibits = exhibit_rows(doc)
    out: List[Finding] = []
    seen_exhibits = set()

    # 1. 서면의 작성 당사자 및 자기 증거 부호 집합 식별
    author_party, my_party_chars = _detect_author_party(doc, exhibits)

    # 2. 증거목록(exhibits) 행 자체의 괄호 속 자리표시 검사 (피드백 5-4)
    for r in exhibits:
        party = r.get("party")
        if party not in my_party_chars:
            continue
        num = r.get("number")
        lbl = f"{party} 제{num}호증"
        if lbl in seen_exhibits:
            continue
        r_name = r.get("name") or ""
        if _EVI_FORM_PLACEHOLDER_RE.search(r_name) and not _EVI_FORM_SEPARATE_MEDIA_RE.search(r_name):
            seen_exhibits.add(lbl)
            out.append(
                _finding(
                    doc,
                    FindingType.EVIDENCE_FORM_DEFECT,
                    EvidenceGrade.B,
                    Severity.MEDIUM,
                    f"서증 형식 결함: 자리표시 또는 미제출 파일명만 기재 — {lbl}",
                    f"{lbl}의 증거목록에 실제 내용 없이 자리표시 또는 첨부 예정 표기만 기재된 형식적 흠결이 있다.",
                    f"{lbl} {r_name}"[:250],
                    status=VerificationStatus.SUSPICIOUS,
                    features={
                        "rule_id": "EVI.EXHIBIT_PLACEHOLDER_ONLY",
                        "defect_code": "EXHIBIT_PLACEHOLDER_ONLY",
                        "exhibit": lbl,
                    },
                )
            )

    # 3. 단락별 순회 및 문장 단위 검사 (인접 문장 결속 및 첨부자료 검사 지원)
    blocks = [b for b in doc.body_blocks() if b.block_type != "running_head"]
    if not blocks:
        rtext = build_reading_text(doc).text
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", rtext) if p.strip()]
    else:
        paragraphs = [b.text.strip() for b in blocks if b.text.strip()]

    for para in paragraphs:
        # 단락 전체가 절차 사유(추가 제출 없음, 중복 생략, 공적 전산 확인, 촉탁·제출명령 사유)인 경우 정상 실무이므로 제외 (전달문 16)
        if _EVI_FORM_PROCEDURAL_JUSTIFICATION_RE.search(para):
            continue

        # 단락 내 문장 순회 (인접 문장 결속 지원)
        sentences = [s.strip() for s in re.split(r"(?<=[다습음죠치시오!?.])\s+|\n+", para) if s.strip()]
        pending_ref = None  # 인접 문장 결속용

        for sentence in sentences:
            if not sentence or len(sentence) < 4:
                continue

            # 정상 실무 보호 1: 추후 제출/보완 예정(입증 계획) 및 기일 지참 서술문은 결함 제외
            if _NORMAL_FUTURE_SUBMISSION_RE.search(sentence):
                pending_ref = None
                continue

            # 정상 실무 보호 2: 물리 매체(USB, CD 등) 별도 제출 표기는 정상 실무이므로 제외
            if _EVI_FORM_SEPARATE_MEDIA_RE.search(sentence):
                pending_ref = None
                continue

            # 정상 실무 보호 3: 결함 해소·추완 진술, 이중 부정 반박, 상대방 주장 인용 반박, 부정의 부정 제외 (피드백 1)
            ref_match = _EVI_FORM_NON_DEFECT_CONTEXT_RE.search(sentence)
            if ref_match:
                # TK-81 잔여 보완: 제외 범위를 반박 절로 한정.
                # 복문에서 반박 절 뒤(연결어미 -며·-고·-나·-지만 등 뒤)에 진짜 서증 결함(미제출 자인 등)이 있으면 제외하지 않고 결함 검사를 계속한다.
                if not _has_defect_suffix_from_refutation(sentence, ref_match, my_party_chars):
                    pending_ref = None
                    continue

            # 정상 실무 보호 4: 절차 사유 (추가 제출 부존재, 중복 첨부 생략, 공적 전산 확인, 촉탁·제출명령 사유) 결함 제외 (전달문 16)
            if _EVI_FORM_PROCEDURAL_JUSTIFICATION_RE.search(sentence):
                pending_ref = None
                continue

            # 상대방 주어에 의한 서술/탄핵 배제 및 상대방 주장 인용 반박 배제 (전달문 17 조건 2)
            opp_words = None
            if author_party == "원고":
                opp_words = r"(?:피고|상대방|피신청인|채무자|피고인)"
            elif author_party == "피고":
                opp_words = r"(?:원고|상대방|신청인|채권자|고소인)"
            else:
                opp_words = r"(?:상대방|상대측)"

            if opp_words:
                # 1) 상대방 주어 + 제출/주장/인용/원용/작성/서증/호증
                if re.search(opp_words + r"\b[^\n.]{0,30}(?:제출|주장|인용|원용|작성|서증|호증)", sentence):
                    pending_ref = None
                    continue
                # 2) 전달문 17 조건 2: 상대방 주어 + 인용 어미(-다고/-라고) + 역접(-지만/-나/-였으나)
                if re.search(opp_words + r"(?:는|가|은|이|의|측은|측이)?\s*[^\n.]{0,60}?(?:다고|라고)\s*(?:주장하|다투|말하|강변하|지적하|언급하|하)?(?:지만|나\b|였으나|었으나|나마|되\b)", sentence):
                    pending_ref = None
                    continue
                # 3) 전달문 19·20·26 TK-81: 상대방 주어 + 관형형(-다는/-라는) + 주장/지적 + 부정 평가 반박
                opp_match = re.search(
                    opp_words + r"(?:는|가|은|이|의|측은|측이)?\s*[^\n.]{0,60}?(?:다는|라는)\s*(?:주장|지적|항변|진술|의견|의혹)[^\n.]{0,30}?"
                    r"(?:"
                    r"사실과\s*(?:다르|다릅|달라|달랐)(?!\s*(?:지\s*(?:않|아니)|않|아니|아닙))"
                    r"|사실이\s*(?:아닙|아니|아님)(?!\s*(?:지\s*(?:않|아니)|않|아니))"
                    r"|(?:사실과\s*)?(?:틀립[니시]|틀렸[다습음으]|틀려[서야도]|틀리다|틀린\s*(?:것|주장|지적)(?:이|입|으))(?!\s*(?:지\s*(?:않|아니)|않|아니|아닙|없))"
                    r"|(?:명백한\s*)?잘못(?:입니다|이다|임|되었[다습음으]|되어\b|된\s*(?:것|주장|지적|판단)(?:이|입|으)|(?:\s*(?:알|파악|이해|해석|판단)(?:하고|한|하였)))(?!\s*(?:지\s*(?:않|아니)|않|아니|아닙|없))"
                    r"|그릇된"
                    r"|착오에\s*기인"
                    r"|이유\s*(?:없|아닙|아니)(?!\s*(?:지\s*않|지\s*아니))"
                    r"|근거\s*(?:없|부족)(?!\s*(?:지\s*않|지\s*아니))"
                    r"|부당"
                    r"|터무니\s*없"
                    r"|어불성설"
                    r")",
                    sentence,
                )
                if opp_match:
                    if not _has_defect_suffix_from_refutation(sentence, opp_match, my_party_chars):
                        pending_ref = None
                        continue

            # 일반 탄핵 키워드 (신빙성 배척, 진정성립 다툼, 입증 부족 등) 배제
            if re.search(r"신빙성(?:이|은)?\s*(?:없|의심|떨어|배척)|진정성립(?:이|은)?\s*(?:인정될\s*수\s*없|부인|다투)|입증하기에?\s*부족", sentence):
                pending_ref = None
                continue

            # 본안 서면 자체의 제출/접수/법원 표기 단락(전자서명 생략 등) 제외
            if re.search(r"(?:귀\s*중|법원\s*귀중|소송대리인|제출인)", sentence):
                pending_ref = None
                continue

            refs = parse_exhibits(sentence)
            target_ref = None

            if refs:
                my_refs = [r for r in refs if r.get("party") in my_party_chars]
                if my_refs:
                    target_ref = my_refs[0]
                    pending_ref = target_ref  # 다음 인접 문장을 위해 기억
                else:
                    pending_ref = None
                    continue
            elif pending_ref is not None:
                # 피드백 3: 인접 문장 결속 (앞 문장에 자기 호증이 있고 결함 진술이 이어지는 경우)
                target_ref = pending_ref
                pending_ref = None
            else:
                continue

            if target_ref is None:
                continue

            lbl = target_ref.get("label") or f"{target_ref.get('party')} 제{target_ref.get('number')}호증"
            if lbl in seen_exhibits:
                continue

            defect = None

            # 축 1: 서증 자리표시 기호/마크업 또는 내용 없이 파일명 단독 -> SUSPICIOUS · B
            if _EVI_FORM_PLACEHOLDER_RE.search(sentence):
                defect = (
                    VerificationStatus.SUSPICIOUS,
                    EvidenceGrade.B,
                    Severity.MEDIUM,
                    f"서증 형식 결함: 자리표시 또는 미제출 파일명만 기재 — {lbl}",
                    f"{lbl}에 대해 실제 내용이나 사본 없이 자리표시 또는 미제출 파일명만 기재된 형식적 흠결이 있다.",
                    "EXHIBIT_PLACEHOLDER_ONLY",
                    "EVI.EXHIBIT_PLACEHOLDER_ONLY",
                )

            # 축 2: 서면 자체의 부제출 자인 (문서 내 진술 모순) -> CONTRADICTED · B
            elif _EVI_FORM_UNSUBMITTED_RE.search(sentence) or _EVI_FORM_EXHIBIT_UNSUBMITTED_RE.search(sentence):
                defect = (
                    VerificationStatus.CONTRADICTED,
                    EvidenceGrade.B,
                    Severity.MEDIUM,
                    f"서증 형식 결함: 서증 미제출 자인 — {lbl}",
                    f"{lbl}을 입증자료로 원용하면서도 서면 스스로 해당 문서나 원본이 제출되지 않았음을 자인하는 모순이 있다.",
                    "UNSUBMITTED_EVIDENCE_ADMISSION",
                    "EVI.UNSUBMITTED_EVIDENCE_ADMISSION",
                )

            # 축 3: 필수 기재사항(서명·작성자·날짜) 공란 양식 -> SUSPICIOUS · B
            elif _EVI_FORM_BLANK_RE.search(sentence):
                defect = (
                    VerificationStatus.SUSPICIOUS,
                    EvidenceGrade.B,
                    Severity.MEDIUM,
                    f"서증 형식 결함: 작성자 성명 또는 서명·날인 공란 — {lbl}",
                    f"{lbl}의 작성자 성명이나 서명·날인란이 공란인 채로 제출되어 진정성립을 인정할 수 없는 형식적 흠결이 있다.",
                    "BLANK_FORM_DEFECT",
                    "EVI.BLANK_FORM_DEFECT",
                )

            # 축 4: 중요 내용 식별 불가 자인 + 증명력 주장 -> CONTRADICTED · B
            elif _EVI_FORM_UNIDENTIFIABLE_RE.search(sentence):
                defect = (
                    VerificationStatus.CONTRADICTED,
                    EvidenceGrade.B,
                    Severity.MEDIUM,
                    f"서증 형식 결함: 중요 기재사항 잘림 또는 식별 불가 자인 — {lbl}",
                    f"{lbl}의 중요 내용(금액, 글자 등)이 잘리거나 식별 불가능함을 자인하면서도 이를 입증자료로 원용한 모순이 있다.",
                    "UNIDENTIFIABLE_CONTENT_TRUNCATED",
                    "EVI.UNIDENTIFIABLE_CONTENT_TRUNCATED",
                )

            if defect:
                seen_exhibits.add(lbl)
                status, grade, sev, title, detail, dcode, rule_id = defect
                out.append(
                    _finding(
                        doc,
                        FindingType.EVIDENCE_FORM_DEFECT,
                        grade,
                        sev,
                        title,
                        detail,
                        sentence[:250],
                        status=status,
                        features={
                            "rule_id": rule_id,
                            "defect_code": dcode,
                            "exhibit": lbl,
                        },
                    )
                )

    return out


def check_document(doc: NormalizedDocument) -> List[Finding]:
    exhibits = exhibit_rows(doc)
    return (
        check_exhibits(doc)
        + check_statements(doc, exhibits)
        + check_evidence_numbering_mismatches(doc, exhibits)
        + check_evidence_form_defects(doc, exhibits)
    )


# --- 서면 간 문장 복사 -------------------------------------------------------------
_QUOTED_RE = re.compile(r"[“\"「『][^”\"」』]{6,}[”\"」』]")
_NORMALIZE_RE = re.compile(r"[\s\W_]+", re.UNICODE)
# 서명·날인·제출 확인 등 서면 간 겹치기 쉬운 정형 상투구 문구 패턴
_BOILERPLATE_RE = re.compile(r"(?:사실과\s*다름없음을\s*확인|서명\s*날인\s*(?:합니다|함|하였음)|작성하여\s*제출합니다|본인의\s*자유로운\s*의사)")


def _shingles(text: str, n: int = 5) -> set:
    return {text[i:i + n] for i in range(max(0, len(text) - n + 1))}


def _sentences_for_copy(doc: NormalizedDocument) -> List[Tuple[str, str]]:
    text = build_reading_text(doc).text
    out = []
    for start, end in sentence_bounds(text):
        sentence = text[start:end].strip()
        body = _QUOTED_RE.sub("", sentence)  # 판례·법령 인용문은 서면끼리 겹치는 것이 정상이다
        # 서명·날인 확인 등 정형 상투구는 서면 간 겹칠 수 있으므로 복사 탐지 대상에서 제외한다
        if _BOILERPLATE_RE.search(body):
            continue
        key = _NORMALIZE_RE.sub("", body)
        if len(key) >= COPY_MIN_CHARS:
            out.append((sentence, key))
    return out


# 서면 공통 서두 표제부(송달장소, 요청취지, 제출경위 등) 패턴
# 진술서 제목이 머리글로만 분리된 경우, 표제부 뒤부터가 실제 진술 구역이다.
PREAMBLE_HEADING_RE = re.compile(
    r"(?:송달장소\s*:[^\n]+(?:\n|$)|"
    r"(?:요청|청구)\s*취지[^\n]+(?:\n|$)|"
    r"제출\s*경위[^\n]+(?:\n|$))"
)


def _statement_start(doc_or_text: NormalizedDocument | str, reading_text: Optional[str] = None) -> Optional[int]:
    """진술서·확인서 문서의 실제 진술 본문 시작 오프셋을 반환한다.
    
    1. 본문 텍스트 내에 '진술서·사실확인서·확인서' 제목 줄이 직접 있는 경우 그 제목 줄 바로 뒤의 오프셋을 반환한다.
    2. 여러 쪽에 반복되는 머리글(running_head)로 분류되어 본문 텍스트에서는 제외되었으나
       문서 블록에 해당 제목이 있는 경우, 서면 표제부(송달장소·요청취지 등 공통 서두) 뒤의 실제 진술 구역 시작 오프셋을 반환한다.
    진술서·확인서 계열 문서가 아니면 None을 반환한다.
    """
    if isinstance(doc_or_text, str):
        text = doc_or_text
        doc = None
    else:
        doc = doc_or_text
        text = reading_text if reading_text is not None else build_reading_text(doc).text

    # 1. 본문 텍스트 내 직접 제목 줄 탐색
    heading = STATEMENT_HEADING_RE.search(text)
    if heading:
        return heading.end()

    # 2. doc 객체가 주어진 경우, 머리글(running_head) 또는 상단 블록의 진술서 제목 탐색
    if doc is not None:
        is_statement = any(
            STATEMENT_HEADING_RE.search(b.text or "")
            for b in doc.blocks
            if b.block_type in ("running_head", "paragraph")
        )
        if is_statement:
            # 진술서 제목이 머리글로만 분리된 경우:
            # 서면 서두의 표제부(송달장소, 요청취지, 제출경위 등 다른 서면과 공통인 부분)가 있으면 그 뒤부터 진술 구역으로 본다.
            preamble_matches = list(PREAMBLE_HEADING_RE.finditer(text[:2000]))
            if preamble_matches:
                return preamble_matches[-1].end()
            return 0

    return None


# 문서 종류 상수 (B-2 비진술서 복제 탐지용)
DOC_KIND_FACT_CONFIRMATION = "FACT_CONFIRMATION"      # 사실경위서 등 원본 서증
DOC_KIND_STATEMENT = "STATEMENT"                      # 진술서, 사실확인서 등 진술 서증
DOC_KIND_EVIDENCE_EXPLANATION = "EVIDENCE_EXPLANATION"  # 증거설명서, 증거목록 (민사소송규칙 제106조 예외)
DOC_KIND_PLEADING = "PLEADING"                        # 소장, 준비서면, 답변서, 의견서 등 소송서면
DOC_KIND_OTHER = "OTHER"

FACT_CONFIRMATION_HEADING_RE = re.compile(
    r"(?:^|\n)\s*(?:사\s*실\s*경\s*위\s*서|사\s*건\s*경\s*위\s*서|경\s*위\s*서)\s*(?:\n|$)"
)

EVIDENCE_EXPLANATION_HEADING_RE = re.compile(
    r"(?:^|\n)\s*(?:증\s*거\s*설\s*명\s*서|증\s*거\s*목\s*록)\s*(?:\n|$)"
)

PLEADING_HEADING_RE = re.compile(
    r"(?:^|\n)\s*(?:소\s*장|준\s*비\s*서\s*면|답\s*변\s*서|의\s*견\s*서|항\s*소\s*장|상\s*고\s*장)\s*(?:\n|$)"
)

_EXHIBIT_REFERENCE_RE = re.compile(
    r"(?:(?:갑|을)\s*제?\s*\d+\s*호증|사실경위서(?:의\s*기재|에\s*의하면|를\s*살펴보면))"
)


def _document_title_kind(doc: NormalizedDocument, reading_text: Optional[str] = None) -> Tuple[str, Optional[int]]:
    """문서의 표제를 분석하여 (문서 종류, 본문 시작 오프셋)을 반환한다 (조건 3 검증)."""
    text = reading_text if reading_text is not None else build_reading_text(doc).text
    top_text = text[:1500]

    # 블록 머리글/단락 텍스트도 보조 확인
    head_blocks_text = "\n".join(b.text or "" for b in doc.blocks[:5])

    # 1. 증거설명서 / 증거목록 (민사소송규칙 제106조 예외 대상)
    if (EVIDENCE_EXPLANATION_HEADING_RE.search(top_text)
            or EVIDENCE_EXPLANATION_HEADING_RE.search(head_blocks_text)):
        return DOC_KIND_EVIDENCE_EXPLANATION, 0

    # 2. 사실경위서 (원본 서증)
    m_fact = FACT_CONFIRMATION_HEADING_RE.search(top_text)
    if m_fact:
        return DOC_KIND_FACT_CONFIRMATION, m_fact.end()
    if any(FACT_CONFIRMATION_HEADING_RE.search(b.text or "")
           for b in doc.blocks if b.block_type in ("running_head", "paragraph")):
        return DOC_KIND_FACT_CONFIRMATION, 0

    # 3. 진술서 / 사실확인서
    stmt_start = _statement_start(doc, text)
    if stmt_start is not None:
        return DOC_KIND_STATEMENT, stmt_start

    # 4. 소송 대리 서면 (소장, 준비서면, 답변서, 의견서)
    if (PLEADING_HEADING_RE.search(top_text)
            or any(PLEADING_HEADING_RE.search(b.text or "")
                   for b in doc.blocks if b.block_type in ("running_head", "paragraph"))):
        return DOC_KIND_PLEADING, 0

    return DOC_KIND_OTHER, None


def cross_document_copies(documents: Iterable[NormalizedDocument]) -> List[Finding]:
    """진술서 대필 의심 및 서증 원본(사실경위서) 통복제 결함을 탐지한다.

    1. 진술서·확인서 계열 문서(4순위): 다른 서면 문장과 일치 시 B등급(SUSPICIOUS)
    2. 소송서면이 사실경위서 원본 문단을 통복제한 경우(5순위): C등급(SUSPICIOUS)
       - 민사소송규칙 제106조 예외: 증거설명서는 통복제 결함에서 제외(SKIP)
       - 서증 정식 원용 표기가 포함된 문장 제외(SKIP)
    3. 소송서면 간 정상적인 변론 요지 재진술(7순위): 정상 보호(SKIP)
    """
    docs = list(documents)
    texts = {d.document_id: build_reading_text(d).text for d in docs}
    doc_kinds = {d.document_id: _document_title_kind(d, texts[d.document_id]) for d in docs}

    # 진술서나 사실경위서가 포함되어 있지 않고 소송서면 간에도 복사 검사 대상이 없으면 종료
    has_statements = any(k[0] == DOC_KIND_STATEMENT for k in doc_kinds.values())
    has_facts = any(k[0] == DOC_KIND_FACT_CONFIRMATION for k in doc_kinds.values())
    if not has_statements and not has_facts:
        return []

    prepared = {d.document_id: _sentences_for_copy(d) for d in docs}
    index: Dict[str, set] = {}
    for d in docs:
        for position, (_, key) in enumerate(prepared[d.document_id]):
            for gram in _shingles(key, 8):
                index.setdefault(gram, set()).add((d.document_id, position))
    by_id = {d.document_id: d for d in docs}
    out: List[Finding] = []

    for owner in docs:
        owner_kind, start = doc_kinds[owner.document_id]
        # 진술서(DOC_KIND_STATEMENT)이거나 사실경위서 복사 대상인 소송서면(DOC_KIND_PLEADING)만 owner 대상
        if owner_kind not in (DOC_KIND_STATEMENT, DOC_KIND_PLEADING):
            continue

        pairs: Dict[str, List[Tuple[str, str, float]]] = {}
        for sentence, key in prepared[owner.document_id]:
            # 진술서인 경우 진술 본문 시작 오프셋 이후 문장만 비교
            if owner_kind == DOC_KIND_STATEMENT and start is not None:
                if texts[owner.document_id].find(sentence, start) == -1:
                    continue

            # 소송서면인 경우 정식 서증 원용 문맥("갑 제1호증 사실경위서에 의하면...")은 제외
            if owner_kind == DOC_KIND_PLEADING and _EXHIBIT_REFERENCE_RE.search(sentence):
                continue

            hits: Dict[Tuple[str, int], int] = {}
            for gram in _shingles(key, 8):
                for hit in index.get(gram, ()):
                    if hit[0] != owner.document_id:
                        hits[hit] = hits.get(hit, 0) + 1
            grams = _shingles(key)
            for (other_id, position), count in hits.items():
                if count < 3:
                    continue
                other_sentence, other_key = prepared[other_id][position]
                other_grams = _shingles(other_key)
                overlap = len(grams & other_grams) / max(1, min(len(grams), len(other_grams)))
                if overlap >= COPY_SIMILARITY:
                    other_kind = doc_kinds[other_id][0]
                    # 7순위: 소송서면 간 정상 재진술(소장 ↔ 준비서면)은 제외
                    if owner_kind == DOC_KIND_PLEADING and other_kind == DOC_KIND_PLEADING:
                        continue
                    # 민사소송규칙 제106조 예외: 증거설명서 대상 제외
                    if owner_kind == DOC_KIND_EVIDENCE_EXPLANATION:
                        continue
                    # 5순위: 소송서면(PLEADING)의 경우 other가 사실경위서(FACT_CONFIRMATION)일 때만 통복제로 판정
                    if owner_kind == DOC_KIND_PLEADING and other_kind != DOC_KIND_FACT_CONFIRMATION:
                        continue

                    pairs.setdefault(other_id, []).append((sentence, other_sentence, round(overlap, 2)))

        for other_id, matched in pairs.items():
            other = by_id[other_id]
            other_kind = doc_kinds[other_id][0]

            if owner_kind == DOC_KIND_STATEMENT:
                # 4순위: 진술서 문서 대필·작출 의심 (EvidenceGrade.B 고정)
                out.append(_finding(
                    owner, FindingType.CROSS_DOC_COPY, EvidenceGrade.B, Severity.MEDIUM,
                    f"진술 문서에 다른 서면({other.filename})과 같은 문장이 {len(matched)}건 있다",
                    "진술인 명의의 문서에 대리인 서면 등 다른 문서의 문장이 그대로 있으면 대필·작출을 "
                    "의심할 단서가 된다. 작성 경위는 사람이 확인한다.",
                    matched[0][0], status=VerificationStatus.SUSPICIOUS,
                    features={"other_document_id": other_id, "similarity": matched[0][2],
                              "pairs": [{"statement": a[:200], "other": b[:200], "similarity": s}
                                        for a, b, s in matched[:5]]}
                ))
            elif owner_kind == DOC_KIND_PLEADING and other_kind == DOC_KIND_FACT_CONFIRMATION:
                # 5순위: 서증 원본(사실경위서) 통문단 복제 검출 (조건 2: EvidenceGrade.C 고정)
                out.append(_finding(
                    owner, FindingType.CROSS_DOC_COPY, EvidenceGrade.C, Severity.MEDIUM,
                    f"소송 서면에 증거자료({other.filename})의 본문과 같은 문장이 {len(matched)}건 있다",
                    "소장·준비서면 등 소송 대리 서면에 사실경위서 등 원본 서증의 본문 문단이 인용 표시 없이 "
                    "그대로 복제되어 기재되었습니다. 서증 기재와 일치하는 변론인지 또는 단순 통복제인지 사람이 확인해야 합니다.",
                    matched[0][0], status=VerificationStatus.SUSPICIOUS,
                    features={"other_document_id": other_id, "similarity": matched[0][2],
                              "copy_category": "FACT_CONFIRMATION_REPLICATION",
                              "rule_id": "EVI.COPY_FACT_CONFIRMATION", "human_review": True,
                              "pairs": [{"statement": a[:200], "other": b[:200], "similarity": s}
                                        for a, b, s in matched[:5]]}
                ))

    return out

