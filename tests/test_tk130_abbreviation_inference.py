"""TK-130: 문서에 정식 법령명이 없는 비공식 약칭의 공식 법령 추정.

합성 법령명만 쓴다(실제 법령·서면의 이름이 아니다). 목록 응답은 어간 검색을 흉내 낸다.
"""
from types import SimpleNamespace

import httpx
import pytest

from packages.common.enums import AdapterStatus, CitationType
from packages.common.schemas import Citation
from packages.legal_engine.law_name_inference import pick, score
from packages.legal_engine.verifier import LegalVerifier
from packages.source_adapters.law_go_kr import LawGoKrAdapter
from packages.source_adapters.local_mirror import LocalLegalMirror

FULL = "시험재해 예방 및 처벌 등에 관한 법률"


def row(name=FULL, law_id="000901", mst="901", **extra):
    return {"법령명한글": name, "법령ID": law_id, "법령일련번호": mst, "공포일자": "20200101",
            "시행일자": "20200301", "공포번호": "11", "제개정구분명": "일부개정", **extra}


def body(article="6", deleted=False):
    return {"법령": {
        "기본정보": {"법령ID": "000901", "법령일련번호": "901", "법령명_한글": FULL, "시행일자": "20200301",
                 "공포일자": "20200101", "공포번호": "11"},
        "조문": {"조문단위": [{"조문번호": article, "조문여부": "조문", "조문시행일자": "20200301",
                           **({"조문제개정유형": "삭제"} if deleted else {}),
                           "조문내용": f"제{article}조 삭제 <2020. 1. 1.>" if deleted
                           else f"제{article}조(처벌) 처벌에 관한 본문이다."}]},
        "부칙": {"부칙단위": {"부칙공포일자": "20200101", "부칙공포번호": "11",
                         "부칙내용": ["제1조(시행일) 이 법은 2020년 3월 1일부터 시행한다."]}}}}


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    law = LawGoKrAdapter(mirror=LocalLegalMirror(tmp_path / "empty"))
    monkeypatch.setattr(law, "status", lambda: AdapterStatus.READY)
    monkeypatch.setattr(LawGoKrAdapter, "api_key", property(lambda self: "TEST_SECRET_OC"))
    return law


def install(monkeypatch, adapter, rows_for, article="6", detail=None, fail_query=None, deleted=False):
    queries = []

    def request(url, *, params):
        if "MST" in params:
            if detail == "error":
                return httpx.Response(500, json={}, request=httpx.Request("GET", url))
            payload = body(article, deleted=deleted)
        else:
            queries.append(params.get("query") or params.get("LID"))
            if fail_query and params.get("query") == fail_query:
                return httpx.Response(500, json={}, request=httpx.Request("GET", url))
            rows = rows_for(params)
            if isinstance(rows, dict):          # 쪽 단위 응답(totalCnt·page 직접 지정)
                payload = {"LawSearch": rows}
            else:
                payload = {"LawSearch": {"totalCnt": len(rows), "page": 1, "law": rows}}
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))
    monkeypatch.setattr(adapter, "_http_get", request)
    return queries


def by_stem(rows):
    """적힌 이름 그대로는 0건, 어간·정식명·LID로는 rows를 돌려준다(공식 목록 검색 흉내)."""
    def rows_for(params):
        q = params.get("query")
        if params.get("LID"):
            return [r for r in rows if r["법령ID"].lstrip("0") == str(params["LID"]).lstrip("0")]
        if q is None:
            return rows
        names = [r["법령명한글"].replace(" ", "") for r in rows]
        return rows if any(q.replace(" ", "") in n for n in names) else []
    return rows_for


def cite(written, article="6", paragraph=None):
    raw = f"{written} 제{article}조" + (f" 제{paragraph}항" if paragraph else "")
    return Citation.create(CitationType.STATUTE, raw, law_name=written, article=article, paragraph=paragraph)


def verify(adapter, citation):
    return LegalVerifier(SimpleNamespace(law=adapter)).verify_statute(
        citation, as_of="2026-01-01", current_date="2026-09-26")


def types(verdict):
    return {f.type.value for f in verdict.findings}


