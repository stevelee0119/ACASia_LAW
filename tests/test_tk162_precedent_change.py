"""TK-162 판례 효력 확인(뒤의 전원합의체 판결에 의한 판례 변경 역조회). 사건번호·문장은 모두 합성이다."""
from __future__ import annotations

import pytest

from packages.common.enums import AdapterStatus, CitationType, FindingType, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.opinion_attribution import detect_changed_precedent_distortion
from packages.legal_engine.precedent_change import (MAX_CITATIONS, MAX_FETCH_PER_CITATION, overruling_sentences,
                                                    review_precedent_changes)
from packages.legal_engine.verifier import LegalVerifier
from packages.source_adapters.base import AdapterResponse

FORMULA = {
    "모두": "이와 달리 합성 쟁점에 관하여 반대 취지로 판시한 대법원 2091. 3. 14. 선고 2090다11111 판결, "
            "대법원 2092. 5. 2. 선고 2091다22222 판결 등은 이 판결의 견해에 배치되는 범위에서 이를 모두 변경하기로 한다.",
    "기본": "종전에 이와 달리 판단한 대법원 2091. 3. 14. 선고 2090다11111 판결은 이 판결의 견해에 배치되는 범위에서 이를 변경하기로 한다.",
    "내에서": "이와 견해를 달리한 대법원 2090다11111 판결 등은 이 판결의 견해에 배치되는 범위 내에서 변경한다.",
}


@pytest.mark.parametrize("form", sorted(FORMULA))
def test_overruling_sentence_forms_list_the_changed_cases(form):
    text = "앞 문단의 합성 판시이다. " + FORMULA[form] + " 그러므로 상고를 기각한다."
    [item] = overruling_sentences(text)
    assert "2090다11111" in item["case_numbers"] and item["sentence"].startswith(("이와", "종전에"))


@pytest.mark.parametrize("text", [
    "원심판결을 파기하고, 사건을 원심법원에 환송한다.",                                # 변경 문장 없음
    "종전 대법원 2090다11111 판결의 견해를 변경할 필요는 없다.",                       # 변경하지 않는다는 문장
    "대법원 2090다11111 판결은 이 판결의 견해와 같은 취지이므로 이를 유지한다.",          # 유지
])
def test_non_overruling_sentences_are_ignored(text):
    assert overruling_sentences(text) == []


def test_lv05_detects_the_common_all_overruled_form():
    claim = "합성 쟁점에 관하여 반대 취지로 보아야 한다"
    found = detect_changed_precedent_distortion(claim, FORMULA["모두"], cited_case_number="2090다11111")
    assert found and found["verdict"] == "CHANGED_PRECEDENT"


# --- 역조회 -------------------------------------------------------------------------------------------
class FakeLaw:
    def __init__(self, records=None, status=AdapterStatus.READY, search_status=AdapterStatus.READY, details=None):
        self.records, self._status, self.search_status = records or [], status, search_status
        self.details = details or {}
        self.searches, self.fetches = [], []

    def status(self):
        return self._status

    def search_cases_by_query(self, query, **kw):
        self.searches.append(query)
        return AdapterResponse(self.search_status, list(self.records), None, "synthetic")

    def fetch_case(self, record, **kw):
        self.fetches.append(record["case_number"])
        text = self.details.get(record["case_number"])
        return AdapterResponse(AdapterStatus.READY, [{"full_text": text}] if text else [], None, "synthetic")


class FakeLegal:
    def __init__(self, law):
        self.registry = type("R", (), {"law": law})()


def _verdict(number="2090다11111", court="대법원", date="2091-03-14", status=VerificationStatus.VERIFIED, cid="c1"):
    """파이프라인 engine_data.legal_verdicts의 판정 사전과 그 인용."""
    citation = Citation(citation_id=cid, type=CitationType.CASE, raw_text=f"{court} {number} 판결", court=court,
                        case_number=number, canonical_case_number=number, decision_date=date, page=1)
    verdict = {"citation_id": cid, "type": "CASE", "status": str(status), "levels": {}, "review": {}, "findings": [],
               "official_record": {"case_number": number, "decision_date": date, "court": court}}
    return citation, verdict


def _run(law, *pairs):
    return review_precedent_changes(FakeLegal(law), [c for c, _ in pairs], [v for _, v in pairs])


def _enbanc(number="2095다99999", date="2095-01-20", text=FORMULA["모두"], with_text=True):
    return {"case_number": number, "decision_date": date, "court": "대법원", "case_kind": "전원합의체 판결",
            "source_id": "9", "full_text": text if with_text else None}


def test_overruled_precedent_gets_a_review_warning_with_official_sentence():
    law = FakeLaw([_enbanc()])
    pair = _verdict()
    citation, verdict = pair
    out = _run(law, pair)
    change = verdict["review"]["precedent_change"]
    assert change["status"] == "OVERRULED" and change["overruled_by"]["case_number"] == "2095다99999"
    [finding] = out["findings"]
    assert finding.type == FindingType.CASE_HOLDING_DISTORTION and finding.status == VerificationStatus.SUSPICIOUS
    assert "PRECEDENT_OVERRULED" in finding.tags and "배치되는 범위" in finding.confidence_features["grounded_evidence_quote"]
    assert finding.confidence_features["citation_id"] == citation.citation_id
    assert verdict["status"] == str(VerificationStatus.VERIFIED)  # 실재 확인 판정은 바꾸지 않는다
    assert finding.detail.startswith("대법원 2095. 1. 20. 선고 2095다99999 전원합의체 판결이") and len(finding.detail) < 120
    assert finding.evidence[0].excerpt.endswith("변경하기로 한다")  # 변경 문장 전문은 근거에
    assert [f["finding_id"] for f in verdict["findings"]] == [finding.finding_id]  # 판정 사전에도 연결
    assert out["status"] == "OVERRULED_FOUND" and out["looked_up"] == 1


