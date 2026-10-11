"""Synthetic product checks for request-local source inspection, no private data."""
from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import asdict, replace
from types import SimpleNamespace

import httpx
import pytest

from packages.common.config import ProviderConfig
from packages.common.enums import ExternalAIPolicy, LLMRole, VerificationProfile, Severity
from packages.llm_router import cascade_source, privacy, router as module
from packages.llm_router.providers import (AnthropicProvider, GeminiProvider, OpenAIProvider,
                                          LocalLLMProvider, LLMRequest, LLMResponse)
from .test_post013_tk55_cascade_source_spike import PHONES, RRNS, NAMES, SYSTEMS, _escaped_record, _router


def _run(monkeypatch, request, *, role=LLMRole.PRIMARY_REASONER, policy=ExternalAIPolicy.MASKED):
    router, sent, reserved = _router(monkeypatch)
    receipts = []
    router.on_execution = lambda item: receipts.append(item.to_dict())
    result = asyncio.run(router.run(role, request, policy=policy))
    return result, sent, reserved, receipts


@pytest.mark.parametrize("value", PHONES + RRNS + NAMES)
@pytest.mark.parametrize("position", ("official", "document", "question"))
@pytest.mark.parametrize("form", ("duplicate", "nested"))
def test_decoded_actual_cascade_inputs_stop_before_provider_and_budget(monkeypatch, value, position, form):
    record = _escaped_record(value, "fullName" if value in NAMES else "opaque")
    if form == "nested":
        record = json.dumps({"records": [{"encoded": record}]}, ensure_ascii=False)
    evidence, question = {"official": {}, "document": "일반 문서 자료"}, "제공 자료 대조"
    if position == "official":
        evidence["official"] = {"full_text": record}
    elif position == "document":
        evidence["document"] = record
    else:
        question = record
    router, sent, reserved = _router(monkeypatch)
    receipts = []
    router.on_execution = lambda item: receipts.append(item.to_dict())
    result = asyncio.run(router.cascade(question=question, evidence=evidence))
    assert sent == reserved == []
    assert result.executions
    assert all(item.input_privacy["failure_code"] == "PII_INPUT_BLOCKED" for item in result.executions)
    assert all(item.cost_status == "NOT_SENT" for item in result.executions)
    assert value not in json.dumps(receipts, ensure_ascii=False)


@pytest.mark.parametrize("value", PHONES + RRNS + NAMES)
def test_actual_critic_scans_parsed_primary_reply(monkeypatch, value):
    rationale = _escaped_record(value, "fullName" if value in NAMES else "opaque")
    router, sent, reserved = _router(monkeypatch, primary_rationale=rationale)
    result = asyncio.run(router.cascade(question="제공 자료 대조", evidence={"official": {}}))
    assert len(sent) == len(reserved) == 1
    assert sent[0][0] == "anthropic"
    assert any(item.input_privacy.get("failure_code") == "PII_INPUT_BLOCKED" for item in result.executions)


@pytest.mark.parametrize("profile", (VerificationProfile.STANDARD, VerificationProfile.DEEP_VERIFY))
@pytest.mark.parametrize("document", (
    '{"holding":"일반 법령 검토 자료"}',
    '{"holding":"일반 자료","holding":"초록환경 관측자료"}',
    '{"opaque":"문서함"}',
))
def test_actual_three_roles_preserve_legacy_wire_payloads_and_benign_json(monkeypatch, profile, document):
    evidence = {"official": {"confirmed_metadata": {"court": "초록행정법원", "case_name": "자료 열람"}},
                "document": document}
    router, sent, reserved = _router(monkeypatch)
    result = asyncio.run(router.cascade(question="제공 자료 대조", evidence=evidence, profile=profile))
    assert len(sent) == len(reserved) == 3
    verdict = {"status": "VERIFIED", "rationale": "일반 자료 확인", "confidence": 0.95,
               "evidence_quotes": [], "contradicts": False}
    for index, (_, request) in enumerate(sent):
        assert request.system == f"{module.SYSTEM_BASE}\n[역할] {(LLMRole.PRIMARY_REASONER, LLMRole.INDEPENDENT_CRITIC, LLMRole.WEB_GROUNDER)[index]}\n{SYSTEMS[index]}"
        assert request.user == module._build_prompt("제공 자료 대조", evidence, verdict if index == 1 else None)
        assert request.schema == module._VERDICT_SCHEMA
        assert request.max_tokens == module._VERDICT_MAX_TOKENS
        assert request.input_contract is None
    assert all(item.input_privacy["status"] == "PASSED" for item in result.executions)


