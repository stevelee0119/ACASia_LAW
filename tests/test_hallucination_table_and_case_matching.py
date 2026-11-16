"""P0-1 및 P1-1: 대조표 법령 오인 제외·AI 의견 행 정렬·구 사건부호·헌재 라우팅·상세조회 교차오염 방지 시험."""
from __future__ import annotations

import asyncio
import json
from datetime import date
from types import SimpleNamespace

import pytest

from packages.common.enums import (
    AdapterStatus,
    CitationType,
    ExternalAIPolicy,
    VerificationStatus,
)
from packages.common.schemas import Block, Citation, NormalizedDocument, Page
from packages.legal_engine.actionable_guidance import LAW_GO_KR_URL, SCOURT_RULING_SEARCH_URL, generate_actionable_guidance
from packages.legal_engine.argument_validity_verifier import verify_argument_validity
from packages.legal_engine.citation_extractor import extract_from_text
from packages.legal_engine.normalize import case_code_meaning, case_number_possible, is_supreme_court_code
from packages.legal_engine.verifier import LegalVerifier


def _make_doc(text: str) -> NormalizedDocument:
    block = Block(block_id="b1", page=1, text=text)
    page = Page(page_number=1, width=1000.0, height=1400.0, blocks=[block])
    return NormalizedDocument(
        document_id="doc_p01_p11",
        filename="synthetic_brief.pdf",
        mime_type="application/pdf",
        sha256="1" * 64,
        pages=[page],
    )


# ---------------------------------------------------------------------------
# P0-1: 확인된 법령·행정규칙의 대조표 제외 & 미확인 법령 guidance 분기 & item_id 정렬
# ---------------------------------------------------------------------------

def test_verified_statute_and_admin_rule_excluded_from_hallucination_table():
    doc = _make_doc(
        "원고는 민법 제750조 및 행정절차 지침 제3조에 따라 청구하고, 확인안된법령 제99조를 덧붙인다."
    )
    cit_statute = Citation(
        citation_id="cit_stat_ok",
        type=CitationType.STATUTE,
        raw_text="민법 제750조",
        law_name="민법",
        article="750",
        page=1,
        context="민법 제750조에 따라 불법행위 책임을 부담한다.",
    )
    cit_admin = Citation(
        citation_id="cit_admin_ok",
        type=CitationType.ADMIN_RULE,
        raw_text="행정절차 지침 제3조",
        law_name="행정절차 지침",
        article="3",
        page=1,
        context="행정절차 지침 제3조의 절차 요건을 충족한다.",
    )
    cit_unconfirmed_stat = Citation(
        citation_id="cit_stat_missing",
        type=CitationType.STATUTE,
        raw_text="확인안된법령 제99조",
        law_name="확인안된법령",
        article="99",
        page=1,
        context="확인안된법령 제99조가 적용된다.",
    )
    verdicts = [
        {
            "citation_id": "cit_stat_ok",
            "status": "VERIFIED",
            "levels": {"existence": "VERIFIED", "article": "VERIFIED", "content": "NOT_ASSERTED"},
            "official_record": {"law_name": "민법", "version_id": "101"},
            "findings": [],
        },
        {
            "citation_id": "cit_admin_ok",
            "status": "PARTIALLY_VERIFIED",
            "levels": {"existence": "VERIFIED", "article": "VERIFIED", "content": "NOT_ASSERTED"},
            "official_record": {"rule_name": "행정절차 지침", "admrul_id": "202"},
            "findings": [],
        },
        {
            "citation_id": "cit_stat_missing",
            "status": "NOT_FOUND",
            "levels": {"existence": "NOT_FOUND"},
            "official_record": None,
            "findings": [],
        },
    ]

    result = asyncio.run(verify_argument_validity(doc, [cit_statute, cit_admin, cit_unconfirmed_stat], verdicts, []))
    assert [r.citation_id for r in result.rows] == ["cit_stat_missing"]
    row = result.rows[0]
    assert row.actionable_guidance["official_portal_url"] == LAW_GO_KR_URL
    assert "판결서 사본" not in (row.actionable_guidance.get("draft_motion_text") or "")
    assert "법령" in (row.actionable_guidance.get("draft_motion_text") or "")


