"""TK-143: 두 음절 어간 비공식 약칭('XX법') 추정과, 풀리지 않는 짧은 약칭을 부존재로 단정하지 않기.

합성 법령명만 쓴다(실제 법령·서면의 이름이 아니다). TK-130 시험의 목록 흉내를 그대로 쓴다.
"""
import httpx

import test_tk130_abbreviation_inference as t130
from test_tk130_abbreviation_inference import adapter  # noqa: F401  (fixture 재사용)
from packages.legal_engine.law_name_inference import gana_code
from packages.legal_engine.normalize import canonical_law_name


def kinds(verdict):
    return {f.confidence_features.get("verdict_label") for f in verdict.findings}


def test_gana_code_follows_initial_consonant():
    assert [gana_code(x) for x in ("가", "까", "노", "산", "쌍", "오", "짜", "하", "A")] == \
           ["ga", "ga", "na", "sa", "sa", "a", "ja", "ha", None]


def test_two_syllable_stem_is_resolved_from_dictionary_list(monkeypatch, adapter):
    queries = []
    rows = [t130.row(), t130.row(name="시험문재 조정법", law_id="000902", mst="902")]   # 재가 홀수 위치

    def rows_for(params):
        queries.append(dict(params))
        if params.get("gana"):
            return rows                                     # 첫 글자 초성 사전식 목록
        return t130.by_stem(rows)(params)
    t130.install(monkeypatch, adapter, rows_for)
    verdict = t130.verify(adapter, t130.cite("시재법"))
    assert verdict.review["law_alias"]["found"] is True
    assert verdict.review["law_alias"]["resolved"] == t130.FULL
    assert any(q.get("gana") == "sa" and q.get("target") == "law" for q in queries)
    assert "NOT_FOUND_LAW" not in kinds(verdict)


def test_short_name_with_no_candidate_in_complete_list_keeps_not_found_law(monkeypatch, adapter):
    # 공식 목록을 끝까지 읽고도 후보가 없으면 부존재 가능성(CRITICAL)을 유지한다(보호 시험과 같은 정책).
    t130.install(monkeypatch, adapter, lambda params: [])
    verdict = t130.verify(adapter, t130.cite("가나법"))
    assert "NOT_FOUND_LAW" in kinds(verdict) and "ABBREVIATION_UNRESOLVED" not in kinds(verdict)


def test_single_word_short_abbreviation_matching_two_laws_is_unverified(monkeypatch, adapter):
    rows = [t130.row(name="시험보험법", law_id="000905", mst="905"),
            t130.row(name="시험정책 기본법", law_id="000906", mst="906")]
    t130.install(monkeypatch, adapter, lambda params: rows if params.get("gana") else [])
    verdict = t130.verify(adapter, t130.cite("시험법"))
    assert "NOT_FOUND_LAW" not in kinds(verdict)
    [f] = [f for f in verdict.findings if f.confidence_features.get("verdict_label") == "ABBREVIATION_UNRESOLVED"]
    assert str(f.severity) == "MEDIUM" and str(f.status) == "UNVERIFIED"
    from packages.legal_engine.spec_mapping import spec_source_verdict
    assert str(spec_source_verdict(verdict.levels, verdict.notes, has_official_record=False)) == "UNVERIFIABLE"


def test_initials_rule():
    from packages.legal_engine.law_name_inference import _initials_subsequence
    assert _initials_subsequence("노조", "노동조합및노동관계조정") and _initials_subsequence("개보", "개인정보보호")
    assert not _initials_subsequence("시재", "시험문재조정")


def test_ambiguous_short_abbreviation_lists_candidates_without_critical(monkeypatch, adapter):
    rows = [t130.row(name="시험재해 보상법", law_id="000903", mst="903"),
            t130.row(name="시험재해 예방법", law_id="000904", mst="904")]
    t130.install(monkeypatch, adapter, lambda params: rows if params.get("gana") else [])
    verdict = t130.verify(adapter, t130.cite("시재법"))
    assert "NOT_FOUND_LAW" not in kinds(verdict) and "ABBREVIATION_UNRESOLVED" in kinds(verdict)


def test_dictionary_list_failure_is_not_nonexistence(monkeypatch, adapter):
    def request(url, *, params):
        return httpx.Response(500, json={}, request=httpx.Request("GET", url))
    monkeypatch.setattr(adapter, "_http_get", request)
    verdict = t130.verify(adapter, t130.cite("시재법"))
    assert "NOT_FOUND_LAW" not in kinds(verdict)


def test_long_unknown_name_keeps_not_found_law(monkeypatch, adapter):
    t130.install(monkeypatch, adapter, lambda params: [])
    verdict = t130.verify(adapter, t130.cite("가나다라회복법"))
    assert "NOT_FOUND_LAW" in kinds(verdict)


def test_alias_with_subordinate_kind_resolves_to_official_subordinate_name():
    assert canonical_law_name("근기법 시행령") == "근로기준법 시행령"
    assert canonical_law_name("근기법시행규칙") == "근로기준법 시행규칙"
    assert canonical_law_name("근기법") == "근로기준법"
