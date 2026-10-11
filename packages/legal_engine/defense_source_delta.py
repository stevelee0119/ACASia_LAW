"""Source-bound additions to the existing defense rule, never replacements.

This deliberately small grammar proves an author's direct act denial or a
typed legal-effect assertion. It does not certify a premise, completion,
underlying facts, or legal sufficiency. Unproved candidates add nothing.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any


SOURCE_VERSION = "nikl-krdict-2026-10-11/source-delta-1"
SOURCE_SENSES = {
    "하다1:1": {
        "lemma": "하다", "homonym": 1, "sense": 1,
        "definition": "어떤 행동이나 동작, 활동 등을 행하다.",
        "url": "https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=%ED%95%98%EB%8B%A4",
    },
    "받다1:10": {
        "lemma": "받다", "homonym": 1, "sense": 10,
        "definition": "어떠한 결정이나 판결을 당하다.",
        "url": "https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=%EB%B0%9B%EB%8B%A4",
    },
    "면하다1:1": {
        "lemma": "면하다", "homonym": 1, "sense": 1, "hanja": "免",
        "definition": "책임이나 의무를 지지 않게 되다.",
        "url": "https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=%EB%A9%B4%ED%95%98%EB%8B%A4",
    },
    "면하다1:2": {
        "lemma": "면하다", "homonym": 1, "sense": 2, "hanja": "免",
        "definition": "어떤 일을 당하지 않게 되다.",
        "url": "https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord=%EB%A9%B4%ED%95%98%EB%8B%A4",
    },
}

# These are grammatical scopes, not exceptions for particular sample verbs.
_QUOTE = re.compile(r'["“”‘’「」『』]')
_REPORT = re.compile(r"(?:다고|라고|라는|다는|다며|이라며)(?=\s|[,;.!?]|$)")
_CONDITION = re.compile(r"[가-힣]+면(?=\s|[,;.!?]|$)")
_TERMINAL = re.compile(r"\s*(?:다|습니다|어요)?\s*[.!]?\s*\Z")
_DIRECT_DENIAL = re.compile(
    r"\s*(?P<case>을|를)\s+"
    r"(?P<predicate>(?P<action>하지)(?:는|도)?\s*"
    r"(?P<negative>않)(?P<past>았)(?P<closure>으나|지만|으므로))\s*"
)

# Retain the existing legal rule's explicit criminal/disciplinary/admin
# qualification. Bare '책임', '징계', or '제재' is not sense-selected here.
_EFFECT = re.compile(
    r"(?P<object>형사(?:상\s*)?(?:책임|처벌)|징계\s*(?:책임|처분)|"
    r"행정\s*(?:처분|제재))\s*(?P<case>을|를)\s+"
    r"(?P<predicate>(?P<receive>받지\s*않(?:는다|습니다))|"
    r"(?P<release>면(?:한다|합니다)))\s*[.!]?\s*\Z"
)
_PREMISE_CASE = re.compile(r"\s*(?P<case>을|를)\s+(?P<finite>[가-힣]+(?:으므로|므로))\s*\Z")


@lru_cache(maxsize=32)
def _patterns(requirements: tuple[str, ...], limited: tuple[str, ...], leads: tuple[str, ...], articles: tuple[str, ...]):
    lead = "|".join(leads)
    anchor = re.compile(rf"\A\s*(?P<lead>{lead})\s+(?P<assumption>[^,;.!?\n]+?더라도)(?P<boundary>[,;])\s*")
    # Existing configured statutory numbers delimit a civil norm reference;
    # a naked number or an unrelated noun is not a legal-effect source link.
    art = "|".join(re.escape(a) for a in articles)
    citation = re.compile(rf"\s*(?P<norm>(?P<law>헌법|민법|형법)\s*제\s*(?:{art})\s*조(?:의\s*\d+)?)"
                          r"(?P<link>의|에\s*(?:따라|의하여))?\s*")
    return anchor, citation, tuple(re.compile(p) for p in requirements), tuple(re.compile(p) for p in limited)


def _record(kind: str, spans: dict[str, tuple[int, int]], sense: str, role: str, accounting: dict[str, int]) -> dict[str, Any]:
    return {
        "version": SOURCE_VERSION, "kind": kind,
        "source_spans": {key: list(value) for key, value in spans.items()},
        "selected_sense": {"id": sense, **SOURCE_SENSES[sense]},
        "application_role": role, "authored_speaker": "IMPLICIT_WRITER",
        "authored_actor": "UNSPECIFIED_WITHIN_CLOSED_LOCAL_CHAIN",
        "actor_entity_identity_verified": False, "acts_merged": False,
        "premise_assertion_verified": False,
        "normative_scope": "SAME_SENTENCE_EXPLICIT_CIVIL_DEFENSE",
        "supports_asserted_fulfillment": False, "total_requirement_completion": False,
        "facts_verified": False, "legal_sufficiency_verified": False,
        "baseline_observations_changed": False,
        "accounting": accounting,
    }


def source_defense_proof(unit: str, groups: dict[str, Any]) -> dict[str, Any] | None:
    """Return only a closed own-source proof; all other inputs preserve baseline.

    The patterns use source pos/endpos, without copying each candidate suffix.
    Fixed configuration count R gives O(R*N) regex visits. This is a bound on
    this additional grammar, not on observation generation or the pipeline.
    """
    if "\n" in unit or _QUOTE.search(unit) or _REPORT.search(unit):
        return None
    signals = groups.get("structural_signals", {})
    articles: set[str] = set()
    for cluster in groups.get("clusters", {}).values():
        articles.update(str(a) for a in cluster.get("article_numbers", cluster.get("articles", [])))
        for span in cluster.get("ranges", cluster.get("article_ranges", [])):
            start, end = span.get("from") or span.get("start"), span.get("to") or span.get("end")
            if start and end:
                articles.update(str(n) for n in range(int(start), int(end) + 1))
    if not articles:
        return None
    anchor_re, citation_re, requirements, limited = _patterns(
        tuple(signals.get("stated_requirements", [])), tuple(signals.get("limited_conclusions", [])),
        tuple(signals.get("hypothetical_concessions", [])), tuple(sorted(articles)))
    anchor = anchor_re.match(unit)
    if not anchor or _CONDITION.search(unit, anchor.end()):
        return None
    citation = citation_re.match(unit, anchor.end())
    # The initial phase proves only a literal configured statute reference.
    # An unknown topic, subject, possessor or event qualifier cannot be skipped.
    if not citation:
        return None
    first = citation.end()
    base = {"concession": anchor.span("assumption"), "concession_boundary": anchor.span("boundary")}
    base["civil_norm"] = citation.span("norm")
    base["authored_scope"] = (0, len(unit))
    accounting = {"source_chars": len(unit), "source_scope_scans": 4,
                  "requirement_prefix_queries": 0, "conclusion_prefix_queries": 0,
                  "effect_suffix_queries": 0, "whole_document_prefix_searches": 0}

    for requirement_re, pattern in zip(requirements, signals.get("stated_requirements", [])):
        if signals.get("requirement_polarities", {}).get(pattern) == "absent":
            continue
        accounting["requirement_prefix_queries"] += 1
        requirement = requirement_re.match(unit, first)
        if not requirement:
            continue
        denial = _DIRECT_DENIAL.match(unit, requirement.end())
        if not denial:
            continue
        for conclusion_re in limited:
            accounting["conclusion_prefix_queries"] += 1
            conclusion = conclusion_re.match(unit, denial.end())
            if conclusion and _TERMINAL.fullmatch(unit, conclusion.end()):
                spans = {**base, "argument": requirement.span(), "case": denial.span("case"),
                         "predicate": denial.span("predicate"), "action": denial.span("action"),
                         "negation": denial.span("negative"), "past": denial.span("past"),
                         "closure": denial.span("closure"), "conclusion": conclusion.span()}
                return _record("DIRECT_REQUIREMENT_DENIAL", spans, "하다1:1", "ASSERTED_DIRECT_ACT_DENIAL", accounting)

    # A legal noun + case is insufficient. Require its strict selected finite
    # predicate, explicit norm link, and the same author's closed causal clause.
    if citation.group("law") != "민법" or citation.group("link") not in ("에 따라", "에 의하여"):
        return None
    effect = _EFFECT.search(unit, first)
    accounting["effect_suffix_queries"] += 1
    if not effect:
        return None
    # Receiving a 'responsibility' does not by itself select the decision/
    # judgment sense of 받다; the source frame remains unproved in that case.
    responsibility = effect.group("object").endswith("책임")
    if effect.group("receive") and responsibility:
        return None
    for requirement_re, pattern in zip(requirements, signals.get("stated_requirements", [])):
        if signals.get("requirement_polarities", {}).get(pattern) == "absent":
            continue
        accounting["requirement_prefix_queries"] += 1
        requirement = requirement_re.match(unit, first, effect.start())
        if not requirement:
            continue
        premise = _PREMISE_CASE.fullmatch(unit, requirement.end(), effect.start())
        if not premise:
            continue
        spans = {**base, "normative_link": citation.span("link"), "premise_argument": requirement.span(),
                 "premise_case": premise.span("case"), "premise_finite": premise.span("finite"),
                 "effect_argument": effect.span("object"), "effect_case": effect.span("case"),
                 "predicate": effect.span("predicate"), "conclusion": effect.span()}
        sense = "받다1:10" if effect.group("receive") else ("면하다1:1" if responsibility else "면하다1:2")
        return _record("LEGAL_EFFECT_EXTENSION", spans, sense, "ASSERTED_CATEGORICAL_LEGAL_EFFECT", accounting)
    return None