def test_actionable_guidance_branches_by_citation_type():
    # 양성 3건: STATUTE(CONFIRMED_NONEXISTENT), ADMIN_RULE(UNCONFIRMED), STATUTE(CONTENT_MISMATCH)
    g1 = generate_actionable_guidance(
        basis="CONFIRMED_NONEXISTENT",
        cited_authority="가상특례법 제12조",
        citation_type=CitationType.STATUTE,
    )
    assert g1["official_portal_url"] == LAW_GO_KR_URL
    assert "법령" in g1["action_title"]
    assert "판결문" not in (g1["draft_motion_text"] or "")

    g2 = generate_actionable_guidance(
        basis="UNCONFIRMED",
        cited_authority="기관내부예규 제5조",
        citation_type=CitationType.ADMIN_RULE,
    )
    assert g2["official_portal_url"] == LAW_GO_KR_URL
    assert "행정규칙" in g2["action_title"]
    assert "판결서" not in (g2["draft_motion_text"] or "")

    g3 = generate_actionable_guidance(
        basis="CONTENT_MISMATCH",
        cited_authority="가상기본법 제8조",
        citation_type=CitationType.STATUTE,
    )
    assert g3["official_portal_url"] == LAW_GO_KR_URL
    assert "법령" in g3["guidance_summary"]

    # 대조군: CASE는 기존 법원 판결서 열람 안내 유지
    c1 = generate_actionable_guidance(
        basis="UNCONFIRMED",
        cited_authority="대법원 2020다44444 판결",
        citation_type=CitationType.CASE,
    )
    assert c1["official_portal_url"] == SCOURT_RULING_SEARCH_URL
    assert "판결서 사본 제출 요구서 안" in (c1["draft_motion_text"] or "")


def test_attach_ai_opinions_preserves_original_item_id_when_subset_filtered():
    doc = _make_doc(
        "대법원 2019다10001 판결, 대법원 2020다20002 판결, 대법원 2021다30003 판결, 대법원 2022다40004 판결."
    )
    c1 = Citation(citation_id="c1", type=CitationType.CASE, raw_text="대법원 2019다10001 판결",
                  court="대법원", case_number="2019다10001", canonical_case_number="2019다10001",
                  page=1, context="2019다10001 주장")
    c2 = Citation(citation_id="c2", type=CitationType.CASE, raw_text="대법원 2020다20002 판결",
                  court="대법원", case_number="2020다20002", canonical_case_number="2020다20002",
                  page=1, context="2020다20002 주장")
    c3 = Citation(citation_id="c3", type=CitationType.CASE, raw_text="대법원 2021다30003 판결",
                  court="대법원", case_number="2021다30003", canonical_case_number="2021다30003",
                  page=1, context="2021다30003 주장")
    c4 = Citation(citation_id="c4", type=CitationType.CASE, raw_text="대법원 2022다40004 판결",
                  court="대법원", case_number="2022다40004", canonical_case_number="2022다40004",
                  page=1, context="2022다40004 주장")

    verdicts = [
        # Row 1: OFFICIAL_CONFIRMED -> cases_for_ai에서 제외됨 (item_id=1)
        {"citation_id": "c1", "status": "VERIFIED", "levels": {"level1": "VERIFIED", "level3": "VERIFIED"},
         "official_record": {"case_number": "2019다10001", "full_text": "공식 판결 전문"}, "findings": []},
        # Row 2: NOT_FOUND -> cases_for_ai 포함 (item_id=2)
        {"citation_id": "c2", "status": "NOT_FOUND", "levels": {"level1": "NOT_FOUND"},
         "official_record": None, "findings": []},
        # Row 3: summary_only -> cases_for_ai 제외 (item_id=3)
        {"citation_id": "c3", "status": "PARTIALLY_VERIFIED", "levels": {"level1": "VERIFIED"},
         "official_record": {"case_number": "2021다30003", "full_text": ""}, "findings": []},
        # Row 4: NOT_FOUND -> cases_for_ai 포함 (item_id=4)
        {"citation_id": "c4", "status": "NOT_FOUND", "levels": {"level1": "NOT_FOUND"},
         "official_record": None, "findings": []},
    ]

    seen_item_ids = []

    class FakeRouter:
        def has_available_provider(self, *, policy):
            return True

        async def consult_all(self, role, request, *, policy, expected_task=""):
            payload = json.loads(request.user)
            ids = [it["item_id"] for it in payload["items"]]
            seen_item_ids.extend(ids)
            rows_out = [
                {
                    "item_id": iid,
                    "claim_text": f"항목 {iid} 주장",
                    "validity_verdict": "부당" if iid == 4 else "판단 불가",
                    # item 2 자신의 사건번호(2020다20002)는 own_cases로 허용되어야 한다.
                    "legal_reasoning": "2020다20002 판단 근거" if iid == 2 else "4번 항목 전용 근거",
                    "recommended_check": "확인 권고",
                }
                for iid in ids
            ]
            answer = SimpleNamespace(
                used=True,
                parsed={"overall_summary": "검토 요약", "rows": rows_out},
                text="",
                executions=[SimpleNamespace(provider="openai", model="fake-model", error=None)],
            )
            return [answer]

    result = asyncio.run(verify_argument_validity(
        doc,
        [c1, c2, c3, c4],
        verdicts,
        [],
        router=FakeRouter(),
        external_ai_policy=ExternalAIPolicy.MASKED,
        related_authorities={"precedents": [{"case_number": "2018다99999", "court": "대법원"}]},
    ))

    assert seen_item_ids == [2, 4]
    by_cid = {r.citation_id: r for r in result.rows}
    assert by_cid["c1"].ai_opinions == []
    assert by_cid["c3"].ai_opinions == []
    assert len(by_cid["c2"].ai_opinions) == 1
    assert by_cid["c2"].ai_opinions[0]["filtered_out_unprovided"] is False
    assert "2020다20002" in by_cid["c2"].ai_opinions[0]["reasoning"]
    assert len(by_cid["c4"].ai_opinions) == 1
    assert by_cid["c4"].ai_opinions[0]["verdict"] == "부당"
    assert "4번 항목 전용 근거" in by_cid["c4"].ai_opinions[0]["reasoning"]


