"""TK-78: public synthetic requests only; no live APIs or legal quality scoring."""
import asyncio
import copy
from dataclasses import replace
from decimal import Decimal

import pytest

from packages.common.config import Settings, get_settings
from packages.common.enums import LLMRole, Severity, VerificationProfile
from packages.llm_router.budget import effective_pricing, usage_cost
from packages.llm_router.providers import LLMRequest, LLMResponse
from packages.llm_router.router import LLMRouter
from test_efficient_llm_routing import transport, authorship_request  # noqa: F401
from test_operations_completion import ops, seeded_run, completed  # noqa: F401


# 0.13.0 production commit b68cfeec2c5c168a3b9e6e2e92653ea6892521bf.
LEGACY_MODELS = {"anthropic": "claude-opus-5-5", "openai": "gpt-6-luna",
                 "gemini": "gemini-3.8-flash", "local": "local-model"}
ROUTING_FIELDS = {"llm_cross_check", "llm_efficient_routing", "llm_prompt_caching",
                  "llm_review_sample_percent", "llm_routing", "llm_model_overrides", "llm_default_models"}


@pytest.fixture
def unset_routing_env(monkeypatch):
    for key in ("LV_LLM_CROSS_CHECK", "LV_LLM_EFFICIENT_ROUTING", "LV_LLM_PROMPT_CACHING",
                "LV_LLM_REVIEW_SAMPLE_PERCENT", *("LV_" + name.upper() + "_MODEL" for name in
                (*LEGACY_MODELS, "anthropic_review", "openai_review", "openai_extraction", "anthropic_escalation"))):
        monkeypatch.delenv(key, raising=False)


def make_default_router(transport):
    previous, requests, responses = transport
    settings = Settings(allow_network=True, storage_root=previous.settings.storage_root)
    return LLMRouter(settings=settings, ledger=previous.ledger), requests, responses


def sent_models(requests):
    return [body.get("model") or url.split("/models/")[1].split(":")[0] for url, body in requests]


def test_unset_environment_restores_0130_models_and_all(unset_routing_env, tmp_path):
    settings = Settings(storage_root=tmp_path)
    assert not settings.llm_efficient_routing and not settings.llm_prompt_caching
    assert settings.llm_cross_check == "all"
    assert {name: provider.model for name, provider in settings.providers.items()} == LEGACY_MODELS


@pytest.mark.parametrize("contract", ["plain", "authorship", "argument"])
def test_off_uses_all_legacy_models_and_does_not_reuse_requests(transport, unset_routing_env, contract):
    router, requests, responses = make_default_router(transport)
    request = LLMRequest("system", "synthetic text")
    if contract == "authorship":
        request = authorship_request()
        responses.update({name: {"verdict": "UNCERTAIN"} for name in LEGACY_MODELS})
    elif contract == "argument":
        import json
        from packages.legal_engine.argument_validity_verifier import _OPINION_SCHEMA, _OPINION_SYSTEM
        request = LLMRequest(_OPINION_SYSTEM, json.dumps({"items": [{"item_id": 1, "page": 1,
            "cited_case": "synthetic", "확인 상태": "미확인", "surrounding_context_and_claim": "synthetic"}]}),
            schema=_OPINION_SCHEMA, input_contract="argument_review_v1")
        responses.update({name: {"rows": [{"item_id": 1, "validity_verdict": "판단 불가"}]}
                          for name in LEGACY_MODELS})
    for _ in range(2):
        answers = asyncio.run(router.consult_all(LLMRole.PRIMARY_REASONER, request))
        assert len(answers) == 3 and all(a.used for a in answers)
        assert not any(e.reused for a in answers for e in a.executions)
    assert sent_models(requests) == ["claude-opus-5-5", "gpt-6-luna", "gemini-3.8-flash"] * 2
    assert all("cache_control" not in body for _, body in requests)


def test_off_cascade_retains_0130_wire_and_three_calls(transport, unset_routing_env):
    router, requests, responses = make_default_router(transport)
    responses["anthropic"] = {"status": "VERIFIED", "confidence": 1, "rationale": "synthetic"}
    result = asyncio.run(router.cascade(question="q", evidence={"official": {"full_text": "source"}}))
    assert sent_models(requests) == ["claude-opus-5-5", "gpt-6-luna", "gemini-3.8-flash"]
    assert '"confidence": 1' in requests[1][1]["messages"][1]["content"]
    assert not any(s["name"] == "escalation" for s in result.stages)


