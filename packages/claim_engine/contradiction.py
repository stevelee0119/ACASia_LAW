"""Compare like assertions, retaining uncertainty and source locations."""
from __future__ import annotations

from collections import defaultdict
from copy import copy
from dataclasses import fields
from datetime import date
from decimal import Decimal, InvalidOperation
from itertools import combinations
import re
from typing import Any

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Claim, Evidence, Event, Finding
from .structure import structure_claim_text

ENGINE_NAME = "claim_engine.contradiction"
EVENT_LABELS = {"INCORPORATION": "설립", "CONTRACT": "계약", "TERMINATION": "종료",
                "PAYMENT": "지급", "INCIDENT": "사건 발생", "FILING": "제출", "DECISION": "결정"}
ORDER_RULES = [
    ("INCORPORATION", "CONTRACT", "설립일과 계약 당시 당사자의 지위를 확인하세요."),
    ("CONTRACT", "TERMINATION", "종료가 같은 계약에 관한 것인지 확인하세요."),
    ("CONTRACT", "PAYMENT", "선지급 또는 앞선 구두 합의가 있는지 확인하세요."),
    ("INCIDENT", "FILING", "제출 서류가 어느 사건에 관한 것인지 확인하세요."),
    ("FILING", "DECISION", "제출과 결정이 같은 절차에 관한 것인지 확인하세요."),
]


def _structured(event: Event) -> Event:
    """Apply conservative surface flags even to legacy callers constructing Events."""
    result = copy(event)
    lexical = structure_claim_text(event.description)
    for name in ("negated", "hearsay", "quoted", "conditional", "alternative"):
        setattr(result, name, getattr(result, name) or lexical[name])
    for name in ("transaction_id", "event_identity", "object_id", "speaker_id", "target_id",
                 "amount", "currency", "amount_scope", "action"):
        if getattr(result, name) is None:
            setattr(result, name, lexical[name])
    if lexical["stance"] not in {"ASSERTED", "UNSPECIFIED"}:
        result.stance = lexical["stance"]
    elif result.stance == "UNSPECIFIED":
        result.stance = "ASSERTED"
    return result


def _assertion(event: Event) -> bool:
    return (event.stance == "ASSERTED" and not any((event.negated, event.hearsay,
            event.quoted, event.conditional, event.alternative)))


def _identity(event: Event) -> tuple:
    """An exhibit label never proves transaction identity."""
    return (event.project_id, event.transaction_id) if event.transaction_id else ()


def _compatible(first: Event, second: Event) -> bool:
    if not _identity(first) or _identity(first) != _identity(second):
        return False
    for name in ("speaker_id", "target_id", "object_id"):
        left, right = getattr(first, name), getattr(second, name)
        if left and right and left != right:
            return False
    return True


def _evidence(event: Event) -> Evidence:
    return Evidence.create("문서의 주장 내용 (독립적인 사실 입증은 아님)", EvidenceGrade.C,
                           document_id=event.document_id, block_id=event.block_id,
                           page=event.page, span=event.span, excerpt=event.description)


def _location(event: Event) -> dict[str, Any]:
    return {name: getattr(event, name) for name in (
        "event_id", "document_id", "block_id", "page", "span", "project_id",
        "source_run_id", "source_document_sha256", "event_identity", "transaction_id",
    )}


def analyze_timeline(events: list[Event]) -> list[Finding]:
    """Return contextual ordering candidates, never an automatic legal impossibility."""
    by_kind: dict[str, list[Event]] = defaultdict(list)
    for source in events:
        event = _structured(source)
        if event.date and _assertion(event) and event.project_id and event.transaction_id:
            by_kind[event.event_kind].append(event)
    findings = []
    for first_kind, second_kind, rule in ORDER_RULES:
        for first in by_kind[first_kind]:
            for second in by_kind[second_kind]:
                if not _compatible(first, second) or second.date >= first.date:
                    continue
                findings.append(Finding.create(
                    type=FindingType.TIMELINE_CONTRADICTION, status=VerificationStatus.UNVERIFIED,
                    severity=Severity.MEDIUM, evidence_grade=EvidenceGrade.C,
                    title=f"날짜 순서 검토: {EVENT_LABELS[second_kind]}이(가) {EVENT_LABELS[first_kind]}보다 앞섬", detail=rule,
                    document_id=second.document_id, block_id=second.block_id, page=second.page,
                    engine=ENGINE_NAME, advisory_only=True, tags=["TIMELINE", "CONTEXT_REQUIRED"],
                    confidence_features={"identity": list(_identity(first)), "rule": rule,
                                         "sources": [_location(first), _location(second)],
                                         "extraction_confidence_is_probability": False},
                    evidence=[_evidence(first), _evidence(second)],
                ))
    return findings


