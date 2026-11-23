"""2단계 구조화 Fact Triple 추출 및 결정론 검산 엔진 (0.29.0 방안 A/C).

1단계(extract_fact_triples):
  서면 본문에서 (subject, action_stage, target_object, date_iso, amount_krw, exhibit_ref,
  attribution, modality, page, span, excerpt) 구조화 트리플을 추출한다.
  - 행위 단계(DRAFT/SEND/RECEIVE/CONTRACT/PAY/DELIVER/TERMINATE)를 엄격히 구분하여
    '작성일 != 발송일 != 도착일' 같은 정상 시계열이 충돌로 오탐되지 않게 원천 차단한다.
  - 상대방 주장(OPPONENT), 인용문(QUOTED), 예정/가정/부정(PLANNED/HYPOTHETICAL/NEGATED)을 분리한다.

2단계(verify_fact_triples / verify_project_fact_triples):
  추출된 SELF + ASSERTED 트리플 테이블 위에서 결정론적으로 검산한다.
  - 동일 (subject, action_stage, target_object) 일자/금액 충돌 -> FACT_CONTRADICTION (C, SUSPICIOUS)
  - 동일 대상 인과 단계 역전(RECEIVE < SEND, TERMINATE < CONTRACT) -> EVIDENCE_TIMELINE_INVERSION (B, SUSPICIOUS)
  - 문서 간 동일 (action_stage, target_object) 일자/금액 충돌 -> FACT_CONTRADICTION (C, SUSPICIOUS)
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from packages.claim_engine.internal_inconsistency import (
    _CLAUSE_SPLIT_RE,
    _LEGITIMATE_EXCEPTION_RE,
    _VAT_RE,
    _detect_author_party,
    _is_opponent_claim_sentence,
)
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Evidence, Finding, NormalizedDocument
from packages.document_engine.reading_text import build_reading_text, sentence_bounds

ENGINE_NAME = "claim_engine.fact_triples"

_DATE_RE = re.compile(
    r"(?P<y>(?:19|20)\d{2})\s*[.\-년/]\s*(?P<m>\d{1,2})\s*[.\-월/]\s*(?P<d>\d{1,2})\s*일?"
)
_AMOUNT_RE = re.compile(
    r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>억원|억\s*원|억|만원|만\s*원|원)"
)
_EXHIBIT_RE = re.compile(r"(?P<ex>(?:갑|을|병|정|증)\s*제?\s*\d+호증(?:의\s*\d+)?)")

# 단계별 행위 술어 사전 (상호 배타적 단계 구분)
_STAGE_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("DRAFT", re.compile(r"(?:작성|기안|작출|마련)(?:하|했|하였|한|되|되었|된)")),
    ("SEND", re.compile(r"(?:발송|발신|송부|통지|통보|고지)(?:하|했|하였|한|되|되었|된)")),
    ("RECEIVE", re.compile(r"(?:도달|도착|수신|접수|수령|송달받|교부받)(?:하|했|하였|한|되|되었|된|았|었|은)")),
    ("TERMINATE", re.compile(r"(?:해지|해제|취소|철회|해고)(?:하|했|하였|한|되|되었|된)")),
    ("CONTRACT", re.compile(r"(?:체결|약정|합의|계약)(?:하|했|하였|한|되|되었|된)")),
    ("PAY", re.compile(r"(?:지급|입금|변제|송금|상환|납부)(?:하|했|하였|한|되|되었|된)")),
    ("DELIVER", re.compile(r"(?:인도|납품|공급|설치|완공)(?:하|했|하였|한|되|되었|된)")),
)

_TARGET_NOUN_RE = re.compile(
    r"(?:(?:이\s*사건|본건|위|해당|동)\s+)?"
    r"(?P<target>"
    r"매매계약서?|임대차계약서?|도급계약서?|용역계약서?|근로계약서?|계약서|계약|"
    r"회신서|통지서|내용증명|최고서|합의서|확인서|진술서|정산표|견적서|처분서|결정서|"
    r"매매대금|공사대금|용역대금|임대차보증금|보증금|차용금|대여금|합의금|위약금|손해배상금|"
    r"처분|징계|해고"
    r")"
)

_SUBJECT_RE = re.compile(
    r"(?<![가-힣])(?P<subj>원고|피고|신청인|피신청인|채권자|채무자|항소인|피항소인|상고인|피상고인|고소인|피고소인|피고인|임대인|임차인|매도인|매수인)"
)

_PLANNED_OR_MOD_RE = re.compile(
    r"(?:예정|계획|하기로|가정|만약|설령|추후|향후|변경|증액|감액|인상|인하|할인|조정|갱신|연장|단축|"
    r"분할|할부|일부|계약금|중도금|잔금|매월|월간|연간|분기|1차|2차|3차|당초|종전|신규|기존|최초|최종|"
    r"않았다|않는다|아니다|없다|아니며|못하였|못했다)"
)
_QUOTED_CONTEXT_RE = re.compile(r"(?:대법원|고등법원|지방법원|헌법재판소)\s*\d{4}.*?선고")
_LUMP_SUM_TARGETS = frozenset({
    "매매대금", "공사대금", "용역대금", "임대차보증금", "보증금", "차용금", "대여금", "합의금", "위약금",
})


@dataclass(frozen=True)
class FactTriple:
    subject: str
    action_stage: str
    target_object: str
    date_iso: Optional[str] = None
    amount_krw: Optional[int] = None
    exhibit_ref: Optional[str] = None
    attribution: str = "SELF"       # SELF | OPPONENT | QUOTED
    modality: str = "ASSERTED"      # ASSERTED | PLANNED
    document_id: str = ""
    page: int = 1
    span: Tuple[int, int] = (0, 0)
    excerpt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _parse_date(text: str) -> Optional[str]:
    m = _DATE_RE.search(text)
    if not m:
        return None
    try:
        d = date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
        return d.isoformat()
    except ValueError:
        return None


def _parse_amount(text: str) -> Optional[int]:
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    try:
        val = Decimal(m.group("num").replace(",", ""))
    except InvalidOperation:
        return None
    unit = re.sub(r"\s+", "", m.group("unit"))
    if unit in ("억", "억원"):
        val *= Decimal(100_000_000)
    elif unit in ("만", "만원"):
        val *= Decimal(10_000)
    krw = int(val)
    return krw if krw > 0 else None


def _normalize_target(raw: str) -> str:
    s = re.sub(r"\s+", "", raw)
    if s.endswith("계약서"):
        return s[:-1]  # 계약서 -> 계약 통일 (예: 매매계약서 == 매매계약)
    return s


def extract_fact_triples(doc: NormalizedDocument) -> List[FactTriple]:
    """1단계: 문서 본문에서 구조화 FactTriple 목록을 추출한다."""
    reading = build_reading_text(doc)
    text = reading.text or ""
    if not text.strip():
        return []

    author_party = _detect_author_party(doc)
    triples: List[FactTriple] = []

    for s_start, s_end in sentence_bounds(text):
        sent = text[s_start:s_end].strip()
        if len(sent) < 8:
            continue
        if _LEGITIMATE_EXCEPTION_RE.search(sent) or _VAT_RE.search(sent):
            continue

        sent_page = (reading.page_for(s_start) or 1) if hasattr(reading, "page_for") else 1
        if _is_opponent_claim_sentence(sent, author_party):
            sent_attr = "OPPONENT"
        elif _QUOTED_CONTEXT_RE.search(sent):
            sent_attr = "QUOTED"
        else:
            sent_attr = "SELF"

        # 절 단위로 분리하여 '작성 -> 발송 -> 도착' 등 다단계 문장을 독립 트리플로 추출
        clauses = [c.strip() for c in _CLAUSE_SPLIT_RE.split(sent) if c and c.strip()]
        if not clauses:
            clauses = [sent]

        prev_target = ""
        prev_subj = "UNSPECIFIED"
        for clause in clauses:
            stage = next((st for st, pat in _STAGE_PATTERNS if pat.search(clause)), None)
            if stage is None:
                # 대상만 먼저 등장한 앞 절이면 컨텍스트만 승계
                m_t = _TARGET_NOUN_RE.search(clause)
                if m_t:
                    prev_target = _normalize_target(m_t.group("target"))
                m_s = _SUBJECT_RE.search(clause)
                if m_s:
                    prev_subj = m_s.group("subj")
                continue

            m_s = _SUBJECT_RE.search(clause)
            subj = m_s.group("subj") if m_s else prev_subj
            prev_subj = subj

            m_t = _TARGET_NOUN_RE.search(clause)
            target = _normalize_target(m_t.group("target")) if m_t else prev_target
            if m_t:
                prev_target = target

            m_ex = _EXHIBIT_RE.search(clause)
            ex_ref = re.sub(r"\s+", "", m_ex.group("ex")) if m_ex else None

            d_iso = _parse_date(clause)
            amt = _parse_amount(clause)
            if d_iso is None and amt is None:
                continue

            modality = "PLANNED" if _PLANNED_OR_MOD_RE.search(clause) else "ASSERTED"
            attr = sent_attr
            if attr == "SELF" and re.search(r"(?:라고|다고)\s*(?:주장|진술|항변)", clause):
                attr = "OPPONENT"

            triples.append(
                FactTriple(
                    subject=subj,
                    action_stage=stage,
                    target_object=target,
                    date_iso=d_iso,
                    amount_krw=amt,
                    exhibit_ref=ex_ref,
                    attribution=attr,
                    modality=modality,
                    document_id=doc.document_id,
                    page=sent_page,
                    span=(s_start, s_end),
                    excerpt=sent[:200],
                )
            )

    return triples


def verify_fact_triples(
    doc: NormalizedDocument,
    triples: Sequence[FactTriple],
    *,
    existing_findings: Sequence[Finding] = (),
) -> List[Finding]:
    """2단계: 단일 문서의 SELF + ASSERTED FactTriple 테이블에서 충돌 및 인과 단계 역전을 검산한다."""
    findings: List[Finding] = []
    active = [t for t in triples if t.attribution == "SELF" and t.modality == "ASSERTED" and t.target_object]
    if not active:
        return findings

    existing_keys = {
        (f.confidence_features or {}).get("anchor_key")
        for f in existing_findings
        if (f.confidence_features or {}).get("anchor_key")
    }

    # 1. 동일 (action_stage, target_object) 일자 충돌 (subject가 명시되고 서로 다르면 제외)
    by_stage_target: Dict[Tuple[str, str], List[FactTriple]] = defaultdict(list)
    for t in active:
        by_stage_target[(t.action_stage, t.target_object)].append(t)

    for (stage, target), group in by_stage_target.items():
        if f"{target}:{stage}" in existing_keys:
            continue
        # 서로 다른 당사자가 행한 별개 행위면 제외
        explicit_subjs = {t.subject for t in group if t.subject != "UNSPECIFIED"}
        if len(explicit_subjs) > 1:
            continue

        dated = [t for t in group if t.date_iso]
        distinct_dates = []
        seen_d = set()
        for t in dated:
            if t.date_iso not in seen_d:
                seen_d.add(t.date_iso)
                distinct_dates.append(t)
        if len(distinct_dates) >= 2:
            a, b = distinct_dates[0], distinct_dates[1]
            findings.append(
                Finding.create(
                    type=FindingType.FACT_CONTRADICTION,
                    status=VerificationStatus.SUSPICIOUS,
                    severity=Severity.MEDIUM,
                    evidence_grade=EvidenceGrade.C,
                    title=f"구조화 사실 일자 충돌: {target}({stage}) {a.date_iso} ↔ {b.date_iso}",
                    detail=(
                        f"동일 대상 '{target}'의 동일 행위 단계({stage})에 대해 "
                        f"서로 다른 일자({a.date_iso} vs {b.date_iso})가 기재되어 있다."
                    ),
                    document_id=doc.document_id,
                    page=b.page,
                    span=b.span,
                    engine=ENGINE_NAME,
                    confidence=0.72,
                    confidence_features={
                        "deterministic_rule": True,
                        "rule_id": "FACT_TRIPLE.VALUE_CONFLICT",
                        "action_stage": stage,
                        "target_object": target,
                        "anchor_key": f"{target}:{stage}",
                        "values": [a.date_iso, b.date_iso],
                        "human_review": True,
                    },
                    tags=["EVI-INCONS", "FACT_TRIPLE"],
                    evidence=[
                        Evidence.create(
                            description="Fact Triple 일자 충돌",
                            grade=EvidenceGrade.C,
                            document_id=doc.document_id,
                            page=b.page,
                            excerpt=f"[{a.page}쪽] {a.excerpt[:90]} ↔ [{b.page}쪽] {b.excerpt[:90]}",
                            supports=False,
                        )
                    ],
                )
            )

        # 단일 총액 대상에 대한 금액 충돌
        if target in _LUMP_SUM_TARGETS and stage in ("CONTRACT", "PAY"):
            priced = [t for t in group if t.amount_krw]
            distinct_amts = []
            seen_a = set()
            for t in priced:
                if t.amount_krw not in seen_a:
                    seen_a.add(t.amount_krw)
                    distinct_amts.append(t)
            if len(distinct_amts) >= 2:
                a, b = distinct_amts[0], distinct_amts[1]
                findings.append(
                    Finding.create(
                        type=FindingType.FACT_CONTRADICTION,
                        status=VerificationStatus.SUSPICIOUS,
                        severity=Severity.MEDIUM,
                        evidence_grade=EvidenceGrade.C,
                        title=f"구조화 사실 금액 충돌: {target}({stage}) {a.amount_krw:,}원 ↔ {b.amount_krw:,}원",
                        detail=(
                            f"동일 대상 '{target}'의 동일 행위 단계({stage})에 대해 "
                            f"서로 다른 금액({a.amount_krw:,}원 vs {b.amount_krw:,}원)이 기재되어 있다."
                        ),
                        document_id=doc.document_id,
                        page=b.page,
                        span=b.span,
                        engine=ENGINE_NAME,
                        confidence=0.72,
                        confidence_features={
                            "deterministic_rule": True,
                            "rule_id": "FACT_TRIPLE.AMOUNT_CONFLICT",
                            "action_stage": stage,
                            "target_object": target,
                            "anchor_key": f"{target}:{stage}:AMT",
                            "values": [a.amount_krw, b.amount_krw],
                            "human_review": True,
                        },
                        tags=["EVI-INCONS", "FACT_TRIPLE"],
                        evidence=[
                            Evidence.create(
                                description="Fact Triple 금액 충돌",
                                grade=EvidenceGrade.C,
                                document_id=doc.document_id,
                                page=b.page,
                                excerpt=f"[{a.page}쪽] {a.excerpt[:90]} ↔ [{b.page}쪽] {b.excerpt[:90]}",
                                supports=False,
                            )
                        ],
                    )
                )

    # 2. 동일 대상의 인과 단계 선후 역전 (RECEIVE < SEND, TERMINATE < CONTRACT)
    by_target: Dict[str, List[FactTriple]] = defaultdict(list)
    for t in active:
        if t.date_iso:
            by_target[t.target_object].append(t)

    _CAUSAL_PAIRS = (("SEND", "RECEIVE"), ("CONTRACT", "TERMINATE"))
    for target, group in by_target.items():
        for earlier_stage, later_stage in _CAUSAL_PAIRS:
            earliers = [t for t in group if t.action_stage == earlier_stage]
            laters = [t for t in group if t.action_stage == later_stage]
            if not earliers or not laters:
                continue
            emitted = False
            for e_t in earliers:
                for l_t in laters:
                    if l_t.date_iso < e_t.date_iso:
                        findings.append(
                            Finding.create(
                                type=FindingType.EVIDENCE_TIMELINE_INVERSION,
                                status=VerificationStatus.SUSPICIOUS,
                                severity=Severity.MEDIUM,
                                evidence_grade=EvidenceGrade.B,
                                title=f"인과 단계 시계열 역전: {target} {later_stage}({l_t.date_iso}) < {earlier_stage}({e_t.date_iso})",
                                detail=(
                                    f"동일 대상 '{target}'의 후행 단계({later_stage}: {l_t.date_iso})가 "
                                    f"선행 단계({earlier_stage}: {e_t.date_iso})보다 앞서 기재되어 있다."
                                ),
                                document_id=doc.document_id,
                                page=l_t.page,
                                span=l_t.span,
                                engine=ENGINE_NAME,
                                confidence=0.8,
                                confidence_features={
                                    "deterministic_rule": True,
                                    "rule_id": "FACT_TRIPLE.STAGE_INVERSION",
                                    "target_object": target,
                                    "earlier_stage": earlier_stage,
                                    "later_stage": later_stage,
                                    "dates": [e_t.date_iso, l_t.date_iso],
                                    "human_review": True,
                                },
                                tags=["EVI-DATE", "TIMELINE", "FACT_TRIPLE"],
                                evidence=[
                                    Evidence.create(
                                        description="Fact Triple 단계 선후 역전",
                                        grade=EvidenceGrade.B,
                                        document_id=doc.document_id,
                                        page=l_t.page,
                                        excerpt=f"{e_t.excerpt[:90]} ↔ {l_t.excerpt[:90]}",
                                        supports=False,
                                    )
                                ],
                            )
                        )
                        emitted = True
                        break
                if emitted:
                    break

    return findings


def verify_project_fact_triples(
    doc_triples: Sequence[Tuple[NormalizedDocument, Sequence[FactTriple]]],
) -> List[Finding]:
    """2단계(프로젝트 교차): 복수 문서 간 동일 (action_stage, target_object) 충돌을 검산한다."""
    findings: List[Finding] = []
    by_key: Dict[Tuple[str, str], List[Tuple[NormalizedDocument, FactTriple]]] = defaultdict(list)

    for doc, triples in doc_triples:
        for t in triples:
            if t.attribution == "SELF" and t.modality == "ASSERTED" and t.target_object:
                by_key[(t.action_stage, t.target_object)].append((doc, t))

    for (stage, target), items in by_key.items():
        # 문서가 최소 2건 이상이고, 각 문서별 대표값이 충돌할 때만 보고
        by_doc: Dict[str, List[FactTriple]] = defaultdict(list)
        doc_map: Dict[str, NormalizedDocument] = {}
        for d, t in items:
            by_doc[d.document_id].append(t)
            doc_map[d.document_id] = d
        if len(by_doc) < 2:
            continue

        explicit_subjs = {t.subject for _, t in items if t.subject != "UNSPECIFIED"}
        if len(explicit_subjs) > 1:
            continue

        doc_dates: List[Tuple[str, FactTriple]] = []
        for did, d_items in by_doc.items():
            dates = {t.date_iso for t in d_items if t.date_iso}
            if len(dates) == 1:
                t_rep = next(t for t in d_items if t.date_iso)
                doc_dates.append((did, t_rep))
        distinct_dates = {t.date_iso for _, t in doc_dates}
        if len(distinct_dates) >= 2:
            (d1, t1), (d2, t2) = doc_dates[0], next((d, t) for d, t in doc_dates[1:] if t.date_iso != doc_dates[0][1].date_iso)
            findings.append(
                Finding.create(
                    type=FindingType.FACT_CONTRADICTION,
                    status=VerificationStatus.SUSPICIOUS,
                    severity=Severity.MEDIUM,
                    evidence_grade=EvidenceGrade.C,
                    title=f"문서 간 구조화 사실 일자 불일치: {target}({stage}) {t1.date_iso} ↔ {t2.date_iso}",
                    detail=(
                        f"{doc_map[d1].filename}과 {doc_map[d2].filename}에서 동일 대상 '{target}'의 "
                        f"행위 단계({stage}) 일자가 서로 다르다({t1.date_iso} vs {t2.date_iso})."
                    ),
                    document_id=d1,
                    page=t1.page,
                    engine=ENGINE_NAME,
                    confidence=0.72,
                    confidence_features={
                        "deterministic_rule": True,
                        "rule_id": "FACT_TRIPLE.CROSS_DOC_CONFLICT",
                        "action_stage": stage,
                        "target_object": target,
                        "sources": [{"document_id": d1}, {"document_id": d2}],
                        "values": [t1.date_iso, t2.date_iso],
                        "human_review": True,
                    },
                    tags=["EVI-INCONS", "CROSS_DOC", "FACT_TRIPLE"],
                    evidence=[
                        Evidence.create(
                            description=f"{doc_map[d1].filename} ↔ {doc_map[d2].filename}",
                            grade=EvidenceGrade.C,
                            document_id=d1,
                            page=t1.page,
                            excerpt=f"{t1.excerpt[:90]} ↔ {t2.excerpt[:90]}",
                            supports=False,
                        )
                    ],
                )
            )

    return findings
