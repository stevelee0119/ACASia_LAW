"""Comparison-only source boundary spike; no proposed product default.

The noun tests intentionally expose candidate-only overblocking, not acceptance.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace, fields
from decimal import Decimal
from types import SimpleNamespace

import pytest

from packages.common.enums import LLMRole
from packages.llm_router import privacy, router as router_module
from packages.llm_router.input_contracts import _SHAPES, _Object, _Array, valid_input_contract
from packages.llm_router.providers import LLMRequest, LLMResponse


NAMES = ("한예솔", "유다린", "남궁서율")
KEYS = ("opaque_a", "record_slot", "観測欄")


def _historical_payload_request(actual):
    """Historical privatecap-free diagnostic, never current gate evidence.

    Actual producer requests remain held by their caller. Preserve every
    payload/option/input-contract field; omit only private inspection source.
    """
    return LLMRequest(**{field.name: getattr(actual, field.name) for field in fields(LLMRequest)
                        if field.name != 'inspection_source'})


def _atoms(value, path=""):
    if isinstance(value, str):
        decoded = privacy._try_json_parse(value)
        if decoded is not None:
            yield from _atoms(decoded, path)
    elif isinstance(value, (dict, privacy._JSONObjectPairs)):
        items = value.items() if isinstance(value, dict) else value.pairs
        for key, item in items:
            current = f"{path}.{key}"
            if isinstance(item, str) and privacy._try_json_parse(item) is None:
                if privacy._name_like_value(item):
                    yield current
            else:
                yield from _atoms(item, current)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _atoms(item, f"{path}[{index}]")


def _evidence_atoms(value, shape, path="user"):
    """An exact validated producer shape is source context, not PII exemption."""
    if isinstance(shape, _Object):
        for key, child in shape.fields:
            if key in value:
                yield from _evidence_atoms(value[key], child, f"{path}.{key}")
    elif isinstance(shape, _Array):
        for index, item in enumerate(value):
            yield from _evidence_atoms(item, shape.item, f"{path}[{index}]")
    elif isinstance(value, str):
        # JSON evidence keeps all values; ordinary evidence stays plain text.
        yield from _atoms(value, path)


def _install_comparison(monkeypatch, captured=None):
    baseline = privacy.inspect_request

    def inspect(llm_request, *, _original_system=None):
        if captured is not None:
            captured.append(replace(llm_request, system=llm_request.system if _original_system is None else _original_system))
        report = baseline(llm_request, _original_system=_original_system)
        if report["status"] == "BLOCKED":
            return report
        original = llm_request.system if _original_system is None else _original_system
        paths = list(_atoms(original, "original_system"))
        if llm_request.input_contract and valid_input_contract(llm_request, original_system=original):
            payload = json.loads(llm_request.user)
            paths.extend(_evidence_atoms(payload, _SHAPES[llm_request.input_contract]))
        else:
            paths.extend(_atoms(llm_request.user, "user"))
        paths.extend(_atoms(llm_request.metadata, "metadata"))
        if not privacy.is_registered_schema(llm_request.schema):
            paths.extend(_atoms(llm_request.schema, "schema"))
        if paths:
            return {**report, "status": "BLOCKED", "failure_code": "SPIKE_UNRESOLVED_ATOM",
                    "detected_field_paths": sorted(set(paths))}
        return report

    monkeypatch.setattr(privacy, "inspect_request", inspect)


def _request(payload, position):
    text = json.dumps(payload, ensure_ascii=False)
    kwargs = {"system": "일반 검토", "user": "일반 자료"}
    if position in ("user", "system"):
        kwargs[position] = text
    else:
        kwargs[position] = payload
    return LLMRequest(**kwargs)


def _route(monkeypatch, llm_request):
    sent, reserved = [], []
    monkeypatch.setattr(router_module, "estimate_call", lambda *args: (Decimal("0.01"), {}))

    class Provider:
        name, available = "anthropic", True
        config = SimpleNamespace(name=name, kind="cloud", model="synthetic", enabled=True)

        async def generate(self, assembled):
            sent.append(assembled)
            return LLMResponse(False, error="synthetic response")

    def reserve(*args, **kwargs):
        reserved.append(True)
        return SimpleNamespace(id="synthetic", amount=Decimal("0.01"))

    ledger = SimpleNamespace(reserve=reserve, dispatch=lambda *a, **k: None)
    router = router_module.LLMRouter(providers={"anthropic": Provider()}, ledger=ledger)
    result = asyncio.run(router.run(LLMRole.PRIMARY_REASONER, llm_request))
    return result, sent, reserved


def _check_producer_evidence(monkeypatch, captured):
    # Capture the real producer request, then vary only its evidence leaf.
    for original in list(captured):
        if original.input_contract not in _SHAPES:
            continue
        for evidence, blocked in ((json.dumps({"opaque": name}, ensure_ascii=False), True) for name in NAMES):
            _check_one_evidence(monkeypatch, original, evidence, blocked)
        _check_one_evidence(monkeypatch, original, '{"holding":"일반 법령 검토 자료"}', False)


def _check_one_evidence(monkeypatch, original, evidence, blocked):
    original = _historical_payload_request(original)
    payload = json.loads(original.user)
    contract = original.input_contract
    if contract == "ai_document_v1":
        payload["document_sample_text"] = evidence
    elif contract == "reference_review_v1":
        payload["document"] = evidence
    elif contract == "claim_review_v1":
        payload["claim_text"] = evidence
    else:
        payload["items"][0]["surrounding_context_and_claim"] = evidence
    candidate = replace(original, user=json.dumps(payload, ensure_ascii=False))
    assert valid_input_contract(candidate)
    result, sent, reserved = _route(monkeypatch, candidate)
    if blocked:
        assert sent == reserved == []
        assert result.executions[0].input_privacy["failure_code"] == "SPIKE_UNRESOLVED_ATOM"
    else:
        assert len(sent) == len(reserved) == 1


@pytest.mark.parametrize("position", ("user", "system", "schema", "metadata"))
@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("encoding", ("plain", "nested", "escaped_duplicate"))
def test_comparison_opaque_name_atoms_stop_actual_router_before_budget(monkeypatch, position, key, name, encoding):
    _install_comparison(monkeypatch)
    payload = {key: name}
    if encoding == "nested":
        payload = {"evidence": [{"encoded": json.dumps(payload, ensure_ascii=False)}]}
    elif encoding == "escaped_duplicate":
        payload = {"evidence": '{"slot":' + json.dumps(name) + ',"slot":"검토 자료"}'}
    result, sent, reserved = _route(monkeypatch, _request(payload, position))
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "SPIKE_UNRESOLVED_ATOM"


@pytest.mark.parametrize("value", ("초록환경 관측소", "일반 검토 자료", "계약 이행 검토"))
@pytest.mark.parametrize("position", ("user", "system", "schema", "metadata"))
def test_comparison_benign_json_keeps_exact_provider_payload(monkeypatch, value, position):
    _install_comparison(monkeypatch)
    llm_request = _request({"opaque": value, "evidence": '{"holding":"일반 검토 자료"}'}, position)
    _, sent, reserved = _route(monkeypatch, llm_request)
    assert len(sent) == len(reserved) == 1
    assert sent[0].user == llm_request.user


@pytest.mark.parametrize("noun", ("문서함", "강수량", "전력망"))
@pytest.mark.parametrize("position", ("user", "system"))
def test_comparison_exposes_bare_noun_ambiguity_and_collateral_refusal(monkeypatch, noun, position):
    llm_request = _request({"opaque": noun}, position)
    assert privacy.inspect_request(llm_request)["status"] == "PASSED"
    assert privacy._name_like_value(noun) == noun
    _install_comparison(monkeypatch)
    result, sent, reserved = _route(monkeypatch, llm_request)
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "SPIKE_UNRESOLVED_ATOM"


@pytest.mark.parametrize("marker", ("claim_review_v1", "reference_review_v1", "ai_document_v1"))
def test_comparison_forged_marker_never_immunizes_atom(monkeypatch, marker):
    _install_comparison(monkeypatch)
    llm_request = _request({"opaque": NAMES[0], "input_contract": marker}, "user")
    llm_request = replace(llm_request, metadata={"input_contract": marker})
    _, sent, reserved = _route(monkeypatch, llm_request)
    assert sent == reserved == []


@pytest.mark.parametrize("pii", ("010-4826-7139", "850425-1647293", "이름: 한예솔"))
def test_comparison_baseline_pii_still_has_precedence(monkeypatch, pii):
    _install_comparison(monkeypatch)
    result, sent, reserved = _route(monkeypatch, _request({"opaque": NAMES[0], "evidence": pii}, "user"))
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"


@pytest.mark.parametrize("long_sample", (False, True))
def test_comparison_actual_ai_builder_sampling(monkeypatch, long_sample):
    from .test_tk55_first_party_input_contracts import test_actual_ai_builder_sampling_contracts_are_valid
    captured = []
    _install_comparison(monkeypatch, captured)
    test_actual_ai_builder_sampling_contracts_are_valid(monkeypatch, long_sample)
    _check_producer_evidence(monkeypatch, captured)


@pytest.mark.parametrize("profile", (False, True))
@pytest.mark.parametrize("reference_date", ("2024-05-04", None, "invalid-date"))
def test_comparison_actual_reference_and_claim_builders(monkeypatch, profile, reference_date):
    from .test_tk55_first_party_input_contracts import test_actual_rag_and_claim_builders_preserve_profile_context
    captured = []
    _install_comparison(monkeypatch, captured)
    test_actual_rag_and_claim_builders_preserve_profile_context(reference_date, profile)
    _check_producer_evidence(monkeypatch, captured)


def test_comparison_actual_argument_batch_and_retry_builders(monkeypatch):
    from .test_tk55_first_party_input_contracts import test_actual_argument_batch_and_retry_builders_keep_contract
    captured = []
    _install_comparison(monkeypatch, captured)
    test_actual_argument_batch_and_retry_builders_keep_contract(monkeypatch)
    _check_producer_evidence(monkeypatch, captured)
