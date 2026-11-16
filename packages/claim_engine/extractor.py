"""제11.1장 Claim Extraction, 제11.3장 Entity Resolution, 제11.4장 Timeline.

Rule 기반으로 먼저 구조화하고, 의미 판단이 필요한 부분만 LLM에 위임한다.
단순 의견(OPINION)은 사실 검증 대상에서 기본 제외한다.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Dict, List, Optional, Tuple

from packages.common.enums import ClaimType, EntityType
from packages.common.schemas import Claim, Citation, Entity, Event, NormalizedDocument
from packages.common.textutil import sentences

from .calculation import parse_amounts
from .classification import (classify_sentence, document_kind, segment_kind, assertion_mode,
                             event_role, NOMINAL_FACT_RE, OPINION_RE as EXPLICIT_OPINION_RE)
from .entity_resolution import resolve_entities
from .structure import extract_evidence_references, structure_claim_text

# --- Claim 유형 판별 규칙 ----------------------------------------------------
OPINION_RE = re.compile(r"(생각한다|사료된다|보아야\s*한다|타당하다|부당하다|바람직하다|판단된다|여겨진다|믿는다)")
LEGAL_RULE_RE = re.compile(r"(제\s*\d+\s*조|법률\s*제\s*\d+\s*호|규정하고\s*있다|정하고\s*있다|따르면)")
# 판례 취지 서술: 경어체(판시하였습니다, 설시하였습니다 등) 포함
CASE_HOLDING_RE = re.compile(r"(판시하였다|판시한|판결하였다|설시하였다|입장이다|취지이다|보고\s*있다|판시하였습니다|판시했습니다|판결하였습니다|설시하였습니다)")
DOCUMENT_EXISTENCE_RE = re.compile(r"(갑\s*제?\s*\d+\s*호증|을\s*제?\s*\d+\s*호증|증\s*제?\s*\d+\s*호|첨부(?:한|된|하였습니다)|제출(?:한|하였다|하였습니다))")
CALCULATION_RE = re.compile(r"(합계|총액|이자|지연손해금|비율|%|원을\s*지급)")
INTERPRETATION_RE = re.compile(r"(해석된다|해석하여야|유권해석|법령해석)")
# 사실 서술: 평서문 및 경어체/존댓말 과거 완료 서술(체결하였습니다, 납품하였습니다, 공제하였습니다 등) 포함
FACT_RE = re.compile(
    r"(?:(?:였|었|았|했|됐)(?:다|습니다))|"
    r"(하였다|했다|이다|였다|당하였다|지급하였다|체결하였다|발생하였다|근무하였다|"
    r"하였습니다|했습니다|입니다|였습니다|이었습니다|되었습니다|됐습니다|공제하였습니다|납품하였습니다|"
    r"마무리되었습니다|종료되었습니다|확인되었습니다|통보하였습니다|협의하였습니다|요청하였습니다)"
)

DATE_RE = re.compile(
    r"(?P<y>(?:19|20)\d{2})\s*[.\-년]\s*(?P<m>\d{1,2})\s*[.\-월]\s*(?P<d>\d{1,2})\s*[일]?"
)
EVENT_KIND_RE = [
    ("CONTRACT", re.compile(r"(계약(?:을)?\s*체결|약정|합의)")),
    ("TERMINATION", re.compile(r"(해지|해제|종료|파기)")),
    ("PAYMENT", re.compile(r"(지급|송금|입금|변제)")),
    ("INCORPORATION", re.compile(r"(설립|법인등기|개업)")),
    ("FILING", re.compile(r"(제출|접수|신청|고소|고발|기소)")),
    ("DECISION", re.compile(r"(선고|판결|결정|처분)")),
    ("INCIDENT", re.compile(r"(사고|발생|폭행|상해|침해|위반)")),
]

PARTY_ROLE_WORDS = {
    "원고", "피고", "피고인", "참고인", "피의자", "증인", "고소인", "고발인",
    "신청인", "피신청인", "채권자", "채무자", "소외", "망",
}
ORG_WORDS = {"주식회사", "유한회사", "합자회사", "재단법인", "사단법인", "법인"}

# 당사자 표기 바로 뒤에 올 수 있으나 사람 이름이 아닌 토큰.
# 조사가 그대로 이름으로 잡히면 "피고는 원고에게" 에서 '에게'가 PERSON이 된다.
NON_NAME_TOKENS = {
    # 조사·어미
    "에게", "에게서", "으로", "에서", "부터", "까지", "에는", "에도", "라고", "이라",
    "한테", "께서", "께는", "이며", "이고", "라는", "이라는",
    # 당사자 표기 뒤에 흔히 오는 일반명사
    "제출", "주장", "진술", "청구", "답변", "준비", "서면", "대리", "본인", "측은", "측이",
    "소송", "대리인", "당사자", "사건", "회사", "법인", "명의", "프로젝트", "계약", "합의",
    "이행", "손해", "배상", "지급", "반환", "확인", "신청", "요청", "통지", "최고",
}

# 당사자 표기 뒤의 이름. 뒤에 법인 표시가 오면 사람 이름이 아니다.
# 이름 뒤 조사는 선택이 아니라 '조사 또는 경계'로 못박는다.
PERSON_CONTEXT_RE = re.compile(
    r"(?:원고|피고인|피고|참고인|피의자|증인|고소인|고발인|신청인|피신청인|채권자|채무자|망|소외)\s*"
    r"(?!주식회사|유한회사|합자회사|재단법인|사단법인)"
    r"([가-힣]{2,4}?)(?:은|는|이|가|을|를|과|와|의|에게|에|도)?(?![가-힣])"
)


def is_person_name(token: str) -> bool:
    """당사자 표기 뒤에 잡힌 토큰이 사람 이름일 수 있는지 본다."""
    name = (token or "").strip()
    if len(name) < 2 or len(name) > 4:
        return False
    if name in NON_NAME_TOKENS:
        return False
    # 조사만으로 이루어진 토큰은 이름이 아니다
    if all(ch in "은는이가을를과와의에도로서만며고" for ch in name):
        return False
    return True
COMPANY_CONTEXT_RE = re.compile(
    r"(?<![가-힣])([가-힣A-Za-z0-9]{2,10})\s*(?:주식회사|㈜)|(?:주식회사|㈜)\s+([가-힣A-Za-z0-9]{1,20})"
)
COURT_CONTEXT_RE = re.compile(r"([가-힣]{2,10}(?:지방|고등|가정|행정|회생|특허|군사)?법원|대법원|헌법재판소)")


def classify_claim(sentence: str) -> ClaimType:
    if assertion_mode(sentence) in ("HYPOTHETICAL", "ALTERNATIVE", "QUOTED_OTHER"):
        return ClaimType.OPINION
    if OPINION_RE.search(sentence) or EXPLICIT_OPINION_RE.search(sentence):
        return ClaimType.OPINION
    if CASE_HOLDING_RE.search(sentence):
        return ClaimType.CASE_HOLDING
    if INTERPRETATION_RE.search(sentence):
        return ClaimType.LEGAL_INTERPRETATION
    if LEGAL_RULE_RE.search(sentence):
        return ClaimType.LEGAL_RULE
    if DOCUMENT_EXISTENCE_RE.search(sentence):
        return ClaimType.DOCUMENT_EXISTENCE
    if CALCULATION_RE.search(sentence) and parse_amounts(sentence):
        return ClaimType.CALCULATION
    if FACT_RE.search(sentence) or NOMINAL_FACT_RE.search(sentence):
        return ClaimType.FACT
    return ClaimType.OPINION


def partial_date_candidates(sentence, block_text):
    """Keep omitted years as contextual candidates, never confirmed event dates."""
    full = [m.span() for m in DATE_RE.finditer(sentence)]
    years = sorted({int(m["y"]) for m in DATE_RE.finditer(block_text)})
    candidates = []
    for match in re.finditer(r"(?<![\d.])(?P<m>\d{1,2})\s*[.월]\s*(?P<d>\d{1,2})\s*[.일]", sentence):
        if any(start <= match.start() < end for start, end in full):
            continue
        values = []
        for year in years:
            try:
                values.append(date(year, int(match["m"]), int(match["d"])).isoformat())
            except ValueError:
                continue
        candidates.append({"raw_text": match.group(), "span": list(match.span()), "candidate_dates": values,
            "status": "CONTEXT_CANDIDATE" if len(values) == 1 else "UNRESOLVED",
            "basis": "SAME_BLOCK_EXPLICIT_YEARS", "confirmed": False})
    return candidates


def extract_claims(doc: NormalizedDocument, citations: Optional[List[Citation]] = None,
                   *, project_id: Optional[str] = None, source_run_id: Optional[str] = None) -> List[Claim]:
    """표시 본문에서 Claim을 추출한다."""
    citations = citations or []
    by_block: Dict[str, List[Citation]] = {}
    for citation in citations:
        if citation.block_id:
            by_block.setdefault(citation.block_id, []).append(citation)

    claims: List[Claim] = []
    kind = document_kind(b.text for b in doc.prose_blocks()[:8])
    for block in doc.prose_blocks():
        cursor = 0
        for sentence in sentences(block.text):
            start = block.text.find(sentence, cursor)
            if start < 0:
                continue
            cursor = start + len(sentence)
            if len(sentence) < 10:
                continue
            segment = segment_kind(sentence, block_type=block.block_type, source_layer=block.source_layer,
                                   table_ref=block.attributes.get("table_ref"))
            claim_type = classify_sentence(sentence, segment, classify_claim)
            related = [
                c.citation_id
                for c in by_block.get(block.block_id, [])
                if c.raw_text and c.raw_text[:12] in sentence
            ]
            claims.append(
                Claim.create(
                    claim_type,
                    sentence,
                    document_id=doc.document_id,
                    block_id=block.block_id,
                    page=block.page,
                    citation_ids=related,
                    attributes={"length": len(sentence), "extraction_method": "LEXICAL_RULES",
                                "evidence_relationship": "UNASSESSED",
                                # 제목·안내·인용·OCR·표 구간을 본문과 구분해 남긴다.
                                "segment_kind": segment, "document_kind": kind,
                                "assertion_mode": assertion_mode(sentence), "event_role": event_role(sentence),
                                "partial_date_candidates": partial_date_candidates(sentence, block.text),
                                "classification_status": ("UNCLASSIFIED" if claim_type == ClaimType.OPINION
                                    and assertion_mode(sentence) == "ASSERTED"
                                    and not (OPINION_RE.search(sentence) or EXPLICIT_OPINION_RE.search(sentence))
                                    else "CLASSIFIED"),
                                "verification_target": claim_type not in (
                                    ClaimType.DOCUMENT_META, ClaimType.ADVERSARIAL_INSTRUCTION)},
                    project_id=project_id or doc.metadata.get("project_id"),
                    source_run_id=source_run_id,
                    source_document_sha256=doc.sha256,
                    span=(start, cursor),
                    evidence_references=extract_evidence_references(
                        sentence, document_id=doc.document_id, block_id=block.block_id,
                        page=block.page, source_run_id=source_run_id,
                        document_sha256=doc.sha256, offset=start),
                    **structure_claim_text(sentence),
                )
            )
    return claims


def extract_entities(doc: NormalizedDocument, *, project_id: Optional[str] = None) -> List[Entity]:
    """사람·법인·법원 등을 추출한다. 동일 대상 통합은 resolve_entities가 담당한다."""
    found: Dict[Tuple[str, str], Entity] = {}

    def add(entity_type: EntityType, name: str, block, span: Tuple[int, int]) -> None:
        name = name.strip()
        if not name:
            return
        key = (str(entity_type), name)
        entity = found.get(key)
        if entity is None:
            entity = Entity.create(entity_type, name, project_id=project_id or doc.metadata.get("project_id"),
                                   needs_user_confirmation=True, resolution_basis="DOCUMENT_MENTIONS_ONLY")
            found[key] = entity
        entity.mentions.append(
            {"document_id": doc.document_id, "block_id": block.block_id, "page": block.page, "span": list(span)}
        )

    for block in doc.prose_blocks():
        for m in PERSON_CONTEXT_RE.finditer(block.text):
            if not is_person_name(m.group(1)):
                continue
            add(EntityType.PERSON, m.group(1), block, (m.start(1), m.end(1)))
        for m in COMPANY_CONTEXT_RE.finditer(block.text):
            name = (m.group(1) or m.group(2) or "").strip()
            if name in PARTY_ROLE_WORDS or name in ORG_WORDS:
                continue
            add(EntityType.COMPANY, name, block, (m.start(), m.end()))
        for m in COURT_CONTEXT_RE.finditer(block.text):
            add(EntityType.COURT, m.group(1), block, (m.start(1), m.end(1)))
        for amount in parse_amounts(block.text, block_id=block.block_id, page=block.page):
            add(EntityType.MONEY, amount.raw, block, (amount.start, amount.end))
    return list(found.values())


_PRECEDENT_COURT_CUE_RE = re.compile(
    r"(?:대법원|헌법재판소|전원합의체|[가-힣]{1,10}(?:지방|고등|가정|행정|회생|특허|군사)법원)"
)
_PRECEDENT_AFTER_RE = re.compile(
    r"^\s*\.?\s*(?:선고\s*(?:전원합의체\s*)?\d{2,4}[가-힣]{1,4}\d+|자\s*\d{2,4}[가-힣]{1,4}\d+|"
    r"(?:전원합의체\s*)?\d{2,4}[가-힣]{1,4}\d+\s*(?:전원재판부\s*)?(?:판결|결정|명령))"
)
_PRECEDENT_AFTER_GENERIC_RE = re.compile(
    r"^\s*\.?\s*(?:(?:전원합의체|전원재판부)\s*)?(?:판결|결정|명령|선고(?![가-힣]))"
)
_INSTANT_CASE_COURT_RE = re.compile(
    r"이\s*사건\s*(?:원심|제?1심|제?2심|항소심|상고심|소송|사건)"
)
_CASE_CITATION_NUM_RE = re.compile(r"\d{2,4}[가-힣]{1,4}\d+")
_STATUTE_AFTER_ACTION_RE = re.compile(
    r"^\s*\.?\s*(?:(?:,|·)\s*)?(?:(?:자\s*)?(?:법률|대통령령|총리령|부령|시행령|시행규칙|조례)(?:\s*제\s*\d+\s*호|\s*(?:일부|전부)?\s*개정|\s*제정|\s*공포|\s*시행|로|으로|,)|"
    r"(?:일부\s*개정|전부\s*개정|제정|개정|신설|삭제|공포)(?:된|되어|한|으로|법|조항)?)"
)
_STATUTE_EFFECTIVE_RE = re.compile(
    r"^\s*\.?\s*(?:부터\s*)?(?:시행(?:되었|된|되|하|일)?|개정(?:되었|된|되)|공포(?:되었|된|되))"
)
_STATUTE_CUE_RE = re.compile(
    r"(?:법률\s*제\s*\d+\s*호|대통령령\s*제\s*\d+\s*호|총리령\s*제\s*\d+\s*호|부령\s*제\s*\d+\s*호|"
    r"[가-힣]+(?:법률|법|시행령|시행규칙|부칙|조례|규칙)|제\s*\d+\s*조)"
)
_PARTY_FACT_VERB_RE = re.compile(
    r"(?:체결|약정|합의|지급|송금|입금|변제|교부|설립|개업|접수|제출|신청|고소|고발|기소|"
    r"해지|해제|종료|파기|통지|통보|발송|수령|근무|입사|퇴직|퇴사|사망|출생|사고|발생|"
    r"폭행|상해|침해|납품|인도)"
)


def _is_legal_authority_date(sentence: str, match_start: int, match_end: int) -> bool:
    """판례 선고·결정일 또는 법령 제정·개정·시행일 등 법적 근거 날짜인지 판별한다."""
    before = sentence[max(0, match_start - 35):match_start]
    after = sentence[match_end:]

    # 1) 판례/헌재 결정 인용 날짜 ("대법원 2021. 5. 13. 선고 2020다12345 판결", "2019. 7. 18.자 2018헌마100")
    if _PRECEDENT_AFTER_RE.match(after):
        return True
    if _PRECEDENT_COURT_CUE_RE.search(before) and _PRECEDENT_AFTER_GENERIC_RE.match(after):
        if _INSTANT_CASE_COURT_RE.search(before) and not _CASE_CITATION_NUM_RE.search(after[:30]):
            return False
        return True

    # 2) 법령 제정·개정·공포·시행 날짜
    if _STATUTE_AFTER_ACTION_RE.match(after):
        return True
    if _STATUTE_CUE_RE.search(before) and _STATUTE_EFFECTIVE_RE.match(after):
        return True

    return False


def _has_party_fact_cue(sentence: str) -> bool:
    """문장에 당사자 사이의 구체적 사건·행위 표지가 있는지 본다."""
    if any(regex.search(sentence) for name, regex in EVENT_KIND_RE if name != "DECISION"):
        return True
    return bool(_PARTY_FACT_VERB_RE.search(sentence))


def extract_events(doc: NormalizedDocument, *, project_id: Optional[str] = None,
                   source_run_id: Optional[str] = None) -> List[Event]:
    """제11.4장 Timeline 입력. 판례·법령 인용 날짜를 걸러내고 사건 사실관계를 중심으로 추출한다."""
    events: List[Event] = []
    for block in doc.prose_blocks():
        cursor = 0
        for sentence in sentences(block.text):
            start = block.text.find(sentence, cursor)
            if start < 0:
                continue
            cursor = start + len(sentence)
            has_fact_cue = _has_party_fact_cue(sentence)
            if not has_fact_cue and (
                CASE_HOLDING_RE.search(sentence)
                or classify_claim(sentence) in (ClaimType.CASE_HOLDING, ClaimType.LEGAL_RULE, ClaimType.LEGAL_INTERPRETATION)
            ):
                continue
            structure = structure_claim_text(sentence)
            structure.pop("asserted_date")
            for m in DATE_RE.finditer(sentence):
                if _is_legal_authority_date(sentence, m.start(), m.end()):
                    continue
                try:
                    value = date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
                except ValueError:
                    continue
                kind = "GENERIC"
                for name, regex in EVENT_KIND_RE:
                    if regex.search(sentence):
                        kind = name
                        break
                events.append(
                    Event.create(
                        value,
                        sentence.strip()[:300],
                        document_id=doc.document_id,
                        block_id=block.block_id,
                        page=block.page,
                        event_kind=kind,
                        raw_date_text=m.group(0),
                        project_id=project_id or doc.metadata.get("project_id"),
                        source_run_id=source_run_id, source_document_sha256=doc.sha256,
                        span=(start, cursor),
                        evidence_references=extract_evidence_references(
                            sentence, document_id=doc.document_id, block_id=block.block_id,
                            page=block.page, source_run_id=source_run_id,
                            document_sha256=doc.sha256, offset=start),
                        **structure,
                    )
                )
    return events
