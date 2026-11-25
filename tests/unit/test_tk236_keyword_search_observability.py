"""TK-236 unit tests: keyword search failure observability, secret masking, shape mismatch, and path independence."""
from __future__ import annotations

import httpx

from packages.common.enums import AdapterStatus
from packages.source_adapters.law_go_kr import LawGoKrAdapter
from packages.source_adapters.transport import source_get, source_lookup_session


class _StubResp:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = {}

    def json(self):
        return self._payload


def test_tk236_pos1_transport_retry_exhaustion_records_status_and_masked_body(monkeypatch):
    """양성 1: 재조회 소진 시 HTTP 상태코드·마스킹된 본문 머리·시도별 소요/대기·UPSTREAM_ERROR 분류를 남긴다."""
    async def _fake_fetch(url, *, params=None, headers=None, timeout=10.0):
        return _StubResp(503, text="service unavailable for OC=my_secret_oc_123&foo=bar")

    monkeypatch.setattr("packages.source_adapters.transport._fetch_with_deadline", _fake_fetch)
    monkeypatch.setattr("packages.source_adapters.transport._wait", lambda *a, **kw: None)
    monkeypatch.setattr("packages.source_adapters.transport._pace", lambda *a, **kw: None)

    monkeypatch.setenv("LV_LAW_GO_KR_OC", "my_secret_oc_123")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()

    with source_lookup_session(30.0, max_attempts=2, retry_backoff=0.01):
        try:
            source_get("law_go_kr", "https://www.law.go.kr/DRF/lawSearch.do", params={"target": "prec"})
            raise AssertionError("expected SourceRequestStopped")
        except httpx.RequestError as exc:
            resp = adapter._transport_unavailable("손해배상", exc)
            diag = resp.diagnostics
            assert diag["failure_classification"] == "UPSTREAM_ERROR"
            assert diag["http_status"] == 503
            assert "my_secret_oc_123" not in diag["body_head"]
            assert "oc=***" in diag["body_head"].lower()
            assert len(diag["attempts"]) == 2
            assert all("elapsed_ms" in a and "wait_ms" in a for a in diag["attempts"])


def test_tk236_pos2_shape_mismatch_classified_separately(monkeypatch):
    """양성 2: _case_payload_shape_ok() 실패 응답은 SHAPE_MISMATCH로 별도 분류한다."""
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "test_oc")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()
    monkeypatch.setattr(
        adapter,
        "_http_get",
        lambda url, params=None: _StubResp(200, payload={"unexpected_root": []}, text='{"unexpected_root": []}'),
    )
    resp = adapter.search_cases_by_query("손해배상")
    assert resp.status == AdapterStatus.ERROR
    assert resp.diagnostics["failure_classification"] == "SHAPE_MISMATCH"
    assert resp.diagnostics["http_status"] == 200
    assert "unexpected_root" in resp.diagnostics["body_head"]


def test_tk236_pos3_rate_limited_429_classified_with_masked_body(monkeypatch):
    """양성 3: 429 응답은 RATE_LIMITED 분류와 함께 OC가 마스킹된 body_head를 남긴다."""
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "secret_oc_999")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()
    monkeypatch.setattr(
        adapter,
        "_http_get",
        lambda url, params=None: _StubResp(429, text="rate limit OC=secret_oc_999"),
    )
    resp = adapter.search_cases_by_query("손해배상")
    assert resp.status == AdapterStatus.RATE_LIMITED
    assert resp.diagnostics["failure_classification"] == "RATE_LIMITED"
    assert resp.diagnostics["http_status"] == 429
    assert "secret_oc_999" not in resp.diagnostics["body_head"]


def test_tk236_ctrl1_keyword_failure_does_not_degrade_nb_lookup(monkeypatch):
    """대조 1: 키워드 검색 실패 1건이 사건번호 지정 조회(nb) 결과를 깎지 않는다."""
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "test_oc")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()

    def _fake_get(url, params=None):
        if params and params.get("nb"):
            return _StubResp(
                200,
                payload={"PrecSearch": {"totalCnt": "1", "prec": [{"사건번호": "2021다88001", "사건명": "정상", "판례정보일련번호": "10"}]}},
            )
        return _StubResp(502, text="bad gateway")

    monkeypatch.setattr(adapter, "_http_get", _fake_get)
    kw_resp = adapter.search_cases_by_query("손해배상")
    assert kw_resp.status == AdapterStatus.ERROR
    nb_resp = adapter.search_case("2021다88001")
    assert nb_resp.status == AdapterStatus.READY
    assert len(nb_resp.records) == 1


def test_tk236_ctrl2_normal_keyword_search_returns_ready(monkeypatch):
    """대조 2: 정상 키워드 검색 응답은 READY와 레코드를 반환한다."""
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "test_oc")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()
    monkeypatch.setattr(
        adapter,
        "_http_get",
        lambda url, params=None: _StubResp(
            200,
            payload={"PrecSearch": {"totalCnt": "1", "prec": [{"사건번호": "2021다88002", "사건명": "손해배상", "판례정보일련번호": "11"}]}},
        ),
    )
    resp = adapter.search_cases_by_query("손해배상")
    assert resp.status == AdapterStatus.READY
    assert len(resp.records) == 1


def test_tk236_ctrl3_timeout_classified_as_timeout(monkeypatch):
    """대조 3: ReadTimeout 예외는 TIMEOUT으로 분류된다."""
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "test_oc")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()

    def _raise_timeout(url, params=None):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(adapter, "_http_get", _raise_timeout)
    resp = adapter.search_cases_by_query("손해배상")
    assert resp.status == AdapterStatus.TIMEOUT
    assert resp.diagnostics["failure_classification"] == "TIMEOUT"
