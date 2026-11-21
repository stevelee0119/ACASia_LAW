"""TK-224: Official source (law_go_kr) exact lookup & diagnostics and academic source retry/error-cause tests."""
from __future__ import annotations

from dataclasses import replace as dc_replace
from types import SimpleNamespace

import httpx

from packages.common.enums import AdapterStatus
from packages.source_adapters.academic import CrossrefAdapter, OpenAlexAdapter, SemanticScholarAdapter
from packages.source_adapters.law_go_kr import LawGoKrAdapter


def _fake_json_response(status_code: int, payload: dict, headers: dict | None = None):
    return SimpleNamespace(
        status_code=status_code,
        headers=headers or {},
        json=lambda: payload,
        text="",
    )


def _enable_adapter(adapter, monkeypatch):
    adapter.settings = dc_replace(adapter.settings, allow_network=True, law_go_kr_oc="test-oc")
    monkeypatch.setattr("packages.source_adapters.cassette.replay_mode_active", lambda: False)
    return adapter


# ---------------------------------------------------------------------------
# Positive cases (>= 3)
# ---------------------------------------------------------------------------


def test_tk224_pos1_law_go_kr_normalizes_separators_and_matches_via_search2(monkeypatch) -> None:
    """Normalized case number + search=2 fallback matches separator-formatted provider record."""
    adapter = _enable_adapter(LawGoKrAdapter(), monkeypatch)
    seen_params: list[dict] = []

    def _fake_get(url, *, params=None, headers=None, timeout=None):
        seen_params.append(dict(params or {}))
        if "nb" in (params or {}):
            return _fake_json_response(200, {"PrecSearch": {"totalCnt": "0", "prec": []}})
        if (params or {}).get("search") == 2:
            return _fake_json_response(200, {
                "PrecSearch": {
                    "totalCnt": "1",
                    "prec": [{"사건번호": "2019-다-054321", "사건명": "손해배상", "법원명": "대법원", "선고일자": "2020.01.15"}],
                }
            })
        return _fake_json_response(200, {"PrecSearch": {"totalCnt": "0", "prec": []}})

    monkeypatch.setattr(adapter, "_http_get", _fake_get)
    resp = adapter.search_case("2019. 다. 054321")

    assert resp.status == AdapterStatus.READY
    assert len(resp.records) == 1
    assert resp.diagnostics["cause"] == "MATCHED"
    assert resp.diagnostics["normalized_case_number"] == "2019다54321"
    assert resp.diagnostics["provider_raw_count"] == 1
    assert resp.diagnostics["matched_count"] == 1
    assert resp.diagnostics["filtered_out_count"] == 0
    assert seen_params[0].get("nb") == "2019다54321"
    assert seen_params[1].get("search") == 2
    assert seen_params[1].get("query") == "2019다54321"


def test_tk224_pos2_law_go_kr_separates_filter_rejected_all_and_no_provider_results(monkeypatch) -> None:
    """Distinguishes FILTER_REJECTED_ALL (raw>0, matched=0) from NO_PROVIDER_RESULTS (raw=0)."""
    adapter = _enable_adapter(LawGoKrAdapter(), monkeypatch)

    def _fake_get_rejected(url, *, params=None, headers=None, timeout=None):
        if (params or {}).get("search") == 2:
            return _fake_json_response(200, {
                "PrecSearch": {
                    "totalCnt": "2",
                    "prec": [
                        {"사건번호": "2019다99999", "사건명": "관련 판결"},
                        {"사건번호": "2018다54321", "사건명": "유사 번호 판결"},
                    ],
                }
            })
        return _fake_json_response(200, {"PrecSearch": {"totalCnt": "0", "prec": []}})

    monkeypatch.setattr(adapter, "_http_get", _fake_get_rejected)
    resp_rej = adapter.search_case("2019다54321")
    assert resp_rej.status == AdapterStatus.READY
    assert resp_rej.records == []
    assert resp_rej.diagnostics["cause"] == "FILTER_REJECTED_ALL"
    assert resp_rej.diagnostics["provider_raw_count"] == 2
    assert resp_rej.diagnostics["matched_count"] == 0
    assert resp_rej.diagnostics["filtered_out_count"] == 2

    monkeypatch.setattr(
        adapter,
        "_http_get",
        lambda *a, **kw: _fake_json_response(200, {"PrecSearch": {"totalCnt": "0", "prec": []}}),
    )
    resp_empty = adapter.search_case("2019다54321")
    assert resp_empty.status == AdapterStatus.READY
    assert resp_empty.records == []
    assert resp_empty.diagnostics["cause"] == "NO_PROVIDER_RESULTS"
    assert resp_empty.diagnostics["provider_raw_count"] == 0
    assert resp_empty.diagnostics["matched_count"] == 0
    assert resp_empty.diagnostics["filtered_out_count"] == 0