# --- 양성: 비공식 약칭이 공식 약칭(또는 정식명)의 부분수열이고 후보가 하나 ------------------------------
@pytest.mark.parametrize("written,rows", [
    ("시험재해법", [row(법령약칭명="시험재해처벌법")]),            # 공식 약칭의 부분수열
    ("시험재해예방법", [row(법령약칭명="시험재해예방처벌법")]),     # 다른 꼴의 줄임
    ("시험재해처벌법", [row()]),                                   # 약칭 없음 → 정식명 부분수열
])
def test_informal_abbreviation_is_inferred_not_reported_absent(adapter, monkeypatch, written, rows):
    install(monkeypatch, adapter, by_stem(rows))
    verdict = verify(adapter, cite(written))
    assert "STATUTE_NONEXISTENT" not in types(verdict)
    assert verdict.levels["existence"] == "INFERRED_FROM_ABBREVIATION"
    assert verdict.review["law_alias"]["resolved"] == FULL
    assert verdict.status.value != "VERIFIED"          # 추정은 확인됨으로 올리지 않는다
    assert any("ABBREVIATION_INFERRED" in f.tags for f in verdict.findings)


# --- 대조: 추정하지 않고 기존 판정(CRITICAL)을 유지 -----------------------------------------------------------
def test_article_missing_in_candidate_keeps_absence(adapter, monkeypatch):
    install(monkeypatch, adapter, by_stem([row(법령약칭명="시험재해처벌법")]), article="7")
    verdict = verify(adapter, cite("시험재해법", "6"))
    absent = [f for f in verdict.findings if f.type.value == "STATUTE_NONEXISTENT"]
    assert len(absent) == 1 and absent[0].severity.value == "CRITICAL"   # 기존 심각도 그대로
    assert verdict.review["law_alias"]["found"] is False


def test_two_close_candidates_are_not_guessed(adapter, monkeypatch):
    rows = [row(법령약칭명="시험재해처벌법"),
            row(name="시험재해 보상 등에 관한 법률", law_id="000902", mst="902", 법령약칭명="시험재해보상법")]
    install(monkeypatch, adapter, by_stem(rows))
    verdict = verify(adapter, cite("시험재해법"))
    assert "STATUTE_NONEXISTENT" in types(verdict)


@pytest.mark.parametrize("written,abbr", [
    ("시험재해법", "시험재해처벌법시행령"),   # 법률 ↔ 시행령 종류 불일치
    ("재해시험법", "시험재해처벌법"),          # 첫 글자 불일치
    ("시험법", "시험재해처벌법"),              # 어간 3자 미만
])
def test_kind_initial_or_short_stem_controls(written, abbr):
    assert score(written, {"law_name": FULL, "abbreviation": abbr}) == 0


def test_name_is_ignored_when_official_abbreviation_exists():
    # 정식명은 부분수열이지만 공식 약칭(시행령)과는 종류가 달라 후보가 아니다(test_v096 대조와 같은 원칙).
    assert pick("시험재해처벌법", [{"law_name": FULL, "law_id": "1", "abbreviation": "시험재해처벌법시행령"}]) == (None, [])


def test_document_alias_path_is_unchanged(adapter, monkeypatch):
    queries = install(monkeypatch, adapter, by_stem([row(법령약칭명="시험재해처벌법")]))
    citation = cite("시험재해법")
    citation.attributes.update(law_alias_candidate=FULL, law_alias_basis="DOCUMENT_FULL_NAME_PREFIX")
    verdict = verify(adapter, citation)
    assert verdict.review["law_alias"]["basis"] == "DOCUMENT_FULL_NAME_PREFIX"
    assert verdict.levels["existence"] == "VERIFIED"
    assert "시험재해" not in queries                       # 문서 근거가 있으면 어간 검색을 하지 않는다


# --- 결과 구분: 후보 없음·모호·조회 실패·상한·후보 상세 조회 실패 ------------------------------------------------
def outcome(verdict):
    return verdict.review.get("law_alias", {}).get("outcome")


def test_no_candidate_keeps_absence_with_outcome(adapter, monkeypatch):
    install(monkeypatch, adapter, by_stem([]))
    verdict = verify(adapter, cite("시험재해법"))
    assert "STATUTE_NONEXISTENT" in types(verdict) and outcome(verdict) == "NO_CANDIDATE"


def test_ambiguous_keeps_absence_and_lists_candidates(adapter, monkeypatch):
    rows = [row(법령약칭명="시험재해처벌법"),
            row(name="시험재해 보상 등에 관한 법률", law_id="000902", mst="902", 법령약칭명="시험재해보상법")]
    install(monkeypatch, adapter, by_stem(rows))
    verdict = verify(adapter, cite("시험재해법"))
    assert "STATUTE_NONEXISTENT" in types(verdict) and outcome(verdict) == "AMBIGUOUS"
    assert len(verdict.review["law_alias"]["candidates"]) == 2


