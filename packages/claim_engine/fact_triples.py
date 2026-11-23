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

# 단계별 행위 술어 사전 (상호 배타적 단계 구분; 동사/명사형 ~일 포함)
_STAGE_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("DRAFT", re.compile(r"(?:(?:작성|기안|작출|마련|기재)(?:하|했|하였|한|되|되었|된)|작성일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("SEND", re.compile(r"(?:(?:발송|발신|송부|통지|통보|고지)(?:하|했|하였|한|되|되었|된)|(?:발송|통지)일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("RECEIVE", re.compile(r"(?:(?:도달|도착|수신|접수|수령|송달받|교부받)(?:하|했|하였|한|되|되었|된|았|었|은)|(?:도달|도착|수령|접수)일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("SUBMIT", re.compile(r"(?:(?:제출|신청|신고|청구|요청|제기)(?:하|했|하였|한|되|되었|된)|(?:제출|신고|신청)일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("TERMINATE", re.compile(r"(?:(?:해지|해제|취소|철회|해고)(?:하|했|하였|한|되|되었|된)|(?:해지|해제|해고)일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("CONTRACT", re.compile(r"(?:(?:체결|약정|합의|계약|매수|매도|임대|임차|차용|대여|분양|양도)(?:하|했|하였|한|되|되었|된)|(?:계약|체결)일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("PAY", re.compile(r"(?:(?:지급|입금|변제|송금|상환|납부|반환|출금|이체)(?:하|했|하였|한|되|되었|된)|(?:지급|입금|변제)일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("DELIVER", re.compile(r"(?:인도|납품|공급|설치|완공)(?:하|했|하였|한|되|되었|된)")),
    ("WORK_START", re.compile(r"(?:(?:입사|임용|취업|발령)(?:하|했|하였|한|되|되었|된)|(?:입사|취업)일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("WORK_END", re.compile(r"(?:(?:퇴사|퇴직|면직|사직)(?:하|했|하였|한|되|되었|된)|(?:퇴사|퇴직)일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("WORK", re.compile(r"(?:근무|재직)(?:하|했|하였|한)")),
    ("OCCUR", re.compile(r"(?:(?:발생|시행|개시)(?:하|했|하였|한|되|되었|된)|(?:발생|사고|개시)일(?:시|자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("CONFIRM", re.compile(r"(?:(?:확인|점검|감정|조사|확정)(?:하|했|하였|한|되|되었|된)|확인일(?:자)?(?=\s*(?:은|는|이|가|으로|로|:|$)))")),
    ("CALC", re.compile(r"(?:가산|차감|공제|합산|정산)(?:하|했|하였|한|되|되었|된)")),
)

_TARGET_NOUN_RE = re.compile(
    r"(?:(?:이\s*사건|본건|위|해당|동)\s+)?"
    r"(?P<target>"
    r"[가-힣]{0,6}(?:계약서?|확인서|통지서|진술서|합의서|최고서|회신서|정산표|견적서|처분서|결정서|명세서|영수증|보고서|신청서|신고서|청구서)|"
    r"내용증명|준비서면|답변서|소장|판결|결정|명령|"
    r"매매대금|공사대금|용역대금|임대차보증금|보증금|차용금|대여금|합의금|위약금|손해배상금|퇴직금|청구금액|손해액|합계|총액|총계|잔액|"
    r"처분|징계|해고|근로관계|근무|약정|합의|공사|매매|임대차|고소|신고|거래|사건|분쟁|소송|조정|특약"
    r")"
)

_CASE_TARGET_RE = re.compile(r"이\s*사건\s+(?P<target>[가-힣]{2,10})")
_OBJ_PARTICLE_RE = re.compile(r"(?<![가-힣])(?P<target>[가-힣]{2,8})(?:을|를)(?=\s)")
_STOP_TARGETS = frozenset({
    "사실", "내용", "것", "바", "점", "경우", "일자", "날짜", "금액", "부분", "내역", "이유", "취지", "결과",
    "원고", "피고", "신청인", "피신청인", "채권자", "채무자", "항소인", "피항소인", "상고인", "피상고인",
    "임대인", "임차인", "매도인", "매수인", "근로자", "사용자",
})

_SUBJECT_RE = re.compile(
    r"(?<![가-힣])(?P<subj>원고|피고|신청인|피신청인|채권자|채무자|항소인|피항소인|상고인|피상고인|고소인|피고소인|피고인|임대인|임차인|매도인|매수인|근로자|사용자)"
)

_PLANNED_RE = re.compile(
    r"(?:예정|계획|하기로|가정|만약|설령|추후|향후|않았다|않는다|아니다|없다|아니며|못하였|못했다)"
)
_MOD_OR_PART_RE = re.compile(
    r"(?:변경|증액|감액|인상|인하|할인|조정|갱신|연장|단축|"
    r"분할|할부|일부|계약금|중도금|잔금|매월|월간|연간|분기|1차|2차|3차|당초|종전|신규|기존)"
)

_QUOTED_CONTEXT_RE = re.compile(r"(?:대법원|고등법원|지방법원|헌법재판소)\s*\d{4}.*?선고")
_LUMP_SUM_TARGETS = frozenset({
    "매매대금", "공사대금", "용역대금", "임대차보증금", "보증금", "차용금", "대여금", "합의금", "위약금",
    "청구금액", "손해액", "합계", "총액", "총계", "잔액", "퇴직금",
})

_LABEL_STAGE_MAP: Tuple[Tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"(?:작성일|작성일자)"), "DRAFT", "문서"),
    (re.compile(r"(?:발송일|발송일자|통지일)"), "SEND", "통지서"),
    (re.compile(r"(?:도달일|도착일|수령일|접수일)"), "RECEIVE", "통지서"),
    (re.compile(r"(?:계약일|체결일|계약일자)"), "CONTRACT", "계약"),
    (re.compile(r"(?:해지일|해제일|해고일)"), "TERMINATE", "계약"),
    (re.compile(r"(?:지급일|입금일|변제일)"), "PAY", "대금"),
    (re.compile(r"(?:입사일|입사일자)"), "WORK_START", "근무"),
    (re.compile(r"(?:퇴사일|퇴직일|퇴사일자)"), "WORK_END", "근무"),
)


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
    is_partial_or_mod: bool = False
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


def _extract_target(text: str) -> str:
    m_t = _TARGET_NOUN_RE.search(text)
    if m_t:
        return _normalize_target(m_t.group("target"))
    m_c = _CASE_TARGET_RE.search(text)
    if m_c:
        return _normalize_target(m_c.group("target"))
    for m_p in _OBJ_PARTICLE_RE.finditer(text):
        cand = m_p.group("target")
        if cand not in _STOP_TARGETS:
            return _normalize_target(cand)
    return ""


def extract_fact_triples(doc: Optional[NormalizedDocument]) -> List[FactTriple]:
    """1단계: 문서 본문 및 표에서 구조화 FactTriple 목록을 추출한다."""
    if doc is None:
        return []
    reading = build_reading_text(doc)
    text = reading.text or ""
    author_party = _detect_author_party(doc)
    triples: List[FactTriple] = []

    def _process_unit(unit_text: str, page_num: int, span: Tuple[int, int]) -> None:
        sent = unit_text.strip()
        if len(sent) < 6:
            return
        if _LEGITIMATE_EXCEPTION_RE.search(sent) or _VAT_RE.search(sent):
            return

        if _is_opponent_claim_sentence(sent, author_party):
            sent_attr = "OPPONENT"
        elif _QUOTED_CONTEXT_RE.search(sent):
            sent_attr = "QUOTED"
        else:
            sent_attr = "SELF"

        # 문장 전체에서 유일한 서증번호가 있으면 절에 승계
        sent_exhibits = {re.sub(r"\s+", "", m.group("ex")) for m in _EXHIBIT_RE.finditer(sent)}
        sent_exhibit = next(iter(sent_exhibits)) if len(sent_exhibits) == 1 else None

        # 표/라벨 Key-Value 행 처리 (예: '작성일: 2024. 1. 10.' 또는 '계약일 | 2024. 1. 10.')
        kv_m = re.match(r"^(?P<k>[가-힣\s]{2,12})\s*[:：|]\s*(?P<v>.+)$", sent)
        if kv_m:
            k_txt = kv_m.group("k").strip()
            v_txt = kv_m.group("v").strip()
            for k_re, k_stage, k_target in _LABEL_STAGE_MAP:
                if k_re.search(k_txt):
                    d_iso = _parse_date(v_txt)
                    amt = _parse_amount(v_txt)
                    if d_iso or amt:
                        triples.append(
                            FactTriple(
                                subject="UNSPECIFIED",
                                action_stage=k_stage,
                                target_object=k_target,
                                date_iso=d_iso,
                                amount_krw=amt,
                                exhibit_ref=sent_exhibit,
                                attribution=sent_attr,
                                modality="PLANNED" if _PLANNED_RE.search(sent) else "ASSERTED",
                                is_partial_or_mod=bool(_MOD_OR_PART_RE.search(sent)),
                                document_id=doc.document_id,
                                page=page_num,
                                span=span,
                                excerpt=sent[:200],
                            )
                        )
                    return

        # 절 단위로 분리하여 '작성 -> 발송 -> 도착' 등 다단계 문장을 독립 트리플로 추출
        clauses = [c.strip() for c in _CLAUSE_SPLIT_RE.split(sent) if c and c.strip()]
        if not clauses:
            clauses = [sent]

        prev_target = ""
        prev_subj = "UNSPECIFIED"
        orphan_date: Optional[str] = None
        orphan_amt: Optional[int] = None

        for clause in clauses:
            stage = next((st for st, pat in _STAGE_PATTERNS if pat.search(clause)), None)
            if stage is None:
                t_cand = _extract_target(clause)
                if t_cand:
                    prev_target = t_cand
                m_s = _SUBJECT_RE.search(clause)
                if m_s:
                    prev_subj = m_s.group("subj")
                # 앞 절에 날짜/금액만 있고 술어가 없으면 다음 절 술어에 임시 보류
                d_c = _parse_date(clause)
                a_c = _parse_amount(clause)
                if d_c:
                    orphan_date = d_c
                if a_c:
                    orphan_amt = a_c
                continue

            m_s = _SUBJECT_RE.search(clause)
            subj = m_s.group("subj") if m_s else prev_subj
            prev_subj = subj

            t_cand = _extract_target(clause)
            target = t_cand if t_cand else prev_target
            if not target and stage in ("WORK_START", "WORK_END"):
                target = "근무"
            if t_cand:
                prev_target = target

            m_ex = _EXHIBIT_RE.search(clause)
            ex_ref = re.sub(r"\s+", "", m_ex.group("ex")) if m_ex else sent_exhibit

            d_iso = _parse_date(clause) or orphan_date
            amt = _parse_amount(clause) or orphan_amt
            orphan_date = None
            orphan_amt = None
            if d_iso is None and amt is None:
                continue

            modality = "PLANNED" if _PLANNED_RE.search(clause) else "ASSERTED"
            is_mod = bool(_MOD_OR_PART_RE.search(clause))
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
                    is_partial_or_mod=is_mod,
                    document_id=doc.document_id,
                    page=page_num,
                    span=span,
                    excerpt=sent[:200],
                )
            )

    if text.strip():
        for s_start, s_end in sentence_bounds(text):
            sent_page = (reading.page_for(s_start) or 1) if hasattr(reading, "page_for") else 1
            _process_unit(text[s_start:s_end], sent_page, (s_start, s_end))

    # 표/표행 블록도 추출 (reading_text는 table/table_line을 제외하므로 별도 수집)
    for blk in doc.body_blocks():
        if getattr(blk, "block_type", "") in ("table", "table_line") and getattr(blk, "text", ""):
            for line in blk.text.splitlines():
                _process_unit(line, getattr(blk, "page", 1) or 1, (0, 0))

    return triples


def verify_fact_triples(
    doc: NormalizedDocument,
    triples: Sequence[FactTriple],
    *,
    existing_findings: Sequence[Finding] = (),
) -> List[Finding]:
    """2단계: 단일 문서의 SELF + ASSERTED FactTriple 테이블에서 충돌 및 인과 단계 역전을 검산한다."""
    findings: List[Finding] = []
    active_all = [t for t in triples if t.attribution == "SELF" and t.modality == "ASSERTED"]
    if not active_all:
        return findings

    existing_keys = {
        (f.confidence_features or {}).get("anchor_key")
        for f in existing_findings
        if (f.confidence_features or {}).get("anchor_key")
    }
    emitted_anchors = set(existing_keys)

    # 1. 동일 (action_stage, target_object) 일자/금액 충돌 (is_partial_or_mod 제외, subject가 명시되고 서로 다르면 제외)
    by_stage_target: Dict[Tuple[str, str], List[FactTriple]] = defaultdict(list)
    for t in active_all:
        if t.target_object and not t.is_partial_or_mod:
            by_stage_target[(t.action_stage, t.target_object)].append(t)

    for (stage, target), group in by_stage_target.items():
        anchor = f"{target}:{stage}"
        if anchor in emitted_anchors:
            continue
        explicit_subjs = {t.subject for t in group if t.subject != "UNSPECIFIED"}
        if len(explicit_subjs) > 1:
            continue

        dated = [t for t in group if t.date_iso]
        distinct_dates: List[FactTriple] = []
        seen_d = set()
        for t in dated:
            if t.date_iso not in seen_d:
                seen_d.add(t.date_iso)
                distinct_dates.append(t)
        if len(distinct_dates) >= 2:
            a, b = distinct_dates[0], distinct_dates[1]
            emitted_anchors.add(anchor)
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
                        "anchor_key": anchor,
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
            distinct_amts: List[FactTriple] = []
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

    # 1b. 동일 (exhibit_ref, action_stage) 일자 충돌 (target_object 표현이 다르거나 빈 경우 보완)
    by_ex_stage: Dict[Tuple[str, str], List[FactTriple]] = defaultdict(list)
    for t in active_all:
        if t.exhibit_ref and not t.is_partial_or_mod and t.date_iso:
            by_ex_stage[(t.exhibit_ref, t.action_stage)].append(t)

    for (ex_ref, stage), group in by_ex_stage.items():
        ex_anchor = f"{ex_ref}:{stage}"
        if ex_anchor in emitted_anchors:
            continue
        explicit_subjs = {t.subject for t in group if t.subject != "UNSPECIFIED"}
        if len(explicit_subjs) > 1:
            continue
        distinct_dates: List[FactTriple] = []
        seen_d = set()
        for t in group:
            if t.date_iso and t.date_iso not in seen_d:
                seen_d.add(t.date_iso)
                distinct_dates.append(t)
        if len(distinct_dates) >= 2:
            a, b = distinct_dates[0], distinct_dates[1]
            # 이미 동일 target_object로 보고되었으면 중복 생략
            if a.target_object and a.target_object == b.target_object and f"{a.target_object}:{stage}" in emitted_anchors:
                continue
            emitted_anchors.add(ex_anchor)
            findings.append(
                Finding.create(
                    type=FindingType.FACT_CONTRADICTION,
                    status=VerificationStatus.SUSPICIOUS,
                    severity=Severity.MEDIUM,
                    evidence_grade=EvidenceGrade.C,
                    title=f"서증 Fact Triple 일자 충돌: {ex_ref}({stage}) {a.date_iso} ↔ {b.date_iso}",
                    detail=(
                        f"동일 서증 '{ex_ref}'의 동일 행위 단계({stage})에 대해 "
                        f"서로 다른 일자({a.date_iso} vs {b.date_iso})가 기재되어 있다."
                    ),
                    document_id=doc.document_id,
                    page=b.page,
                    span=b.span,
                    engine=ENGINE_NAME,
                    confidence=0.72,
                    confidence_features={
                        "deterministic_rule": True,
                        "rule_id": "FACT_TRIPLE.EXHIBIT_VALUE_CONFLICT",
                        "action_stage": stage,
                        "exhibit_ref": ex_ref,
                        "anchor_key": ex_anchor,
                        "values": [a.date_iso, b.date_iso],
                        "human_review": True,
                    },
                    tags=["EVI-INCONS", "FACT_TRIPLE"],
                    evidence=[
                        Evidence.create(
                            description="서증 Fact Triple 일자 충돌",
                            grade=EvidenceGrade.C,
                            document_id=doc.document_id,
                            page=b.page,
                            excerpt=f"[{a.page}쪽] {a.excerpt[:90]} ↔ [{b.page}쪽] {b.excerpt[:90]}",
                            supports=False,
                        )
                    ],
                )
            )

    # 2. 동일 대상의 인과 단계 선후 역전 (DRAFT <= SEND <= RECEIVE, CONTRACT <= TERMINATE, WORK_START <= WORK_END)
    by_target: Dict[str, List[FactTriple]] = defaultdict(list)
    for t in active_all:
        if t.target_object and t.date_iso and not t.is_partial_or_mod:
            by_target[t.target_object].append(t)

    _CAUSAL_PAIRS = (
        ("DRAFT", "SEND"),
        ("SEND", "RECEIVE"),
        ("CONTRACT", "TERMINATE"),
        ("WORK_START", "WORK_END"),
    )
    for target, group in by_target.items():
        explicit_subjs = {t.subject for t in group if t.subject != "UNSPECIFIED"}
        if len(explicit_subjs) > 1:
            continue
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
    """2단계(프로젝트 교차): 복수 문서 간 동일 (action_stage, target_object) 및 (action_stage, exhibit_ref) 충돌을 검산한다."""
    findings: List[Finding] = []
    by_key: Dict[Tuple[str, str, str], List[Tuple[NormalizedDocument, FactTriple]]] = defaultdict(list)

    for doc, triples in doc_triples:
        for t in triples:
            if t.attribution == "SELF" and t.modality == "ASSERTED" and not t.is_partial_or_mod:
                if t.target_object:
                    by_key[("TARGET", t.action_stage, t.target_object)].append((doc, t))
                elif t.exhibit_ref:
                    by_key[("EXHIBIT", t.action_stage, t.exhibit_ref)].append((doc, t))

    for (kind, stage, anchor_name), items in by_key.items():
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
                    title=f"문서 간 구조화 사실 일자 불일치: {anchor_name}({stage}) {t1.date_iso} ↔ {t2.date_iso}",
                    detail=(
                        f"{doc_map[d1].filename}과 {doc_map[d2].filename}에서 동일 대상 '{anchor_name}'의 "
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
                        "target_object": anchor_name,
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

        if kind == "TARGET" and anchor_name in _LUMP_SUM_TARGETS and stage in ("CONTRACT", "PAY"):
            doc_amts: List[Tuple[str, FactTriple]] = []
            for did, d_items in by_doc.items():
                amts = {t.amount_krw for t in d_items if t.amount_krw}
                if len(amts) == 1:
                    t_rep = next(t for t in d_items if t.amount_krw)
                    doc_amts.append((did, t_rep))
            distinct_amts = {t.amount_krw for _, t in doc_amts}
            if len(distinct_amts) >= 2:
                (d1, t1), (d2, t2) = doc_amts[0], next((d, t) for d, t in doc_amts[1:] if t.amount_krw != doc_amts[0][1].amount_krw)
                findings.append(
                    Finding.create(
                        type=FindingType.FACT_CONTRADICTION,
                        status=VerificationStatus.SUSPICIOUS,
                        severity=Severity.MEDIUM,
                        evidence_grade=EvidenceGrade.C,
                        title=f"문서 간 구조화 사실 금액 불일치: {anchor_name}({stage}) {t1.amount_krw:,}원 ↔ {t2.amount_krw:,}원",
                        detail=(
                            f"{doc_map[d1].filename}과 {doc_map[d2].filename}에서 동일 대상 '{anchor_name}'의 "
                            f"행위 단계({stage}) 금액이 서로 다르다({t1.amount_krw:,}원 vs {t2.amount_krw:,}원)."
                        ),
                        document_id=d1,
                        page=t1.page,
                        engine=ENGINE_NAME,
                        confidence=0.72,
                        confidence_features={
                            "deterministic_rule": True,
                            "rule_id": "FACT_TRIPLE.CROSS_DOC_AMOUNT_CONFLICT",
                            "action_stage": stage,
                            "target_object": anchor_name,
                            "sources": [{"document_id": d1}, {"document_id": d2}],
                            "values": [t1.amount_krw, t2.amount_krw],
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
