"""TK-254: Anthropic 프롬프트 캐시 지점을 고정 지시문(system)에 둔다(합성 입력)."""
from __future__ import annotations

import asyncio
import json

import httpx

from packages.common.config import ProviderConfig, Settings
from packages.llm_router.providers import AnthropicProvider, LLMRequest


def _capture(settings, request, monkeypatch):
    monkeypatch.setenv("TK254_ANTHROPIC_KEY", "synthetic")
    sent = []

    def handler(req: httpx.Request):
        sent.append(json.loads(req.content))
        return httpx.Response(200, json={"content": [{"type": "text", "text": "{}"}], "stop_reason": "end_turn",
                                         "usage": {"input_tokens": 10, "output_tokens": 2,
                                                   "cache_read_input_tokens": 900, "cache_creation_input_tokens": 0}})

    orig = httpx.AsyncClient
    def client(*a, **k):
        k["transport"] = httpx.MockTransport(handler)
        return orig(*a, **k)
    httpx.AsyncClient = client
    try:
        provider = AnthropicProvider(ProviderConfig(name="anthropic", enabled=True, api_key_env="TK254_ANTHROPIC_KEY",
                                                    model="claude-sonnet-5-5",
                                                    base_url="https://api.anthropic.test/v1"))
        provider.settings = settings
        resp = asyncio.run(provider.generate(request))
    finally:
        httpx.AsyncClient = orig
    return sent[-1], resp


def test_tk254_cache_breakpoint_on_system_block_only(tmp_path, monkeypatch):
    settings = Settings(storage_root=tmp_path, llm_prompt_caching=True, allow_network=True)
    body, resp = _capture(settings, LLMRequest("고정 지시문", "매번 바뀌는 입력"), monkeypatch)
    assert "cache_control" not in body
    assert body["system"] == [{"type": "text", "text": "고정 지시문", "cache_control": {"type": "ephemeral"}}]
    assert body["messages"] == [{"role": "user", "content": "매번 바뀌는 입력"}]
    assert resp.cache_read_tokens == 900 and resp.input_tokens == 910


def test_tk254_no_cache_markup_when_disabled_or_system_empty(tmp_path, monkeypatch):
    off = Settings(storage_root=tmp_path, llm_prompt_caching=False, allow_network=True)
    body, _ = _capture(off, LLMRequest("고정 지시문", "입력"), monkeypatch)
    assert body["system"] == "고정 지시문" and "cache_control" not in body
    on = Settings(storage_root=tmp_path, llm_prompt_caching=True, allow_network=True)
    body, _ = _capture(on, LLMRequest("", "입력"), monkeypatch)
    assert body["system"] == "" and "cache_control" not in body


def test_tk254_pricing_has_claude_haiku_5_5_for_measurement():
    """Haiku 5.5 확인 실측 전 단가 등록(공식 표: 10만 토큰 이하 $0.10/$0.50, 캐시 읽기 0.1배, 5분 쓰기 1.25배)."""
    from pathlib import Path
    pricing = json.loads((Path(__file__).resolve().parents[1] / "config" / "pricing.json").read_text(encoding="utf-8"))
    assert pricing["claude-haiku-5-5"] == {"input": 0.1, "output": 0.5, "cache_read": 0.01, "cache_write": 0.125}
    assert pricing["claude-sonnet-5-5"]["cache_read"] == 0.1 and pricing["claude-sonnet-5-5"]["cache_write"] == 2.5
