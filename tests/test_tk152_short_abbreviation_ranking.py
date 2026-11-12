"""TK-152: 두 음절 어간 약칭 추정 랭킹 개선 및 미결 분기 보완.

합성 법령명만 쓴다(실제 법령·서면의 이름이 아니다). TK-130 시험의 목록·본문 흉내를 재사용한다.
"""
import pytest

import test_tk130_abbreviation_inference as t130
from test_tk130_abbreviation_inference import adapter  # noqa: F401  (fixture 재사용)
from packages.legal_engine.law_name_inference import SHORT_STEM, pick, score


def kinds(verdict):
    return {f.confidence_features.get("verdict_label") for f in verdict.findings}


# --- C1: 약칭 가산이 첫 두 말마디 정식명을 이기지 못함 -----------------------------------
def test_c1_official_name_first_two_words_beats_distant_abbreviation_ranking():
    r1 = {"law_name": t130.FULL, "law_id": "000901", "abbreviation": None}
    r2 = {"law_name": "시험문서조정 재정법", "law_id": "000902", "abbreviation": "시험문서재정법"}
    s1 = score("시재법", r1, min_stem=SHORT_STEM)
    s2 = score("시재법", r2, min_stem=SHORT_STEM)
    assert s1 > s2 and s1 - s2 >= 100
    chosen, ranked = pick("시재법", [r1, r2], min_stem=SHORT_STEM)
    assert chosen is not None and chosen["law_id"] == "901"


def test_c1_official_name_first_two_words_beats_distant_abbreviation_verify(monkeypatch, adapter):
    r1 = t130.row(name=t130.FULL, law_id="000901", mst="901")
    r2 = t130.row(name="시험문서조정 재정법", law_id="000902", mst="902", 법령약칭명="시험문서재정법")
    rows = [r1, r2]
    t130.install(monkeypatch, adapter, lambda params: rows if params.get("gana") else t130.by_stem(rows)(params))
    verdict = t130.verify(adapter, t130.cite("시재법"))
    assert verdict.review["law_alias"]["found"] is True
    assert verdict.review["law_alias"]["resolved"] == t130.FULL
    assert "NOT_FOUND_LAW" not in kinds(verdict)


# --- C3: 공식 약칭 맨 앞 이어짐이 둘째 말마디 첫 음절 약칭을 이김 ---------------------------
def test_c3_contiguous_stem_at_front_beats_second_word_initial_ranking():
    r1 = {"law_name": t130.FULL, "law_id": "000901", "abbreviation": "시재예방처벌법"}
    r2 = {"law_name": "시험재해 기본법", "law_id": "000902", "abbreviation": "시험재해법"}
    s1 = score("시재법", r1, min_stem=SHORT_STEM)
    s2 = score("시재법", r2, min_stem=SHORT_STEM)
    assert s1 > s2 and s1 - s2 >= 100
    chosen, ranked = pick("시재법", [r1, r2], min_stem=SHORT_STEM)
    assert chosen is not None and chosen["law_id"] == "901"


def test_c3_contiguous_stem_at_front_beats_second_word_initial_verify(monkeypatch, adapter):
    r1 = t130.row(name=t130.FULL, law_id="000901", mst="901", 법령약칭명="시재예방처벌법")
    r2 = t130.row(name="시험재해 기본법", law_id="000902", mst="902", 법령약칭명="시험재해법")
    rows = [r1, r2]
    t130.install(monkeypatch, adapter, lambda params: rows if params.get("gana") else t130.by_stem(rows)(params))
    verdict = t130.verify(adapter, t130.cite("시재법"))
    assert verdict.review["law_alias"]["found"] is True
    assert verdict.review["law_alias"]["resolved"] == t130.FULL
    assert "NOT_FOUND_LAW" not in kinds(verdict)


# --- 규칙 배제: '…법'으로 적힌 질의에 '…에 관한 규칙'은 후보 제외 ---------------------------
def test_statute_query_excludes_rule_candidate(monkeypatch, adapter):
    r = t130.row(name="시험재해 처리에 관한 규칙", law_id="000903", mst="903")
    assert score("시재법", {"law_name": "시험재해 처리에 관한 규칙", "law_id": "000903"}, min_stem=SHORT_STEM) == 0
    t130.install(monkeypatch, adapter, lambda params: [r] if params.get("gana") else [])
    verdict = t130.verify(adapter, t130.cite("시재법"))
    assert verdict.review["law_alias"]["found"] is False
    assert "시험재해 처리에 관한 규칙" not in (verdict.review["law_alias"].get("candidates") or [])


