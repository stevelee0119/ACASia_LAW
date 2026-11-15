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
    pricing = json.loads((ROOT / "config/pricing.json").read_text(encoding="utf-8"))
    assert "gemini-4-hydrogen" in pricing
    assert pricing["gemini-4-hydrogen"]["input"] > 0
    assert pricing["gemini-4-hydrogen"]["output"] > 0


def test_model_display_name_formats_gemini_4_hydrogen():
    assert model_display_name("gemini-4-hydrogen") == "Gemini 4 Hydrogen"
    assert model_label("gemini", "gemini-4-hydrogen") == "Gemini · Gemini 4 Hydrogen (gemini-4-hydrogen)"
