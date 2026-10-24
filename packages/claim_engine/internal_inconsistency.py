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
    r"(?:피고|원고|상대방)(?:는|의)\s*[^.\n]{0,60}?(?:주장하나|주장은\s*사실과\s*다르|주장은\s*이유\s*없))"
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

# 당사자 호칭 및 직책 결합 서명자 성명 정규식 (조건 4: 호칭/표시에서만 추출)
_PARTY_TITLE_NAME_RE = re.compile(
    r"(?:"
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

# 한국어 금액 파싱 패턴 (반드시 숫자 1개 이상 필수)
_KOREAN_MONEY_RE = re.compile(
    r"(?:"
    r"(?P<eok>\d+(?:,\d{3})*|\d+)\s*억\s*(?:(?P<man>\d+(?:,\d{3})*|\d+)\s*만\s*)?(?:(?P<won>\d+(?:,\d{3})*|\d+)\s*)?원?"
    r"|"
    r"(?P<man_only>\d+(?:,\d{3})*|\d+)\s*만\s*(?:(?P<won_sub>\d+(?:,\d{3})*|\d+)\s*)?원?"
    r"|"
    r"(?P<won_only>\d+(?:,\d{3})*|\d+)\s*원"
    r")"
)

# 수량/금액 총액 한정 표지
_TOTAL_AMOUNT_KEYWORD_RE = re.compile(
    r"(?:총\s*(?:매매대금|공사대금|대여금|임대차보증금|약정금|계약금액|대금)|"
    r"매매대금\s*총액|공사대금\s*총액|총\s*공사대금|총액|전액|총약정금액|총\s*수량|합계)"
)

# 부분 금액 배제 수식어
_PARTIAL_PREFIX_RE = re.compile(r"(?:잔금|잔대금|중[·\s]*잔금|나머지|일부|지연손해금|이자|원리금|계약금|중도금)\s*$")

# 동일 대상 지시어 패턴
_TARGET_REF_RE = re.compile(
    r"(?P<prefix>위|이\s*사건|본건|해당|동)\s*(?P<kind>매매계약|공사계약|도급계약|대여금|임대차계약|계약|채무|거래|교통사고|사고|화재)"
)

# 서증 번호 및 조항 인용 패턴
_EXHIBIT_CLAUSE_RE = re.compile(
    r"(?P<exhibit>(?:갑|을)\s*제?\s*\d+\s*호증(?:\s*\([^)]*\))?)\s*(?P<clause>제\s*\d+\s*조)"
)
_CLAUSE_EXEMPTION_RE = re.compile(r"(?:지체상금[이가을를]?\s*(?:전액\s*)?면제|면제되었|책임이\s*없|성립하지\s*않|부존재|무효)")
_CLAUSE_IMPOSITION_RE = re.compile(r"(?:지체상금[이가을를]?\s*(?:전액\s*)?(?:부과|청구)|부과되|지급하여야|유효)")

# 당사자 역할 패턴
_ROLE_TARGET_RE = re.compile(r"(?P<prefix>위|이\s*사건|본건)\s*(?P<kind>임대차|임대차계약)")
_ROLE_EXCLUDE_RE = re.compile(r"(?:전대|전차|전대차|반소|별개)")
_LANDLORD_STMT_RE = re.compile(r"(?:원고(?:는|가)\s*임대인|임대인인\s*원고)")
_TENANT_STMT_RE = re.compile(r"(?:원고(?:는|가)\s*임차인|임차인인\s*원고)")

# A-4 선후 관계 키워드 (B-3 일시 모순에서 A-4 중복 배제 가드)
_TEMPORAL_SEQUENCE_WORDS_RE = re.compile(
    r"(?:발송|도달|수령|송달|신청|처분|통지|체결|해지|해제|입사|퇴사|보정명령)"
)


def _parse_korean_amount(text: str) -> Optional[int]:
    """한국어 금액 표현을 원 단위 정수로 환산한다."""
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
        total += int(man_str.replace(",", "")) * 10_000
    if won_str:
        total += int(won_str.replace(",", ""))
    return total if total > 0 else None


# --- 2. 수식 파서 (Arithmetic Expression Parser - 조건 5) ---

@dataclass
class ArithmeticFormula:
    formula_str: str
    operator: str
    operands: List[int]
    expected: int
    stated: int
    raw_match: str


def parse_arithmetic_expression(text: str) -> Optional[ArithmeticFormula]:
    """단순 연산자와 숫자로 구성된 사칙연산 수식을 파싱하여 계산 불일치를 검출한다.
    
    문장틀 정규식이 아닌 단순 수식 토큰(A * B = C, A + B = C, A - B = C)을 처리한다.
    """
    # 1. 곱셈: N1 * N2 = RES
    m_mul = re.search(
        r"(?P<n1>\d+(?:,\d{3})*)\s*(?:[가-힣]{0,4})?\s*[×*xX]\s*(?:[가-힣]{0,4})?\s*"
        r"(?P<n2>\d+(?:,\d{3})*)\s*(?:[가-힣]{0,4})?\s*"
        r"(?:[=＝:]\s*)?(?:합계(?:는)?|총(?:액)?(?:은)?|금)?\s*"
        r"(?P<res>\d+(?:,\d{3})*)",
        text
    )
    if m_mul:
        try:
            n1 = int(m_mul.group("n1").replace(",", ""))
            n2 = int(m_mul.group("n2").replace(",", ""))
            res = int(m_mul.group("res").replace(",", ""))
            if n1 > 0 and n2 > 0 and res > 0:
                expected = n1 * n2
                if expected != res:
                    return ArithmeticFormula(
                        formula_str=f"{n1:,} × {n2:,}",
                        operator="×",
                        operands=[n1, n2],
                        expected=expected,
                        stated=res,
                        raw_match=m_mul.group(0),
                    )
        except (ValueError, OverflowError):
            pass

    # 2. 덧셈: N1 + N2 (+ N3) = RES
    m_add = re.search(
        r"(?P<n1>\d+(?:,\d{3})*)\s*원?\s*[+＋]\s*(?P<n2>\d+(?:,\d{3})*)\s*원?"
        r"(?:\s*[+＋]\s*(?P<n3>\d+(?:,\d{3})*)\s*원?)?\s*"
        r"(?:[=＝:]\s*)?(?:합계(?:는)?|총(?:액)?(?:은)?|총)?\s*"
        r"(?P<res>\d+(?:,\d{3})*)\s*원",
        text
    )
    if m_add:
        try:
            n1 = int(m_add.group("n1").replace(",", ""))
            n2 = int(m_add.group("n2").replace(",", ""))
            n3 = int(m_add.group("n3").replace(",", "")) if m_add.group("n3") else 0
            res = int(m_add.group("res").replace(",", ""))
            if n1 > 0 and n2 > 0 and res > 0:
                expected = n1 + n2 + n3
                if expected != res:
                    formula_str = f"{n1:,} + {n2:,}" + (f" + {n3:,}" if n3 else "")
                    return ArithmeticFormula(
                        formula_str=formula_str,
                        operator="+",
                        operands=[n1, n2] + ([n3] if n3 else []),
                        expected=expected,
                        stated=res,
                        raw_match=m_add.group(0),
                    )
        except (ValueError, OverflowError):
            pass

    # 3. 뺄셈: N1 - N2 = RES
    m_sub = re.search(
        r"(?P<n1>\d+(?:,\d{3})*)\s*원?\s*[-－]\s*(?P<n2>\d+(?:,\d{3})*)\s*원?"
        r"(?:\s*[-－]\s*(?P<n3>\d+(?:,\d{3})*)\s*원?)?\s*"
        r"(?:[=＝:]\s*)?(?:잔액(?:은)?|차액(?:은)?|순액(?:은)?|잔여)?\s*"
        r"(?P<res>\d+(?:,\d{3})*)\s*원",
        text
    )
    if m_sub:
        try:
            n1 = int(m_sub.group("n1").replace(",", ""))
            n2 = int(m_sub.group("n2").replace(",", ""))
            n3 = int(m_sub.group("n3").replace(",", "")) if m_sub.group("n3") else 0
            res = int(m_sub.group("res").replace(",", ""))
            if n1 > 0 and n2 > 0 and res > 0:
                expected = n1 - n2 - n3
                if expected != res:
                    formula_str = f"{n1:,} - {n2:,}" + (f" - {n3:,}" if n3 else "")
                    return ArithmeticFormula(
                        formula_str=formula_str,
                        operator="-",
                        operands=[n1, n2] + ([n3] if n3 else []),
                        expected=expected,
                        stated=res,
                        raw_match=m_sub.group(0),
                    )
        except (ValueError, OverflowError):
            pass

    return None


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
    return "CONTRACT"


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

    # 전체 본문에서 임대차 관련 지시어가 최소 1회 이상 존재하는지 확인
    has_lease_context = bool(_ROLE_TARGET_RE.search(text))

    # 문장 단위로 순회
    for start, end in sentence_bounds(text):
        sentence = text[start:end].strip()
        if len(sentence) < 10:
            continue

        # 정당한 차이(오기 정정, 주위적/예비적 주장 등) 필터링
        if _LEGITIMATE_EXCEPTION_RE.search(sentence):
            continue

        page = 1
        blocks = reading.blocks_between(start, end)
        if blocks:
            page = getattr(blocks[0], "page_no", 1) or 1

        # 1. 수식 파서 (사칙연산 불일치 탐지 - 조건 5)
        formula = parse_arithmetic_expression(sentence)
        if formula:
            title = f"문서 내 산술 계산 불일치: {formula.formula_str} = 기재 {formula.stated:,} (실제 {formula.expected:,})"
            detail = f"문서 본문의 계산식({formula.formula_str})과 명시된 결과값({formula.stated:,})이 산술적으로 일치하지 않습니다(실제: {formula.expected:,})."
            findings.append(_make_incons_finding(
                doc=doc,
                kind=FindingType.ARITHMETIC_MISMATCH,
                grade=EvidenceGrade.C,
                severity=Severity.MEDIUM,
                status=VerificationStatus.SUSPICIOUS,
                title=title,
                detail=detail,
                excerpt=sentence[:200],
                page=page,
                features={
                    "rule_id": f"EVI.INCONS_ARITH_{formula.operator}",
                    "inconsistency_type": "ARITHMETIC_MISMATCH",
                    "expected": formula.expected,
                    "actual": formula.stated,
                },
            ))

        # 2. 당사자 역할 및 서증 조항 상반 원용 (문장 단위)
        if has_lease_context and not _ROLE_EXCLUDE_RE.search(sentence):
            key = "lease_party_role"
            if _LANDLORD_STMT_RE.search(sentence):
                role_stmts.append(_RoleStatement(key, "LANDLORD", sentence, page))
            elif _TENANT_STMT_RE.search(sentence):
                role_stmts.append(_RoleStatement(key, "TENANT", sentence, page))

        clause_match = _EXHIBIT_CLAUSE_RE.search(sentence)
        if clause_match:
            exhibit_raw = clause_match.group("exhibit")
            exhibit_norm = re.sub(r"\s+", "", exhibit_raw)
            clause_clean = re.sub(r"\s+", "", clause_match.group("clause"))
            key = f"{exhibit_norm}_{clause_clean}"
            if _CLAUSE_EXEMPTION_RE.search(sentence):
                clause_stmts.append(_ExhibitClauseStatement(key, "EXEMPTION", sentence, page))
            elif _CLAUSE_IMPOSITION_RE.search(sentence):
                clause_stmts.append(_ExhibitClauseStatement(key, "IMPOSITION", sentence, page))

        # 3. 절 분리 기반 결정적 슬롯 추출 (조건 2)
        clauses = [c.strip() for c in _CLAUSE_SPLIT_RE.split(sentence) if len(c.strip()) >= 3]
        if not clauses:
            clauses = [sentence]

        last_subject = "당사자"
        subj_m_sent = _PARTY_TITLE_NAME_RE.search(sentence)
        if subj_m_sent:
            last_subject = subj_m_sent.group("role") or subj_m_sent.group("name") or subj_m_sent.group("name2") or subj_m_sent.group("alias") or "당사자"

        last_date: Optional[Tuple[int, int, int]] = None
        date_m_sent = _DATE_RE.search(sentence)
        if date_m_sent:
            last_date = (int(date_m_sent.group("y")), int(date_m_sent.group("m")), int(date_m_sent.group("d")))

        # A-4 선후 관계 키워드 2개 이상 교차 시 일시 슬롯 배제 가드
        seq_words = _TEMPORAL_SEQUENCE_WORDS_RE.findall(sentence)
        is_cross_event_sequence = len(set(seq_words)) >= 2

        for clause in clauses:
            # (3-1) 주체 업데이트
            subj_m = _PARTY_TITLE_NAME_RE.search(clause)
            if subj_m:
                last_subject = subj_m.group("role") or subj_m.group("name") or subj_m.group("name2") or subj_m.group("alias") or last_subject

            # (3-2) 날짜 업데이트
            date_m = _DATE_RE.search(clause)
            if date_m:
                last_date = (int(date_m.group("y")), int(date_m.group("m")), int(date_m.group("d")))

            # (3-3) 금액 슬롯 추출
            if not _VAT_RE.search(clause) and _TOTAL_AMOUNT_KEYWORD_RE.search(clause):
                amt_match = _KOREAN_MONEY_RE.search(clause)
                if amt_match:
                    raw_amt = amt_match.group(0)
                    preceding = clause[max(0, amt_match.start() - 15):amt_match.start()]
                    if not _PARTIAL_PREFIX_RE.search(preceding):
                        amount_val = _parse_korean_amount(raw_amt)
                        if amount_val:
                            cat = _contract_category(clause) if re.search(r"매매|공사|도급|대여|임대차", clause) else _contract_category(sentence)
                            key = f"total_amount_{cat}"
                            amount_stmts.append(_AmountStatement(key, amount_val, raw_amt, clause, page))

            # (3-4) 일자 슬롯 추출 (동일 사건 복수 일자 - 조건 1)
            # 해당 절에 직접 사건 낱말이 있고, 치료/입원 등 후속 일자가 아닐 때만 추출
            if not is_cross_event_sequence and not _INCIDENT_DATE_EXCLUDE_RE.search(clause):
                incident_m = _TARGET_REF_RE.search(clause)
                if incident_m and date_m:
                    target_key = f"{incident_m.group('prefix')}_{incident_m.group('kind')}"
                    d_tuple = (int(date_m.group("y")), int(date_m.group("m")), int(date_m.group("d")))
                    date_stmts.append(_DateStatement(target_key, d_tuple, f"{d_tuple[0]}. {d_tuple[1]}. {d_tuple[2]}.", clause, page))

            # (3-5) 장소 슬롯 추출 (조건 3)
            if _STAY_PREDICATE_RE.search(clause) and last_date:
                is_excl = bool(_EXCLUSIVE_LIMITER_RE.search(clause) or _EXCLUSIVE_LIMITER_RE.search(sentence))
                loc_matches = re.findall(r"([가-힣a-zA-Z0-9]{2,15})(?:에만|에|에서)", clause)
                for raw_loc in loc_matches:
                    loc = re.sub(r"^(?:오직|내내|줄곧|당일인)\s*", "", raw_loc)
                    if not re.search(r"법원|청|위원회|기준|당시|관련|사건|원고|피고|이유|오직|내내", loc):
                        location_stmts.append(_LocationStatement(last_subject, last_date, loc, is_excl, clause, page))

            # (3-6) 서명자 슬롯 추출 (조건 4)
            if _SIGNER_PREDICATE_RE.search(clause):
                ex_m = _EXHIBIT_TARGET_RE.search(clause) or _EXHIBIT_TARGET_RE.search(sentence)
                if ex_m:
                    # 지시어 제거하여 동일 서증/문서명 정규화
                    raw_target = ex_m.group("ex")
                    ex_target = re.sub(r"^(?:이\s*사건|위|본건|해당)\s*", "", re.sub(r"\s+", "", raw_target))
                    is_sole = bool(re.search(r"단독|유일한|한\s*명|1명", clause) or re.search(r"단독|유일한|한\s*명|1명", sentence))
                    # 직책 결합 성명(대표이사 홍길동 등) 추출
                    for nm_match in _PARTY_TITLE_NAME_RE.finditer(clause):
                        s_name = nm_match.group("name") or nm_match.group("name2") or nm_match.group("alias")
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

    # (3) 당사자 역할 역전 모순 판정 (C등급 / UNVERIFIED)
    role_by_key = defaultdict(list)
    for s in role_stmts:
        role_by_key[s.target_key].append(s)

    for key, stmts in role_by_key.items():
        if len(stmts) < 2:
            continue
        first = stmts[0]
        for other in stmts[1:]:
            if first.role != other.role:
                title = "문서 내 동일 계약상 당사자 지위(임대인 ↔ 임차인) 역전 모순"
                detail = (
                    "동일한 임대차 관계에서 원고의 지위를 한 곳에서는 임대인으로, 다른 곳에서는 임차인으로 "
                    "상반되게 진술하였습니다. 당사자 지위의 오기 여부를 확인해야 합니다."
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
                        "rule_id": "EVI.INCONS_INTERNAL_ROLE",
                        "inconsistency_type": "ROLE",
                        "statements": [first.sentence[:200], other.sentence[:200]],
                        "human_review": True,
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

    # (5) 장소 모순 판정 (조건 3: 동일 주체 + 겹치는 시간 + 한정 표지 결합 상이 장소)
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

    # (6) 서명자 모순 판정 (조건 4: 서증 명시 작성자 vs 본문 진술 불일치 또는 본문 내 상이 진술)
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