# ---------------------------------------------------------------------------
# P1-1: 구 사건부호(다카 등)·헌재 선고 추출·constitutional 라우팅·상세조회 오염 방지
# ---------------------------------------------------------------------------

def test_legacy_and_yaml_case_codes_validation():
    # 양성 3건 이상: 구 사건부호(다카, 나카), 재심(재다), 예규 YAML(카확, 스)
    for valid_no in ("89다카1234", "85나카567", "1995재다123", "2019카확123", "2020스45"):
        assert case_number_possible(valid_no) is True, valid_no
    assert is_supreme_court_code("다카") is True
    assert case_code_meaning("다카") is not None

    # 대조군 3건 이상: 미래 연도, 미존재 부호
    next_year = date.today().year + 1
    for invalid_no in (f"{next_year}다77777", "2099다12345", "2011좋1839", "2099헌바12"):
        assert case_number_possible(invalid_no) is False, invalid_no


def test_constitutional_extraction_variants_and_case_control():
    # 양성 3건: 조사+선고, 자, 법원명 생략 bare
    [c_particle_seongo] = extract_from_text("헌법재판소는 2020. 4. 23. 선고 2018헌바210 결정에서 위헌을 선언했다.")
    assert c_particle_seongo.type == CitationType.CONSTITUTIONAL
    assert c_particle_seongo.case_number == "2018헌바210"
    assert c_particle_seongo.court == "헌법재판소"
    assert "헌법재판소는" not in c_particle_seongo.raw_text

    [c_ja] = extract_from_text("헌재 2019. 11. 28. 자 2017헌마345 결정")
    assert c_ja.type == CitationType.CONSTITUTIONAL
    assert c_ja.case_number == "2017헌마345"

    [c_bare] = extract_from_text("선례(2018헌바210 결정)의 취지에 따르면")
    assert c_bare.type == CitationType.CONSTITUTIONAL
    assert c_bare.case_number == "2018헌바210"

    # 대조군: 일반 법원+비헌재 부호는 CASE 유지, 헌재+대법원 부호는 CASE(법원-부호 불일치 점검 대상) 유지
    [c_ordinary] = extract_from_text("대법원 2020. 5. 14. 선고 2019다250000 판결")
    assert c_ordinary.type == CitationType.CASE

    [c_mismatch] = extract_from_text("헌법재판소는 2018. 3. 22. 2012두26401 결정에서")
    assert c_mismatch.type == CitationType.CASE