# --- 대조군: 같은 등급 둘은 점수 차가 적어 AMBIGUOUS 유지 --------------------------------
def test_same_tier_candidates_remain_ambiguous(monkeypatch, adapter):
    r1 = t130.row(name="시험재해 보상법", law_id="000904", mst="904")
    r2 = t130.row(name="시험재해 예방법", law_id="000905", mst="905")
    t130.install(monkeypatch, adapter, lambda params: [r1, r2] if params.get("gana") else [])
    verdict = t130.verify(adapter, t130.cite("시재법"))
    assert verdict.review["law_alias"]["found"] is False
    assert verdict.review["law_alias"]["outcome"] == "AMBIGUOUS"
    assert "ABBREVIATION_UNRESOLVED" in kinds(verdict)
    assert "NOT_FOUND_LAW" not in kinds(verdict)


# --- C2: 우선 후보에 인용 조문이 없으면 ARTICLE_NOT_IN_CANDIDATE → MEDIUM 미결 -------------
def test_c2_article_not_in_candidate_becomes_abbreviation_unresolved(monkeypatch, adapter):
    r = t130.row(name=t130.FULL, law_id="000901", mst="901")
    rows = [r]
    t130.install(monkeypatch, adapter, lambda params: rows if params.get("gana") else t130.by_stem(rows)(params), article="6")
    verdict = t130.verify(adapter, t130.cite("시재법", article="99"))
    assert verdict.review["law_alias"]["outcome"] == "ARTICLE_NOT_IN_CANDIDATE"
    assert "ABBREVIATION_UNRESOLVED" in kinds(verdict)
    assert "NOT_FOUND_LAW" not in kinds(verdict)
    [f] = [f for f in verdict.findings if f.confidence_features.get("verdict_label") == "ABBREVIATION_UNRESOLVED"]
    assert str(f.severity) == "MEDIUM" and str(f.status) == "UNVERIFIED"
    assert t130.FULL in f.detail
    assert "약칭 추정 후보 법령의 조회 버전에 인용 조문이 없어 그 후보로 확정하지 못했다" in f.detail


# --- 대조군: 어간 4자 이상은 약칭 꼴이 아니므로 NOT_FOUND_LAW CRITICAL 유지 ----------------
def test_four_char_stem_keeps_not_found_law_on_missing_article(monkeypatch, adapter):
    t130.install(monkeypatch, adapter, lambda params: [])
    verdict = t130.verify(adapter, t130.cite("가나다라회복법", article="99"))
    assert "NOT_FOUND_LAW" in kinds(verdict)
    assert "ABBREVIATION_UNRESOLVED" not in kinds(verdict)
    [f] = [f for f in verdict.findings if f.confidence_features.get("verdict_label") == "NOT_FOUND_LAW"]
    assert str(f.severity) == "CRITICAL"


# --- F3 (X7 승인): 두 음절 어간 NO_CANDIDATE 미결 완화 ------------------------------------
def test_two_syllable_stem_with_no_candidate_becomes_unresolved(monkeypatch, adapter):
    t130.install(monkeypatch, adapter, lambda params: [])
    verdict = t130.verify(adapter, t130.cite("가나법"))
    assert verdict.review["law_alias"]["outcome"] == "NO_CANDIDATE"
    assert "ABBREVIATION_UNRESOLVED" in kinds(verdict)
    assert "NOT_FOUND_LAW" not in kinds(verdict)
    [f] = [f for f in verdict.findings if f.confidence_features.get("verdict_label") == "ABBREVIATION_UNRESOLVED"]
    assert str(f.severity) == "MEDIUM" and str(f.status) == "UNVERIFIED"
    assert "첫 글자 목록에 글자 순서가 맞는 후보가 없으나, 앞 낱말을 생략한 공식 약칭일 수 있다" in f.detail


# --- 대조군: 어간 3자 약칭 꼴의 NO_CANDIDATE는 CRITICAL 유지 -----------------------------
def test_three_syllable_stem_with_no_candidate_keeps_critical(monkeypatch, adapter):
    t130.install(monkeypatch, adapter, lambda params: [])
    verdict = t130.verify(adapter, t130.cite("가나다법"))
    assert "NOT_FOUND_LAW" in kinds(verdict)
    assert "ABBREVIATION_UNRESOLVED" not in kinds(verdict)
    [f] = [f for f in verdict.findings if f.confidence_features.get("verdict_label") == "NOT_FOUND_LAW"]
    assert str(f.severity) == "CRITICAL"
