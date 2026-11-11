"""TK-134: 조례 인용은 법령 목록이 아니라 자치법규 목록(target=ordin)에서 확인한다.

응답은 법제처 공동활용 가이드(자치법규 목록·본문 조회 API)의 필드 이름으로 만든 합성 응답이다. 실제 응답의
최상위 키 이름은 OC 키로 받은 실제 응답으로 확인해야 한다(미검증). 조례 이름은 합성이다.
"""
from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from packages.common.enums import AdapterStatus, CitationType
from packages.legal_engine import LegalVerifier
from packages.legal_engine.citation_extractor import extract_from_text
from packages.legal_engine.source_review import _is_ordinance_form
from packages.source_adapters.law_go_kr import LawGoKrAdapter
from packages.source_adapters.local_mirror import LocalLegalMirror

LAW_ROWS = [{"법령명한글": "주차장법", "법령ID": "1", "법령일련번호": "10", "시행일자": "20200101"}]
ORDIN = {"자치법규일련번호": "900", "자치법규명": "가람시 공영주차장 운영 조례", "자치법규ID": "77",
         "지자체기관명": "가람시", "자치법규종류": "조례", "시행일자": "20250101", "공포일자": "20241201"}
OTHER = dict(ORDIN, 자치법규명="나래군 공영주차장 운영 조례", 지자체기관명="나래군", 자치법규ID="78")
BODY = {"자치법규": {"조문": {"조": [{"조문번호": "000100", "조문여부": "Y", "조제목": "목적"},
                                     {"조문번호": "000200", "조문여부": "N", "조제목": "제2장"},
                                     {"조문번호": "000300", "조문여부": "Y", "조제목": "요금"}]}}}


@pytest.fixture
def law(monkeypatch, tmp_path):
    adapter = LawGoKrAdapter(mirror=LocalLegalMirror(tmp_path / "empty"))
    monkeypatch.setattr(adapter, "status", lambda: AdapterStatus.READY)
    monkeypatch.setattr(LawGoKrAdapter, "api_key", property(lambda self: "TEST_OC"))
    return adapter


def serve(monkeypatch, law, ordin_rows, body=BODY, ordin_status=200, calls=None):
    def request(url, *, params):
        if calls is not None:
            calls.append(dict(params))
        req = httpx.Request("GET", url)
        if params.get("target") == "ordin" and url.endswith("lawService.do"):
            return httpx.Response(200, json=body, request=req)
        if params.get("target") == "ordin":
            return httpx.Response(ordin_status, json={"OrdinSearch": {"totalCnt": len(ordin_rows), "law": ordin_rows}},
                                  request=req)
        return httpx.Response(200, json={"LawSearch": {"totalCnt": 1, "page": 1, "law": LAW_ROWS}}, request=req)
    monkeypatch.setattr(law, "_http_get", request)


def verify(law, text):
    [citation] = [c for c in extract_from_text(text) if c.type == CitationType.STATUTE]
    result = LegalVerifier(SimpleNamespace(law=law)).verify_citations([citation], current_date="2026-11-03")
    return citation, result.data["verdicts"][0], result.findings


def test_ordinance_form_detection():
    assert _is_ordinance_form("가람시 공영주차장 운영 조례") and _is_ordinance_form("「가람시 주차장 조례」")
    assert _is_ordinance_form("가람시 공영주차장 운영 규칙")
    assert not _is_ordinance_form("주차장법 시행규칙") and not _is_ordinance_form("도로법 시행규칙")
    assert not _is_ordinance_form("주차장법") and not _is_ordinance_form("공영주차장 운영 규칙")


def test_existing_ordinance_is_found_in_ordinance_list_not_critical(law, monkeypatch):
    calls = []
    serve(monkeypatch, law, [ORDIN], calls=calls)
    _, verdict, findings = verify(law, "가람시 공영주차장 운영 조례 제3조는 요금을 정한다.")
    assert not [f for f in findings if str(f.severity) in ("CRITICAL", "HIGH")]
    assert verdict["levels"]["existence"] == "VERIFIED" and verdict["levels"]["article"] == "VERIFIED"
    assert verdict["review"]["ordinance_lookup"]["source"] == "ORDINANCE_LIST"
    assert any(c.get("target") == "ordin" for c in calls)


