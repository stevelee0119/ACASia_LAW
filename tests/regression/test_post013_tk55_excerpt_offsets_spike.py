"""Comparison-only source→decoded selection tests for two actual producers."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from packages.common.enums import ExternalAIPolicy
from packages.llm_router import privacy
from packages.llm_router.providers import LLMRequest
from packages.pii_engine.detector import detect
from .post013_excerpt_projection import projected_numeric_matches, projection_json
from .test_post013_tk55_boundary_spike import _route
from .test_post013_tk55_cascade_source_spike import PHONES, RRNS


VALUES = PHONES + RRNS


def enc(value):
    return ''.join(f'\\u{ord(char):04x}' for char in value)


def _argument(source, *, exclude=None):
    from korean_law_profile.test_review_path import pii_engine
    from packages.legal_engine.argument_validity_verifier import _attach_ai_opinions
    from packages.verification_engine.sanitized_input import strip_injections
    captured, masked_inputs = [], []
    pii = pii_engine()

    def hide(text):
        masked_inputs.append(text)
        return pii.mask_text(strip_injections(text, [exclude] if exclude else [])).masked_text

    class Capture:
        async def consult_all(self, role, request, **kwargs):
            captured.append(request)
            return []

    item = {"citation": SimpleNamespace(page=1, raw_text="합성 인용 자료"), "context": source}
    asyncio.run(_attach_ai_opinions(SimpleNamespace(rows=[]), [item], Capture(), ExternalAIPolicy.MASKED, hide))
    request = captured[0]
    rendered = json.loads(request.user)["items"][0]["surrounding_context_and_claim"]
    assert source[:1000] in masked_inputs  # Real cut→mask, not mask→cut.
    return request, source, ((0, min(1000, len(source))),), rendered


def _claim(source, *, exclude=None, claim="표식단어"):
    from korean_law_profile.test_review_path import inputs, pii_engine
    from packages.rag_engine.review import review_document, _claim_salient_words
    from packages.verification_engine.sanitized_input import strip_injections
    captured, masked_sources = [], []
    base_pii = pii_engine()

    class PII:
        def mask_text(self, text):
            result = base_pii.mask_text(strip_injections(text, [exclude] if exclude else []))
            if text == source:
                masked_sources.append(result.masked_text)
            return result

    class Capture:
        settings = SimpleNamespace(korean_law_review_profile=False)

        def has_available_provider(self, **kwargs):
            return True

        async def run(self, role, request, **kwargs):
            captured.append(request)
            return SimpleNamespace(used=False, executions=[], quarantined=False, parsed=None)

    result, library, context = inputs((claim, source))
    review_document(result, library, Capture(), context, PII())
    request = next(item for item in captured if item.input_contract == "claim_review_v1")
    rendered = json.loads(request.user)["reference_sources"][0]["text"]
    assert len(masked_sources) == 1  # Real mask→excerpt, one actual mask call.
    inspected_source = masked_sources[0]
    pos = next((inspected_source.find(word) for word in _claim_salient_words(claim)
                if word in inspected_source), -1)
    start = max(0, pos - 200) if pos != -1 else 0
    end = min(len(inspected_source), start + 800)
    if pos != -1 and end - start < 800 and len(inspected_source) > end - start:
        start = max(0, end - 800)
    assert rendered == inspected_source[start:end]
    return request, inspected_source, ((start, end),), rendered


def _compare(monkeypatch, request, source, ranges, rendered, *, candidate=None):
    baseline = privacy.inspect_request
    ranges = tuple(tuple(pair) for pair in ranges)
    expected = (request.system, request.user, json.dumps(request.schema, sort_keys=True, ensure_ascii=False))
    projection = projection_json(source, ranges, rendered)

    def inspect(candidate, *, _original_system=None):
        report = baseline(candidate, _original_system=_original_system)
        if report["status"] == "BLOCKED":
            return report
        extra = baseline(LLMRequest(system="", user=projection))
        if extra["status"] == "BLOCKED":
            return extra  # Existing PII has precedence over binding failure.
        if (candidate.user != expected[1] or _original_system != expected[0]
                or json.dumps(candidate.schema, sort_keys=True, ensure_ascii=False) != expected[2]):
            return {**report, "status": "BLOCKED", "failure_code": "INPUT_CONTRACT_VIOLATION"}
        return report

    with monkeypatch.context() as scoped:
        scoped.setattr(privacy, "inspect_request", inspect)
        return _route(scoped, request if candidate is None else candidate)


def _source(value, form):
    body = '가' * 1600
    literal = enc(value)
    if form == "closing_quote_outside":
        return '{"slot":"' + literal + body + '"}'
    if form == "unicode_mid_escape":
        # Both real prefix bounds cut an unrelated six-character escape;
        # the whole contact literal is already inside the selected range.
        return '{"slot":"' + literal + ('\\uac00' * 350) + '"}'
    if form == "surrogate_before_phone":
        return '{"slot":"\\ud83d\\ude00' + literal + body + '"}'
    if form == "duplicate":
        return '{"slot":"' + literal + body + '","slot":"일반 자료"}'
    if form == "nested":
        inner = '{"slot":"' + literal + body + '","slot":"일반 자료"}'
        return json.dumps({"records": [{"encoded": inner}]}, ensure_ascii=False)
    if form == "deep_nested":
        inner = '{"slot":"' + literal + body + '"}'
        return json.dumps({"encoded": json.dumps({"encoded": inner}, ensure_ascii=False)}, ensure_ascii=False)
    if form == "mixed_masked_plain":
        return '{"slot":"연락 ' + value + ' 자료 ' + literal + body + '"}'
    raise AssertionError(form)


@pytest.mark.parametrize("producer", (_argument, _claim), ids=("cut_mask_argument", "mask_cut_claim"))
@pytest.mark.parametrize("value", VALUES)
@pytest.mark.parametrize("form", ("closing_quote_outside", "unicode_mid_escape", "surrogate_before_phone",
                                  "duplicate", "nested", "deep_nested", "mixed_masked_plain"))
def test_actual_selected_encoded_numeric_recovers_without_closing_quote(monkeypatch, producer, value, form):
    request, source, ranges, rendered = producer(_source(value, form))
    assert privacy._try_json_parse(source) is not None
    before, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1
    assert before.executions[0].input_privacy["status"] == "PASSED"
    assert projected_numeric_matches(source, ranges, rendered)
    outcome, compared, reservations = _compare(monkeypatch, request, source, ranges, rendered)
    assert compared == reservations == []
    assert outcome.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"


@pytest.mark.parametrize("value", VALUES)
def test_actual_claim_selection_starts_inside_literal(monkeypatch, value):
    source = '{"slot":"' + '가' * 600 + enc(value) + '표식단어' + '나' * 1600 + '"}'
    request, inspected, ranges, rendered = _claim(source)
    assert ranges[0][0] > source.index('"', source.index(':')) + 1
    assert enc(value) in rendered
    _, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1
    _, compared, reservations = _compare(monkeypatch, request, inspected, ranges, rendered)
    assert compared == reservations == []


@pytest.mark.parametrize("producer", (_argument, _claim), ids=("argument", "claim"))
@pytest.mark.parametrize("value", VALUES)
@pytest.mark.parametrize("control", ("outside", "already_masked", "excluded"))
def test_actual_omitted_masked_excluded_pii_is_not_recovered(monkeypatch, producer, value, control):
    if control == "outside":
        source, exclude = '{"body":"' + '가' * 1600 + '","slot":"' + enc(value) + '"}', None
    elif control == "already_masked":
        source, exclude = '{"slot":"연락 ' + value + ' ' + '가' * 1600 + '"}', None
    else:
        source, exclude = '{"slot":"' + enc(value) + '가' * 1600 + '"}', enc(value)
    request, inspected, ranges, rendered = producer(source, exclude=exclude)
    assert value not in rendered and enc(value) not in rendered
    assert projected_numeric_matches(inspected, ranges, rendered) == ()
    _, sent, reserved = _route(monkeypatch, request)
    _, compared, reservations = _compare(monkeypatch, request, inspected, ranges, rendered)
    assert len(sent) == len(reserved) == len(compared) == len(reservations) == 1
    assert compared[0].user == sent[0].user == request.user


@pytest.mark.parametrize("producer", (_argument, _claim), ids=("argument", "claim"))
@pytest.mark.parametrize("value", ("문서함", "초록환경 관측자료", "일반 법령 검토 자료",
                                  "123-45-67890", "2024-06-18", "2022다123456"))
def test_actual_benign_json_legal_numeric_controls_keep_wire(monkeypatch, producer, value):
    request, source, ranges, rendered = producer(_source(value, "closing_quote_outside"))
    assert projected_numeric_matches(source, ranges, rendered) == ()
    _, sent, reserved = _route(monkeypatch, request)
    _, compared, reservations = _compare(monkeypatch, request, source, ranges, rendered)
    assert len(sent) == len(reserved) == len(compared) == len(reservations) == 1
    assert compared[0].user == sent[0].user == request.user


@pytest.mark.parametrize("value", VALUES)
@pytest.mark.parametrize("part", ("escape_cut", "escape_start", "surrogate_cut", "discontinuous"))
def test_atomic_offset_controls_never_complete_omitted_units_or_join_gaps(value, part):
    source = '{"slot":"' + enc(value) + '\\ud83d\\ude00' + ' 가' * 30 + '"}'
    begin = source.index(enc(value))
    last = begin + len(enc(value))
    if part == "escape_cut":
        ranges = ((0, last - 1),)
    elif part == "escape_start":
        ranges = ((begin + 1, last),)
    elif part == "surrogate_cut":
        # Surrogate half is not emitted; the whole selected numeric survives.
        ranges = ((0, last + 6),)
    else:
        ranges = ((begin, begin + 18), (begin + 24, last))
    rendered = ''.join(source[start:end] for start, end in ranges)
    found = projected_numeric_matches(source, ranges, rendered)
    if part == "escape_cut":
        # Existing detector accepts some ten-digit phone spellings. Preserve
        # that policy, but never supply the omitted last escape/digit.
        expected = [(m.kind, m.text) for m in detect(value[:-1])
                    if m.kind in ("PHONE", "RRN") and m.confidence >= 0.6]
        assert [(kind, text) for kind, text, _ in found] == expected
        assert all(text != value and text in value[:-1] for _, text, _ in found)
    else:
        assert bool(found) == (part == "surrogate_cut")


@pytest.mark.parametrize("value", VALUES)
def test_discontinuous_ranges_keep_complete_separate_numeric_units(value):
    source = '{"a":"' + enc(value) + '","b":"' + ('가' * 30) + '","c":"' + enc(value) + '"}'
    first, second = source.index(enc(value)), source.rindex(enc(value))
    ranges = ((first, first + len(enc(value))), (second, second + len(enc(value))))
    rendered = ''.join(source[start:end] for start, end in ranges)
    found = projected_numeric_matches(source, ranges, rendered)
    assert len(found) == 2


@pytest.mark.parametrize("value", VALUES)
def test_untyped_plain_prose_is_not_reinterpreted_as_json(value):
    source = '일반 자료 ' + enc(value)
    assert projected_numeric_matches(source, ((0, len(source)),), source) == ()


@pytest.mark.parametrize("producer", (_argument, _claim), ids=("argument", "claim"))
@pytest.mark.parametrize("position", ("user", "system", "schema"))
def test_comparison_exact_binding_mismatch_has_no_legacy_fallback(monkeypatch, producer, position):
    request, source, ranges, rendered = producer(_source("일반 법령 검토 자료", "closing_quote_outside"))
    if position == "user":
        changed = replace(request, user=request.user + ' ')
    elif position == "system":
        changed = replace(request, system=request.system + ' ')
    else:
        changed = replace(request, schema={**request.schema, "additionalProperties": False})
    outcome, sent, reserved = _compare(monkeypatch, request, source, ranges, rendered, candidate=changed)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy["failure_code"] == "INPUT_CONTRACT_VIOLATION"


@pytest.mark.parametrize("producer", (_argument, _claim), ids=("argument", "claim"))
@pytest.mark.parametrize("position", ("user", "system", "schema", "metadata", "projection"))
def test_comparison_existing_pii_priority_survives_binding_mismatch(monkeypatch, producer, position):
    request, source, ranges, rendered = producer(_source(PHONES[0] if position == "projection" else "일반 자료",
                                                        "closing_quote_outside"))
    if position in ("user", "projection"):
        changed = replace(request, user=request.user + (' ' if position == "projection" else PHONES[1]))
    elif position == "system":
        changed = replace(request, system=PHONES[1])
    elif position == "schema":
        changed = replace(request, schema={"dynamic": PHONES[1]})
    else:
        changed = replace(request, metadata={**request.metadata, "dynamic": PHONES[1]})
    outcome, sent, reserved = _compare(monkeypatch, request, source, ranges, rendered, candidate=changed)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"


def test_surrogate_pair_uses_one_atomic_twelve_character_source_span():
    from .post013_excerpt_projection import _decode_string
    literal = '"\\ud83d\\ude00A"'
    decoded, spans = _decode_string(literal, tuple((i, i + 1) for i in range(len(literal))))
    assert decoded == '😀A'
    assert spans == ((1, 13), (13, 14))