@pytest.mark.parametrize("mutation", ("user", "system", "role", "schema", "json_marker", "redacted_copy", "uninitialized", "removed"))
def test_present_invalid_source_never_falls_back_to_legacy(monkeypatch, mutation):
    request = cascade_source.build_cascade_request("primary", "제공 자료 대조", {"official": {}, "document": "일반 자료"})
    role = LLMRole.PRIMARY_REASONER
    if mutation == "user":
        request = replace(request, user=request.user + " ")
    elif mutation == "system":
        request = replace(request, system=SYSTEMS[1])
    elif mutation == "role":
        role = LLMRole.INDEPENDENT_CRITIC
    elif mutation == "schema":
        request = replace(request, schema={**request.schema, "additionalProperties": False})
    elif mutation == "json_marker":
        request = replace(request, inspection_source={"stage": "primary", "source": "일반 자료"})
    elif mutation == "redacted_copy":
        request = copy.deepcopy(request)
    elif mutation == "removed":
        request = replace(request, inspection_source=None)
    else:
        request = replace(request, inspection_source=object.__new__(cascade_source._CascadeSource))
    result, sent, reserved, _ = _run(monkeypatch, request, role=role)
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "INPUT_CONTRACT_VIOLATION"


@pytest.mark.parametrize("bad_primary", (None, "ordinary reply", ["ordinary reply"]))
def test_malformed_critic_primary_reply_fails_closed(monkeypatch, bad_primary):
    request = cascade_source.build_cascade_request("critic", "제공 자료 대조", {"official": {}}, primary_verdict=bad_primary)
    result, sent, reserved, _ = _run(monkeypatch, request, role=LLMRole.INDEPENDENT_CRITIC)
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "INPUT_CONTRACT_VIOLATION"


def test_empty_primary_verdict_retains_original_critic_prompt(monkeypatch):
    request = cascade_source.build_cascade_request("critic", "제공 자료 대조", {"official": {}}, primary_verdict={})
    assert request.user == module._build_prompt("제공 자료 대조", {"official": {}}, {})
    assert cascade_source.valid_cascade_source(request)
    _, sent, reserved, _ = _run(monkeypatch, request, role=LLMRole.INDEPENDENT_CRITIC)
    assert len(sent) == len(reserved) == 1


@pytest.mark.parametrize("where", ("source", "original_system", "metadata", "schema"))
def test_pii_precedence_and_all_existing_paths_survive_source_mismatch(monkeypatch, where):
    record = _escaped_record(PHONES[0])
    evidence = {"official": {}, "document": record if where == "source" else "일반 자료"}
    request = cascade_source.build_cascade_request("primary", "제공 자료 대조", evidence)
    request = replace(request, user=request.user + " ")
    if where == "original_system":
        request = replace(request, system=json.dumps({"contact": PHONES[0]}))
    elif where == "metadata":
        request = replace(request, metadata={"encoded": record})
    elif where == "schema":
        request = replace(request, schema={"type": "object", "default": {"contact": PHONES[0]}})
    result, sent, reserved, receipts = _run(monkeypatch, request)
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"
    assert PHONES[0] not in json.dumps(receipts, ensure_ascii=False)


def test_snapshot_freezes_input_and_replace_preserves_request_context(monkeypatch):
    evidence = {"official": {"full_text": "일반 법령 자료", "nested": [{"holding": "일반 기록"}]}, "document": "일반 문서 자료"}
    request = cascade_source.build_cascade_request("primary", "제공 자료 대조", evidence)
    original_user, source = request.user, request.inspection_source
    evidence["official"]["nested"][0]["holding"] = PHONES[0]
    evidence["document"] = _escaped_record(PHONES[1])
    assert request.user == original_user
    assert PHONES[0] not in source._inspection_text()
    with pytest.raises(AttributeError):
        source._CascadeSource__snapshot = "{}"
    with pytest.raises(AttributeError):
        del source._CascadeSource__snapshot
    request = replace(request, max_tokens=100, temperature=0.1)
    assert request.inspection_source is source
    _, sent, reserved, _ = _run(monkeypatch, request)
    assert len(sent) == len(reserved) == 1 and sent[0][1].user == original_user


def test_output_schema_mutation_is_detected_without_mutating_the_constant(monkeypatch):
    request = cascade_source.build_cascade_request("primary", "제공 자료 대조", {"official": {}})
    before = copy.deepcopy(module._VERDICT_SCHEMA)
    request.schema["properties"]["rationale"]["type"] = "number"
    assert module._VERDICT_SCHEMA == before
    result, sent, reserved, _ = _run(monkeypatch, request)
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "INPUT_CONTRACT_VIOLATION"


def test_source_receipt_hashes_untrusted_field_keys(monkeypatch):
    request = cascade_source.build_cascade_request("primary", "제공 자료 대조", {
        "official": {"slot_" + NAMES[0]: _escaped_record(NAMES[1], "fullName")}})
    result, sent, reserved, receipts = _run(monkeypatch, request)
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"
    for name in NAMES[:2]:
        assert name not in json.dumps(receipts, ensure_ascii=False)
    assert any(path.startswith("cascade_source.") for path in result.executions[0].input_privacy["detected_field_paths"])