def test_candidate_list_failure_is_recorded_separately(adapter, monkeypatch):
    # 후보 목록 조회 실패는 '후보 없음'과 구분해 기록한다(심각도는 TK-130 이전 판정 유지: 평가 측 결정).
    install(monkeypatch, adapter, by_stem([row(법령약칭명="시험재해처벌법")]), fail_query="시험재해")
    verdict = verify(adapter, cite("시험재해법"))
    assert outcome(verdict) == "LOOKUP_FAILED"
    assert any("후보 목록 조회에 실패" in n for n in verdict.notes)


def test_candidate_search_page_cap_is_incomplete_not_unique(adapter, monkeypatch):
    def pages(params):
        q = params.get("query")
        if q and q.startswith("시험재해"):
            page = int(params.get("page", 1))
            only = [row(법령약칭명="시험재해처벌법")] if page == 1 else []
            filler = [row(name=f"무관한 법률 {page}-{i}", law_id=f"9{page:02d}{i:03d}", mst=f"9{page:02d}{i:03d}")
                      for i in range(100 - len(only))]
            return {"totalCnt": 1000, "page": page, "law": only + filler}
        return []
    install(monkeypatch, adapter, pages)
    verdict = verify(adapter, cite("시험재해법"))
    assert outcome(verdict) == "INCOMPLETE"
    assert verdict.review["law_alias"]["found"] is False


def test_candidate_detail_failure_is_unverified_not_absent(adapter, monkeypatch):
    install(monkeypatch, adapter, by_stem([row(법령약칭명="시험재해처벌법")]), detail="error")
    verdict = verify(adapter, cite("시험재해법"))
    assert "STATUTE_NONEXISTENT" not in types(verdict)
    assert outcome(verdict) == "CANDIDATE_LOOKUP_FAILED"
    assert verdict.status.value == "UNVERIFIED"


def test_selected_law_id_is_pinned_for_same_name_laws(adapter, monkeypatch):
    # 같은 정식명의 다른 법령 ID(더 최근)가 있어도 추정에서 고른 ID로 대조한다.
    rows = [row(법령약칭명="시험재해처벌법"),
            row(law_id="000903", mst="903", 법령약칭명="재해시험특례법", 시행일자="20240101", 공포일자="20231201")]
    queries = install(monkeypatch, adapter, by_stem(rows))
    verdict = verify(adapter, cite("시험재해법"))
    assert verdict.review["law_alias"]["law_id"] == "901"
    assert "901" in [str(q).lstrip("0") for q in queries]
    assert verdict.levels["existence"] == "INFERRED_FROM_ABBREVIATION"


@pytest.mark.parametrize("kwargs,status,phrase", [
    ({"deleted": True}, "DELETED", "삭제된 조문"),
    ({}, "UNVERIFIED", "지정 조항은 확인하지 못했다"),
])
def test_unconfirmed_provision_says_only_the_name_was_inferred(adapter, monkeypatch, kwargs, status, phrase):
    install(monkeypatch, adapter, by_stem([row(법령약칭명="시험재해처벌법")]), **kwargs)
    citation = cite("시험재해법") if kwargs else cite("시험재해법", paragraph="3")
    verdict = verify(adapter, citation)
    found = [f for f in verdict.findings if "ABBREVIATION_INFERRED" in f.tags]
    assert len(found) == 1 and found[0].confidence_features["provision_status"] == status
    assert phrase in found[0].detail and "인용 조문이 그 법령의 조회 버전에 있어" not in found[0].detail
    assert verdict.status.value != "VERIFIED"


# --- 값·문장이 다른 양성 3꼴(AGENTS.md L13): 법령·조문 구조·인용 문장이 모두 다르다 ---------------------------------
def other_law(name, law_id, mst, article, text):
    """다른 합성 법령 하나의 목록 행과 본문 응답."""
    listing = {"법령명한글": name, "법령ID": law_id, "법령일련번호": mst, "공포일자": "20190101",
               "시행일자": "20190701", "공포번호": "7", "제개정구분명": "제정"}
    detail = {"법령": {
        "기본정보": {"법령ID": law_id, "법령일련번호": mst, "법령명_한글": name, "시행일자": "20190701",
                 "공포일자": "20190101", "공포번호": "7"},
        "조문": {"조문단위": [{"조문번호": article, "조문여부": "조문", "조문시행일자": "20190701", "조문내용": text}]},
        "부칙": {"부칙단위": {"부칙공포일자": "20190101", "부칙공포번호": "7",
                         "부칙내용": ["제1조(시행일) 이 법은 2019년 7월 1일부터 시행한다."]}}}}
    return listing, detail