@pytest.mark.parametrize("confidence,count", [(1, 1), (0.5, 2)])
def test_explicit_auto_with_efficiency_off_keeps_legacy_thresholds(transport, unset_routing_env, confidence, count):
    router, requests, responses = make_default_router(transport)
    router.settings.llm_cross_check = "auto"
    responses["anthropic"] = {"status": "VERIFIED", "confidence": confidence, "rationale": "synthetic"}
    responses["openai"] = {"status": "CONTRADICTED", "rationale": "synthetic"}
    asyncio.run(router.cascade(question="q", evidence={}, profile=VerificationProfile.STANDARD,
                              severity_hint=Severity.LOW))
    assert len(requests) == count


def test_on_flag_selects_task_models_without_changing_provider_defaults(transport, unset_routing_env, monkeypatch):
    monkeypatch.setenv("LV_LLM_EFFICIENT_ROUTING", "1")
    router, requests, _ = make_default_router(transport)
    request = LLMRequest("system", "synthetic text")
    for role, req in [(LLMRole.PRIMARY_REASONER, request), (LLMRole.INDEPENDENT_CRITIC, request),
                      (LLMRole.LOW_COST_EXTRACTOR, request),
                      (LLMRole.PRIMARY_REASONER, replace(request, model_tier="escalation"))]:
        exclude = ["gemini", "anthropic"] if role == LLMRole.LOW_COST_EXTRACTOR else None
        assert asyncio.run(router.run(role, req, exclude=exclude)).used
    assert sent_models(requests) == ["claude-sonnet-5-5", "gpt-6.1-sol", "gpt-6-luna", "claude-opus-5-5"]
    assert {name: p.model for name, p in router.settings.providers.items()} == LEGACY_MODELS


@pytest.mark.parametrize("model,read_rate", [("claude-sonnet-5-5", "0.2"),
    ("gpt-6.1-sol", "0.1"), ("gpt-6-luna", "0.01")])
def test_configured_cache_rates_are_used_in_settlement(tmp_path, model, read_rate):
    settings = Settings(storage_root=tmp_path)
    pricing = settings.pricing[model]
    response = LLMResponse(True, input_tokens=1_000_000, output_tokens=1, cache_read_tokens=1_000_000)
    cost, status = usage_cost(response, (Decimal(str(pricing["input"])), Decimal(str(pricing["output"]))),
                              Decimal(10), pricing=pricing)
    expected = Decimal(read_rate) + Decimal(str(pricing["output"])) / Decimal(1_000_000)
    assert status == "REPORTED" and cost == expected


@pytest.mark.parametrize("day,rates", [("2026-12-31", (.75, 3.75, .075)), ("2027-01-01", (1.5, 7.5, .15))])
def test_gemini_promotion_checks_all_three_rates(transport, day, rates):
    router, _, _ = transport
    table = effective_pricing(router.settings, router.providers["gemini"], today=day)
    assert tuple(table[k] for k in ("input", "output", "cache_read")) == rates


def legacy_execution(settings, monkeypatch):
    from apps.api import job_control
    monkeypatch.setattr(job_control, "get_settings", lambda: settings)
    execution = job_control.execution_settings_snapshot()
    for name in ROUTING_FIELDS | {"rag_claim_max_per_document", "rag_claim_budget_seconds", "rag_claim_budget_usd"}:
        execution["settings"].pop(name)
    return execution


@pytest.mark.parametrize("current_on,current_network", [(False, True), (True, True), (True, False)])
def test_legacy_queue_runs_off_and_preserves_frozen_settings(transport, unset_routing_env, monkeypatch,
                                                           current_on, current_network):
    from apps.worker import runtime
    router, _, _ = make_default_router(transport)
    execution = legacy_execution(router.settings, monkeypatch)
    original = copy.deepcopy(execution)
    current = replace(router.settings, llm_efficient_routing=current_on, llm_cross_check="auto",
                      llm_prompt_caching=True, allow_network=current_network,
                      providers={name: replace(p, model="later-operator-model")
                                 for name, p in router.settings.providers.items()})
    monkeypatch.setattr(runtime, "get_settings", lambda: current)
    restored = runtime.snapshot_settings({"execution": execution})
    assert not restored.llm_efficient_routing and not restored.llm_prompt_caching
    assert restored.llm_cross_check == "all" and restored.allow_network == current_network
    assert restored.providers == router.settings.providers and restored.pricing == router.settings.pricing
    assert execution == original
    routed = LLMRouter(settings=restored, ledger=router.ledger)
    assert routed.settings.llm_model_overrides == {}


