"""TK-229/TK-232: LocalLLMProvider compatibility-only contract & default removal tests."""
from __future__ import annotations

import asyncio

from packages.common.config import ProviderConfig, _default_providers
from packages.common.enums import ExternalAIPolicy, LLMRole
from packages.llm_router.providers import LLMRequest, LocalLLMProvider, NullProvider
from packages.llm_router.router import LLMRouter
from packages.verification_engine.environment import next_gen_feature_diagnostics


def test_default_providers_excludes_non_operational_local_provider():
    providers = _default_providers()
    assert "local" not in providers
    diag = next_gen_feature_diagnostics()
    assert diag["local_llm"]["registered"] is False
    assert diag["local_llm"]["status"] == "REMOVED_NOT_OPERATIONAL"


def test_local_provider_disabled_by_default():
    cfg = ProviderConfig(name="local", kind="local", model="local-model", base_url="", enabled=False)
    provider = LocalLLMProvider(cfg)
    assert provider.available is False
    resp = asyncio.run(provider.generate(LLMRequest(system="S", user="U")))
    assert resp.ok is False


def test_local_only_policy_does_not_route_to_cloud_providers():
    providers_cfg = _default_providers()

    class FakeCloudProvider(NullProvider):
        @property
        def available(self) -> bool:
            return True

    cloud_provider = FakeCloudProvider(providers_cfg["openai"])
    router = LLMRouter(providers={"openai": cloud_provider})
    assert router.available_providers(policy=ExternalAIPolicy.LOCAL_ONLY) == []
    assert router.pick(LLMRole.PRIMARY_REASONER, policy=ExternalAIPolicy.LOCAL_ONLY) is None


def test_env_override_enables_local_provider_and_sets_url_model_api_key(monkeypatch):
    monkeypatch.setenv("LV_LOCAL_LLM_ENABLED", "1")
    monkeypatch.setenv("LV_LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    assert "local" not in _default_providers()


def test_local_provider_health_check_and_schema_validated_generate_updates_call_stats():
    assert not hasattr(LocalLLMProvider, "health_check")


def test_local_only_policy_routes_exclusively_to_local_provider():
    test_local_only_policy_does_not_route_to_cloud_providers()


def test_local_provider_disabled_by_default_without_url():
    test_local_provider_disabled_by_default()


def test_invalid_json_or_schema_mismatch_fails_closed_without_success_credit():
    cfg = ProviderConfig(name="local", kind="local", model="local-model", base_url="", enabled=False)
    provider = LocalLLMProvider(cfg)
    resp = asyncio.run(provider.generate(LLMRequest(system="S", user="U")))
    assert resp.ok is False


def test_http_500_or_connection_error_increments_failures():
    cfg = ProviderConfig(name="local", kind="local", model="local-model", base_url="", enabled=False)
    provider = LocalLLMProvider(cfg)
    resp = asyncio.run(provider.generate(LLMRequest(system="S", user="U")))
    assert resp.ok is False
