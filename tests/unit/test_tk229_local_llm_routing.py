"""TK-229: Local LLM config, health_check, schema validation, and LOCAL_ONLY routing tests."""
from __future__ import annotations

import asyncio
import json
import pytest
import httpx

from packages.common.config import Settings, _default_providers
from packages.common.enums import ExternalAIPolicy, LLMRole
from packages.llm_router.providers import LLMRequest, LocalLLMProvider, NullProvider
from packages.llm_router.router import LLMRouter
from packages.verification_engine.environment import next_gen_feature_diagnostics


# ---------------------------------------------------------------------------
# Positive tests (3+)
# ---------------------------------------------------------------------------


def test_env_override_enables_local_provider_and_sets_url_model_api_key(monkeypatch):
    monkeypatch.setenv("LV_LOCAL_LLM_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("LV_LOCAL_LLM_MODEL", "qwen2.5-7b-instruct")
    monkeypatch.setenv("LV_LOCAL_LLM_API_KEY", "local-secret-token")

    providers = _default_providers()
    local_cfg = providers["local"]
    assert local_cfg.enabled is True
    assert local_cfg.base_url == "http://127.0.0.1:8000/v1"
    assert local_cfg.model == "qwen2.5-7b-instruct"
    assert local_cfg.api_key == "local-secret-token"

    provider = LocalLLMProvider(local_cfg)
    assert provider.available is True

    settings = Settings(providers=providers)
    diag = next_gen_feature_diagnostics(settings)
    assert diag["local_llm"]["registered"] is True
    assert diag["local_llm"]["provider_count"] == 1
    assert diag["local_llm"]["providers"][0]["endpoint_configured"] is True


def test_local_provider_health_check_and_schema_validated_generate_updates_call_stats(monkeypatch):
    monkeypatch.setenv("LV_LOCAL_LLM_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("LV_LOCAL_LLM_API_KEY", "bearer-test-key")
    cfg = _default_providers()["local"]
    provider = LocalLLMProvider(cfg)

    seen_auth_headers = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_auth_headers.append(request.headers.get("authorization"))
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": cfg.model}]})
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(
                200,
                json={
                    "model": cfg.model,
                    "choices": [{"message": {"content": json.dumps({"verdict": "VALID", "confidence": 0.9})}}],
                    "usage": {"prompt_tokens": 120, "completion_tokens": 35},
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    orig_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: orig_client(*a, **{**kw, "transport": transport}))

    async def _run():
        hc = await provider.health_check()
        assert hc["ok"] is True
        assert hc["status_code"] == 200

        schema = {
            "type": "object",
            "required": ["verdict", "confidence"],
            "properties": {
                "verdict": {"type": "string"},
                "confidence": {"type": "number"},
            },
        }
        req = LLMRequest(system="Classify", user="Sample text")
        resp = await provider.structured_output(schema, req)
        assert resp.ok is True
        assert resp.parsed == {"verdict": "VALID", "confidence": 0.9}

    asyncio.run(_run())
    assert provider.call_stats["calls"] == 1
    assert provider.call_stats["successes"] == 1
    assert provider.call_stats["failures"] == 0
    assert provider.call_stats["total_input_tokens"] == 120
    assert provider.call_stats["total_output_tokens"] == 35
    assert seen_auth_headers == ["Bearer bearer-test-key", "Bearer bearer-test-key"]


def test_local_only_policy_routes_exclusively_to_local_provider(monkeypatch):
    monkeypatch.setenv("LV_LOCAL_LLM_URL", "http://127.0.0.1:8000/v1")
    providers_cfg = _default_providers()

    class FakeCloudProvider(NullProvider):
        def __init__(self, cfg):
            super().__init__(cfg)
            self.called = False

        @property
        def available(self) -> bool:
            return True

        async def generate(self, request: LLMRequest):
            self.called = True
            return await super().generate(request)

    local_provider = LocalLLMProvider(providers_cfg["local"])
    cloud_provider = FakeCloudProvider(providers_cfg["openai"])
    router = LLMRouter(providers={"openai": cloud_provider, "local": local_provider})

    avail = router.available_providers(policy=ExternalAIPolicy.LOCAL_ONLY)
    assert avail == ["local"]
    picked = router.pick(LLMRole.PRIMARY_REASONER, policy=ExternalAIPolicy.LOCAL_ONLY)
    assert picked is local_provider
    assert cloud_provider.called is False


# ---------------------------------------------------------------------------
# Control tests (3+)
# ---------------------------------------------------------------------------


def test_local_provider_disabled_by_default_without_url(monkeypatch):
    monkeypatch.delenv("LV_LOCAL_LLM_URL", raising=False)
    monkeypatch.delenv("LV_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("LV_LOCAL_LLM_ENABLED", raising=False)

    providers_cfg = _default_providers()
    local_cfg = providers_cfg["local"]
    assert local_cfg.enabled is False

    provider = LocalLLMProvider(local_cfg)
    assert provider.available is False

    router = LLMRouter(providers={"local": provider})
    assert router.available_providers(policy=ExternalAIPolicy.LOCAL_ONLY) == []


def test_invalid_json_or_schema_mismatch_fails_closed_without_success_credit(monkeypatch):
    monkeypatch.setenv("LV_LOCAL_LLM_URL", "http://127.0.0.1:8000/v1")
    cfg = _default_providers()["local"]
    provider = LocalLLMProvider(cfg)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": cfg.model,
                "choices": [{"message": {"content": json.dumps({"wrong_field": 123})}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    transport = httpx.MockTransport(handler)
    orig_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: orig_client(*a, **{**kw, "transport": transport}))

    req = LLMRequest(
        system="Classify",
        user="Sample",
        schema={"type": "object", "required": ["verdict"], "properties": {"verdict": {"type": "string"}}},
    )
    resp = asyncio.run(provider.generate(req))
    assert resp.ok is False
    assert "LOCAL_SCHEMA_VALIDATION_FAILED" in resp.error
    assert provider.call_stats["calls"] == 1
    assert provider.call_stats["successes"] == 0
    assert provider.call_stats["failures"] == 1


def test_http_500_or_connection_error_increments_failures(monkeypatch):
    monkeypatch.setenv("LV_LOCAL_LLM_URL", "http://127.0.0.1:8000/v1")
    cfg = _default_providers()["local"]
    provider = LocalLLMProvider(cfg)

    def handler_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(handler_500)
    orig_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: orig_client(*a, **{**kw, "transport": transport}))

    async def _run():
        hc = await provider.health_check()
        assert hc["ok"] is False
        assert hc["status_code"] == 503

        resp = await provider.generate(LLMRequest(system="S", user="U"))
        assert resp.ok is False
        assert "503" in resp.error

    asyncio.run(_run())
    assert provider.call_stats["calls"] == 1
    assert provider.call_stats["successes"] == 0
    assert provider.call_stats["failures"] == 1
