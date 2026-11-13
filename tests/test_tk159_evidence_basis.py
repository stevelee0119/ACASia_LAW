"""TK-159(B1): 판정별 근거 원문 식별자·구간·근거 상태(시험용 내부 Mirror의 가상 판례·법령, 합성 문장)."""
from __future__ import annotations

import pytest

from packages.common.textutil import contains_fuzzy_normalized, locate_fuzzy_normalized, normalize_quote
from packages.legal_engine.evidence_basis import quote_span, sha256_text
from test_legal_engine import _verify  # noqa: F401  (같은 Mirror·추출 경로)

STATUSES = {"SOURCE_MATCHED", "SOURCE_MISMATCHED", "SOURCE_FOUND_NOT_DECIDED", "LOOKUP_FAILED", "NOT_FOUND",
            "NO_SOURCE", "RULE_BASED", "MISSING_BASIS"}


def test_every_verdict_carries_a_basis_with_a_known_status(registry):
    _, result = _verify(registry, '대법원 2099. 1. 15. 선고 2099도99999 판결은 "테스트를 위한 가상의 판시사항이다"라고 판시하였다. '
                                  "대법원 2019. 3. 3. 선고 2019도88888 판결")
    for verdict in result.data["verdicts"]:
        basis = verdict["evidence_basis"]
        assert basis["basis_status"] in STATUSES
        assert basis["basis_status"] != "MISSING_BASIS"  # 확인·불일치 판정은 근거 식별자를 가져야 한다


def test_quote_match_records_official_source_and_span(registry):
    _, result = _verify(registry, '대법원 2099. 1. 15. 선고 2099도99999 판결은 "테스트를 위한 가상의 판시사항이다"라고 판시하였다.')
    basis = result.data["verdicts"][0]["evidence_basis"]
    assert basis["basis_status"] == "SOURCE_MATCHED"
    assert basis["source"]["id"] and basis["source"]["case_number"]
    span = basis["passage"]
    assert span["normalization"] == "normalize_quote" and span["end"] > span["start"] >= 0
    assert "가상의 판시사항" in span["excerpt"] and len(span["text_sha256"]) == 64


def test_lookup_unavailable_is_not_reported_as_a_mismatch(registry):
    _, result = _verify(registry, "대법원 2019. 3. 3. 선고 2019도88888 판결")
    basis = result.data["verdicts"][0]["evidence_basis"]
    assert basis["source"] is None and basis["basis_status"] in ("LOOKUP_FAILED", "NOT_FOUND", "NO_SOURCE")


def test_metadata_mismatch_is_a_source_mismatch_with_identifier(registry):
    _, result = _verify(registry, "대법원 2098. 5. 5. 선고 2099도99999 판결")
    basis = result.data["verdicts"][0]["evidence_basis"]
    assert basis["basis_status"] == "SOURCE_MISMATCHED" and basis["source"]["id"]


@pytest.mark.parametrize("hay,needle", [
    ("가 나 다 라 마 바 사 아 자 차 카 타 파 하", "라 마 바 사"),
    ("이 조문은 손해를 배상할 책임을 진다고 규정한다", "손해를 배상할 책임을 진다"),
    ("이 조문은 손해를 배상할 책임을 진다고 규정한다", "손해를 배상한 책임을 진다"),  # 근사 일치
])
def test_locate_agrees_with_contains_fuzzy(hay, needle):
    h, n = normalize_quote(hay), normalize_quote(needle)
    ratio, start = locate_fuzzy_normalized(h, n)
    _, best = contains_fuzzy_normalized(h, n, threshold=1.01)  # 끝까지 훑은 최고값
    assert start >= 0 and abs(ratio - best) < 1e-9


def test_quote_span_hash_matches_normalized_text():
    span = quote_span("손해를 배상할 책임", "이 조문은 손해를 배상할 책임을 진다")
    assert span["text_sha256"] == sha256_text(normalize_quote("이 조문은 손해를 배상할 책임을 진다"))
    assert quote_span("", "원문") is None and quote_span("인용", "") is None


def test_official_statute_basis_has_version_and_provision_hash(monkeypatch, tmp_path):
    from packages.common.enums import AdapterStatus
    from packages.legal_engine.evidence_basis import build_basis
    from packages.source_adapters.law_go_kr import LawGoKrAdapter
    from packages.source_adapters.local_mirror import LocalLegalMirror
    from test_legal_completion import install_law, statute, verifier

    law = LawGoKrAdapter(mirror=LocalLegalMirror(tmp_path / "empty"))
    monkeypatch.setattr(law, "status", lambda: AdapterStatus.READY)
    monkeypatch.setattr(LawGoKrAdapter, "api_key", property(lambda self: "TEST_ONLY_KEY"))
    install_law(monkeypatch, law)
    verdict = verifier(law).verify_statute(statute(), as_of="2021-12-31", current_date="2026-11-13")
    basis = build_basis(verdict)
    assert basis["source"]["kind"] == "OFFICIAL_LAW"
    assert basis["source"]["version_id"] == "100" and basis["source"]["effective_from"] == "2019-01-01"
    assert len(basis["passage"]["text_sha256"]) == 64 and basis["passage"]["path"]["article"] == "10의2"


def test_impossible_case_number_contradiction_is_rule_based(registry):
    _, result = _verify(registry, "대법원 2099. 3. 3. 선고 2099도88888 판결")  # 아직 오지 않은 연도(형식 규칙)
    rows = [v["evidence_basis"] for v in result.data["verdicts"] if v["status"] == "CONTRADICTED"]
    assert rows and all(b["basis_status"] == "RULE_BASED" and b["source"]["rules"] for b in rows)
