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
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument
from packages.document_engine.reading_text import build_reading_text, sentence_bounds

ENGINE_NAME = "claim_engine"


# --- 정당한 차이 (Legitimate Differences) 예외 패턴 ---
_LEGITIMATE_EXCEPTION_RE = re.compile(
    r"(?:오기(?:이므로|로\s*인하여)?\s*.*(?:바로잡|정정)|"
    r"(?:바로잡|정정)합니다|"
    r"착오로\s*(?:잘못\s*)?기재|"
    r"주위적(?:으로)?|예비적(?:으로)?|"
    r"설령\s*.*(?:가정하더라도|본다\s*하더라도)|"
    r"(?:피고|원고|상대방)(?:는|의)\s*.*(?:주장하나|주장은\s*사실과\s*다르|주장은\s*이유\s*없))"
)


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

    # 모순 대조 및 Finding 생성
    # (1) 금액 모순 판정 (C등급 / SUSPICIOUS)
    for i in range(len(amount_stmts)):
        for j in range(i + 1, len(amount_stmts)):
            s1 = amount_stmts[i]
            s2 = amount_stmts[j]
            if s1.target_key == s2.target_key and s1.amount != s2.amount:
                title = f"문서 내 동일 계약 총액 진술 불일치: {s1.amount:,}원 ↔ {s2.amount:,}원"
                detail = (
                    f"동일한 계약/채무에 대해 문서 내 서로 다른 진술에서 총액을 서로 다르게 기재하였습니다. "
                    f"단순 오기이거나 주장 변경인지 사람이 확인해야 합니다."
                )
                excerpt = f"[{s1.page}쪽] {s1.sentence[:120]} ↔ [{s2.page}쪽] {s2.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.UNVERIFIED,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=s1.page,
                    features={
                        "rule_id": "EVI.INCONS_INTERNAL_AMOUNT",
                        "inconsistency_type": "AMOUNT",
                        "statements": [s1.sentence[:200], s2.sentence[:200]],
                        "human_review": True,
                    },
                ))

    # (2) 일자 모순 판정 (C등급 / SUSPICIOUS)
    for i in range(len(date_stmts)):
        for j in range(i + 1, len(date_stmts)):
            s1 = date_stmts[i]
            s2 = date_stmts[j]
            if s1.target_key == s2.target_key and s1.date_val != s2.date_val:
                d1_str = f"{s1.date_val[0]}. {s1.date_val[1]}. {s1.date_val[2]}."
                d2_str = f"{s2.date_val[0]}. {s2.date_val[1]}. {s2.date_val[2]}."
                title = f"문서 내 동일 사건 발생일 진술 불일치: {d1_str} ↔ {d2_str}"
                detail = (
                    f"동일한 사고/사건에 대해 발생 일자를 서로 다르게 진술하였습니다. "
                    f"어느 쪽 일자가 정확한지 확인이 필요합니다."
                )
                excerpt = f"[{s1.page}쪽] {s1.sentence[:120]} ↔ [{s2.page}쪽] {s2.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.UNVERIFIED,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=s1.page,
                    features={
                        "rule_id": "EVI.INCONS_INTERNAL_DATE",
                        "inconsistency_type": "DATE",
                        "statements": [s1.sentence[:200], s2.sentence[:200]],
                        "human_review": True,
                    },
                ))

    # (3) 역할 모순 판정 (C등급 / SUSPICIOUS)
    for i in range(len(role_stmts)):
        for j in range(i + 1, len(role_stmts)):
            s1 = role_stmts[i]
            s2 = role_stmts[j]
            if s1.target_key == s2.target_key and s1.role != s2.role:
                title = "문서 내 동일 계약상 당사자 지위(임대인 ↔ 임차인) 역전 모순"
                detail = (
                    "동일한 임대차 관계에서 원고의 지위를 한 곳에서는 임대인으로, 다른 곳에서는 임차인으로 "
                    "상반되게 진술하였습니다. 당사자 지위의 오기 여부를 확인해야 합니다."
                )
                excerpt = f"[{s1.page}쪽] {s1.sentence[:120]} ↔ [{s2.page}쪽] {s2.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.C,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.UNVERIFIED,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=s1.page,
                    features={
                        "rule_id": "EVI.INCONS_INTERNAL_ROLE",
                        "inconsistency_type": "ROLE",
                        "statements": [s1.sentence[:200], s2.sentence[:200]],
                        "human_review": True,
                    },
                ))

    # (4) 서증 조항 상반 원용 판정 (B등급 상향 / CONTRADICTED)
    for i in range(len(clause_stmts)):
        for j in range(i + 1, len(clause_stmts)):
            s1 = clause_stmts[i]
            s2 = clause_stmts[j]
            if s1.exhibit_clause_key == s2.exhibit_clause_key and s1.effect != s2.effect:
                title = f"동일 서증 조항 원용 상반 단정: {s1.exhibit_clause_key} (면제 ↔ 부과/청구)"
                detail = (
                    f"동일한 서증 번호 및 조항({s1.exhibit_clause_key})을 명시적으로 원용하면서 "
                    f"객관적으로 상반된 법적 효과(면제 ↔ 부과)를 단정하여 모순이 명백합니다."
                )
                excerpt = f"[{s1.page}쪽] {s1.sentence[:120]} ↔ [{s2.page}쪽] {s2.sentence[:120]}"
                findings.append(_make_incons_finding(
                    doc=doc,
                    kind=FindingType.FACT_CONTRADICTION,
                    grade=EvidenceGrade.B,
                    severity=Severity.MEDIUM,
                    status=VerificationStatus.CONTRADICTED,
                    title=title,
                    detail=detail,
                    excerpt=excerpt,
                    page=s1.page,
                    features={
                        "rule_id": "EVI.INCONS_INTERNAL_CLAUSE",
                        "inconsistency_type": "CLAUSE_CONTRADICTION",
                        "statements": [s1.sentence[:200], s2.sentence[:200]],
                    },
                ))

    return findings