def test_missing_article_in_existing_ordinance_is_high_not_nonexistence(law, monkeypatch):
    serve(monkeypatch, law, [ORDIN])
    _, verdict, findings = verify(law, "가람시 공영주차장 운영 조례 제2조는 요금을 정한다.")   # 제2조는 '장' 표제뿐
    [finding] = findings
    assert finding.confidence_features["verdict_label"] == "ORDINANCE_ARTICLE_NOT_FOUND"
    assert str(finding.severity) == "HIGH" and str(finding.type) != "STATUTE_NONEXISTENT"


def test_name_without_local_government_matches_several_and_is_left_to_a_person(law, monkeypatch):
    serve(monkeypatch, law, [ORDIN, OTHER])
    _, verdict, findings = verify(law, "공영주차장 운영 조례 제3조에 따르면 요금이 정해진다.")
    assert findings == [] and verdict["levels"]["existence"] == "PARTIALLY_VERIFIED"
    assert verdict["review"]["ordinance_lookup"]["ambiguous"] is True


def test_ordinance_absent_from_both_lists_is_high_not_found(law, monkeypatch):
    serve(monkeypatch, law, [])
    _, verdict, findings = verify(law, "다솜시 무인비행 관리 조례 제5조는 비행을 금지한다.")
    [finding] = findings
    assert finding.confidence_features["verdict_label"] == "NOT_FOUND_ORDINANCE"
    assert str(finding.severity) == "HIGH" and "부존재 확정 아님" in finding.detail


def test_ordinance_lookup_failure_is_unverified_not_nonexistence(law, monkeypatch):
    serve(monkeypatch, law, [], ordin_status=500)
    _, verdict, findings = verify(law, "가람시 공영주차장 운영 조례 제3조는 요금을 정한다.")
    assert verdict["levels"]["existence"] == "UNVERIFIED"
    assert not [f for f in findings if str(f.type) == "STATUTE_NONEXISTENT"]


def test_statute_form_still_gets_not_found_law(law, monkeypatch):
    serve(monkeypatch, law, [ORDIN])
    _, verdict, findings = verify(law, "군간부 징계절차에 관한 특례법 제8조는 초과 징계를 금지한다.")
    [finding] = findings
    assert finding.confidence_features["verdict_label"] == "NOT_FOUND_LAW"


def test_article_numbers_in_plain_or_six_digit_form_are_both_read():
    from packages.source_adapters.law_go_kr import _ordinance_article_number
    assert [_ordinance_article_number(n) for n in ("000300", "000302", "3", "3의2")] == ["3", "3의2", "3", "3의2"]


def test_ordinance_verdicts_use_existing_spec_and_component_vocabulary(law, monkeypatch):
    """새 판정 이름을 만들지 않는다: 명세 판정(spec_mapping)·화면 구성요소(components)가 그대로 읽어야 한다."""
    from packages.legal_engine.components import citation_components
    expected = [([ORDIN], "가람시 공영주차장 운영 조례 제3조는 요금을 정한다.", "PARTIAL", "CONFIRMED"),
                ([ORDIN, OTHER], "공영주차장 운영 조례 제3조에 따르면 요금이 정해진다.", "UNVERIFIABLE", "PARTIAL"),
                ([], "다솜시 무인비행 관리 조례 제5조는 비행을 금지한다.", "NOT_FOUND", "NOT_FOUND_IN_SEARCHED_SCOPE")]
    for rows, text, spec, component in expected:
        serve(monkeypatch, law, rows)
        _, verdict, _ = verify(law, text)
        assert str(verdict["spec_verdict"]) == spec
        [existence] = [c for c in citation_components("STATUTE", verdict["levels"]) if c["key"] == "law_existence"]
        assert existence["status"] == component


def test_ordinance_name_is_not_inferred_as_a_national_law_abbreviation(law, monkeypatch):
    calls = []
    serve(monkeypatch, law, [ORDIN], calls=calls)
    _, verdict, _ = verify(law, "가람시 공영주차장 운영 조례 제3조는 요금을 정한다.")
    assert "law_alias" not in verdict["review"] and not any("약칭 추정" in n for n in verdict["notes"])
