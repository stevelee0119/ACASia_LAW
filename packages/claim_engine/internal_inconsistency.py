"""TK-90 문서 안 진술 불일치(EVI-INCONS) 구조적 탐지 모듈.

조건부 승인(129) 및 2-2 공통 수용 규약 반영:
1. '결재일 > 송달일' 선후 비교 완전 삭제 (사건 간 순서는 A-4 범위, 병렬 검사 금지).
   동일 사건 하나에 날짜가 둘 이상인 경우만 다루며, A-4 중복 억제 규칙 적용.
2. 슬롯 추출은 결정적 규칙: 절 분리 -> 속성 사전 -> 값 -> 대상 명사구 및 지시어 해소.
3. 장소: 같은 주체 + 겹치는 시간 + 장소 명사구 + 처소조사(에/에서) + 머무름 술어 사전(전체 기재) + 한정 표지(오직, 내내, ~만 등).
   장소명 목록은 두지 않음.
4. 서명자: 당사자 표시/호칭/(이하 '...') 정의에서만 이름 추출 + 서명 술어 사전(전체 기재).
   서증 명시 작성자 vs 본문 서술 불일치 대조. 서명자명 목록은 두지 않음.
5. 수량·금액: 같은 대상 명사구 + 동일 시점 + 상이한 수치. 산술 계산 정규식(_ARITH_*) 완전 삭제,
   사칙연산은 수식 파서(arithmetic expression parser)로 분리(C등급).
6. 등급: B = 서증 명시 속성 vs 본문 서술 직접 모순(장소·서명자·금액), 동일 서증 조항 상반 원용.
         C = 본문 내 서술 상호 모순, 계산식 불일치.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument
from packages.document_engine.reading_text import build_reading_text, sentence_bounds

ENGINE_NAME = "claim_engine"


# --- 정당한 차이 (Legitimate Differences) 및 예외 가드 ---
_LEGITIMATE_EXCEPTION_RE = re.compile(
    r"(?:오기(?:이므로|로\s*인하여)?\s*[^.\n]{0,60}?(?:바로잡|정정)|"
    r"(?:바로잡|정정)합니다|"
    r"착오로\s*(?:잘못\s*)?기재|"
    r"주위적(?:으로)?|예비적(?:으로)?|"
    r"설령\s*[^.\n]{0,60}?(?:가정하더라도|본다\s*하더라도)|"
    r"(?:피고|상대방|피신청인)(?:는|이|가|의)\s*[^.\n]{0,100}?(?:[다라]고|[다라]며)\s*(?:주장|다투|진술|번복|항변)|"
    r"(?:피고|상대방)(?:는|의)\s*[^.\n]{0,60}?(?:주장하나|주장은\s*사실과\s*다르|주장은\s*이유\s*없))"
)

# 부가세/세액 구분 예외 패턴
_VAT_RE = re.compile(r"(?:부가(?:가치)?세|공급가액|세액|VAT)", re.IGNORECASE)

# 후속 일자(치료, 입원 등) 배제 패턴 (대조군 2)
_INCIDENT_DATE_EXCLUDE_RE = re.compile(r"(?:치료|입원|진단|통고|수령|해제|지급기일|만기|퇴원|발급|합의)")

# 절 분리 정규식: 숫자가 아닌 쉼표, 세미콜론, 서술어 어간 뒤 연결어미
_CLAUSE_SPLIT_RE = re.compile(
    r"(?<!\d),(?!\d)|;|"
    r"(?<=[하되있없었였겠])(?:고|며|나|지만|는데|자)\s+|"
    r"(?<=[가-힣])(?:한\s*(?:후|뒤|다음))\s+"
)

# 상대방 주장 인용절 패턴 (T2: 상대방 주어 + 인용 종결 + 주장/다툼/진술/번복/항변)
_OPPONENT_CLAIM_RE = re.compile(
    r"(?:피고|상대방|피신청인)(?:는|이|가)\s*[^.\n]{0,100}?(?:[다라]고|[다라]며)\s*(?:주장|다투|진술|번복|항변)(?:합니다|한다|하였|하고|하며|함|이나|으나|지만)?"
)

# --- 1. 속성 사전 (표면형 전체 코드 상수화) ---

# 머무름 술어 정규식 (조건 3: 어간 및 활용형 포괄)
_STAY_PREDICATE_RE = re.compile(
    r"(?:"
    r"있(?:었[고으며다]?|고|으며|으나|다|는)?|"
    r"머물(?:렀[고으며다]?|러|며|고|다|는)?|"
    r"체류(?:하[여였고며면자나다]?|한|하는)?|"
    r"근무(?:하[여였고며면자나다]?|한|하는)?|"
    r"거주(?:하[여였고며면자나다]?|한|하는)?|"
    r"상주(?:하[여였고며면자나다]?|한|하는)?|"
    r"체재(?:하[여였고며면자나다]?|한|하는)?|"
    r"투숙(?:하[여였고며면자나다]?|한|하는)?"
    r")"
)

# 장소 한정 표지
_EXCLUSIVE_LIMITER_RE = re.compile(r"(?:오직|단독으로|오로지|에만|만\s*(?:있|머물|체류|근무|상주)|내내|줄곧|하루\s*종일)")

# 상대 날짜 표지 (T6)
_RELATIVE_DATE_RE = re.compile(r"(?:같은\s*날|당일(?:인)?|그날|동일한\s*날|해당\s*일)")

# 서명 술어 사전 (조건 4: 표면형 전체 기재)
SIGNER_PREDICATES = frozenset({
    "서명", "서명하", "서명하였", "서명한", "서명하고", "서명하여", "서명인", "서명자",
    "날인", "날인하", "날인하였", "날인한", "날인하고", "날인하여", "날인자", "날인인",
    "기명", "기명하", "기명하였", "기명한", "기명날인", "기명날인하", "기명날인하였", "기명날인한",
    "작성", "작성하", "작성하였", "작성한", "작성하고", "작성자", "작성인", "작성인은", "작성자는",
    "조인", "조인하", "조인하였", "조인한", "조인하고",
})

_SIGNER_PREDICATE_RE = re.compile(
    r"(?:" + "|".join(re.escape(w) for w in sorted(SIGNER_PREDICATES, key=len, reverse=True)) + r")"
)

# 단독/유일 서명 표지 (T7: 단독, 유일, 한 명, 만, 만이, 혼자, 외에는)
_SOLE_SIGNER_RE = re.compile(r"(?:단독(?:으로)?|유일(?:한|하게)?|한\s*명(?:만)?|1명(?:만)?|만이?|혼자|외에는\s*(?:없|않))")

# 당사자 호칭 및 직책 결합 서명자 성명 정규식 (T7: 원고 김민수, 피고 박지훈 등 호칭+이름 포함)
_PARTY_TITLE_NAME_RE = re.compile(
    r"(?:"
    r"(?P<role_party>원고|피고(?:인)?|신청인|피신청인)\s+(?P<party_name>[가-힣]{2,4})"
    r"|"
    r"(?P<role>원고|피고(?:인)?|신청인|피신청인)"
    r"|"
    r"(?:\((?:이하\s*['\"]?)(?P<alias>[가-힣]{2,10})(?:['\"]?\s*(?:이라\s*함|\))|\)))"
    r"|"
    r"(?P<title>대표(?:이사)?|이사|사장|변호사|법무사|담당자|팀장|과장|부장)\s*(?P<name>[가-힣]{2,4})(?=[이가은는을를의]|입니다|이고|이며|\s|$)"
    r"|"
    r"(?P<name2>[가-힣]{2,4})\s*(?:씨|귀하)"
    r")"
)

# 서증 및 확인서류 문서 대상 패턴 (지시어 포함)
_EXHIBIT_TARGET_RE = re.compile(
    r"(?P<ex>(?:갑|을)\s*제?\s*\d+\s*호증|(?:이\s*사건|위|본건|해당)?\s*[가-힣]{0,8}(?:계약서|확인서|동의서|각서|합의서))"
)

# 날짜 패턴 (YYYY. M. D. 또는 YYYY년 M월 D일)
_DATE_RE = re.compile(r"(?P<y>\d{4})[.\s년]+(?P<m>\d{1,2})[.\s월]+(?P<d>\d{1,2})[.\s일]*")

# 한국어 금액 파싱 패턴 (T5: 억·만 아래 자리의 천·백·십 단위 및 아라비아 숫자 혼용 지원)
_KOREAN_MONEY_RE = re.compile(
    r"(?:"
    r"(?P<eok>\d+(?:,\d{3})*|\d+)\s*억\s*(?:(?P<man>[0-9,가-힣]+)\s*만\s*)?(?:(?P<won>[0-9,가-힣]+)\s*)?원?"
    r"|"
    r"(?P<man_only>[0-9,가-힣]+)\s*만\s*(?:(?P<won_sub>[0-9,가-힣]+)\s*)?원?"
    r"|"
    r"(?P<won_only>\d+(?:,\d{3})*|\d+)\s*원"
    r")"
)

# T4: 계약 대금 명사 사전 (전체 기재: 매매대금, 공사대금, 용역대금, 차임, 보증금, 대여금, 약정금, 계약금액, 대금)
CONTRACT_AMOUNT_NOUNS = frozenset({
    "매매대금", "공사대금", "용역대금", "차임", "보증금", "임대차보증금",
    "대여금", "약정금", "계약금액", "대금",
})

# 수량/금액 총액 및 계약대금 한정 표지 (T4: '총'은 선택 표지, 계약대금 명사 + 확정 서술 매칭)
_TOTAL_AMOUNT_KEYWORD_RE = re.compile(
    r"(?:"
    r"(?:총\s*)?(?:매매대금|공사대금|용역대금|임대차보증금|보증금|대여금|약정금|계약금액|대금|차임)|"
    r"매매대금\s*총액|공사대금\s*총액|총액|전액|총약정금액|총\s*수량|합계"
    r")"
)

# 확정 서술 패턴 (T4: -은/는 … 원(이다|으로 정하|으로 약정 등))
_DEFINITIVE_PREDICATE_RE = re.compile(
    r"(?:이다|입니다|으로\s*정하|으로\s*약정|으로\s*합의|으로\s*기재|으로\s*명시|임|이었|상당)"
)

# 부분 금액 배제 수식어
_PARTIAL_PREFIX_RE = re.compile(r"(?:잔금|잔대금|중[·\s]*잔금|나머지|일부|지연손해금|이자|원리금|계약금|중도금)\s*$")

# T3: 동일 대상 지시어 패턴 (지시어는 키에서 제외하고 핵심 명사만 추출)
_TARGET_REF_RE = re.compile(
    r"(?:(?P<prefix>위|이\s*사건|본건|해당|동)\s*)?(?P<kind>교통사고|사고|화재|매매계약|공사계약|도급계약|대여금계약|임대차계약|계약|대여금|채무|거래)"
)

# 서증 번호 및 조항 인용 패턴
_EXHIBIT_CLAUSE_RE = re.compile(
    r"(?P<exhibit>(?:갑|을)\s*제?\s*\d+\s*호증(?:\s*\([^)]*\))?)\s*(?P<clause>제\s*\d+\s*조)"
)
_CLAUSE_EXEMPTION_RE = re.compile(r"(?:지체상금[이가을를]?\s*(?:전액\s*)?면제|면제되었|책임이\s*없|성립하지\s*않|부존재|무효)")
_CLAUSE_IMPOSITION_RE = re.compile(r"(?:(?:지체상금|손해배상금|위약금|대금)[이가을를]?\s*(?:전액\s*)?(?:부과|청구)|부과되|부과하여야|지급하여야|청구하여야|유효)")

# T8: 당사자 지위 닫힌 짝 사전 (임대인/임차인, 매도인/매수인, 도급인/수급인, 대주/차주, 위임인/수임인)
PARTY_ROLE_PAIRS = {
    "임대인": "임차인",
    "임차인": "임대인",
    "매도인": "매수인",
    "매수인": "매도인",
    "도급인": "수급인",
    "수급인": "도급인",
    "대주": "차주",
    "차주": "대주",
    "위임인": "수임인",
    "수임인": "위임인",
}

# T8: 당사자 지위 결합 정규식: X는 (… 계약의|에서) Z(이다|로서|인)
_PARTY_ROLE_STMT_RE = re.compile(
    r"(?P<party>원고|피고(?:인)?|신청인|피신청인)(?:는|은|이|가)\s*"
    r"(?:[^.\n]{0,30}?(?P<contract>임대차|매매|도급|공사|대여|위임)(?:계약)?(?:의|에서|상)\s*)?"
    r"(?P<role>임대인|임차인|매도인|매수인|도급인|수급인|대주|차주|위임인|수임인)"
    r"(?:이다|입니다|(?:으)?로서|인|이며|이고|에\s*해당)"
)
_ROLE_EXCLUDE_RE = re.compile(r"(?:전대|전차|전대차|반소|별개)")

# A-4 선후 관계 키워드 (B-3 일시 모순에서 A-4 중복 배제 가드)
_TEMPORAL_SEQUENCE_WORDS_RE = re.compile(
    r"(?:발송|도달|수령|송달|신청|처분|통지|체결|해지|해제|입사|퇴사|보정명령)"
)


def _parse_sub_chunk(s: str) -> int:
    """천, 백, 십 단위 및 아라비아 숫자가 혼용된 금액 청크를 정수로 변환한다."""
    s = s.strip().replace(",", "")
    if not s:
        return 0
    if s.isdigit():
        return int(s)

    total = 0
    # 천 단위
    m_cheon = re.search(r"(\d+)?천", s)
    if m_cheon:
        val = int(m_cheon.group(1)) if m_cheon.group(1) else 1
        total += val * 1000
        s = s[:m_cheon.start()] + s[m_cheon.end():]
    # 백 단위
    m_baek = re.search(r"(\d+)?백", s)
    if m_baek:
        val = int(m_baek.group(1)) if m_baek.group(1) else 1
        total += val * 100
        s = s[:m_baek.start()] + s[m_baek.end():]
    # 십 단위
    m_sip = re.search(r"(\d+)?십", s)
    if m_sip:
        val = int(m_sip.group(1)) if m_sip.group(1) else 1
        total += val * 10
        s = s[:m_sip.start()] + s[m_sip.end():]
    # 남은 순수 숫자
    m_rem = re.search(r"\d+", s)
    if m_rem:
        total += int(m_rem.group(0))
    return total


def _parse_korean_amount(text: str) -> Optional[int]:
    """한국어 금액 표현을 원 단위 정수로 환산한다 (T5).
    
    천·백·십 혼용 ('2억 5천만 원', '3천5백만 원', '1억2천만 원', '5,000만 원' 등)을 지원한다.
    """
    m = _KOREAN_MONEY_RE.search(text)
    if not m:
        return None
    eok_str = m.group("eok")
    man_str = m.group("man") or m.group("man_only")
    won_str = m.group("won") or m.group("won_sub") or m.group("won_only")

    total = 0
    if eok_str:
        total += int(eok_str.replace(",", "")) * 100_000_000
    if man_str:
        total += _parse_sub_chunk(man_str) * 10_000
    if won_str:
        total += _parse_sub_chunk(won_str)
    return total if total > 0 else None


# --- 3. 슬롯 데이터 클래스 ---

@dataclass
class _AmountStatement:
    target_key: str
    amount: int
    raw_amount: str
    sentence: str
    page: int


@dataclass
class _DateStatement:
    target_key: str
    date_val: Tuple[int, int, int]
    raw_date: str
    sentence: str
    page: int


@dataclass
class _RoleStatement:
    target_key: str
    party: str
    contract: str
    role: str
    sentence: str
    page: int


@dataclass
class _ExhibitClauseStatement:
    exhibit_clause_key: str
    effect: str
    sentence: str
    page: int


@dataclass
class _LocationStatement:
    subject: str
    time_window: Tuple[int, int, int]
    location: str
    is_exclusive: bool
    sentence: str
    page: int


@dataclass
class _SignerStatement:
    exhibit_or_target: str
    signer_name: str
    is_sole: bool
    sentence: str
    page: int


def _make_incons_finding(
    doc: NormalizedDocument,
    kind: FindingType,
    grade: EvidenceGrade,
    severity: Severity,
    status: VerificationStatus,
    title: str,
    detail: str,
    excerpt: str,
    page: int,
    features: Dict[str, Any],
) -> Finding:
    """Finding 규격에 부합하는 일관된 모순 Finding 객체를 생성한다."""
    evidence_list = []
    if excerpt:
        evidence_list.append(Evidence.create(
            description="진술 모순 대조 발췌",
            grade=grade,
            document_id=doc.document_id,
            page=page,
            excerpt=excerpt[:300],
        ))

    return Finding.create(
        type=kind,
        status=status,
        severity=severity,
        evidence_grade=grade,
        title=title,
        detail=detail,
        confidence=0.7 if grade == EvidenceGrade.B else 0.5,
        confidence_features={"deterministic_rule": True, **features},
        document_id=doc.document_id,
        page=page,
        engine=ENGINE_NAME,
        tags=["EVIDENCE"],
        evidence=evidence_list,
    )


def _contract_category(text: str) -> str:
    """계약/채무 진술의 대분류(매매, 공사, 대여, 임대차 등)를 정규화한다."""
    if re.search(r"매매", text):
        return "SALE"
    if re.search(r"공사|도급", text):
        return "CONSTRUCTION"
    if re.search(r"대여", text):
        return "LOAN"
    if re.search(r"임대차", text):
        return "LEASE"
    if re.search(r"위임", text):
        return "MANDATE"
    return "CONTRACT"


def _normalize_incident_kind(kind: str) -> str:
    """T3: 사고/사건 명사를 정규화하여 지시어와 무관하게 결합한다."""
    if re.search(r"교통사고|사고", kind):
        return "사고"
    if re.search(r"화재", kind):
        return "화재"
    if re.search(r"매매계약", kind):
        return "매매계약"
    if re.search(r"공사계약|도급계약", kind):
        return "공사도급계약"
    if re.search(r"임대차계약", kind):
        return "임대차계약"
    if re.search(r"대여금|채무|거래", kind):
        return "대여금채무"
    return kind


def check_internal_inconsistency(doc: NormalizedDocument) -> List[Finding]:
    """소송 서면 본문 안의 진술 간 구조적 모순(EVI-INCONS)을 탐지한다."""
    findings: List[Finding] = []
    reading = build_reading_text(doc, [b for b in doc.body_blocks() if b.block_type != "running_head"])
    text = reading.text

    amount_stmts: List[_AmountStatement] = []
    date_stmts: List[_DateStatement] = []
    role_stmts: List[_RoleStatement] = []
    clause_stmts: List[_ExhibitClauseStatement] = []
    location_stmts: List[_LocationStatement] = []
    signer_stmts: List[_SignerStatement] = []

    # 서증 목록 사전 구축 (서증명/번호 -> 작성자 속성)
    exhibit_author_map: Dict[str, str] = {}
    for block in doc.body_blocks():
        btext = block.text or ""
        ex_m = re.search(r"(?P<ex>(?:갑|을)\s*제?\s*\d+\s*호증)", btext)
        if ex_m:
            ex_key = re.sub(r"\s+", "", ex_m.group("ex"))
            author_m = re.search(r"(?:작성자|발신인|작성인)(?:\s*(?:은|는))?\s*[:：]?\s*(?P<author>[가-힣]{2,4})", btext)
            if author_m:
                exhibit_author_map[ex_key] = author_m.group("author")

    # T6: 단락(block) 단위 직전 절대 일자 및 주어 유지 변수
    current_block_id: Optional[str] = None
    block_last_date: Optional[Tuple[int, int, int]] = None
    block_last_subject: str = "당사자"

    # 문장 단위로 순회
    for start, end in sentence_bounds(text):
        sentence = text[start:end].strip()
        if len(sentence) < 10:
            continue

        # T2: 정당한 차이 및 상대방 주장 인용 필터링
        if _LEGITIMATE_EXCEPTION_RE.search(sentence) or _OPPONENT_CLAIM_RE.search(sentence):
            continue

        page = 1
        blocks = reading.blocks_between(start, end)
        if blocks:
            b_obj = blocks[0]
            page = getattr(b_obj, "page_no", 1) or 1
            b_id = getattr(b_obj, "block_id", None)
            if b_id != current_block_id:
                current_block_id = b_id
                block_last_date = None
                block_last_subject = "당사자"

        # T8: 당사자 지위 3항 구조 (당사자, 계약, 지위) 추출
        if not _ROLE_EXCLUDE_RE.search(sentence):
            for role_m in _PARTY_ROLE_STMT_RE.finditer(sentence):
                party_val = role_m.group("party")
                contract_val = role_m.group("contract") or _contract_category(sentence)
                role_val = role_m.group("role")
                key = f"{party_val}_{contract_val}"
                role_stmts.append(_RoleStatement(key, party_val, contract_val, role_val, sentence, page))

        # 서증 조항 상반 원용 (문장 내 모든 출현 탐색)
        clause_matches = list(_EXHIBIT_CLAUSE_RE.finditer(sentence))
        if clause_matches:
            for idx, c_m in enumerate(clause_matches):
                exhibit_raw = c_m.group("exhibit")
                exhibit_norm = re.sub(r"\s+", "", exhibit_raw)
                clause_clean = re.sub(r"\s+", "", c_m.group("clause"))
                key = f"{exhibit_norm}_{clause_clean}"
                next_start = clause_matches[idx + 1].start() if idx + 1 < len(clause_matches) else len(sentence)
                scope = sentence[c_m.start():next_start]
                if _CLAUSE_EXEMPTION_RE.search(scope):
                    clause_stmts.append(_ExhibitClauseStatement(key, "EXEMPTION", scope, page))
                elif _CLAUSE_IMPOSITION_RE.search(scope):
                    clause_stmts.append(_ExhibitClauseStatement(key, "IMPOSITION", scope, page))
                elif _CLAUSE_EXEMPTION_RE.search(sentence) and len(clause_matches) == 1:
                    clause_stmts.append(_ExhibitClauseStatement(key, "EXEMPTION", sentence, page))
                elif _CLAUSE_IMPOSITION_RE.search(sentence) and len(clause_matches) == 1:
                    clause_stmts.append(_ExhibitClauseStatement(key, "IMPOSITION", sentence, page))

        # 절 분리 기반 결정적 슬롯 추출 (조건 2)
        clauses = [c.strip() for c in _CLAUSE_SPLIT_RE.split(sentence) if len(c.strip()) >= 3]
        if not clauses:
            clauses = [sentence]

        last_subject = block_last_subject
        subj_m_sent = _PARTY_TITLE_NAME_RE.search(sentence)
        if subj_m_sent:
            last_subject = (
                subj_m_sent.group("party_name")
                or subj_m_sent.group("role")
                or subj_m_sent.group("name")
                or subj_m_sent.group("name2")
                or subj_m_sent.group("alias")
                or last_subject
            )
            block_last_subject = last_subject

        # T6: 날짜 해소 (절대 날짜 우선, 상대 날짜 표현 시 단락 직전 절대 날짜 승계)
        last_date: Optional[Tuple[int, int, int]] = None
        date_m_sent = _DATE_RE.search(sentence)
        if date_m_sent:
            last_date = (int(date_m_sent.group("y")), int(date_m_sent.group("m")), int(date_m_sent.group("d")))
            block_last_date = last_date
        elif _RELATIVE_DATE_RE.search(sentence) and block_last_date:
            last_date = block_last_date

        # A-4 선후 관계 키워드 2개 이상 교차 시 일시 슬롯 배제 가드
        seq_words = _TEMPORAL_SEQUENCE_WORDS_RE.findall(sentence)
        is_cross_event_sequence = len(set(seq_words)) >= 2

        for clause in clauses:
            # (3-1) 주체 업데이트
            subj_m = _PARTY_TITLE_NAME_RE.search(clause)
            if subj_m:
                last_subject = (
                    subj_m.group("party_name")
                    or subj_m.group("role")
                    or subj_m.group("name")
                    or subj_m.group("name2")
                    or subj_m.group("alias")
                    or last_subject
                )
                block_last_subject = last_subject

            # (3-2) 날짜 업데이트
            date_m = _DATE_RE.search(clause)
            if date_m:
                last_date = (int(date_m.group("y")), int(date_m.group("m")), int(date_m.group("d")))
                block_last_date = last_date
            elif _RELATIVE_DATE_RE.search(clause) and block_last_date:
                last_date = block_last_date

            # (3-3) 금액 슬롯 추출 (T4: 계약 대금 명사 사전 + 확정 서술 매칭, '총'은 선택 표지)
            if not _VAT_RE.search(clause):
                has_contract_amt = any(n in clause for n in CONTRACT_AMOUNT_NOUNS)
                has_total_kw = bool(_TOTAL_AMOUNT_KEYWORD_RE.search(clause))
                if has_contract_amt or has_total_kw:
                    amt_match = _KOREAN_MONEY_RE.search(clause)
                    if amt_match:
                        raw_amt = amt_match.group(0)
                        preceding = clause[max(0, amt_match.start() - 15):amt_match.start()]
                        following = clause[amt_match.end():min(len(clause), amt_match.end() + 20)]
                        # 확정 서술 확인: '총' 표지가 있거나 확정 서술어(-이다/-으로 정하 등)가 결합된 경우
                        is_definitive = has_total_kw or bool(_DEFINITIVE_PREDICATE_RE.search(following)) or not following.strip()
                        if is_definitive and not _PARTIAL_PREFIX_RE.search(preceding):
                            amount_val = _parse_korean_amount(raw_amt)
                            if amount_val:
                                cat = _contract_category(clause) if re.search(r"매매|공사|도급|대여|임대차|위임", clause) else _contract_category(sentence)
                                key = f"total_amount_{cat}"
                                amount_stmts.append(_AmountStatement(key, amount_val, raw_amt, clause, page))

            # (3-4) 일자 슬롯 추출 (동일 사건 복수 일자 - T3: 지시어 제거 및 핵심 명사 정규화)
            if not is_cross_event_sequence and not _INCIDENT_DATE_EXCLUDE_RE.search(clause):
                incident_m = _TARGET_REF_RE.search(clause)
                cur_date = date_m or (last_date if _RELATIVE_DATE_RE.search(clause) else None)
                if incident_m and (date_m or last_date):
                    norm_kind = _normalize_incident_kind(incident_m.group("kind"))
                    target_key = f"event_{norm_kind}"
                    d_tuple = (int(date_m.group("y")), int(date_m.group("m")), int(date_m.group("d"))) if date_m else last_date
                    if d_tuple:
                        date_stmts.append(_DateStatement(target_key, d_tuple, f"{d_tuple[0]}. {d_tuple[1]}. {d_tuple[2]}.", clause, page))

            # (3-5) 장소 슬롯 추출 (조건 3 & T6)
            if _STAY_PREDICATE_RE.search(clause) and last_date:
                is_excl = bool(_EXCLUSIVE_LIMITER_RE.search(clause) or _EXCLUSIVE_LIMITER_RE.search(sentence))
                loc_matches = re.findall(r"([가-힣a-zA-Z0-9]{2,15})(?:에만|에|에서)", clause)
                for raw_loc in loc_matches:
                    loc = re.sub(r"^(?:오직|내내|줄곧|당일인)\s*", "", raw_loc)
                    if not re.search(r"법원|청|위원회|기준|당시|관련|사건|원고|피고|이유|오직|내내", loc):
                        location_stmts.append(_LocationStatement(last_subject, last_date, loc, is_excl, clause, page))

            # (3-6) 서명자 슬롯 추출 (조건 4 & T7: 호칭+이름 및 단독 표지 확장)
            if _SIGNER_PREDICATE_RE.search(clause):
                ex_m = _EXHIBIT_TARGET_RE.search(clause) or _EXHIBIT_TARGET_RE.search(sentence)
                if ex_m:
                    raw_target = ex_m.group("ex")
                    ex_target = re.sub(r"^(?:이\s*사건|위|본건|해당)\s*", "", re.sub(r"\s+", "", raw_target))
                    is_sole = bool(_SOLE_SIGNER_RE.search(clause) or _SOLE_SIGNER_RE.search(sentence))
                    for nm_match in _PARTY_TITLE_NAME_RE.finditer(clause):
                        s_name = nm_match.group("party_name") or nm_match.group("name") or nm_match.group("name2") or nm_match.group("alias")
                        if s_name and s_name not in ("피고", "원고", "피고인", "작성", "서명", "확인", "사건"):
                            signer_stmts.append(_SignerStatement(ex_target, s_name, is_sole, clause, page))

    # --- 4. 버킷 기반 비교 및 모순 판정 ---

    # (1) 금액 모순 판정 (C등급 / UNVERIFIED)
    amount_by_key = defaultdict(list)
    for s in amount_stmts:
        amount_by_key[s.target_key].append(s)

    for key, stmts in amount_by_key.items():
        if len(stmts) < 2:
            continue
        first = stmts[0]
        for other in stmts[1:]:
            if first.amount != other.amount:
                title = f"문서 내 동일 계약 총액 진술 불일치: {first.amount:,}원 ↔ {other.amount:,}원"
                detail = (
                    f"동일한 계약/채무에 대해 문서 내 서로 다른 진술에서 총액을 서로 다르게 기재하였습니다. "
                    f"단순 오기이거나 주장 변경인지 사람이 확인해야 합니다."
                )
                excerpt = f"[{first.page}쪽] {first.sentence[:120]} ↔ [{other.page}쪽] {other.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.UNVERIFIED,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=first.page,
                    features={
                        "rule_id": "EVI.INCONS_INTERNAL_AMOUNT",
                        "inconsistency_type": "AMOUNT",
                        "statements": [first.sentence[:200], other.sentence[:200]],
                        "human_review": True,
                    },
                ))
                break

    # (2) 일자 모순 판정 (동일 사건 복수 일자 - C등급 / UNVERIFIED)
    date_by_key = defaultdict(list)
    for s in date_stmts:
        date_by_key[s.target_key].append(s)

    for key, stmts in date_by_key.items():
        if len(stmts) < 2:
            continue
        first = stmts[0]
        for other in stmts[1:]:
            if first.date_val != other.date_val:
                d1_str = f"{first.date_val[0]}. {first.date_val[1]}. {first.date_val[2]}."
                d2_str = f"{other.date_val[0]}. {other.date_val[1]}. {other.date_val[2]}."
                title = f"문서 내 동일 사건 발생일 진술 불일치: {d1_str} ↔ {d2_str}"
                detail = (
                    f"동일한 사고/사건에 대해 발생 일자를 서로 다르게 진술하였습니다. "
                    f"어느 쪽 일자가 정확한지 확인이 필요합니다."
                )
                excerpt = f"[{first.page}쪽] {first.sentence[:120]} ↔ [{other.page}쪽] {other.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.UNVERIFIED,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=first.page,
                    features={
                        "rule_id": "EVI.INCONS_INTERNAL_DATE",
                        "inconsistency_type": "DATE",
                        "statements": [first.sentence[:200], other.sentence[:200]],
                        "human_review": True,
                    },
                ))
                break

    # (3) 당사자 역할 역전 모순 판정 (T8: 3항 구조 및 닫힌 짝 사전 상반 지위 검출)
    role_by_key = defaultdict(list)
    for s in role_stmts:
        role_by_key[s.target_key].append(s)

    for key, stmts in role_by_key.items():
        if len(stmts) < 2:
            continue
        first = stmts[0]
        for other in stmts[1:]:
            # 닫힌 짝 사전(PARTY_ROLE_PAIRS)에서 서로 상반된 지위인 경우
            if PARTY_ROLE_PAIRS.get(first.role) == other.role:
                title = f"문서 내 동일 계약상 당사자 지위({first.role} ↔ {other.role}) 역전 모순"
                detail = (
                    f"동일한 {first.contract} 계약 관계에서 {first.party}의 지위를 한 곳에서는 {first.role}(으)로, "
                    f"다른 곳에서는 {other.role}(으)로 상반되게 진술하였습니다. 당사자 지위의 오기 여부를 확인해야 합니다."
                )
                excerpt = f"[{first.page}쪽] {first.sentence[:120]} ↔ [{other.page}쪽] {other.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.B,
                    severity=Severity.HIGH,
                    status=VerificationStatus.CONTRADICTED,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=first.page,
                    features={
                        "rule_id": "EVI.INCONS_INTERNAL_ROLE",
                        "inconsistency_type": "ROLE",
                        "statements": [first.sentence[:200], other.sentence[:200]],
                        "party": first.party,
                        "contract": first.contract,
                        "role1": first.role,
                        "role2": other.role,
                    },
                ))
                break

    # (4) 동일 서증 조항 상반 원용 판정 (B등급 / CONTRADICTED)
    clause_by_key = defaultdict(list)
    for s in clause_stmts:
        clause_by_key[s.exhibit_clause_key].append(s)

    for key, stmts in clause_by_key.items():
        if len(stmts) < 2:
            continue
        first = stmts[0]
        for other in stmts[1:]:
            if first.effect != other.effect:
                title = f"동일 서증 조항 원용 상반 단정: {first.exhibit_clause_key} (면제 ↔ 부과/청구)"
                detail = (
                    f"동일한 서증 번호 및 조항({first.exhibit_clause_key})을 명시적으로 원용하면서 "
                    f"객관적으로 상반된 법적 효과(면제 ↔ 부과)를 단정하여 모순이 명백합니다."
                )
                excerpt = f"[{first.page}쪽] {first.sentence[:120]} ↔ [{other.page}쪽] {other.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.B,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.CONTRADICTED,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=first.page,
                    features={
                        "rule_id": "EVI.INCONS_INTERNAL_CLAUSE",
                        "inconsistency_type": "CLAUSE_CONTRADICTION",
                        "statements": [first.sentence[:200], other.sentence[:200]],
                    },
                ))
                break

    # (5) 장소 모순 판정 (조건 3 & T6: 동일 주체 + 겹치는 시간 + 한정 표지 결합 상이 장소)
    loc_by_key = defaultdict(list)
    for loc_s in location_stmts:
        k = f"{loc_s.subject}_{loc_s.time_window[0]}.{loc_s.time_window[1]}.{loc_s.time_window[2]}"
        loc_by_key[k].append(loc_s)

    for k, stmts in loc_by_key.items():
        if len(stmts) < 2:
            continue
        # 한 쪽이라도 배타적 한정(is_exclusive)이 있는 경우에만 장소 비교
        if not any(s.is_exclusive for s in stmts):
            continue
        first = stmts[0]
        for other in stmts[1:]:
            if first.location != other.location:
                dt_str = f"{first.time_window[0]}. {first.time_window[1]}. {first.time_window[2]}."
                title = f"동일 일시 상호배타적 장소 체류 모순: '{first.location}' ↔ '{other.location}'"
                detail = f"동일한 일시/기간({dt_str})에 배타적으로 서로 다른 장소에 체류·근무하였다고 진술하여 모순됩니다."
                excerpt = f"[{first.page}쪽] {first.sentence[:120]} ↔ [{other.page}쪽] {other.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.SUSPICIOUS,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=first.page,
                    features={
                        "rule_id": "EVI.INCONS_LOC_EXCLUSIVE",
                        "inconsistency_type": "LOCATION",
                        "statements": [first.sentence[:200], other.sentence[:200]],
                    },
                ))
                break

    # (6) 서명자 모순 판정 (조건 4 & T7)
    # (6-1) 서증 목록 작성자 vs 본문 서술 불일치 (B등급 / CONTRADICTED)
    for s in signer_stmts:
        norm_key = re.sub(r"\s+", "", s.exhibit_or_target)
        if norm_key in exhibit_author_map:
            doc_author = exhibit_author_map[norm_key]
            if doc_author and s.signer_name and doc_author != s.signer_name:
                title = f"서증 기재 작성자·서명자 진술 불일치: 서증({doc_author}) ↔ 본문 주장({s.signer_name})"
                detail = f"서증({s.exhibit_or_target})의 기재상 작성자({doc_author})와 본문 서술상의 서명·작성자({s.signer_name})가 상반됩니다."
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.B,
                    severity=Severity.HIGH,
                    status=VerificationStatus.CONTRADICTED,
                    title=title,
                    detail=detail,
                    excerpt=f"[{s.page}쪽] {s.sentence[:150]} (서증 기재: {doc_author})",
                    page=s.page,
                    features={
                        "rule_id": "EVI.INCONS_SIGNER_DOC_MISMATCH",
                        "inconsistency_type": "SIGNER",
                        "doc_author": doc_author,
                        "stmt_author": s.signer_name,
                    },
                ))

    # (6-2) 본문 내 동일 서증/문서에 대한 상이한 단독 서명자 진술 (C등급 / SUSPICIOUS)
    signer_by_target = defaultdict(list)
    for s in signer_stmts:
        signer_by_target[s.exhibit_or_target].append(s)

    for target, stmts in signer_by_target.items():
        if len(stmts) < 2:
            continue
        # 한쪽이라도 단독/유일 서명자(is_sole) 주장이 있는 경우에만 상호 모순 판정 (공동 서명자 오탐 방지)
        if not any(s.is_sole for s in stmts):
            continue
        first = stmts[0]
        for other in stmts[1:]:
            if first.signer_name != other.signer_name:
                title = f"동일 문서 서명자 진술 상반 모순: '{first.signer_name}' ↔ '{other.signer_name}'"
                detail = f"동일 문서({target})의 서명·작성자에 관하여 서로 다른 인물을 지정하여 모순됩니다."
                excerpt = f"[{first.page}쪽] {first.sentence[:120]} ↔ [{other.page}쪽] {other.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.SUSPICIOUS,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=first.page,
                    features={
                        "rule_id": "EVI.INCONS_SIGNER_INTERNAL",
                        "inconsistency_type": "SIGNER",
                        "statements": [first.sentence[:200], other.sentence[:200]],
                    },
                ))
                break

    return findings
