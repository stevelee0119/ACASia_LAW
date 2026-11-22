"""Unit tests for LocalLLMProvider compatibility adapter (TK-232)."""
from __future__ import annotations

import asyncio
from typing import Any, Dict

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


def test_local_llm_compat_generate_and_usage(monkeypatch):
    class _FakeClient:
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
                    "choices": [{"message": {"content": '{"verdict":"SUPPORTED"}'}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 120, "completion_tokens": 18},
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
    provider = LocalLLMProvider(
        ProviderConfig(name="local", enabled=True, model="mock-local", base_url="http://localhost:8000/v1", kind="local")
    )
    resp = asyncio.run(provider.generate(LLMRequest(system="Judge", user="Check", max_tokens=256)))
    assert resp.ok is True
    assert resp.input_tokens == 120
    assert resp.output_tokens == 18


def test_local_llm_disabled_returns_error():
    provider = LocalLLMProvider(
        ProviderConfig(name="local", enabled=False, model="mock-local", base_url="", kind="local")
    )
    resp = asyncio.run(provider.generate(LLMRequest(system="Judge", user="Check")))
    assert resp.ok is False
