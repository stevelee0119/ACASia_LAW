"""TK-235 unit tests: MATCHED / NOT_IN_PUBLIC_DB / LOOKUP_FAILED classification and U2 denominator separation."""
from __future__ import annotations

from types import SimpleNamespace

from packages.source_adapters.base import AdapterStatus
from packages.source_adapters.law_go_kr import LawGoKrAdapter
from scripts.live_source_check import check_law_go_kr, partition_failures


class _StubResp:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_tk235_pos1_nb_fallback_unrelated_classified_not_in_public_db(monkeypatch):
    """양성 1: nb 조회가 totalCnt=1로 무관한 사건번호를 반환해도 오매칭하지 않고 NOT_IN_PUBLIC_DB로 분류한다."""
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "test_oc")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()
    monkeypatch.setattr(
        adapter,
        "_http_get",
        lambda url, params=None: _StubResp(
            200,
            {"PrecSearch": {"totalCnt": "1", "prec": [{"사건번호": "2021도9002", "사건명": "타사건", "판례정보일련번호": "1"}]}},
        ),
    )
    resp = adapter.search_case("2021모9001")
    assert resp.status == AdapterStatus.READY
    assert resp.records == []
    assert resp.diagnostics["lookup_outcome"] == "NOT_IN_PUBLIC_DB"
    assert "2021도9002" in resp.diagnostics["returned_candidate_case_numbers"]


def test_tk235_pos2_http_error_classified_lookup_failed(monkeypatch):
    """양성 2: 업스트림 HTTP 503 오류는 NOT_IN_PUBLIC_DB가 아니라 LOOKUP_FAILED로 분류한다."""
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "test_oc")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()
    monkeypatch.setattr(adapter, "_http_get", lambda url, params=None: _StubResp(503, {}))
    resp = adapter.search_case("2021모9001")
    assert resp.status == AdapterStatus.ERROR
    assert resp.diagnostics["lookup_outcome"] == "LOOKUP_FAILED"


def test_tk235_pos3_live_source_check_separates_unlisted_probe_from_fatal():
    """양성 3: U2 점검에서 공개 DB 미수록 확인 대상은 advisory로 분리되어 fatal/warnings에 섞이지 않는다."""
    class _StubLaw:
        name = "law_go_kr"
        def status(self):
            return AdapterStatus.READY
        def search_law(self, q):
            return SimpleNamespace(status=AdapterStatus.READY, records=[{"법령명한글": q}], diagnostics={"lookup_outcome": "MATCHED"})
        def search_case(self, q):
            if q == "2015모2524":
                return SimpleNamespace(
                    status=AdapterStatus.READY,
                    records=[],
                    message="",
                    source_record=None,
                    diagnostics={"lookup_outcome": "NOT_IN_PUBLIC_DB", "returned_candidate_case_numbers": ["2015도6980"]},
                )
            return SimpleNamespace(status=AdapterStatus.READY, records=[{"case_number": q}], message="", source_record=None, diagnostics={"lookup_outcome": "MATCHED"})

    results = check_law_go_kr(SimpleNamespace(law=_StubLaw()))
    unlisted = [r for r in results if "2015모2524" in r.name][0]
    assert unlisted.status == "NOT_IN_PUBLIC_DB"
    assert unlisted.advisory is True
    fatal, warnings, advisories = partition_failures({"live_legal": results})
    assert fatal == []
    assert warnings == []
    assert any("2015모2524" in a.name for a in advisories)


def test_tk235_ctrl1_exact_match_classified_matched(monkeypatch):
    """대조 1: 완전 튜플 일치 시 MATCHED로 분류되고 레코드를 채택한다."""
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "test_oc")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()
    monkeypatch.setattr(
        adapter,
        "_http_get",
        lambda url, params=None: _StubResp(
            200,
            {"PrecSearch": {"totalCnt": "1", "prec": [{"사건번호": "2021모9001", "사건명": "일치", "판례정보일련번호": "2"}]}},
        ),
    )
    resp = adapter.search_case("2021모9001")
    assert resp.status == AdapterStatus.READY
    assert len(resp.records) == 1
    assert resp.diagnostics["lookup_outcome"] == "MATCHED"


def test_tk235_ctrl2_empty_results_classified_not_in_public_db(monkeypatch):
    """대조 2: 공급자 원응답 0건도 NOT_IN_PUBLIC_DB로 분류된다."""
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "test_oc")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    adapter = LawGoKrAdapter()
    monkeypatch.setattr(adapter, "_http_get", lambda url, params=None: _StubResp(200, {"PrecSearch": {"totalCnt": "0", "prec": []}}))
    resp = adapter.search_case("2021모9001")
    assert resp.status == AdapterStatus.READY
    assert resp.records == []
    assert resp.diagnostics["lookup_outcome"] == "NOT_IN_PUBLIC_DB"
    assert resp.diagnostics["cause"] == "NO_PROVIDER_RESULTS"


def test_tk235_ctrl3_other_case_missing_in_live_check_is_non_advisory():
    """대조 3: 미수록 확인 대상이 아닌 일반 판례가 누락되면 advisory=False로 실패 처리된다."""
    class _StubLaw:
        name = "law_go_kr"
        def status(self):
            return AdapterStatus.READY
        def search_law(self, q):
            return SimpleNamespace(status=AdapterStatus.READY, records=[{"법령명한글": q}], diagnostics={"lookup_outcome": "MATCHED"})
        def search_case(self, q):
            if q == "2014다236311":
                return SimpleNamespace(status=AdapterStatus.READY, records=[], message="", source_record=None, diagnostics={"lookup_outcome": "NOT_IN_PUBLIC_DB"})
            return SimpleNamespace(status=AdapterStatus.READY, records=[{"case_number": q}], message="", source_record=None, diagnostics={"lookup_outcome": "MATCHED"})

    results = check_law_go_kr(SimpleNamespace(law=_StubLaw()))
    civil = [r for r in results if "2014다236311" in r.name][0]
    assert civil.ok is False
    assert civil.advisory is False
