from __future__ import annotations

from types import SimpleNamespace

from packages.common.config import Settings
from packages.common.enums import AdapterStatus
from packages.source_adapters.academic import SemanticScholarAdapter
from packages.source_adapters.law_go_kr import LawGoKrAdapter


def _make_adapter(monkeypatch, responses: list[dict]) -> tuple[LawGoKrAdapter, list[dict]]:
    calls: list[dict] = []
    adapter = LawGoKrAdapter()
    adapter.settings = Settings(allow_network=True, law_go_kr_oc="test_oc")

    def fake_get(url: str, params: dict | None = None, **kwargs):
        calls.append(dict(params or {}))
        idx = min(len(calls) - 1, len(responses) - 1)
        return SimpleNamespace(status_code=200, json=lambda p=responses[idx]: p)

    monkeypatch.setattr(adapter, "_http_get", fake_get)
    return adapter, calls


def test_law_go_kr_case_number_variant_positives(monkeypatch):
    # Pos 1: Re-appeal decision (모) with fullwidth digits and spaces
    a1, c1 = _make_adapter(monkeypatch, [
        {"PrecSearch": {"totalCnt": "1", "prec": [{"판례일련번호": "1001", "사건번호": "２０１５ 모 ２５２４(재항고)", "법원명": "대법원", "선고일자": "2015.11.27"}]}}
    ])
    r1 = a1.search_case("２０１５\u200b모 ２５２４")
    assert r1.status == AdapterStatus.READY and len(r1.records) == 1
    assert c1[0].get("nb") == "2015모2524"

    # Pos 2: Empty 사건번호 field, case number carried in 사건명
    a2, _ = _make_adapter(monkeypatch, [
        {"PrecSearch": {"totalCnt": "1", "prec": [{"판례일련번호": "1002", "사건번호": "", "사건명": "재항고기각결정에대한재항고 [2015모2524]", "법원명": "대법원"}]}}
    ])
    r2 = a2.search_case("2015모2524")
    assert r2.status == AdapterStatus.READY and len(r2.records) == 1

    # Pos 3: Merged case number with hyphen/dot separators
    a3, _ = _make_adapter(monkeypatch, [
        {"PrecSearch": {"totalCnt": "1", "prec": [{"판례일련번호": "1003", "사건번호": "2019-다-54321, 2019. 다. 54322", "법원명": "대법원"}]}}
    ])
    r3 = a3.search_case("2019. 다. 54322")
    assert r3.status == AdapterStatus.READY and len(r3.records) == 1


def test_law_go_kr_case_number_false_match_controls(monkeypatch):
    # Ctrl 1: Prefix-similar serial (2015모252 vs 2015모2524) must NOT match
    a1, _ = _make_adapter(monkeypatch, [
        {"PrecSearch": {"totalCnt": "1", "prec": [{"판례일련번호": "2001", "사건번호": "2015모252", "법원명": "대법원"}]}}
    ])
    r1 = a1.search_case("2015모2524")
    assert r1.records == [] and r1.diagnostics["cause"] == "FILTER_REJECTED_ALL"

    # Ctrl 2: Different year (2016모2524 vs 2015모2524) must NOT match
    a2, _ = _make_adapter(monkeypatch, [
        {"PrecSearch": {"totalCnt": "1", "prec": [{"판례일련번호": "2002", "사건번호": "2016모2524", "법원명": "대법원"}]}}
    ])
    r2 = a2.search_case("2015모2524")
    assert r2.records == [] and r2.diagnostics["cause"] == "FILTER_REJECTED_ALL"

    # Ctrl 3: Different case code (2015도2524 vs 2015모2524) must NOT match
    a3, _ = _make_adapter(monkeypatch, [
        {"PrecSearch": {"totalCnt": "1", "prec": [{"판례일련번호": "2003", "사건번호": "2015도2524", "법원명": "대법원"}]}}
    ])
    r3 = a3.search_case("2015모2524")
    assert r3.records == [] and r3.diagnostics["cause"] == "FILTER_REJECTED_ALL"


def test_semantic_scholar_no_key_429_uses_fast_backoff(monkeypatch):
    adapter = SemanticScholarAdapter()
    adapter.settings = Settings(allow_network=True, semantic_scholar_key=None)
    calls = []

    def fake_get(url: str, params: dict | None = None, headers: dict | None = None):
        calls.append(url)
        return SimpleNamespace(status_code=429, headers={})

    monkeypatch.setattr(adapter, "_http_get", fake_get)
    resp = adapter.search("tort liability")
    assert resp.status == AdapterStatus.RATE_LIMITED
    assert resp.diagnostics["attempts"] == 3
