"""Gemini 모델 gemini-4-hydrogen 전환 설정·단가·표시명 검증."""
from __future__ import annotations

import json
from pathlib import Path

from packages.common.config import get_settings
from packages.report_engine.model_opinions import model_display_name, model_label


ROOT = Path(__file__).resolve().parents[1]


def test_providers_json_uses_gemini_4_hydrogen():
    providers = json.loads((ROOT / "config/providers.json").read_text(encoding="utf-8"))
    assert providers["gemini"]["model"] == "gemini-4-hydrogen"
    settings = get_settings()
    assert settings.providers["gemini"].model == "gemini-4-hydrogen"


def test_pricing_json_has_gemini_4_hydrogen():
    from packages.llm_router.budget import effective_pricing

    pricing = json.loads((ROOT / "config/pricing.json").read_text(encoding="utf-8"))
    assert "gemini-4-hydrogen" in pricing
    hydrogen = pricing["gemini-4-hydrogen"]
    assert hydrogen["input"] == 1.5
    assert hydrogen["output"] == 7.5
    assert hydrogen["cache_read"] == 0.075
    assert "after_2026-12-31" not in hydrogen

    from packages.llm_router.providers import GeminiProvider

    settings = get_settings()
    provider = GeminiProvider(settings.providers["gemini"])
    for day in ("2026-11-15", "2026-12-31", "2027-01-01"):
        table = effective_pricing(settings, provider, today=day)
        assert (table["input"], table["output"], table["cache_read"]) == (1.5, 7.5, 0.075)


def test_model_display_name_formats_gemini_4_hydrogen():
    assert model_display_name("gemini-4-hydrogen") == "Gemini 4 Hydrogen"
    assert model_label("gemini", "gemini-4-hydrogen") == "Gemini · Gemini 4 Hydrogen (gemini-4-hydrogen)"


def test_gemini_provider_omits_temperature_only_for_hydrogen(monkeypatch):
    import asyncio
    from dataclasses import replace
    import httpx
    from packages.llm_router.providers import GeminiProvider, LLMRequest

    seen = []

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, params=None, json=None):
            seen.append((url, json))
            return httpx.Response(200, json={
                "candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
            })

    from packages.common.config import reset_settings
    monkeypatch.setattr(httpx, "AsyncClient", Client)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    reset_settings()
    try:
        settings = get_settings()
        base_cfg = settings.providers["gemini"]
        req = LLMRequest("sys", "user", temperature=0.25, max_tokens=512, schema={"type": "object"})

        for model_name, expect_temp in (
            ("gemini-4-hydrogen", False),
            ("gemini-3.8-flash", True),
            ("operator-custom-gemini", True),
        ):
            cfg = replace(base_cfg, model=model_name, enabled=True)
            res = asyncio.run(GeminiProvider(cfg).generate(req))
            assert res.ok
            url, body = seen[-1]
            assert f"/models/{model_name}:generateContent" in url
            gen_cfg = body["generationConfig"]
            assert gen_cfg["maxOutputTokens"] == 512
            assert gen_cfg["responseMimeType"] == "application/json"
            if expect_temp:
                assert gen_cfg["temperature"] == 0.25
            else:
                assert "temperature" not in gen_cfg
    finally:
        reset_settings()