VARIED = [
    # (적힌 이름, 인용 원문, 조문 번호, 공식 정식명, 공식 약칭, 조문 본문)
    ("가상보건법", "가상보건법 제12조에 따라 지원을 신청하였다", "12",
     "가상보건 진흥 및 지원에 관한 법률", "가상보건진흥법", "제12조(지원) 국가는 비용을 지원할 수 있다."),
    ("모의교통특별법", "모의교통특별법 제3조는 안전관리 의무를 정한다", "3",
     "모의교통 안전관리 특별법", None, "제3조(의무) 운영자는 안전관리계획을 세워야 한다."),
    ("표본정보법", "피고는 표본정보법 제27조를 위반하였다고 주장한다", "27",
     "표본정보 보호 및 이용에 관한 법률", "표본정보보호법", "제27조(금지) 누구든지 정보를 누설하여서는 아니 된다."),
]


@pytest.mark.parametrize("written,raw,article,name,abbr,text", VARIED)
def test_varied_laws_and_sentences_are_inferred(adapter, monkeypatch, written, raw, article, name, abbr, text):
    listing, detail = other_law(name, "000777", "777", article, text)
    if abbr:
        listing["법령약칭명"] = abbr

    def request(url, *, params):
        if "MST" in params:
            payload = detail
        else:
            q = (params.get("query") or "").replace(" ", "")
            hit = params.get("LID") or (q and q in name.replace(" ", ""))
            rows = [listing] if hit else []
            payload = {"LawSearch": {"totalCnt": len(rows), "page": 1, "law": rows}}
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))
    monkeypatch.setattr(adapter, "_http_get", request)
    citation = Citation.create(CitationType.STATUTE, raw, law_name=written, article=article)
    verdict = verify(adapter, citation)
    assert "STATUTE_NONEXISTENT" not in types(verdict)
    assert verdict.review["law_alias"]["resolved"] == name
    assert verdict.levels["existence"] == "INFERRED_FROM_ABBREVIATION"


# --- 명세 판정값: 추정 성공은 NOT_FOUND가 아니다 ---------------------------------------------------------------------
def test_spec_verdict_for_inferred_statute_is_partial_not_absent(adapter, monkeypatch):
    from packages.legal_engine.spec_mapping import spec_source_verdict
    install(monkeypatch, adapter, by_stem([row(법령약칭명="시험재해처벌법")]))
    verdict = verify(adapter, cite("시험재해법"))
    value = spec_source_verdict(verdict.levels, verdict.notes, has_official_record=bool(verdict.official_record))
    assert str(value) == "PARTIAL"


@pytest.mark.parametrize("levels,expected", [
    ({"existence": "INFERRED_FROM_ABBREVIATION", "content": "CONTRADICTED"}, "MISMATCH"),
    ({"existence": "NOT_FOUND"}, "NOT_FOUND"),                    # 대조: 부존재는 그대로
    ({"existence": "VERIFIED", "content": "VERIFIED", "temporal": "VERIFIED"}, "VERIFIED_EXACT"),
])
def test_spec_verdict_controls(levels, expected):
    from packages.legal_engine.spec_mapping import spec_source_verdict
    assert str(spec_source_verdict(levels, [], has_official_record=True)) == expected


# --- 약칭 후보 조회 시간 초과: 재시도 소진 뒤 부존재 CRITICAL을 남기지 않는다 -------------------------------------
def test_timed_out_candidate_lookup_leaves_no_absence_finding(tmp_path, monkeypatch):
    # 실제 전송 계층(transport) 경로로 시간 초과를 낸다. 정확 이름 목록은 0건, 어간 검색은 계속 시간 초과.
    from dataclasses import replace
    from packages.source_adapters import transport
    from test_source_transport import install_mock

    def handler(request):
        query = request.url.params.get("query")
        if query and query != "시험재해법":
            raise httpx.ReadTimeout("candidate lookup timed out", request=request)
        return httpx.Response(200, json={"LawSearch": {"totalCnt": 0, "page": 1, "law": []}})
    install_mock(monkeypatch, handler)
    law = LawGoKrAdapter(mirror=LocalLegalMirror(root=tmp_path / "empty"))
    law.settings = replace(law.settings, allow_network=True, law_go_kr_oc="test")
    with transport.source_lookup_session(120, retry_backoff=0):
        result = LegalVerifier(SimpleNamespace(law=law)).verify_citations([cite("시험재해법")])
    verdict = result.data["verdicts"][0]
    assert verdict["source_lookup"]["retryable"]
    assert verdict["status"] == "UNVERIFIED"
    assert not any(f.type.value == "STATUTE_NONEXISTENT" for f in result.findings)