def _comparable_amount(event: Event) -> Decimal | None:
    if not event.amount or not event.currency:
        return None
    try:
        value = Decimal(event.amount)
        return value if value.is_finite() else None
    except InvalidOperation:
        return None


def cross_document_contradictions(events_by_document: dict[str, list[Event]]) -> list[Finding]:
    """Compare individual events; transaction-only contract matches stay candidates.

    Payments without an event_identity are never compared: one transaction can
    contain many installments. Results describe conflicting assertions, not proof.
    """
    groups: dict[tuple, list[Event]] = defaultdict(list)
    for document_id, events in events_by_document.items():
        for source in events:
            event = _structured(source)
            if source.document_id and source.document_id != document_id:
                raise ValueError("Event document_id conflicts with the document group")
            event.document_id = document_id
            if not _assertion(event) or not _identity(event) or event.event_kind == "GENERIC":
                continue
            if not event.event_identity and event.event_kind != "CONTRACT":
                continue
            groups[(_identity(event), event.event_kind, event.event_identity)].append(event)
    findings = []
    for (_, kind, event_identity), events in groups.items():
        for first, second in combinations(events, 2):
            if first.document_id == second.document_id or not _compatible(first, second):
                continue
            differences = {}
            if first.date and second.date and first.date != second.date:
                differences["date"] = [first.date.isoformat(), second.date.isoformat()]
            left, right = _comparable_amount(first), _comparable_amount(second)
            if (event_identity and first.currency == second.currency
                    and first.amount_scope == second.amount_scope and left is not None and right is not None
                    and left != right):
                differences["amount"] = [str(left), str(right)]
            if not differences:
                continue
            identified = bool(event_identity and first.project_id and first.speaker_id and first.target_id
                              and first.speaker_id == second.speaker_id and first.target_id == second.target_id)
            findings.append(Finding.create(
                type=FindingType.CROSS_DOCUMENT_CONTRADICTION, status=VerificationStatus.UNVERIFIED,
                severity=Severity.MEDIUM, evidence_grade=EvidenceGrade.C,
                title=f"{EVENT_LABELS.get(kind, kind)}에 관한 문서의 기재가 다릅니다", detail=(
                    "식별자가 일치하는 같은 행위에 서로 다른 값이 기재되어 있습니다. 각 원문의 주장을 확인하세요."
                    if identified else "불일치 후보입니다. 같은 사건·당사자·개별 행위인지 먼저 확인하세요."),
                engine=ENGINE_NAME, document_id=second.document_id, block_id=second.block_id, page=second.page,
                advisory_only=True, tags=["CROSS_DOCUMENT", "ASSERTION_CONFLICT" if identified else "IDENTITY_UNCERTAIN"],
                confidence_features={"comparison_scope": "EXPLICIT_EVENT" if identified else "CANDIDATE",
                                     "differences": differences, "sources": [_location(first), _location(second)],
                                     "evidence_relationship": "UNASSESSED"},
                evidence=[_evidence(first), _evidence(second)],
            ))
    return findings


def claim_contradictions(claims: list[Claim], *, project_id: str) -> list[Finding]:
    """Adapt structured claims to comparison, within one explicit project."""
    if not project_id:
        raise ValueError("project_id is required")
    by_document: dict[str, list[Event]] = defaultdict(list)
    event_fields = {field.name for field in fields(Event)} - {"event_id", "date", "description", "event_kind"}
    for claim in claims:
        if claim.project_id != project_id or not claim.document_id or not claim.action:
            continue
        try:
            claimed_date = date.fromisoformat(claim.asserted_date) if claim.asserted_date else None
        except ValueError:
            continue
        kwargs = {name: getattr(claim, name) for name in event_fields if hasattr(claim, name)}
        by_document[claim.document_id].append(Event(
            event_id=claim.claim_id, date=claimed_date, description=claim.text,
            event_kind=claim.action, **kwargs))
    return cross_document_contradictions(by_document)


