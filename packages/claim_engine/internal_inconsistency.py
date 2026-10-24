"""TK-90 문서 안 진술 불일치(EVI-INCONS) 구조적 탐지 및 예외 분별 모듈.

승인된 설계 메모 docs/handoff/requests/93_evi_incons_internal_inconsistency_design.md 기준:
1. 동일 대상(Entity-Event) 결합 구조: 지시어('위', '이 사건', '본건') 또는 동일 서증 번호·조항 인용 결합 한정.
2. 슬롯 단위 속성 비교:
   - 금액 모순: 동일 계약/채무의 '총액/전액' 확정 진술 간 충돌 (분할 금액·잔액·이자 제외) -> C등급(SUSPICIOUS)
   - 일자 모순: 동일 사건의 직접 결합된 '발생일/체결일' 충돌 (치료·진단·통고 등 후속일 제외) -> C등급(SUSPICIOUS)
   - 역할 모순: 동일 계약 내 주체의 상반된 법률적 지위 단정 (전대차·반소 복수지위 제외) -> C등급(SUSPICIOUS)
   - 서증 조항 상반 원용: 동일 서증 번호 및 동일 조항의 상반된 효과 단정 -> B등급(CONTRADICTED)
3. 정당한 차이(오기 정정, 주위적/예비적 청구, 상대방 주장 반박) 예외 필터링.
4. 선형 시간 복잡도 유지 및 ReDoS 방지: 유한 윈도우 및 선형 파싱.
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


# --- 정당한 차이 (Legitimate Differences) 예외 패턴 ---
_LEGITIMATE_EXCEPTION_RE = re.compile(
    r"(?:오기(?:이므로|로\s*인하여)?\s*[^.\n]{0,60}?(?:바로잡|정정)|"
    r"(?:바로잡|정정)합니다|"
    r"착오로\s*(?:잘못\s*)?기재|"
    r"주위적(?:으로)?|예비적(?:으로)?|"
    r"설령\s*[^.\n]{0,60}?(?:가정하더라도|본다\s*하더라도)|"
    r"(?:피고|원고|상대방)(?:는|의)\s*[^.\n]{0,60}?(?:주장하나|주장은\s*사실과\s*다르|주장은\s*이유\s*없))"
)


# --- 부가세/세액 구분 예외 패턴 ---
_VAT_RE = re.compile(r"(?:부가(?:가치)?세|공급가액|세액|VAT)", re.IGNORECASE)


# --- 1. 금액 모순 (동일 계약 총액 진술 충돌) ---
_TOTAL_AMOUNT_STMT_RE = re.compile(
    r"(?:(?P<total>총\s*(?:매매대금|공사대금|대여금|임대차보증금|약정금|계약금액|대금)|매매대금\s*총액|공사대금\s*총액|총액|전액|총약정금액)[^\d]{0,25}?"
    r"(?P<amount>(?:\d+(?:,\d{3})*|\d+)\s*억\s*(?:(?:\d+(?:,\d{3})*|\d+)\s*만\s*)?원?|(?:\d+(?:,\d{3})*|\d+)\s*만\s*원|(?:\d+(?:,\d{3})*|\d+)\s*원))"
)

_TARGET_CONTRACT_RE = re.compile(
    r"(?P<prefix>위|이\s*사건|본건)\s*(?P<kind>매매계약|공사계약|도급계약|대여금|임대차계약|계약|채무|거래)"
)

# 추출된 금액 바로 앞의 한정어가 부분 금액(잔금, 계약금 등)인지 검사
_PARTIAL_PREFIX_RE = re.compile(
    r"(?:잔금|잔대금|중[·\s]*잔금|나머지|일부|지연손해금|이자|원리금|계약금|중도금)\s*$"
)

_KOREAN_MONEY_RE = re.compile(
    r"(?:(?P<eok>\d+(?:,\d{3})*|\d+)\s*억\s*)?"
    r"(?:(?P<man>\d+(?:,\d{3})*|\d+)\s*만\s*)?"
    r"(?:(?P<won>\d+(?:,\d{3})*|\d+)\s*)?원"
)


def _parse_korean_amount(text: str) -> Optional[int]:
    """한국어 금액 표현을 원 단위 정수로 환산한다."""
    m = _KOREAN_MONEY_RE.search(text)
    if not m:
        return None
    eok_str = m.group("eok")
    man_str = m.group("man")
    won_str = m.group("won")

    if not eok_str and not man_str and not won_str:
        return None

    total = 0
    if eok_str:
        total += int(eok_str.replace(",", "")) * 100_000_000
    if man_str:
        total += int(man_str.replace(",", "")) * 10_000
    if won_str:
        total += int(won_str.replace(",", ""))
    return total if total > 0 else None


# --- 2. 일자 모순 (동일 사건 발생일 충돌) ---
_INCIDENT_TARGET_RE = re.compile(
    r"(?P<prefix>위|이\s*사건|본건)\s*(?P<kind>교통사고|사고|화재사고|충돌사고)"
)

_INCIDENT_DATE_EXCLUDE_RE = re.compile(
    r"(?:치료|입원|진단|통고|수령|해제|지급기일|만기|퇴원|발급|합의)"
)

_DATE_PATTERN_RE = re.compile(
    r"(?P<year>\d{4})[.\s년]+(?P<month>\d{1,2})[.\s월]+(?P<day>\d{1,2})[.\s일]*"
)


# --- 3. 당사자 역할/지위 모순 ---
_ROLE_TARGET_RE = re.compile(
    r"(?P<prefix>위|이\s*사건|본건)\s*(?P<kind>임대차|임대차계약)"
)

_ROLE_EXCLUDE_RE = re.compile(
    r"(?:전대|전차|전대차|반소|별개)"
)

_LANDLORD_STMT_RE = re.compile(r"(?:원고(?:는|가)\s*임대인|임대인인\s*원고)")
_TENANT_STMT_RE = re.compile(r"(?:원고(?:는|가)\s*임차인|임차인인\s*원고)")


# --- 4. 서증 조항 상반 원용 (B등급 상향 조건) ---
_EXHIBIT_CLAUSE_RE = re.compile(
    r"(?P<exhibit>(?:갑|을)\s*제?\s*\d+\s*호증(?:\s*\([^)]*\))?)\s*(?P<clause>제\s*\d+\s*조)"
)

_CLAUSE_EXEMPTION_RE = re.compile(
    r"(?:지체상금[이가을를]?\s*(?:전액\s*)?면제|면제되었|책임이\s*없|성립하지\s*않|부존재|무효)"
)
_CLAUSE_IMPOSITION_RE = re.compile(
    r"(?:지체상금[이가을를]?\s*(?:전액\s*)?(?:부과|청구)|부과되|지급하여야|유효)"
)


# --- 5. 산술 불일치 (ARITHMETIC_MISMATCH) 패턴 ---
_ARITH_MULT_RE = re.compile(
    r"(?P<n1>\d+(?:,\d{3})*)\s*(?P<u1>[가-힣]{1,5})?\s*[×*xX]\s*"
    r"(?P<u2>[가-힣]{1,5}\s*)?(?P<n2>\d+(?:,\d{3})*)\s*(?P<u3>[가-힣]{1,5})?\s*"
    r"(?:[=＝:]|합계(?:는)?|총(?:액)?(?:은)?|추가\s*임금(?:은)?|지급액(?:은)?|금액은|금)?\s*"
    r"(?:총\s*)?(?P<res>\d+(?:,\d{3})*)\s*(?P<ures>[가-힣]{1,5})?"
)

_ARITH_ADD_RE = re.compile(
    r"(?P<n1>\d+(?:,\d{3})*)\s*원?\s*[+＋]\s*(?P<n2>\d+(?:,\d{3})*)\s*원?"
    r"(?:\s*[+＋]\s*(?P<n3>\d+(?:,\d{3})*)\s*원?)?\s*"
    r"(?=[=＝:합총])(?:[=＝:]\s*)?(?:합계(?:는)?|총액(?:은)?|총)?\s*(?P<res>\d+(?:,\d{3})*)\s*원"
)

_ARITH_SUB_RE = re.compile(
    r"(?P<n1>\d+(?:,\d{3})*)\s*원?\s*[-－]\s*(?P<n2>\d+(?:,\d{3})*)\s*원?"
    r"(?:\s*[-－]\s*(?P<n3>\d+(?:,\d{3})*)\s*원?)?\s*"
    r"(?=[=＝:잔순])(?:[=＝:]\s*)?(?:잔액(?:은)?|순액(?:은)?|잔여)?\s*(?P<res>\d+(?:,\d{3})*)\s*원"
)

_ARITH_NET_DESC_RE = re.compile(
    r"지출\s*(?P<n1>\d+(?:,\d{3})*)\s*원[^.\n]{0,25}?(?:환급|수입|입금)\s*(?P<n2>\d+(?:,\d{3})*)\s*원"
    r"[^.\n]{0,35}?(?:순액|차액)[^\d]{0,15}?(?P<res>\d+(?:,\d{3})*)\s*원"
)


# --- 6. 문서 내 사건·처분 속성 모순 패턴 ---
_APPR_DATE_RE = re.compile(
    r"결재일(?:자)?(?:는)?\s*(?P<year>\d{4})[.\s년]+(?P<month>\d{1,2})[.\s월]+(?P<day>\d{1,2})[.\s일]*"
)
_SERV_DATE_RE = re.compile(
    r"송달(?:완료)?일(?:자)?(?:는)?\s*(?P<year>\d{4})[.\s년]+(?P<month>\d{1,2})[.\s월]+(?P<day>\d{1,2})[.\s일]*"
)

_EXCLUSIVE_LOC_RE = re.compile(
    r"(?P<datetime>\d{4}[.\s년]+\d{1,2}[.\s월]+\d{1,2}[.\s일]*(?:\s*\d{1,2}:\d{2})?)[^.\n]{0,25}?"
    r"(?:내내|동안)[^.\n]{0,30}?(?P<loc1>[가-힣a-zA-Z0-9]+)에만\s*있었고"
    r"[^.\n]{0,40}?(?P<loc2>[가-힣a-zA-Z0-9]+)에만\s*있었"
)

_RECEIPT_STMT_RE = re.compile(
    r"접수번호\s*(?P<id>[A-Z0-9-]+)[^.\n]{0,35}?(?:접수일|일자)[^\d]{0,10}?"
    r"(?P<year>\d{4})[.\s년]+(?P<month>\d{1,2})[.\s월]+(?P<day>\d{1,2})[.\s일]*"
)

_SIGNER_SOLE_RE = re.compile(
    r"(?:확인서|동의서|합의서|각서)[^.\n]{0,30}?(?:서명자|서명인은)\s*(?P<name>[가-힣]{2,4})\s*(?:한\s*명|1명|단독)"
)
_SIGNER_DENIAL_RE = re.compile(
    r"유일한\s*서명자(?:는)?\s*(?P<sole>[가-힣]{2,4})[^.\n]{0,30}?(?P<denied>[가-힣]{2,4})(?:은|는)\s*서명하지"
)

_DISPATCH_TIME_RE = re.compile(
    r"(?:회신|통고|발신)[^.\n]{0,30}?(?:발신\s*시각|발신일시)[^\d]{0,10}?(?P<time>\d{1,2}:\d{2})"
)
_DISPATCH_DENY_RE = re.compile(
    r"(?P<t1>\d{1,2}:\d{2})(?:이며|\s*발신)[^.\n]{0,25}?(?P<t2>\d{1,2}:\d{2})\s*발신\s*기록은\s*(?:없었|부존재)"
)


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


def _is_legitimate_exception(sentence: str) -> bool:
    """오기 정정, 주위적/예비적 주장, 상대방 반박 등 정당한 차이 여부를 판별한다."""
    return bool(_LEGITIMATE_EXCEPTION_RE.search(sentence))


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

    appr_dates: List[Tuple[Tuple[int, int, int], str, int]] = []
    serv_dates: List[Tuple[Tuple[int, int, int], str, int]] = []
    receipt_stmts: Dict[str, List[Tuple[Tuple[int, int, int], str, int]]] = defaultdict(list)
    sole_signers: List[Tuple[str, str, int]] = []
    denied_signers: List[Tuple[str, str, str, int]] = []
    dispatch_times: List[Tuple[str, str, int]] = []
    dispatch_denies: List[Tuple[str, str, str, int]] = []

    # 전체 본문에서 임대차 관련 지시어가 최소 1회 이상 존재하는지 확인
    has_lease_context = bool(_ROLE_TARGET_RE.search(text))

    # 문장 단위로 순회하며 유효한 슬롯 추출
    for start, end in sentence_bounds(text):
        sentence = text[start:end].strip()
        if len(sentence) < 10:
            continue

        # 정당한 차이(오기 정정, 주위적/예비적 주장 등) 필터링
        if _is_legitimate_exception(sentence):
            continue

        page = 1
        blocks = reading.blocks_between(start, end)
        if blocks:
            page = getattr(blocks[0], "page_no", 1) or 1

        # 1. 금액 슬롯 추출
        if not _VAT_RE.search(sentence):
            amt_match = _TOTAL_AMOUNT_STMT_RE.search(sentence)
            if amt_match:
                raw_amt = amt_match.group("amount")
                # 금액 바로 앞 15자 윈도우에서 잔금/계약금 등 부분 수식어 배제
                preceding = sentence[max(0, amt_match.start("amount") - 15):amt_match.start("amount")]
                if not _PARTIAL_PREFIX_RE.search(preceding):
                    amount_val = _parse_korean_amount(raw_amt)
                    if amount_val and re.search(r"위|이\s*사건|본건", sentence):
                        category = _contract_category(sentence)
                        key = f"total_amount_{category}"
                        amount_stmts.append(_AmountStatement(key, amount_val, raw_amt, sentence, page))

        # 2. 일자 슬롯 추출 (동일 사건 발생일 한정)
        if not _INCIDENT_DATE_EXCLUDE_RE.search(sentence):
            incident_match = _INCIDENT_TARGET_RE.search(sentence)
            date_match = _DATE_PATTERN_RE.search(sentence)
            if incident_match and date_match:
                key = f"{incident_match.group('prefix')}_{incident_match.group('kind')}"
                date_tuple = (
                    int(date_match.group("year")),
                    int(date_match.group("month")),
                    int(date_match.group("day")),
                )
                date_stmts.append(_DateStatement(key, date_tuple, date_match.group(0), sentence, page))

        # 3. 당사자 역할 슬롯 추출
        if has_lease_context and not _ROLE_EXCLUDE_RE.search(sentence):
            key = "lease_party_role"
            if _LANDLORD_STMT_RE.search(sentence):
                role_stmts.append(_RoleStatement(key, "LANDLORD", sentence, page))
            elif _TENANT_STMT_RE.search(sentence):
                role_stmts.append(_RoleStatement(key, "TENANT", sentence, page))

        # 4. 동일 서증 조항 원용 상반 단정 슬롯 추출
        clause_match = _EXHIBIT_CLAUSE_RE.search(sentence)
        if clause_match:
            exhibit_raw = clause_match.group("exhibit")
            # 호증 번호 정규화: "갑 제1호증(도급계약서)" -> "갑1"
            h_match = re.search(r"([갑을])\s*제?\s*(\d+)\s*호증", exhibit_raw)
            if h_match:
                exhibit_norm = f"{h_match.group(1)}{h_match.group(2)}"
            else:
                exhibit_norm = re.sub(r"\s+", "", exhibit_raw)
            clause_clean = re.sub(r"\s+", "", clause_match.group("clause"))
            key = f"{exhibit_norm}_{clause_clean}"
            if _CLAUSE_EXEMPTION_RE.search(sentence):
                clause_stmts.append(_ExhibitClauseStatement(key, "EXEMPTION", sentence, page))
            elif _CLAUSE_IMPOSITION_RE.search(sentence):
                clause_stmts.append(_ExhibitClauseStatement(key, "IMPOSITION", sentence, page))

        # 5. 산술 불일치 (ARITHMETIC_MISMATCH) 탐지
        # (5-1) 곱셈 계산식
        mult_m = _ARITH_MULT_RE.search(sentence)
        if mult_m:
            try:
                n1 = int(mult_m.group("n1").replace(",", ""))
                n2 = int(mult_m.group("n2").replace(",", ""))
                res = int(mult_m.group("res").replace(",", ""))
                if n1 > 0 and n2 > 0 and res > 0:
                    expected = n1 * n2
                    if expected != res:
                        title = f"문서 내 산술 계산 불일치: {n1:,} × {n2:,} = 기재 {res:,} (실제 {expected:,})"
                        detail = f"문서 본문의 계산식({n1:,} × {n2:,})과 명시된 결과값({res:,})이 산술적으로 일치하지 않습니다(실제: {expected:,})."
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
                                "rule_id": "EVI.INCONS_ARITH_MULT",
                                "inconsistency_type": "ARITHMETIC_MISMATCH",
                                "expected": expected,
                                "actual": res,
                            },
                        ))
            except (ValueError, OverflowError):
                pass

        # (5-2) 덧셈 합산식
        add_m = _ARITH_ADD_RE.search(sentence)
        if add_m:
            try:
                n1 = int(add_m.group("n1").replace(",", ""))
                n2 = int(add_m.group("n2").replace(",", ""))
                n3 = int(add_m.group("n3").replace(",", "")) if add_m.group("n3") else 0
                res = int(add_m.group("res").replace(",", ""))
                if n1 > 0 and n2 > 0 and res > 0:
                    expected = n1 + n2 + n3
                    if expected != res:
                        formula_str = f"{n1:,} + {n2:,}" + (f" + {n3:,}" if n3 else "")
                        title = f"문서 내 산술 합산 불일치: {formula_str} = 기재 {res:,} (실제 {expected:,})"
                        detail = f"문서 본문의 합산식({formula_str})과 명시된 총액({res:,})이 산술적으로 일치하지 않습니다(실제: {expected:,})."
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
                                "rule_id": "EVI.INCONS_ARITH_ADD",
                                "inconsistency_type": "ARITHMETIC_MISMATCH",
                                "expected": expected,
                                "actual": res,
                            },
                        ))
            except (ValueError, OverflowError):
                pass

        # (5-3) 뺄셈 차감식
        sub_m = _ARITH_SUB_RE.search(sentence)
        if sub_m:
            try:
                n1 = int(sub_m.group("n1").replace(",", ""))
                n2 = int(sub_m.group("n2").replace(",", ""))
                n3 = int(sub_m.group("n3").replace(",", "")) if sub_m.group("n3") else 0
                res = int(sub_m.group("res").replace(",", ""))
                if n1 > 0 and n2 > 0 and res > 0:
                    expected = n1 - n2 - n3
                    if expected != res:
                        formula_str = f"{n1:,} - {n2:,}" + (f" - {n3:,}" if n3 else "")
                        title = f"문서 내 산술 차감 불일치: {formula_str} = 기재 {res:,} (실제 {expected:,})"
                        detail = f"문서 본문의 차감식({formula_str})과 명시된 잔액({res:,})이 산술적으로 일치하지 않습니다(실제: {expected:,})."
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
                                "rule_id": "EVI.INCONS_ARITH_SUB",
                                "inconsistency_type": "ARITHMETIC_MISMATCH",
                                "expected": expected,
                                "actual": res,
                            },
                        ))
            except (ValueError, OverflowError):
                pass

        # (5-4) 서술형 지출·환급 순액
        net_m = _ARITH_NET_DESC_RE.search(sentence)
        if net_m:
            try:
                n1 = int(net_m.group("n1").replace(",", ""))
                n2 = int(net_m.group("n2").replace(",", ""))
                res = int(net_m.group("res").replace(",", ""))
                if n1 > 0 and n2 > 0 and res > 0:
                    expected = n1 - n2
                    if expected != res:
                        title = f"문서 내 지출·환급 순액 불일치: {n1:,}원 - {n2:,}원 = 기재 {res:,}원 (실제 {expected:,}원)"
                        detail = f"문서 본문의 지출({n1:,}원) 및 환급({n2:,}원)에 대한 순액 기재({res:,}원)가 일치하지 않습니다(실제: {expected:,}원)."
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
                                "rule_id": "EVI.INCONS_ARITH_NET",
                                "inconsistency_type": "ARITHMETIC_MISMATCH",
                                "expected": expected,
                                "actual": res,
                            },
                        ))
            except (ValueError, OverflowError):
                pass

        # 6. 상호배타적 장소 독점 모순
        loc_m = _EXCLUSIVE_LOC_RE.search(sentence)
        if loc_m:
            loc1, loc2 = loc_m.group("loc1"), loc_m.group("loc2")
            if loc1 != loc2:
                title = f"동일 일시 상호배타적 장소 독점 모순: '{loc1}' ↔ '{loc2}'"
                detail = f"동일한 일시({loc_m.group('datetime')})에 배타적으로 서로 다른 장소에만 체류하였다고 진술하여 모순됩니다."
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.SUSPICIOUS,
                    title=title,
                    detail=detail,
                    excerpt=sentence[:200],
                    page=page,
                    features={"rule_id": "EVI.INCONS_LOC_EXCLUSIVE", "inconsistency_type": "LOCATION"},
                ))

        # 7. 결재일 / 송달일 슬롯 추출
        appr_m = _APPR_DATE_RE.search(sentence)
        if appr_m:
            appr_dates.append(((int(appr_m.group("year")), int(appr_m.group("month")), int(appr_m.group("day"))), sentence, page))

        serv_m = _SERV_DATE_RE.search(sentence)
        if serv_m:
            serv_dates.append(((int(serv_m.group("year")), int(serv_m.group("month")), int(serv_m.group("day"))), sentence, page))

        # 8. 접수번호 슬롯 추출
        rcpt_m = _RECEIPT_STMT_RE.search(sentence)
        if rcpt_m:
            rid = rcpt_m.group("id")
            rdate = (int(rcpt_m.group("year")), int(rcpt_m.group("month")), int(rcpt_m.group("day")))
            receipt_stmts[rid].append((rdate, sentence, page))

        # 9. 서명자 슬롯 추출
        sole_m = _SIGNER_SOLE_RE.search(sentence)
        if sole_m:
            sole_signers.append((sole_m.group("name"), sentence, page))
        deny_m = _SIGNER_DENIAL_RE.search(sentence)
        if deny_m:
            denied_signers.append((deny_m.group("sole"), deny_m.group("denied"), sentence, page))

        # 10. 발신 시각 슬롯 추출
        disp_m = _DISPATCH_TIME_RE.search(sentence)
        if disp_m:
            dispatch_times.append((disp_m.group("time"), sentence, page))
        disp_deny_m = _DISPATCH_DENY_RE.search(sentence)
        if disp_deny_m:
            dispatch_denies.append((disp_deny_m.group("t1"), disp_deny_m.group("t2"), sentence, page))

    # --- O(N) 버킷 기반 슬롯 비교 ---
    # (1) 금액 모순 판정 (C등급 / SUSPICIOUS)
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

    # (2) 일자 모순 판정 (C등급 / SUSPICIOUS)
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

    # (3) 역할 모순 판정 (C등급 / SUSPICIOUS)
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

    # (4) 서증 조항 상반 원용 판정 (B등급 상향 / CONTRADICTED)
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

    # (5) 결재일 > 송달완료일 선후 역전 판정
    for ad, asnt, apg in appr_dates:
        for sd, ssnt, spg in serv_dates:
            if ad > sd:
                title = f"문서 내 결재일·송달일 선후 역전 모순: 결재 {ad[0]}.{ad[1]}.{ad[2]} > 송달 {sd[0]}.{sd[1]}.{sd[2]}"
                detail = "처분 또는 공문서의 결재일자 이전에 이미 송달이 완료되었다고 기재되어 문서 내 선후 관계가 모순됩니다."
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.SUSPICIOUS,
                    title=title,
                    detail=detail,
                    excerpt=f"[{apg}쪽] {asnt[:100]} ↔ [{spg}쪽] {ssnt[:100]}",
                    page=apg,
                    features={"rule_id": "EVI.INCONS_DATE_INVERSION", "inconsistency_type": "DATE"},
                ))
                break

    # (6) 동일 접수번호 일자 불일치
    for rid, rlist in receipt_stmts.items():
        if len(rlist) >= 2:
            d1, s1, p1 = rlist[0]
            for d2, s2, p2 in rlist[1:]:
                if d1 != d2:
                    title = f"동일 접수번호({rid}) 접수일자 불일치: {d1[0]}.{d1[1]}.{d1[2]} ↔ {d2[0]}.{d2[1]}.{d2[2]}"
                    detail = f"동일한 접수번호({rid})에 대해 문서 내 서로 다른 접수일자가 기재되어 확인이 필요합니다."
                    findings.append(_make_incons_finding(
                        doc=doc,
                        kind=FindingType.FACT_CONTRADICTION,
                        grade=EvidenceGrade.C,
                        severity=Severity.MEDIUM,
                        status=VerificationStatus.SUSPICIOUS,
                        title=title,
                        detail=detail,
                        excerpt=f"[{p1}쪽] {s1[:100]} ↔ [{p2}쪽] {s2[:100]}",
                        page=p1,
                        features={"rule_id": "EVI.INCONS_RECEIPT_DATE", "inconsistency_type": "DATE"},
                    ))
                    break

    # (7) 확인서 단독 서명자 상반 모순
    for s_name, s_snt, s_pg in sole_signers:
        for d_sole, d_denied, d_snt, d_pg in denied_signers:
            if s_name == d_denied or s_name != d_sole:
                title = f"동일 문서 서명자 진술 상반 모순: '{s_name}' ↔ '{d_sole}'"
                detail = "동일 확인서의 단독 서명자에 관하여 서로 다른 인물을 지정하거나 서명 사실을 부인하여 모순됩니다."
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.SUSPICIOUS,
                    title=title,
                    detail=detail,
                    excerpt=f"[{s_pg}쪽] {s_snt[:100]} ↔ [{d_pg}쪽] {d_snt[:100]}",
                    page=s_pg,
                    features={"rule_id": "EVI.INCONS_SIGNER", "inconsistency_type": "PERSON"},
                ))
                break

    # (8) 회신 발신 시각 충돌 및 부존재 진술
    for d_time, d_snt, d_pg in dispatch_times:
        for t1, t2, den_snt, den_pg in dispatch_denies:
            if d_time == t2 and t1 != d_time:
                title = f"동일 회신 발신 시각 충돌: {d_time} 발신 주장 ↔ {t1} 발신({t2} 기록 부존재)"
                detail = f"동일 회신의 발신 시각에 관하여 {d_time}에 발신되었다는 주장과 해당 시각 발신 기록이 없다는 진술이 충돌합니다."
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.SUSPICIOUS,
                    title=title,
                    detail=detail,
                    excerpt=f"[{d_pg}쪽] {d_snt[:100]} ↔ [{den_pg}쪽] {den_snt[:100]}",
                    page=d_pg,
                    features={"rule_id": "EVI.INCONS_DISPATCH_TIME", "inconsistency_type": "TIME"},
                ))
                break

    return findings