def test_same_citation_in_several_dated_reviews_is_looked_up_and_warned_once():
    law = FakeLaw([_enbanc()])
    citation, first = _verdict()
    second = {**first, "review": {}, "findings": []}  # 기준일별 판정 사본(같은 인용)
    out = review_precedent_changes(FakeLegal(law), [citation], [first, second])
    assert len(law.searches) == 1 and len(out["findings"]) == 1
    assert second["review"]["precedent_change"]["status"] == "OVERRULED"


@pytest.mark.parametrize("records", [
    [_enbanc(text=FORMULA["모두"].replace("2090다11111", "2090다11112"))],  # 다른 사건이 변경됨
    [_enbanc(date="2090-01-01")],                                              # 인용 판례보다 앞선 판결
    [_enbanc(number="2090다11111")],                                           # 자기 자신
    [{**_enbanc(), "full_text": "합성 판결 이유에는 변경 문장이 없다."}],
])
def test_no_warning_without_a_later_overruling_sentence_naming_the_cited_case(records):
    pair = _verdict()
    out = _run(FakeLaw(records), pair)
    change = pair[1]["review"]["precedent_change"]
    assert out["findings"] == [] and change["status"] in ("NOT_FOUND_IN_SCOPE", "INCOMPLETE")
    assert "확인은 아니다" in change["note"]


def test_lookup_failure_and_offline_source_do_not_warn():
    failed = _verdict()
    out = _run(FakeLaw(search_status=AdapterStatus.RATE_LIMITED), failed)
    assert out["findings"] == [] and failed[1]["review"]["precedent_change"]["status"] == "LOOKUP_FAILED"
    offline_law = FakeLaw([_enbanc()], status=AdapterStatus.DISABLED)
    offline = _verdict()
    out = _run(offline_law, offline)
    assert out["findings"] == [] and offline[1]["review"]["precedent_change"]["reason"] == "SOURCE_UNAVAILABLE"
    assert offline_law.searches == [] and out["status"] == "SOURCE_UNAVAILABLE"


@pytest.mark.parametrize("pair", [
    _verdict(court="서울고등법원", number="2090나11111"),          # 하급심
    _verdict(status=VerificationStatus.NOT_FOUND),                 # 실재 미확인
])
def test_only_officially_confirmed_supreme_court_precedents_are_checked(pair):
    law = FakeLaw([_enbanc()])
    out = _run(law, pair)
    assert law.searches == [] and "precedent_change" not in pair[1]["review"] and out["status"] == "NO_TARGET"


def test_full_text_is_fetched_when_missing_and_fetches_are_capped():
    records = [_enbanc(number=f"2095다{90000 + i}", date=f"2095-01-{10 + i:02d}", with_text=False) for i in range(6)]
    details = {records[0]["case_number"]: "합성 판결 이유이다.", records[5]["case_number"]: FORMULA["기본"]}
    law = FakeLaw(records, details=details)
    pair = _verdict()
    _run(law, pair)
    assert pair[1]["review"]["precedent_change"]["status"] == "OVERRULED"  # 최근 판결(2095-01-15)부터 본다
    assert len(law.fetches) <= MAX_FETCH_PER_CITATION


def test_lookup_budget_and_same_case_dedup():
    law = FakeLaw([])
    pairs = [_verdict(number=f"2090다{20000 + i}", cid=f"c{i}") for i in range(MAX_CITATIONS + 2)]
    pairs.append(_verdict(number="2090다20000", cid="dup"))
    _run(law, *pairs)
    assert len(law.searches) == MAX_CITATIONS
    assert [v["review"]["precedent_change"].get("reason") for _, v in pairs[MAX_CITATIONS:MAX_CITATIONS + 2]] \
        == ["LOOKUP_BUDGET"] * 2
    assert pairs[-1][1]["review"]["precedent_change"]["status"] == pairs[0][1]["review"]["precedent_change"]["status"]


def test_offline_registry_records_not_assessed_without_lookup(registry):
    pair = _verdict()
    out = review_precedent_changes(LegalVerifier(registry), [pair[0]], [pair[1]])
    assert out["findings"] == [] and pair[1]["review"]["precedent_change"]["status"] == "NOT_ASSESSED"


def test_pipeline_runs_the_stage_outside_citation_lookup(tmp_path):
    """처리 흐름의 별도 단계로 기록되고(인용 확인 단계와 분리), 오프라인 합성 실행에서 경고를 내지 않는다."""
    from scripts.audit.runner import run_synthetic
    result = run_synthetic(tmp_path)["result"]
    record = result.run_manifest["engines"]["precedent_change"]
    assert record["input_unit"] == "역조회한 판례" and record["errors"] in ([], 0, None)
    assert not any("PRECEDENT_OVERRULED" in (f.tags or []) for f in result.all_findings)