def test_tk224_pos3_academic_retries_transient_429_and_recovers(monkeypatch) -> None:
    """OpenAlexAdapter retries transient 429 and succeeds when subsequent attempt returns 200."""
    adapter = _enable_adapter(OpenAlexAdapter(), monkeypatch)
    calls = {"n": 0}

    def _fake_get(url, *, params=None, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _fake_json_response(429, {}, headers={"Retry-After": "0"})
        return _fake_json_response(200, {
            "results": [{"title": "Contract Remedies Study", "publication_year": 2022, "doi": "10.1000/test", "authorships": []}]
        })

    monkeypatch.setattr(adapter, "_http_get", _fake_get)
    resp = adapter.search("contract remedies")

    assert resp.status == AdapterStatus.READY
    assert len(resp.records) == 1
    assert resp.diagnostics["attempts"] == 2


# ---------------------------------------------------------------------------
# Control cases (>= 3)
# ---------------------------------------------------------------------------


def test_tk224_ctrl1_law_go_kr_fail_closed_never_adopts_different_case_number(monkeypatch) -> None:
    """Fail-Closed: never adopts a different case number even if year or serial partially overlaps."""
    adapter = _enable_adapter(LawGoKrAdapter(), monkeypatch)
    monkeypatch.setattr(
        adapter,
        "_http_get",
        lambda *a, **kw: _fake_json_response(200, {
            "PrecSearch": {
                "totalCnt": "2",
                "prec": [
                    {"사건번호": "2021도9877", "사건명": "2021도9876 관련 판결"},
                    {"사건번호": "2020도9876", "사건명": "다른 연도 사건"},
                ],
            }
        }),
    )
    resp = adapter.search_case("2021도9876")
    assert resp.records == []
    assert resp.diagnostics["matched_count"] == 0
    assert resp.diagnostics["filtered_out_count"] > 0
    assert resp.diagnostics["cause"] == "FILTER_REJECTED_ALL"


def test_tk224_ctrl2_academic_persistent_429_separates_rate_limited_status(monkeypatch) -> None:
    """Persistent 429 on OpenAlex & SemanticScholar maps to RATE_LIMITED (not ERROR) with attempts."""
    for cls in (OpenAlexAdapter, SemanticScholarAdapter):
        adapter = _enable_adapter(cls(), monkeypatch)
        monkeypatch.setattr(
            adapter,
            "_http_get",
            lambda *a, **kw: _fake_json_response(429, {}, headers={"Retry-After": "0"}),
        )
        resp = adapter.search("legal theory")
        assert resp.status == AdapterStatus.RATE_LIMITED
        assert resp.diagnostics["error_cause"] == "RATE_LIMITED"
        assert resp.diagnostics["retryable"] is True
        assert resp.diagnostics["attempts"] == 3


def test_tk224_ctrl3_academic_4xx_no_retry_and_timeout_separated(monkeypatch) -> None:
    """HTTP 400 fails fast without retry (HTTP_4XX), while ReadTimeout maps to TIMEOUT."""
    crossref = _enable_adapter(CrossrefAdapter(), monkeypatch)
    calls = {"n": 0}

    def _fake_400(*a, **kw):
        calls["n"] += 1
        return _fake_json_response(400, {})

    monkeypatch.setattr(crossref, "_http_get", _fake_400)
    resp_400 = crossref.search("bad query")
    assert resp_400.status == AdapterStatus.ERROR
    assert resp_400.diagnostics["error_cause"] == "HTTP_4XX"
    assert resp_400.diagnostics["retryable"] is False
    assert calls["n"] == 1

    openalex = _enable_adapter(OpenAlexAdapter(), monkeypatch)
    monkeypatch.setattr("time.sleep", lambda _s: None)

    def _fake_timeout(*a, **kw):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(openalex, "_http_get", _fake_timeout)
    resp_to = openalex.search("slow query")
    assert resp_to.status == AdapterStatus.TIMEOUT
    assert resp_to.diagnostics["error_cause"] == "TIMEOUT"
    assert resp_to.diagnostics["retryable"] is True
    assert resp_to.diagnostics["attempts"] == 3
