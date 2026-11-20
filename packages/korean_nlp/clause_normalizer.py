"""Korean Legal Clause Normalizer (P1 PR-05).

Decomposes Korean legal sentences into structured `NormalizedClause` records with:
- Exact reading-text offsets (`reading_span`)
- Speaker role & attribution (`AUTHOR` / `OPPONENT` / `COURT` / `THIRD_PARTY` / `UNKNOWN`)
- Polarity with double-negation resolution (`ASSERTED` / `NEGATED` / `DOUBLE_NEGATED_ASSERTED`)
- Modality (`DEFINITIVE` / `MANDATORY` / `PERMISSIVE` / `HYPOTHETICAL` / `ALTERNATIVE` / `INTERROGATIVE`)
- Temporal aspect (`PAST_FACT` / `PRESENT_STATE` / `FUTURE_PLAN` / `ATEMPORAL_RULE`)
- Discourse relation (`MAIN` / `CONDITION` / `CONCESSION` / `CAUSE` / `EXCEPTION_PROVISO`)
- Explicit uncertainty (`parse_confidence`, `uncertainty_reasons`)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from packages.document_engine.reading_text import build_reading_text, sentence_bounds

from .tokenizer import LegalTokenizer, get_tokenizer


# --- Clause boundary & grammatical markers ---------------------------------------------
_CLAUSE_SPLIT_RE = re.compile(
    r"(?:으므로|므로|기\s*때문에|지만|는데|으나|더라도|하더라도|라면|다면|한다면|된다면|"
    r"(?<=[가-힣])(?:았|었|였)(?:고|으며)\s+|"
    r"(?:지|하지|되지)\s*않(?:고|으며)\s+|"
    r"(?<!\d),|;)\s*"
)
_QUOTED_BREAK_RE = re.compile(
    r"(?:라고|다고|라는|다는)\s*(?:취지로\s*)?(?:주장|항변|다투|판시|설시|판단)"
)

# Speaker / subject markers
_OPPONENT_SURFACE_RE = re.compile(
    r"(?:원고|피고|상대방|청구인|피청구인|신청인|피신청인|항소인|피항소인|상고인|피상고인|채권자|채무자|피고인)"
    r"(?:\s*측)?(?:\s*(?:은|는|이|가|측은|측에서는))?"
)
_COURT_SURFACE_RE = re.compile(
    r"(?:대법원|헌법재판소|헌재|고등법원|지방법원|행정법원|원심|법원|재판부|다수의견|반대의견|별개의견|전원합의체)"
    r"(?:은|는|이|가|에서)?"
)
_AUTHOR_SURFACE_RE = re.compile(
    r"(?:본\s*원고|본\s*피고|당\s*소송대리인|신청인\s*본인|작성자|당사|본인)(?:은|는|이|가)?"
)

# Attribution verbs
_OPPONENT_REPORT_VERB_RE = re.compile(
    r"(?:라고|다고|라는|다는|고)\s*(?:취지로\s*)?(?:주장|항변|다투|반박|요구|진술)"
    r"(?:하나|하지만|하였으나|하였지만|하는데|하고\s*있으나|합니다만|하였는바|하는바|한다|하였다|했다)|"
    r"(?:라는|다는)\s*(?:[가-힣]+(?:의|측의)\s*)?(?:주장|항변)(?:은|는)\s*"
    r"(?:이유\s*없|받아들일\s*수\s*없|부당|잘못|근거\s*없|타당하지\s*않)"
)
_COURT_REPORT_VERB_RE = re.compile(
    r"(?:라고|다고|라는|다는|고)\s*(?:취지로\s*)?(?:판시|설시|판단|보았|보고|본다|결정|해석|밝혔|선고)"
    r"(?:하였|했|한\s*바|한다|하고|하였다|했다)?|"
    r"판시(?:하였|했|한\s*바|한다|하고)|취지로\s*판단"
)
_CASE_CITE_MARKER_RE = re.compile(r"(?:19|20)?\d{2}\s*(?:헌[가-힣]|[가-힣]{1,3})\s*\d{2,6}|선고\s|판결|결정")

# Negation markers (avoid matching inside positive words like '아니라' vs '아니한다')
_NEGATION_RE = re.compile(
    r"아니(?:다|라|며|고|므로|어서|었|기|한다|하다|하고|하였|함|오|지|에요)|아닙|아님|아닐|"
    r"(?:하지|되지|지|치)(?:는|도|만)?\s*(?:않|아니하|못하)|"
    r"(?:할|볼|될|인정할|인정될|단정할|말할|해석할|이해할)\s*수\s*(?:는|도)?\s*없|"
    r"(?:가|이|은|는|도)?\s*없(?:다|고|으며|으나|으므로|어|었|음|지)|"
    r"불가(?:능)?(?:하|라|이)"
)

# Modality markers
_HYPOTHETICAL_LEAD_RE = re.compile(r"(?:설령|설사|가사|가령|만약|만일|혹시)\s")
_HYPOTHETICAL_TAIL_RE = re.compile(
    r"(?:하더라도|더라도|이라도|라도|라면|이라면|다면|한다면|된다면|하면|였을지|일지라도|ㄹ지라도)(?:\s|,|;|$)"
)
_ALTERNATIVE_RE = re.compile(r"(?:예비적(?:으로)?|또는|아니면|혹은|가정적(?:으로)?|선택적(?:으로)?)")
_INTERROGATIVE_RE = re.compile(r"(?:\?\s*$|인지\s*여부|하였는지|했는지|여부(?:에|가|를)|할\s*것인가|인가\s*$)")
_MANDATORY_RE = re.compile(r"(?:하여야\s*한다|해야\s*한다|의무가\s*있다|금지된다|불허된다|당연히\s*무효)")
_PERMISSIVE_RE = re.compile(r"(?:할\s*수\s*있다|허용된다|가능하다|재량에\s*속한다|무방하다)")

# Temporal markers
_FUTURE_PLAN_RE = re.compile(
    r"(?:할\s*예정|예정이다|예정임|추후\s*제출|제출할\s*것|지급하기로\s*한|지급할\s*예정|진행할\s*계획|향후\s)"
)
_PAST_FACT_RE = re.compile(r"(?:하였|했|였|었)(?:다|고|으며|으나|는데|으므로)|체결한|지급한|발생한")

# Discourse markers
_PROVISO_RE = re.compile(r"(?:다만|단,|그러나\s*예외적으로|특별한\s*사정이\s*없는\s*한)")
_CONCESSION_RE = re.compile(r"(?:비록|설령|설사|하더라도|더라도|불구하고|지만|으나)")
_CONDITION_RE = re.compile(r"(?:만약|만일|경우에는|라면|다면|한다면|한하여)")
_CAUSE_RE = re.compile(r"(?:때문에|으므로|므로|따라서|그러므로|이에\s*따라)")

# Quantifiers
_QUANTIFIER_RE = re.compile(
    r"어떠한\s*경우(?:에도|라도)|어떤\s*경우(?:에도|라도)|언제나|항상|예외\s*(?:없이|없는)|"
    r"모든\s*경우(?:에|에도)?|무조건|절대(?:로|적으로)?|원칙적으로|대체로|일반적으로"
)


@dataclass(frozen=True)
class NormalizedClause:
    clause_id: str
    sentence_index: int
    raw_text: str
    normalized_text: str
    reading_span: Tuple[int, int]
    block_id: Optional[str] = None
    page: Optional[int] = None
    speaker_role: str = "AUTHOR"          # AUTHOR | OPPONENT | COURT | THIRD_PARTY | UNKNOWN
    speaker_surface: Optional[str] = None
    attribution_type: str = "DIRECT_ASSERTION"  # DIRECT_ASSERTION | OPPONENT_SUMMARY | QUOTED_PRECEDENT | REPORTED_SPEECH
    polarity: str = "ASSERTED"            # ASSERTED | NEGATED | DOUBLE_NEGATED_ASSERTED
    negation_count: int = 0
    modality: str = "DEFINITIVE"          # DEFINITIVE | MANDATORY | PERMISSIVE | HYPOTHETICAL | ALTERNATIVE | INTERROGATIVE
    temporal_aspect: str = "ATEMPORAL_RULE"  # PAST_FACT | PRESENT_STATE | FUTURE_PLAN | ATEMPORAL_RULE
    discourse_relation: str = "MAIN"      # MAIN | CONDITION | CONCESSION | CAUSE | EXCEPTION_PROVISO
    predicate_lemma: Optional[str] = None
    quantifiers: List[str] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    parse_confidence: float = 1.0
    uncertainty_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _split_clauses_with_spans(sentence: str, base_offset: int) -> List[Tuple[str, Tuple[int, int]]]:
    """Split a sentence into sub-clauses while keeping exact character offsets."""
    if not sentence or not sentence.strip():
        return []
    breaks: List[int] = [0]
    for match in _CLAUSE_SPLIT_RE.finditer(sentence):
        end_pos = match.end()
        # Keep quotation verb phrases attached to the quoted clause
        prefix = sentence[breaks[-1]:end_pos]
        if match.group(0).startswith(",") and _QUOTED_BREAK_RE.search(prefix):
            breaks.append(end_pos)
        elif not match.group(0).startswith(","):
            breaks.append(end_pos)
    if breaks[-1] < len(sentence):
        breaks.append(len(sentence))

    spans: List[Tuple[str, Tuple[int, int]]] = []
    for idx in range(len(breaks) - 1):
        s_idx, e_idx = breaks[idx], breaks[idx + 1]
        chunk = sentence[s_idx:e_idx]
        stripped = chunk.strip()
        if not stripped:
            continue
        lead_ws = len(chunk) - len(chunk.lstrip())
        trail_ws = len(chunk) - len(chunk.rstrip())
        abs_start = base_offset + s_idx + lead_ws
        abs_end = base_offset + e_idx - trail_ws
        spans.append((stripped, (abs_start, abs_end)))
    return spans or [(sentence.strip(), (base_offset, base_offset + len(sentence.strip())))]


def _detect_speaker(clause: str, previous_sentence: str) -> Tuple[str, Optional[str], str, List[str]]:
    reasons: List[str] = []
    opp_report = _OPPONENT_REPORT_VERB_RE.search(clause)
    court_report = _COURT_REPORT_VERB_RE.search(clause)
    opp_subj = _OPPONENT_SURFACE_RE.search(clause)
    court_subj = _COURT_SURFACE_RE.search(clause)
    author_subj = _AUTHOR_SURFACE_RE.search(clause)

    if opp_report:
        surf = opp_subj.group(0).strip() if opp_subj else None
        return ("OPPONENT", surf, "OPPONENT_SUMMARY", reasons)

    if court_report and (court_subj or _CASE_CITE_MARKER_RE.search(clause) or _CASE_CITE_MARKER_RE.search(previous_sentence)):
        surf = court_subj.group(0).strip() if court_subj else None
        return ("COURT", surf, "QUOTED_PRECEDENT", reasons)

    if opp_subj and not author_subj:
        # Subject is counterparty, but without an explicit report verb it may be a fact statement about them
        reasons.append("IMPLICIT_SPEAKER_BOUNDARY")
        return ("OPPONENT" if "주장" in clause or "항변" in clause else "AUTHOR", opp_subj.group(0).strip(), "DIRECT_ASSERTION", reasons)

    if court_subj and ("판결" in clause or "판시" in clause or "결정" in clause):
        return ("COURT", court_subj.group(0).strip(), "QUOTED_PRECEDENT", reasons)

    if author_subj:
        return ("AUTHOR", author_subj.group(0).strip(), "DIRECT_ASSERTION", reasons)

    # Korean legal prose frequently omits grammatical subjects; record uncertainty explicitly.
    reasons.append("OMITTED_SUBJECT")
    return ("AUTHOR", None, "DIRECT_ASSERTION", reasons)


_TRUE_DOUBLE_NEG_RE = re.compile(
    r"(?:지|하지|되지|않는다고|없다고|아니라고|않음을|없음을)\s*(?:볼|할|인정할|단정할|말할|해석할|이해할)\s*수\s*(?:는|도)?\s*없|"
    r"(?:지|없지)\s*(?:않|아니하)|"
    r"(?:아니할|않을|없을)\s*수\s*(?:는|도)?\s*없|"
    r"부정할\s*수\s*없"
)


def _detect_polarity(clause: str) -> Tuple[str, int]:
    neg_count = len(_NEGATION_RE.findall(clause))
    if neg_count == 0:
        return ("ASSERTED", 0)
    if neg_count % 2 == 1:
        return ("NEGATED", neg_count)
    if _TRUE_DOUBLE_NEG_RE.search(clause):
        return ("DOUBLE_NEGATED_ASSERTED", neg_count)
    return ("NEGATED", neg_count)


def _detect_modality(clause: str) -> str:
    if _INTERROGATIVE_RE.search(clause):
        return "INTERROGATIVE"
    if _HYPOTHETICAL_LEAD_RE.search(clause) or _HYPOTHETICAL_TAIL_RE.search(clause + " "):
        return "HYPOTHETICAL"
    if _ALTERNATIVE_RE.search(clause):
        return "ALTERNATIVE"
    if _MANDATORY_RE.search(clause):
        return "MANDATORY"
    if _PERMISSIVE_RE.search(clause):
        return "PERMISSIVE"
    return "DEFINITIVE"


def _detect_temporal(clause: str) -> str:
    if _FUTURE_PLAN_RE.search(clause):
        return "FUTURE_PLAN"
    if _PAST_FACT_RE.search(clause):
        return "PAST_FACT"
    return "ATEMPORAL_RULE"


def _detect_discourse(clause: str) -> str:
    if _PROVISO_RE.search(clause):
        return "EXCEPTION_PROVISO"
    if _CONCESSION_RE.search(clause):
        return "CONCESSION"
    if _CONDITION_RE.search(clause):
        return "CONDITION"
    if _CAUSE_RE.search(clause):
        return "CAUSE"
    return "MAIN"


def normalize_sentence(
    sentence: str,
    *,
    sentence_index: int = 0,
    base_offset: int = 0,
    previous_sentence: str = "",
    block_id: Optional[str] = None,
    page: Optional[int] = None,
    tokenizer: Optional[LegalTokenizer] = None,
) -> List[NormalizedClause]:
    """Normalize a single Korean legal sentence into one or more `NormalizedClause` objects."""
    tok = tokenizer or get_tokenizer()
    sub_clauses = _split_clauses_with_spans(sentence, base_offset)
    results: List[NormalizedClause] = []

    for sub_idx, (raw_clause, span) in enumerate(sub_clauses):
        speaker_role, speaker_surface, attribution_type, reasons = _detect_speaker(raw_clause, previous_sentence)
        pol, neg_count = _detect_polarity(raw_clause)
        modality = _detect_modality(raw_clause)
        temporal = _detect_temporal(raw_clause)
        discourse = _detect_discourse(raw_clause)
        quantifiers = [m.group(0).strip() for m in _QUANTIFIER_RE.finditer(raw_clause)]

        toks = tok.tokenize(raw_clause)
        content_tokens = [t.form for t in toks if t.tag.startswith(("N", "V", "SL", "SN"))]
        predicates = [t.form for t in toks if t.tag.startswith("V")]
        predicate_lemma = predicates[-1] if predicates else None

        if len(sub_clauses) > 2:
            reasons.append("MULTI_CLAUSE_NESTING")
        confidence = max(0.4, round(1.0 - 0.15 * len(reasons), 2))
        norm_text = re.sub(r"\s+", " ", raw_clause).strip()

        results.append(
            NormalizedClause(
                clause_id=f"CL_{sentence_index}_{sub_idx}",
                sentence_index=sentence_index,
                raw_text=raw_clause,
                normalized_text=norm_text,
                reading_span=span,
                block_id=block_id,
                page=page,
                speaker_role=speaker_role,
                speaker_surface=speaker_surface,
                attribution_type=attribution_type,
                polarity=pol,
                negation_count=neg_count,
                modality=modality,
                temporal_aspect=temporal,
                discourse_relation=discourse,
                predicate_lemma=predicate_lemma,
                quantifiers=quantifiers,
                tokens=content_tokens,
                parse_confidence=confidence,
                uncertainty_reasons=reasons,
            )
        )
    return results


def normalize_document_clauses(doc: Any, *, tokenizer: Optional[LegalTokenizer] = None) -> List[NormalizedClause]:
    """Normalize all prose sentences of a `NormalizedDocument` and cache in `doc.structure`."""
    reading = build_reading_text(doc)
    bounds = sentence_bounds(reading.text)
    tok = tokenizer or get_tokenizer()
    all_clauses: List[NormalizedClause] = []
    prev_sentence = ""

    for s_idx, (start, end) in enumerate(bounds):
        sent = reading.text[start:end].strip()
        if not sent:
            continue
        block, _ = reading.locate(start)
        clauses = normalize_sentence(
            sent,
            sentence_index=s_idx,
            base_offset=start,
            previous_sentence=prev_sentence,
            block_id=block.block_id if block else None,
            page=block.page if block else None,
            tokenizer=tok,
        )
        all_clauses.extend(clauses)
        prev_sentence = sent

    if hasattr(doc, "structure") and isinstance(doc.structure, dict):
        doc.structure["normalized_clauses"] = [c.to_dict() for c in all_clauses]
        doc.structure["clause_normalizer_backend"] = tok.backend
    return all_clauses
