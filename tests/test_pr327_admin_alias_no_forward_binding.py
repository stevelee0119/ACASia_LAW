"""PR #327 재작업: 이름이 종류명뿐인 행정규칙 인용의 명칭 연결은 위치·명시적 지시에 근거해야 한다.

모두 합성 입력이다. 미래 이름·후행 별칭 정의의 비전파, 명시적 선행 지시의 연결, 복수 후보와 중복 약칭의
미확정(fail-closed), 출처 조회 대조, Python/JavaScript 참조 결속 일치를 확인한다.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.common.enums import AdapterStatus, CitationType
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.legal_engine.citation_extractor import extract_citations
from packages.legal_engine.source_review import verify_admin_rule_source
from packages.legal_engine.verifier import LegalVerifier
from packages.rag_engine.reference_binding import identifier_match
from packages.source_adapters.base import AdapterResponse

ROOT = Path(__file__).resolve().parents[1]


def _rules(text: str):
    doc = NormalizedDocument("d", "d.txt", "text/plain", "h", pages=[Page(1, blocks=[Block("b1", text, 1)])])
    return [c for c in extract_citations(doc) if c.type == CitationType.ADMIN_RULE]


def _by_article(text: str):
    out = {}
    for c in _rules(text):
        out.setdefault(c.article, []).append(c)
    return out


# --- 미래 이름 비전파 -------------------------------------------------------------------------

@pytest.mark.parametrize("early, formal, article", [
    ("본 지침 제5조", "행정기관 개인정보 보호 지침", "10"),
    ("해당 지침 제5조", "가상 시설 접근 관리 지침", "3"),
    ("이 지침 제2조", "공공 문서 보존 지침", "8"),
])
def test_later_formal_name_does_not_name_earlier_generic_citation(early, formal, article):
    text = f"먼저 {early}에 따른다. 한편 「{formal}」 제{article}조는 별개의 규칙이다."
    by_article = _by_article(text)
    early_article = "".join(ch for ch in early if ch.isdigit())
    early_cit = by_article[early_article][0]
    assert early_cit.law_name == "지침"
    assert not early_cit.attributes.get("law_alias_candidate")
    assert by_article[article][0].law_name.replace(" ", "").endswith(formal.replace(" ", "")[-6:])


def test_internal_named_citation_not_overwritten_by_later_formal_rule():
    text = "내부 지침 제5조를 본다. 이어서 「행정기관 개인정보 보호 지침」 제10조가 있다."
    by_article = _by_article(text)
    assert by_article["5"][0].law_name != by_article["10"][0].law_name
    assert not by_article["5"][0].attributes.get("law_alias_candidate")


# --- 후행 별칭 정의 비전파 ----------------------------------------------------------------------

@pytest.mark.parametrize("generic, formal, abbr", [
    ("훈령", "가상 문서 처리 훈령", "문서훈령"),
    ("예규", "가상 계약 심사 예규", "심사예규"),
    ("고시", "가상 시설 안전 고시", "안전고시"),
])
def test_later_alias_definition_is_not_applied_backwards(generic, formal, abbr):
    text = (f"본 {generic} 제3조에 따라 처리한다. 이후 「{formal}」(이하 '{abbr}'이라 한다) 제4조를 본다. "
            f"{abbr} 제5조도 같다.")
    by_article = _by_article(text)
    assert by_article["3"][0].law_name == generic
    assert not by_article["3"][0].attributes.get("law_alias_candidate")
    after = by_article["5"][0]
    assert after.attributes.get("law_alias_basis") == "DOCUMENT_DEFINITION"
    assert after.attributes.get("law_alias_candidate")


# --- 명시적 선행 지시 연결 ----------------------------------------------------------------------

@pytest.mark.parametrize("formal, demonstrative", [
    ("행정기관 개인정보 보호 지침", "위 지침"),
    ("가상 시설 출입 훈령", "동 훈령"),
    ("가상 계약 관리 예규", "해당 예규"),
])
def test_explicit_demonstrative_links_unique_preceding_rule(formal, demonstrative):
    text = f"「{formal}」 제10조가 있다. 또한 {demonstrative} 제5조도 같다."
    by_article = _by_article(text)
    assert by_article["5"][0].law_name.replace(" ", "") == formal.replace(" ", "")


def test_unmarked_same_suffix_does_not_inherit_nearest_preceding_rule():
    text = "「행정기관 개인정보 보호 지침」 제10조가 있다. 또한 지침 제5조도 같다."
    by_article = _by_article(text)
    assert by_article["5"][0].law_name == "지침"


# --- 동일 suffix 다중 후보 -----------------------------------------------------------------------

def test_multiple_same_kind_candidates_leave_generic_citation_unresolved():
    text = "「라마 보호 지침」 제1조와 「바사 관리 지침」 제2조가 있다. 위 지침 제5조도 같다. 그리고 지침 제6조도 있다."
    by_article = _by_article(text)
    assert by_article["5"][0].law_name == "지침"
    assert by_article["6"][0].law_name == "지침"


@pytest.mark.parametrize("ordinal, expected", [
    ("첫 번째 지침", "라마보호지침"),
    ("두 번째 지침", "바사관리지침"),
    ("첫째 지침", "라마보호지침"),
])
def test_explicit_ordinal_selects_exact_preceding_rule(ordinal, expected):
    text = f"「라마 보호 지침」 제1조와 「바사 관리 지침」 제2조가 있다. {ordinal} 제5조를 본다."
    by_article = _by_article(text)
    assert by_article["5"][0].law_name.replace(" ", "") == expected


def test_ordinal_beyond_available_candidates_stays_unresolved():
    text = "「라마 보호 지침」 제1조가 있다. 두 번째 지침 제5조를 본다."
    assert _by_article(text)["5"][0].law_name == "지침"


# --- 중복 별칭 정의 ------------------------------------------------------------------------------

def test_duplicate_alias_for_different_rules_is_not_resolved():
    text = ("「라마 업무 지침」(이하 '업무지침'이라 한다) 제1조와 「바사 업무 지침」(이하 '업무지침'이라 한다) 제2조가 있다. "
            "업무지침 제5조를 본다.")
    cit = _by_article(text)["5"][0]
    assert not cit.attributes.get("law_alias_candidate")


def test_duplicate_alias_for_same_rule_is_still_resolved():
    text = ("「라마 업무 지침」(이하 '업무지침'이라 한다) 제1조를 본다. "
            "「라마 업무 지침」(이하 '업무지침'이라 한다) 제2조도 본다. 업무지침 제5조를 본다.")
    cit = _by_article(text)["5"][0]
    assert cit.attributes.get("law_alias_candidate", "").replace(" ", "") == "라마업무지침"


def test_duplicate_statute_alias_is_not_resolved_either():
    text = ("「라마 처리에 관한 법률」(이하 '처리법'이라 한다) 제1조와 「바사 처리에 관한 법률」(이하 '처리법'이라 한다) 제2조가 있다. "
            "처리법 제5조를 본다.")
    doc = NormalizedDocument("d", "d.txt", "text/plain", "h", pages=[Page(1, blocks=[Block("b1", text, 1)])])
    cits = [c for c in extract_citations(doc) if c.type == CitationType.STATUTE and c.article == "5"]
    assert cits and not any(c.attributes.get("law_alias_candidate") for c in cits)


# --- 출처 검증 대조 ------------------------------------------------------------------------------

class _FakeLaw:
    def __init__(self, known: str):
        self.known = known
        self.queries: list[str] = []
        self.fetched: list[str] = []

    def search_admin_rule(self, name):
        self.queries.append(name)
        if name.replace(" ", "") == self.known.replace(" ", ""):
            return AdapterResponse(AdapterStatus.READY, [{
                "source_id": "1", "rule_name": self.known, "agency": "가상부", "rule_kind": "지침",
                "effective_from": "2025-01-01"}], complete=True)
        return AdapterResponse(AdapterStatus.READY, [], complete=True)

    def fetch_admin_rule(self, rec):
        self.fetched.append(rec.get("rule_name"))
        return AdapterResponse(AdapterStatus.READY, [{
            "full_text": "제5조 본문", "articles": ["5"], "article_texts": {"5": "제5조 본문"}}], complete=True)


@pytest.mark.parametrize("text, article, formal", [
    ("본 지침 제5조에 따른다. 한편 「행정기관 개인정보 보호 지침」 제10조는 별개다.", "5", "행정기관 개인정보 보호 지침"),
    ("「라마 보호 지침」 제1조와 「바사 관리 지침」 제2조가 있다. 지침 제5조도 같다.", "5", "바사 관리 지침"),
    ("「행정기관 개인정보 보호 지침」 제10조가 있다. 또한 지침 제5조도 같다.", "5", "행정기관 개인정보 보호 지침"),
])
def test_source_review_never_queries_a_wrongly_inferred_rule(text, article, formal):
    cit = _by_article(text)[article][0]
    law = _FakeLaw(known=formal)
    verdict = verify_admin_rule_source(LegalVerifier(SimpleNamespace(law=law)), cit)
    assert formal.replace(" ", "") not in [q.replace(" ", "") for q in law.queries]
    assert law.fetched == []
    assert verdict.levels["existence"] != "VERIFIED"


def test_source_review_retries_only_the_explicitly_resolved_rule():
    text = "「행정기관 개인정보 보호 지침」 제10조가 있다. 또한 위 지침 제5조도 같다."
    cit = _by_article(text)["5"][0]
    law = _FakeLaw(known="행정기관 개인정보 보호 지침")
    verdict = verify_admin_rule_source(LegalVerifier(SimpleNamespace(law=law)), cit)
    assert [q.replace(" ", "") for q in law.queries][0] == "행정기관개인정보보호지침"
    assert verdict.levels["existence"] == "VERIFIED"


# --- 유형·span 보존, Python/JavaScript 결속 일치 -------------------------------------------------

def test_citation_type_and_source_span_survive_resolution():
    text = "「행정기관 개인정보 보호 지침」 제10조가 있다. 또한 위 지침 제5조도 같다."
    for cit in _rules(text):
        assert cit.type == CitationType.ADMIN_RULE
        start, end = cit.attributes["reading_span"]
        assert text[start:end].strip() and "제" in text[start:end]


def test_python_and_javascript_reference_binding_agree_on_resolved_and_unresolved():
    app_js = (ROOT / "apps/web/static/app.js").read_text(encoding="utf-8")
    start = app_js.index("const EXPLICIT_WHITESPACE_RE")
    end = app_js.index("function referenceObservationBlock", start)
    js_helpers = app_js[start:end]

    reference = "「행정기관 개인정보 보호 지침」 제5조는 사전 보고 의무를 정한다."
    cases = []
    for text in (
        "「행정기관 개인정보 보호 지침」 제10조가 있다. 또한 위 지침 제5조도 같다.",
        "「행정기관 개인정보 보호 지침」 제10조가 있다. 또한 지침 제5조도 같다.",
        "본 지침 제5조에 따른다. 한편 「행정기관 개인정보 보호 지침」 제10조는 별개다.",
        "「라마 보호 지침」 제1조와 「바사 관리 지침」 제2조가 있다. 지침 제5조도 같다.",
    ):
        cit = _by_article(text)["5"][0]
        cases.append({"citation_id": cit.citation_id, "law_name": cit.law_name, "article": cit.article,
                      "attributes": {k: v for k, v in cit.attributes.items()
                                     if k in ("law_alias_candidate", "law_alias_basis")}})
    py = [identifier_match(c, reference) for c in cases]
    runner = js_helpers + """
const inputs = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = inputs.cases.map(c => referenceIdentifierMatch(c, inputs.ref));
process.stdout.write(JSON.stringify(out));
"""
    proc = subprocess.run(["node", "-e", runner], input=json.dumps({"cases": cases, "ref": reference}, ensure_ascii=False),
                          capture_output=True, text=True, encoding="utf-8", check=True)
    assert json.loads(proc.stdout) == py
    assert py[0]["full"] is True
    assert [r["full"] for r in py[1:]] == [False, False, False]
