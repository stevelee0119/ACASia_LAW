"""Public comparison only: actual producer truncation can destroy JSON context.

The token projection is a diagnostic for numeric literals, not a product rule
or authenticated source contract. No existing expectations are changed.
"""
from __future__ import annotations

import asyncio
import json
import re
from types import SimpleNamespace

import pytest

from packages.common.enums import ExternalAIPolicy
from packages.llm_router import privacy
from packages.llm_router.providers import LLMRequest
from .test_post013_tk55_boundary_spike import _route
from .test_post013_tk55_cascade_source_spike import PHONES, RRNS


def _record(value, *, outside=False):
    literal = '"' + ''.join(f'\\u{ord(char):04x}' for char in value) + '"'
    padding = json.dumps('일반 기록 ' * 400, ensure_ascii=False)
    return ('{"body":' + padding + ',"opaque":' + literal + '}' if outside else
            '{"opaque":' + literal + ',"body":' + padding + '}')


def _project_complete_literals(source, selected):
    # Only a known complete source JSON and its exact producer prefix enter
    # this comparison. Arbitrary raw prose is not scanned as JSON syntax.
    assert privacy._try_json_parse(source) is not None
    assert source.startswith(selected)
    tokens = []
    for match in re.finditer(r'"(?:[^"\\]|\\.)*"', source):
        if match.end() <= len(selected):
            tokens.append(json.loads(match.group()))
    return json.dumps(tokens, ensure_ascii=False)


def _route_projection(monkeypatch, request, source, selected):
    # Test-observed producer identity only; a product capability and nested
    # span mapping still require a separately approved design/implementation.
    baseline = privacy.inspect_request
    projection = _project_complete_literals(source, selected)

    def compare(candidate, *, _original_system=None):
        report = baseline(candidate, _original_system=_original_system)
        if report["status"] == "BLOCKED":
            return report
        if (candidate.user != request.user or _original_system != request.system
                or candidate.schema != request.schema):
            return report
        extra = baseline(LLMRequest(system="", user=projection))
        return extra if extra["status"] == "BLOCKED" else report

    with monkeypatch.context() as scoped:
        scoped.setattr(privacy, "inspect_request", compare)
        return _route(scoped, request)


def _argument_request(source):
    from packages.legal_engine.argument_validity_verifier import _attach_ai_opinions
    captured = []

    class Capture:
        async def consult_all(self, role, request, **kwargs):
            captured.append(request)
            return []

    item = {"citation": SimpleNamespace(page=1, raw_text="合成資料"), "context": source}
    asyncio.run(_attach_ai_opinions(SimpleNamespace(rows=[]), [item], Capture(), ExternalAIPolicy.MASKED, None))
    request = captured[0]
    selected = json.loads(request.user)["items"][0]["surrounding_context_and_claim"]
    assert selected == source[:1000]
    return request, selected


def _claim_request(source):
    from korean_law_profile.test_review_path import inputs, pii_engine
    from packages.rag_engine.review import review_document
    captured = []

    class Capture:
        settings = SimpleNamespace(korean_law_review_profile=False)

        def has_available_provider(self, **kwargs):
            return True

        async def run(self, role, request, **kwargs):
            captured.append(request)
            return SimpleNamespace(used=False, executions=[], quarantined=False, parsed=None)

    result, library, context = inputs()
    library.sources[0]["text"] = source
    review_document(result, library, Capture(), context, pii_engine())
    request = next(item for item in captured if item.input_contract == "claim_review_v1")
    selected = json.loads(request.user)["reference_sources"][0]["text"]
    assert selected == source[:800]
    return request, selected


@pytest.mark.parametrize("producer", (_argument_request, _claim_request), ids=("argument", "claim"))
@pytest.mark.parametrize("value", PHONES + RRNS)
def test_actual_excerpt_loses_complete_json_numeric_context(monkeypatch, producer, value):
    source = _record(value)
    request, selected = producer(source)
    assert privacy.inspect_request(LLMRequest(system="", user=source))["failure_code"] == "PII_INPUT_BLOCKED"
    assert privacy._try_json_parse(selected) is None
    assert privacy.inspect_request(request)["status"] == "PASSED"
    _, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1  # Existing residual, not acceptance.
    assert sent[0].user == request.user
    projected = _project_complete_literals(source, selected)
    assert privacy.inspect_request(LLMRequest(system="", user=projected))["failure_code"] == "PII_INPUT_BLOCKED"
    result, sent, reserved = _route_projection(monkeypatch, request, source, selected)
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"


@pytest.mark.parametrize("producer", (_argument_request, _claim_request), ids=("argument", "claim"))
@pytest.mark.parametrize("value", PHONES + RRNS)
def test_full_source_blocking_would_refuse_nontransmitted_numeric_controls(monkeypatch, producer, value):
    source = _record(value, outside=True)
    request, selected = producer(source)
    assert privacy.inspect_request(LLMRequest(system="", user=source))["failure_code"] == "PII_INPUT_BLOCKED"
    _, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1
    assert '\\u0030' not in selected and value not in selected
    projected = _project_complete_literals(source, selected)
    assert privacy.inspect_request(LLMRequest(system="", user=projected))["status"] == "PASSED"
    _, compared, reservations = _route_projection(monkeypatch, request, source, selected)
    assert len(compared) == len(reservations) == 1
    assert compared[0].user == sent[0].user


@pytest.mark.parametrize("value", ("초록환경 관측자료", "일반 법령 검토 자료", "문서함"))
@pytest.mark.parametrize("producer", (_argument_request, _claim_request), ids=("argument", "claim"))
def test_truncated_benign_json_keeps_provider_payload_and_reservation(monkeypatch, producer, value):
    source = _record(value)
    request, selected = producer(source)
    _, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1
    assert sent[0].user == request.user
    assert privacy.inspect_request(LLMRequest(system="", user=_project_complete_literals(source, selected)))["status"] == "PASSED"
    _, compared, reservations = _route_projection(monkeypatch, request, source, selected)
    assert len(compared) == len(reservations) == 1
    assert compared[0].user == sent[0].user


@pytest.mark.parametrize("value", PHONES + RRNS)
def test_existing_complete_argument_json_numeric_gate_remains_prebudget(monkeypatch, value):
    source = '{"opaque":' + '"' + ''.join(f'\\u{ord(char):04x}' for char in value) + '"}'
    request, _ = _argument_request(source)
    outcome, sent, reserved = _route(monkeypatch, request)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"
