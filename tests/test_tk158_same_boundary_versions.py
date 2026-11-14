"""TK-158: 같은 시행일에 개정판이 여럿일 때 인용 조문 문언을 판마다 비교해 같으면 확정, 다르면 미확인(사유 명시).

연혁·본문은 모두 합성이다(법령명 '검증법', 번호·날짜는 구조 시험용). 네트워크·자격 증명 없이 공식 응답 꼴만 흉내 낸다.
"""
from copy import deepcopy
from types import SimpleNamespace

import httpx
import pytest

from packages.common.enums import AdapterStatus, CitationType
from packages.common.schemas import Citation
from packages.legal_engine import LegalVerifier
from packages.source_adapters.law_go_kr import LawGoKrAdapter
from packages.source_adapters.legal_history import BOUNDARY_ERROR, BOUNDARY_TEXT_DIFFERS
from packages.source_adapters.local_mirror import LocalLegalMirror
from packages.verification_engine.review_items import HUMAN_READABLE_UNVERIFIED_REASONS


def row(mst, effective, promulgated):
    return {"법령명한글": "검증법", "법령ID": "000123", "법령일련번호": mst, "공포일자": promulgated,
            "시행일자": effective, "공포번호": mst, "제개정구분명": "일부개정"}


def body(r, text):
    return {"법령": {
        "기본정보": {"법령ID": "000123", "법령일련번호": r["법령일련번호"], "법령명_한글": "검증법",
                 "시행일자": r["시행일자"], "공포일자": r["공포일자"], "공포번호": r["공포번호"]},
        "조문": {"조문단위": [
            {"조문번호": "7", "조문여부": "조문", "조문시행일자": r["시행일자"], "조문내용": text},
            {"조문번호": "8", "조문여부": "조문", "조문시행일자": r["시행일자"], "조문내용": "제8조(다른 조) 판마다 다른 문장 " + r["법령일련번호"]},
        ]}}}


ROWS = [row("100", "20190101", "20180601"), row("200", "20220101", "20210601"), row("201", "20220101", "20210901")]
SAME = "제7조(합성 조문) 이 조문의 문언은 두 판에서 같다."


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    law = LawGoKrAdapter(mirror=LocalLegalMirror(tmp_path / "empty"))
    monkeypatch.setattr(law, "status", lambda: AdapterStatus.READY)
    monkeypatch.setattr(LawGoKrAdapter, "api_key", property(lambda self: "TEST_ONLY_KEY"))
    return law


def install(monkeypatch, adapter, rows, texts):
    calls = []

    def request(url, *, params):
        calls.append(deepcopy(params))
        if "MST" in params:
            r = next(x for x in rows if x["법령일련번호"] == params["MST"] and x["시행일자"] == params["efYd"])
            payload = body(r, texts[r["법령일련번호"]])
        else:
            payload = {"LawSearch": {"totalCnt": len(rows), "page": 1, "law": rows}}
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))
    monkeypatch.setattr(adapter, "_http_get", request)
    return calls


def test_same_provision_text_at_boundary_is_confirmed(adapter, monkeypatch):
    install(monkeypatch, adapter, ROWS, {"100": "제7조(합성 조문) 옛 문언.", "200": SAME, "201": SAME})
    got = adapter.resolve_statute("검증법", as_of="2023-06-12", current_date="2026-11-13", article="7")
    assert got.ok, got.message
    record = got.records[0]
    assert record["version_selection"] == "SAME_PROVISION_AT_BOUNDARY"
    assert record["boundary_versions"] == ["200", "201"]
    assert record["version_id"] == "200"  # 결정적: 판 번호가 작은 쪽을 대표로 싣는다(문언은 같다)


def test_other_articles_may_differ_only_the_cited_one_is_compared(adapter, monkeypatch):
    # 제8조는 판마다 다르지만 인용은 제7조다 → 확정
    install(monkeypatch, adapter, ROWS, {"100": "옛", "200": SAME, "201": "제7조(합성 조문)  이 조문의 문언은 두 판에서\n같다."})
    assert adapter.resolve_statute("검증법", as_of="2023-06-12", current_date="2026-11-13", article="7").ok


def test_different_provision_text_stays_unverified_with_reason(adapter, monkeypatch):
    install(monkeypatch, adapter, ROWS, {"100": "옛", "200": SAME, "201": "제7조(합성 조문) 두 번째 판에서 바뀐 문언."})
    got = adapter.resolve_statute("검증법", as_of="2023-06-12", current_date="2026-11-13", article="7")
    assert not got.ok and got.status == AdapterStatus.ERROR
    assert got.message == BOUNDARY_TEXT_DIFFERS
    assert "판마다 달라" in HUMAN_READABLE_UNVERIFIED_REASONS[BOUNDARY_TEXT_DIFFERS]


def test_without_article_keeps_previous_behaviour(adapter, monkeypatch):
    install(monkeypatch, adapter, ROWS, {"100": "옛", "200": SAME, "201": SAME})
    got = adapter.resolve_statute("검증법", as_of="2023-06-12", current_date="2026-11-13")
    assert not got.ok and got.message == BOUNDARY_ERROR


def test_missing_article_in_one_version_is_not_confirmed(adapter, monkeypatch):
    install(monkeypatch, adapter, ROWS, {"100": "옛", "200": SAME, "201": SAME})
    got = adapter.resolve_statute("검증법", as_of="2023-06-12", current_date="2026-11-13", article="9")
    assert not got.ok  # 어느 판에도 없는 조문 → 확정하지 않는다


@pytest.mark.parametrize("order", [1, -1])
def test_result_does_not_depend_on_history_order(adapter, monkeypatch, order):
    install(monkeypatch, adapter, ROWS[::order], {"100": "옛", "200": SAME, "201": SAME})
    got = adapter.resolve_statute("검증법", as_of="2023-06-12", current_date="2026-11-13", article="7")
    assert got.ok and got.records[0]["version_id"] == "200"


def _verify(adapter, as_of="2023-06-12"):
    citation = Citation.create(CitationType.STATUTE, "검증법 제7조", law_name="검증법", article="7")
    return LegalVerifier(SimpleNamespace(law=adapter)).verify_statute(citation, as_of=as_of, current_date="2026-11-13")


def test_verifier_main_path_no_longer_leaves_same_text_unverified(adapter, monkeypatch):
    install(monkeypatch, adapter, ROWS, {"100": "옛", "200": SAME, "201": SAME})
    verdict = _verify(adapter)
    assert not any(BOUNDARY_ERROR in n for n in verdict.notes)
    assert verdict.official_record and verdict.official_record.get("version_selection") == "SAME_PROVISION_AT_BOUNDARY"


def test_verifier_main_path_reports_differing_text(adapter, monkeypatch):
    install(monkeypatch, adapter, ROWS, {"100": "옛", "200": SAME, "201": "제7조 바뀐 문언"})
    verdict = _verify(adapter)
    assert verdict.official_record is None
    assert any(BOUNDARY_TEXT_DIFFERS in n for n in verdict.notes) or any(
        BOUNDARY_TEXT_DIFFERS in (f.detail or "") for f in verdict.findings)