def test_verifier_fetch_case_constitutional_routing_and_contamination_guard():
    # Case 1: bare 헌재 결정 -> constitutional=True 로 fetch_case 호출 + 사건번호 일치 시 병합
    seen_calls = []

    class LawMatchingConst:
        def search_case(self, query, court=None):
            rec = {
                "case_number": "2018헌바210",
                "court": "헌법재판소",
                "decision_date": "2020-04-23",
                "case_name": "가상 위헌심판",
                "case_kind": "결정",
                "full_text": "",
                "raw": {"헌재결정례일련번호": "9001"},
            }
            return SimpleNamespace(status=AdapterStatus.READY, records=[rec], source_record=None, message="", found=True)

        def fetch_case(self, case, *, constitutional=False):
            seen_calls.append((case.get("case_number"), constitutional))
            return SimpleNamespace(
                status=AdapterStatus.READY,
                records=[{"case_number": "2018헌바210", "full_text": "헌법재판소 결정 전문", "summary": "요지"}],
                source_record=None,
            )

    [bare_const] = extract_from_text("2018헌바210 결정")
    res1 = LegalVerifier(SimpleNamespace(law=LawMatchingConst())).verify_citations([bare_const], current_date="2026-09-25")
    assert seen_calls == [("2018헌바210", True)]
    assert res1.data["verdicts"][0]["official_record"]["full_text"] == "헌법재판소 결정 전문"

    # Case 2: fetch_case가 다른 사건번호의 상세 기록을 돌려주면 병합 차단
    class LawMismatchedDetail:
        def search_case(self, query, court=None):
            rec = {
                "case_number": "2018헌바210",
                "court": "헌법재판소",
                "decision_date": "2020-04-23",
                "case_name": "가상 사건",
                "case_kind": "결정",
                "full_text": "",
            }
            return SimpleNamespace(status=AdapterStatus.READY, records=[rec], source_record=None, message="", found=True)

        def fetch_case(self, case, *, constitutional=False):
            return SimpleNamespace(
                status=AdapterStatus.READY,
                records=[{"case_number": "2015도99999", "full_text": "전혀 다른 형사 사건 전문"}],
                source_record=None,
            )

    res2 = LegalVerifier(SimpleNamespace(law=LawMismatchedDetail())).verify_citations([bare_const], current_date="2026-09-25")
    assert not res2.data["verdicts"][0]["official_record"].get("full_text")
    assert any("사건번호" in n and "건너뜀" in n for n in res2.data["verdicts"][0]["notes"])

    # Case 3: 공식 DB 일치 시 number_format IMPOSSIBLE 초기화 확인 (대조군)
    cit_unknown_code = Citation(
        citation_id="c_unk",
        type=CitationType.CASE,
        raw_text="대법원 1989. 5. 10. 선고 88특수123 판결",
        court="대법원",
        decision_date="1989-05-10",
        case_number="88특수123",
        canonical_case_number="88특수123",
        case_kind="판결",
    )

    class LawConfirmsUnknownCode:
        def search_case(self, query, court=None):
            rec = {
                "case_number": "88특수123",
                "court": "대법원",
                "decision_date": "1989-05-10",
                "case_name": "특수사건",
                "case_kind": "판결",
                "full_text": "공식 판결 전문",
            }
            return SimpleNamespace(status=AdapterStatus.READY, records=[rec], source_record=None, message="", found=True)

    res3 = LegalVerifier(SimpleNamespace(law=LawConfirmsUnknownCode())).verify_citations([cit_unknown_code], current_date="2026-09-25")
    assert res3.data["verdicts"][0]["levels"]["number_format"] == "VALID"
    assert res3.data["verdicts"][0]["status"] != VerificationStatus.SUSPICIOUS.value