_WEEKDAYS_KR = ("월", "화", "수", "목", "금", "토", "일")
_TIMELINE_ATTACHMENT_RE = re.compile(
    r"(?:별첨|별지|첨부)\s*제?\s*\d+\s*호?(?:\s*의\s*\d+)*"
    r"(?:\s*[,\(]?\s*(?:제\s*|[pP]\.\s*)?\d+(?:\s*[~～\-–]\s*\d+)?\s*(?:쪽|면|페이지|[pP](?![A-Za-z]))\s*\)?)?"
)


def _format_timeline_date(d: date) -> str:
    return f"{d.year % 100:02d}.{d.month}.{d.day}.({_WEEKDAYS_KR[d.weekday()]})"


def _format_timeline_evidence(event: Event) -> str:
    from .exhibits import parse_exhibits

    found: list[str] = []
    for ref in event.evidence_references or []:
        raw = " ".join(str(ref.get("raw_text") or "").split()).strip()
        if raw and raw not in found:
            found.append(raw)
    if found:
        return ", ".join(found)

    desc = event.description or ""
    spans_and_labels: list[tuple[int, int, str]] = []
    seen_spans: set[tuple[int, int]] = set()
    for ref in parse_exhibits(desc):
        span = tuple(ref["span"])
        if span in seen_spans:
            continue
        seen_spans.add(span)
        label = " ".join(str(ref.get("label") or "").split()).strip()
        if label:
            spans_and_labels.append((span[0], span[1], label))

    for match in _TIMELINE_ATTACHMENT_RE.finditer(desc):
        m_start, m_end = match.start(), match.end()
        if any(not (m_end <= s0 or m_start >= s1) for s0, s1 in seen_spans):
            continue
        text = " ".join(match.group(0).split()).strip(" ,.;:()[]{}")
        if text:
            spans_and_labels.append((m_start, m_end, text))

    spans_and_labels.sort(key=lambda item: (item[0], item[1]))
    for _, _, label in spans_and_labels:
        if label not in found:
            found.append(label)
    return ", ".join(found) if found else "[근거 미작성]"


def _timeline_dedup_key(event: Event, desc: str, evidence_summary: str) -> tuple[Any, ...]:
    date_key = event.date.isoformat() if event.date else ""
    has_doc_id = bool(event.document_id or event.source_document_sha256)
    has_exact_loc = (event.span is not None) or bool(event.block_id and event.page is not None)
    has_complete_source = has_doc_id and has_exact_loc
    source_key: tuple[Any, ...] = (
        (
            event.document_id or "",
            event.source_document_sha256 or "",
            event.block_id or "",
            event.page if event.page is not None else -1,
            tuple(event.span) if event.span is not None else (),
        )
        if has_complete_source
        else ("__incomplete_source__", event.event_id)
    )
    fact_key = (
        event.event_identity or "",
        event.transaction_id or "",
        event.action or "",
        event.speaker_id or "",
        event.speaker_text or "",
        event.target_id or "",
        event.target_text or "",
        bool(event.negated),
        bool(event.hearsay),
        bool(event.quoted),
        bool(event.conditional),
        bool(event.alternative),
        event.stance or "",
        evidence_summary,
    )
    return (date_key, desc, source_key, fact_key)


def build_timeline(events: list[Event]) -> list[dict[str, Any]]:
    ordered = sorted(
        (e for e in events if e.date),
        key=lambda e: (e.date, e.document_id or "", e.page or 0, (e.span or (0, 0))[0]),
    )
    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for event in ordered:
        desc = " ".join((event.description or "").split())
        ev_summary = _format_timeline_evidence(event)
        key = _timeline_dedup_key(event, desc, ev_summary)
        if key in seen:
            continue
        seen.add(key)
        item = event.to_dict()
        item["formatted_date"] = _format_timeline_date(event.date)
        item["formatted_content"] = desc
        item["evidence_summary"] = ev_summary
        out.append(item)
    return out