def test_legacy_job_completes_without_retry_even_when_worker_opted_in(ops, monkeypatch):
    from apps.api.db import VerificationRun
    from apps.api.job_control import DurableJob, JobStore, snapshot_hash
    from apps.worker import runtime
    from packages.verification_engine import VerificationPipeline
    run = seeded_run(ops)
    with ops() as session:
        job = session.get(DurableJob, run.id)
        snapshot = copy.deepcopy(job.snapshot)
        for key in ROUTING_FIELDS | {"rag_claim_max_per_document", "rag_claim_budget_seconds", "rag_claim_budget_usd"}:
            snapshot["execution"]["settings"].pop(key)
        job.snapshot, job.snapshot_hash = snapshot, snapshot_hash(snapshot)
        original_budget_id, original_hash = job.budget_run_id, job.snapshot_hash
        session.commit()
    monkeypatch.setattr(get_settings(), "llm_efficient_routing", True)
    monkeypatch.setattr(get_settings(), "llm_cross_check", "auto")
    calls = []
    def pipeline(self, *args, **kwargs):
        assert not self.settings.llm_efficient_routing
        assert self.settings.llm_cross_check == "all"
        assert self.router.budget_run_id == original_budget_id
        assert self.router.limits == snapshot["execution"]["budget"]
        calls.append(run.id)
        return completed(run)
    monkeypatch.setattr(VerificationPipeline, "run", pipeline)
    runtime.execute(run.id, store=JobStore(ops))
    with ops() as session:
        job = session.get(DurableJob, run.id)
        assert session.get(VerificationRun, run.id).state == "COMPLETED", job.last_error
        assert job.attempts == 1 and job.budget_run_id == original_budget_id
        assert job.snapshot_hash == original_hash
    assert calls == [run.id]


def test_legacy_fallback_still_rejects_unrelated_parser_drift(transport, monkeypatch):
    from apps.worker import runtime
    router, _, _ = transport
    execution = legacy_execution(router.settings, monkeypatch)
    monkeypatch.setattr(runtime, "get_settings", lambda: replace(router.settings, ocr_lang="different"))
    with pytest.raises(runtime.ExecutionSettingsChanged, match="ocr_lang"):
        runtime.snapshot_settings({"execution": execution})


@pytest.mark.parametrize("enabled,expected", [(False, "run"), (True, "run_any")])
def test_claim_rag_fallback_is_opt_in(enabled, expected):
    from types import SimpleNamespace
    from test_tk68_rag_batch_truncation import SimulatedRouter, _make_doc_result, _make_dummy_library
    from packages.llm_router.router import RouterResult
    from packages.rag_engine.review import review_document
    from packages.verification_engine.pipeline import ProjectContext
    text = "Synthetic contract delivery was due before payment."
    result = _make_doc_result(text)
    result.claims = [{"claim_id": "claim-synthetic", "type": "ARGUMENT", "text": text, "page": 1}]
    library = _make_dummy_library([{"source_id": "R1", "title": "Synthetic contract", "text": text, "page": 1}])
    routes = []
    class Router(SimulatedRouter):
        settings = SimpleNamespace(llm_efficient_routing=enabled)
        async def run(self, role, request, **kwargs):
            if request.input_contract == "claim_review_v1":
                routes.append("run")
                return RouterResult(note="Synthetic primary failure")
            return await super().run(role, request, **kwargs)
        async def run_any(self, role, request, **kwargs):
            routes.append("run_any")
            return RouterResult(used=True, parsed={"observations": []})
    pii = SimpleNamespace(mask_text=lambda value: SimpleNamespace(masked_text=value))
    review_document(result, library, Router(text), ProjectContext("synthetic-project"), pii)
    assert routes == [expected]