@pytest.mark.parametrize("mode", ("retry", "fallback"))
def test_actual_retry_fallback_carry_request_local_source(monkeypatch, mode):
    router, sent, reserved = _router(monkeypatch, transient=mode == "retry", primary_failure=mode == "fallback")
    result = asyncio.run(router.cascade(question="제공 자료 대조", evidence={"official": {}, "document": "일반資料"}))
    assert result.executions
    for _, request in sent:
        assert type(request.inspection_source) is cascade_source._CascadeSource
    if mode == "retry":
        assert len(sent) == 6 and len(reserved) == 3
        for index in (0, 2, 4):
            assert sent[index][1] is sent[index + 1][1]
    else:
        assert len(sent) == len(reserved) == 3
        assert sent[0][1].inspection_source is sent[1][1].inspection_source


@pytest.mark.parametrize("early", ("quick", "deterministic"))
def test_early_cascade_paths_do_not_build_sources_or_dispatch(monkeypatch, early):
    router, sent, reserved = _router(monkeypatch)
    monkeypatch.setattr(cascade_source, "build_cascade_request", lambda *a, **k: pytest.fail("early path built a source"))
    kwargs = ({"profile": VerificationProfile.QUICK, "severity_hint": Severity.LOW} if early == "quick"
              else {"deterministic": {"conclusive": True, "status": "VERIFIED", "evidence_grade": "A"}})
    asyncio.run(router.cascade(question="제공 자료 대조", evidence={"official": {}}, **kwargs))
    assert sent == reserved == []


@pytest.mark.parametrize("policy", (ExternalAIPolicy.MASKED, ExternalAIPolicy.ORIGINAL, ExternalAIPolicy.LOCAL_ONLY))
def test_cloud_policy_behavior_is_preserved_for_valid_source(monkeypatch, policy):
    request = cascade_source.build_cascade_request("primary", "제공 자료 대조", {"document": _escaped_record(PHONES[0])})
    _, sent, reserved, _ = _run(monkeypatch, request, policy=policy)
    expected = 1 if policy == ExternalAIPolicy.ORIGINAL else 0
    assert len(sent) == len(reserved) == expected


@pytest.mark.parametrize("invalid", (False, True))
def test_local_provider_keeps_local_pii_policy_but_requires_valid_source(monkeypatch, invalid):
    router, sent, reserved = _router(monkeypatch)
    provider = router.providers["anthropic"]
    provider.config.kind = "local"
    request = cascade_source.build_cascade_request("primary", "제공 자료 대조", {"document": _escaped_record(PHONES[0])})
    if invalid:
        request = replace(request, user=request.user + " ")
    result = asyncio.run(router.run(LLMRole.PRIMARY_REASONER, request, policy=ExternalAIPolicy.LOCAL_ONLY))
    assert reserved == []
    assert len(sent) == (0 if invalid else 1)
    if invalid:
        assert result.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"


@pytest.mark.parametrize("adapter", (OpenAIProvider, AnthropicProvider, GeminiProvider, LocalLLMProvider))
def test_source_is_redacted_from_asdict_repr_receipts_and_provider_wire(monkeypatch, caplog, adapter):
    request = cascade_source.build_cascade_request("primary", "제공 자료 대조", {"official": {"full_text": "일반 자료"}})
    source = request.inspection_source
    raw_snapshot = source._inspection_text()
    serialized = asdict(request)
    assert serialized["inspection_source"] == "<cascade inspection source>"
    assert raw_snapshot not in repr(source)
    assert raw_snapshot not in repr(request)
    assert raw_snapshot not in json.dumps(serialized, ensure_ascii=False, default=str)
    body = []

    class Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, *, headers=None, json=None, **kwargs):
            body.append(json)
            return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}],
                "content": [{"type": "text", "text": "{}"}],
                "candidates": [{"content": {"parts": [{"text": "{}"}]}}]})

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    monkeypatch.setenv("SYNTHETIC_PROVIDER_KEY", "synthetic")
    config = ProviderConfig(name="synthetic", enabled=True, api_key_env="SYNTHETIC_PROVIDER_KEY",
                            model="synthetic", base_url="https://synthetic.invalid", kind="local" if adapter is LocalLLMProvider else "cloud")
    provider = adapter(config)
    provider.settings = replace(provider.settings, allow_network=True)
    asyncio.run(provider.generate(request))
    assert body
    assert all("inspection_source" not in payload for payload in body)
    assert raw_snapshot not in json.dumps(body, ensure_ascii=False)
    report = privacy.inspect_request(request)
    assert raw_snapshot not in json.dumps(report, ensure_ascii=False)
    assert raw_snapshot not in caplog.text
