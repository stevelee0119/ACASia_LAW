"""Unit tests for upgraded LocalLLMProvider (P0 PR-01)."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import httpx

from packages.common.config import ProviderConfig
from packages.llm_router.providers import LLMRequest, LocalLLMProvider


class _DummyResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any], text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> Dict[str, Any]:
        return self._payload


def test_local_llm_sends_json_schema_and_tracks_usage(monkeypatch):
    captured_payloads: List[Dict[str, Any]] = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            captured_payloads.append(json)
            return _DummyResponse(
                200,
                {
                    "choices": [{"message": {"content": '{"verdict":"SUPPORTED"}'}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 120, "completion_tokens": 18},
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
    monkeypatch.setenv("LV_LOCAL_LLM_BACKEND", "openai_compat")
    provider = LocalLLMProvider(
        ProviderConfig(name="local", enabled=True, model="qwen-legal-test", base_url="http://localhost:8000/v1", kind="local")
    )
    provider._quirks.clear()

    schema = {"type": "object", "properties": {"verdict": {"type": "string"}}, "required": ["verdict"]}
    resp = asyncio.run(
        provider.structured_output(
            schema,
            LLMRequest(system="Judge claims", user="Check citation", max_tokens=256),
        )
    )
    assert resp.ok is True
    assert resp.parsed == {"verdict": "SUPPORTED"}
    assert resp.input_tokens == 120
    assert resp.output_tokens == 18
    assert resp.usage_complete is True
    assert captured_payloads[0]["response_format"]["type"] == "json_schema"
    assert captured_payloads[0]["response_format"]["json_schema"]["schema"] == schema


def test_local_llm_detects_truncation_via_checked(monkeypatch):
    class _TruncatedClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            return _DummyResponse(
                200,
                {
                    "choices": [{"message": {"content": '{"verdict": "SUP'}, "finish_reason": "length"}],
                    "usage": {"prompt_tokens": 50, "completion_tokens": 64},
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", _TruncatedClient)
    provider = LocalLLMProvider(
        ProviderConfig(name="local", enabled=True, model="trunc-test", base_url="http://localhost:8000/v1", kind="local")
    )
    resp = asyncio.run(provider.generate(LLMRequest(system="sys", user="usr", max_tokens=64)))
    assert resp.ok is False
    assert "OUTPUT_TRUNCATED" in resp.error
    assert resp.input_tokens == 50
    assert resp.output_tokens == 64


def test_local_llm_ollama_format_and_400_quirk_fallback(monkeypatch):
    seen_payloads: List[Dict[str, Any]] = []

    class _FallbackClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            seen_payloads.append(dict(json))
            if "response_format" in json and json["response_format"].get("type") == "json_schema":
                return _DummyResponse(400, {}, text="Unsupported response_format json_schema")
            return _DummyResponse(
                200,
                {
                    "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", _FallbackClient)
    monkeypatch.setenv("LV_LOCAL_LLM_BACKEND", "openai_compat")
    provider = LocalLLMProvider(
        ProviderConfig(name="local", enabled=True, model="quirk-test", base_url="http://localhost:8000/v1", kind="local")
    )
    provider._quirks.clear()
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    resp = asyncio.run(provider.structured_output(schema, LLMRequest(system="sys", user="usr")))
    assert resp.ok is True
    assert resp.parsed == {"ok": True}
    assert len(seen_payloads) == 2
    assert seen_payloads[1]["response_format"] == {"type": "json_object"}
