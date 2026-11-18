"""261116 Batch C(항목 9 Time-Table 사실관계 필터링 · 항목 8·8-1 무리한 주장/계산 논리 흐름) 회귀 시험."""
from __future__ import annotations

import io
import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
from frontend_helpers import select_first_project

from packages.claim_engine.calculation import CalculationEngine
from packages.claim_engine.extractor import extract_events
from packages.claim_engine.fact_checks import check_periods
from packages.claim_engine.korean_amount import words_digits_mismatches
from packages.common.enums import FindingType, JobState
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.legal_engine.claim_review import review_claims
from packages.legal_engine.legal_rules import review_legal_rules
from packages.verification_engine.review_items import build_document_review_items

ROOT = Path(__file__).resolve().parents[1]
CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b|\b[a-z]+_[a-z_]+\b")


def _make_doc(*texts: str, tables: list | None = None, block_type: str = "paragraph") -> NormalizedDocument:
    doc = NormalizedDocument(document_id="doc1", filename="합성서면배치C.pdf", mime_type="application/pdf", sha256="abc123")
    page = Page(page_number=1)
    for idx, text in enumerate(texts, start=1):
        page.blocks.append(Block(block_id=f"b{idx}", text=text, page=1, block_type=block_type))
    doc.pages.append(page)
    if tables is not None:
        doc.structure["tables"] = tables
    return doc


# ==============================================================================
# 항목 9: Time-Table 판례·법령 날짜 배제 / 사건 사실관계 중심 구성 (>= 3 양성 + >= 3 대조)
# ==============================================================================

@pytest.mark.parametrize(
    "sentence",
    [
        "대법원 2021. 5. 13. 선고 2020다99881 판결은 손해배상 책임의 성립 요건을 설시하였다.",
        "헌법재판소 2019. 7. 18.자 2018헌마999 전원재판부 결정에 따르면 심판청구는 부적법하다.",
        "가상특별법(2022. 1. 4. 법률 제88001호로 일부 개정되어 2022. 7. 5.부터 시행된 것) 제3조가 적용된다.",
        "가상공공법은 2015. 3. 27. 제정되어 2016. 1. 1.부터 시행되었다.",
    ],
)
def test_item9_positive_excludes_precedent_and_statute_dates(sentence: str):
    """[항목 9 양성] 판례 선고일·헌재 결정일·법령 제개정 및 시행일은 Time-Table에서 제외한다."""
    events = extract_events(_make_doc(sentence))
    assert events == [], f"판례·법령 날짜가 타임라인에 포함됨: {[e.description for e in events]}"


def test_item9_positive_mixed_sentence_keeps_only_fact_date():
    """[항목 9 양성/혼합문] 같은 문장에 사건 사실 날짜와 인용 판례 날짜가 함께 있으면 사건 날짜만 남긴다."""
    sentence = (
        "피고는 2023. 4. 10. 원고와 물품 공급 계약을 체결하고 계약금을 수령하였으며, "
        "이는 대법원 2019. 2. 14. 선고 2018다77001 판결의 취지에도 부합한다."
    )
    events = extract_events(_make_doc(sentence))
    assert [e.date for e in events] == [date(2023, 4, 10)]


@pytest.mark.parametrize(
    "sentence,expected_date",
    [
        ("2024. 1. 1.부터 이 사건 물품 공급 계약이 본격적으로 시행되었다.", date(2024, 1, 1)),
        ("피고인은 2023. 5. 10. 형사 사건에서 징역형의 집행유예를 선고받았다.", date(2023, 5, 10)),
        ("원고는 2024. 8. 20. 서울중앙지방법원에 이 사건 소장을 접수하였다.", date(2024, 8, 20)),
        ("이 사건 제1심 법원은 2024. 9. 12. 원고 일부 승소 판결을 선고하였다.", date(2024, 9, 12)),
    ],
)
def test_item9_control_preserves_party_facts_and_instant_procedural_events(sentence: str, expected_date: date):
    """[항목 9 대조군] 당사자 사실관계 및 당해 사건 소송 경과 날짜는 유사 단어가 있어도 유지한다."""
    events = extract_events(_make_doc(sentence))
    assert [e.date for e in events] == [expected_date]


# ==============================================================================
# 항목 8 · 8-1: 계산/법리 주장 논리 흐름(2열 서면 주장 / 3열 정당 계산·결론 / 4열 확인 사항)
# ==============================================================================

def test_item8_positive_calculation_engines_populate_three_column_structure():
    """[항목 8 양성 1] 표 합계·산식 그래프·서술형 산식·한글숫자 병기·기간 계산 모두 정당한 계산 방식과 확인 사항을 분리 제공한다."""
    doc_calc = _make_doc(
        "가상 물품 단가 50,000원에 3회를 곱하면 180,000원이다.\n"
        "보증금은 일금 오백만원(5,500,000원)으로 정한다.\n"
        "2024. 1. 1.부터 2024. 1. 10.까지 총 15일간 지체하였다.",
        tables=[{
            "table_ref": "tbl-1",
            "page": 1,
            "cells": [
                ["항목", "공급가액", "부가가치세", "합계금액"],
                ["합성 자재 납품", "1,000,000원", "100,000원", "1,250,000원"],
            ],
        }],
    )
    findings = CalculationEngine().verify_document(doc_calc) + words_digits_mismatches(doc_calc) + check_periods(doc_calc)
    assert len(findings) >= 4
    for f in findings:
        feats = f.confidence_features or {}
        assert feats.get("stated_claim"), f"stated_claim 누락: {f.title}"
        assert feats.get("lawful_calculation"), f"lawful_calculation 누락: {f.title}"
        assert feats.get("verification_needed"), f"verification_needed 누락: {f.title}"

    doc_res = SimpleNamespace(
        document_id="doc_batch_c",
        findings=findings,
        citations=[],
        ai_hallucination_table=[],
        engine_data={},
    )
    items = build_document_review_items(doc_res)
    assert len(items) == len(findings)
    for item in items:
        assert item.reasoning_sections and item.reasoning_sections.get("review")
        assert item.counteraction
        assert item.claim_text != item.reasoning_sections["review"]
        assert CODE_RE.findall(item.reasoning_sections["review"]) == []
        assert CODE_RE.findall(item.counteraction) == []


def test_item8_positive_legal_rule_and_claim_review_items_separate_columns():
    """[항목 8-1 양성 2] 무리한 법리 주장 finding은 2열 원 주장 / 3열 정당 법리 결론·근거 / 4열 확인 필요 내용으로 분리된다."""
    text = (
        "청구취지\n"
        "1. 피고를 징역 1년에 처한다.\n"
        "청구원인\n"
        "1. 서명하지 않은 합의는 언제나 법적으로 효력이 없다.\n"
        "2. 피고가 무손해 반증을 제시하지 못하면 원고 청구액 전액이 손해로 확정 간주된다.\n"
    )
    doc = _make_doc(text)
    rule_findings = review_legal_rules(doc)
    claim_findings = review_claims(doc, skip_sentences=[f.confidence_features.get("claim", "") for f in rule_findings])
    all_findings = rule_findings + claim_findings
    assert len(all_findings) >= 2

    doc_res = SimpleNamespace(
        document_id="doc_batch_c",
        findings=all_findings,
        citations=[],
        ai_hallucination_table=[],
        engine_data={},
    )
    items = build_document_review_items(doc_res)
    for item in items:
        assert item.reasoning_sections and item.reasoning_sections.get("review")
        assert item.counteraction
        assert " — '" not in item.verdict_label
        assert CODE_RE.findall(item.verdict_label) == []
        assert CODE_RE.findall(item.reasoning_sections["review"]) == []
        assert CODE_RE.findall(item.counteraction) == []


def test_item8_positive_docx_and_pdf_reports_include_tier3_items_without_codes():
    """[항목 8·8-1 양성 3] DOCX와 PDF 보고서 '3. 법률적으로 무리한 주장' 표에 3단 계산·법리 항목이 코드 없이 실린다."""
    docx_mod = pytest.importorskip("docx")
    pypdf = pytest.importorskip("pypdf")
    from apps.api.routers.reports import _DocumentView
    from packages.report_engine import build_report_docx
    from packages.report_engine.pdf_report import build_report_pdf

    doc = _make_doc(
        "가상 품목 단가 10,000원에 5개를 곱하면 70,000원이다.",
        tables=[{
            "table_ref": "tbl-rep",
            "page": 2,
            "cells": [
                ["구분", "금액"],
                ["품목1", "100,000원"],
                ["품목2", "200,000원"],
                ["합계", "350,000원"],
            ],
        }],
    )
    findings = CalculationEngine().verify_document(doc)
    items = build_document_review_items(SimpleNamespace(
        document_id=doc.document_id,
        findings=findings,
        citations=[],
        ai_hallucination_table=[],
        engine_data={},
    ))

    result_json = {
        "documents": [{
            "document_id": doc.document_id,
            "filename": doc.filename,
            "sha256": doc.sha256,
            "findings": [],
            "review_items": [i.to_dict() for i in items],
            "ai_hallucination_table": [],
            "engine_data": {},
        }]
    }
    doc_view = _DocumentView(
        SimpleNamespace(id=doc.document_id, filename=doc.filename, quarantined=False, rag_indexable=False, sha256=doc.sha256),
        findings,
        result_json,
    )
    run_view = SimpleNamespace(
        run_id="run1",
        project_id="proj1",
        verification_key="vk1",
        state=JobState.COMPLETED,
        started_at=datetime(2026, 11, 16, 10, 0),
        finished_at=datetime(2026, 11, 16, 10, 1),
        scores={},
        timeline=[],
        unavailable_sources=[],
        unverified_items=[],
        errors=[],
        input_snapshot={},
        model_executions=[],
        run_manifest={},
        source_objects={},
        documents=[doc_view],
        project_findings=[],
        all_findings=findings,
    )

    docx_bytes = build_report_docx(run_view, project={"name": "배치C 검증"})
    d = docx_mod.Document(io.BytesIO(docx_bytes))
    docx_text = "\n".join([p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells])
    assert "3. 법률적으로 무리한 주장" in docx_text
    assert "300,000원" in docx_text and "350,000원" in docx_text
    assert "확인 필요 사항:" in docx_text
    docx_body = docx_text.split("전체 기술 부록", 1)[0]
    assert CODE_RE.findall(docx_body) == []

    pdf_bytes = build_report_pdf(run_view, project={"name": "배치C 검증"})
    pdf_text = "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(io.BytesIO(pdf_bytes)).pages)
    flat_pdf = re.sub(r"\s+", "", pdf_text)
    assert "3.법률적으로무리한주장" in flat_pdf
    assert "300,000원" in flat_pdf and "350,000원" in flat_pdf
    assert "확인필요사항:" in flat_pdf
    assert CODE_RE.findall(pdf_text) == []


def test_item8_positive_browser_tier3_table_shows_lawful_calc_and_verification_items():
    """[항목 8·8-1 브라우저 양성] 3단 표 3열에 정당한 계산·근거가, 4열에 확인 필요 사항이 렌더링되고 2단과 구분된다."""
    options = {"headless": True}
    if os.getenv("LV_TEST_BROWSER_CHANNEL"):
        options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]

    tier3_item = {
        "item_id": "d1_FINDING_calc1",
        "kind": "FACT",
        "document_id": "d1",
        "location": {"page": 2},
        "claim_text": "합계 기재 금액: 350,000원 (품목1 100,000원 / 품목2 200,000원)",
        "cited_authority": None,
        "official_status": "NOT_ASSESSED",
        "reference_status": "NOT_CHECKED",
        "verdict_label": "합계가 세부 금액 합산값과 다르다 (차이 50,000원)",
        "severity": "HIGH",
        "evidence_sources": ["세금계산서 합계 검산", "국세청 표준 산식"],
        "finding_ids": ["calc1"],
        "citation_id": None,
        "reasoning_sections": {
            "review": "세부 2개 항목(100,000원, 200,000원)의 정당한 합산 금액은 300,000원입니다 (서면 기재 350,000원과 차액 +50,000원).",
            "ai_label": "",
            "opinions": [],
        },
        "counteraction": "원본 계산서와 거래명세서를 대조해 누락 항목 여부를 확인해야 합니다.",
    }
    tier2_item = {
        "item_id": "d1_CITATION_cit1",
        "kind": "CITATION",
        "document_id": "d1",
        "location": {"page": 1, "display": "1쪽"},
        "claim_text": "가상 판례 인용 주장",
        "cited_authority": "대법원 2022다99991 판결",
        "official_status": "OFFICIAL_NOT_FOUND",
        "reference_status": "NOT_CHECKED",
        "verdict_label": "공식 DB 미확인",
        "severity": "HIGH",
        "finding_ids": ["citf1"],
        "citation_id": "cit1",
        "reasoning_sections": {"review": "원문 조회 범위에서 확인되지 않음", "ai_label": "", "opinions": []},
        "counteraction": "판결서 원문 대조 요청",
    }

    static_dir = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static_dir).as_posix()}": p for p in static_dir.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"

    from packages.common.display_text import CODE_WORDS, FIELD_WORDS, FINDING_TYPE_NAMES, PHRASES, WORD_NAMES
    from packages.common.finding_category_map import CATEGORY_TO_TAB, FINDING_CATEGORY_MAP, get_category_counts

    project_data = {
        "id": "p1",
        "name": "배치C UI 검증",
        "can_delete": True,
        "document_count": 1,
        "external_ai_policy": "MASKED",
        "scope_revision": 0,
        "requested_issues": [],
    }
    run_data = {
        "id": "r1",
        "project_id": "p1",
        "state": "COMPLETED",
        "progress": 1,
        "stage_message": "",
        "document_ids": ["d1"],
        "scores": {},
        "unverified_items": [],
        "errors": [],
        "unavailable_sources": [],
        "input_snapshot": {"scope_revision": 0},
        "started_at": "2026-11-16T00:00:00",
    }
    findings_data = [
        {"id": "calc1", "finding_id": "calc1", "finding_type": "ARITHMETIC_MISMATCH", "type": "ARITHMETIC_MISMATCH", "severity": "HIGH", "status": "CONTRADICTED", "review_status": "NEEDS_REVIEW", "title": tier3_item["verdict_label"], "detail": "내부 계산 불일치", "document_id": "d1", "page": 2},
        {"id": "citf1", "finding_id": "citf1", "finding_type": "CASE_NOT_FOUND", "type": "CASE_NOT_FOUND", "severity": "HIGH", "status": "UNCONFIRMED", "review_status": "NEEDS_REVIEW", "title": "판례 미확인", "detail": "조회 범위 미확인", "document_id": "d1", "page": 1, "citation_id": "cit1"},
    ]

    def route_handler(route):
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        replies = {
            "/api/health": {"status": "ok", "version": "0.22.0"},
            "/api/auth/me": {"user_id": "u", "email": "t@example.com", "display_name": "검토자", "role": "ADMIN", "authentication": "local"},
            "/api/identity/me": {"user_id": "u", "email": "t@example.com", "display_name": "검토자", "role": "ADMIN", "authentication": "local"},
            "/api/verification-runs": {"active_count": 0, "runs": []},
            "/api/projects": [project_data],
            "/api/projects/p1": project_data,
            "/api/projects/p1/documents": [{"id": "d1", "filename": "합성서면.pdf", "included_in_verification": True}],
            "/api/projects/p1/runs": [run_data],
            "/api/projects/p1/findings": findings_data,
            "/api/projects/p1/audit": {"events": []},
            "/api/projects/p1/runs/r1/external-ai-answers": {"saved": False, "codes": {}, "answers": {}},
            "/api/privacy-notice": {"version": "v1", "bullets": [], "ack_label": "", "report_header": ""},
            "/api/finding-categories": {
                "categories": {ft.value: cat.value for ft, cat in FINDING_CATEGORY_MAP.items()},
                "tabs": {ft.value: CATEGORY_TO_TAB[cat].value for ft, cat in FINDING_CATEGORY_MAP.items()},
                "counts": get_category_counts(),
                "names": FINDING_TYPE_NAMES,
                "code_words": CODE_WORDS,
                "field_words": FIELD_WORDS,
                "word_names": WORD_NAMES,
                "phrases": [list(p) for p in PHRASES],
            },
        }
        if path in replies:
            return route.fulfill(json=replies[path])
        if path.endswith(("/result", "/results")):
            return route.fulfill(json={
                "status": "COMPLETED",
                "findings": findings_data,
                "documents": [{"id": "d1", "document_id": "d1", "filename": "합성서면.pdf", "review_items": [tier3_item, tier2_item], "ai_hallucination_table": [], "engine_data": {}}],
            })
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        return route.fulfill(json=[])

    with sync_playwright() as p:
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route("**/*", route_handler)
        page.goto("http://batchc.test/")
        select_first_project(page)

        page.locator('.tabs button[data-tab="legal-claims"]').click()
        t3_row = page.locator("#tier3Rows tr").first
        expect(t3_row).to_be_visible()
        expect(t3_row.locator(".legal-conclusion-basis")).to_contain_text("정당한 합산 금액은 300,000원")
        expect(t3_row.locator(".legal-basis-sources")).to_contain_text("세금계산서 합계 검산")
        expect(t3_row.locator(".summary-verification")).to_contain_text("확인 필요 사항:")
        expect(t3_row.locator(".summary-verification")).to_contain_text("원본 계산서와 거래명세서")
        assert t3_row.locator(".summary-action").count() == 0

        # 2단 인용 표는 기존 요약 형식(.summary-reason '의심 사유')을 유지
        page.locator('.tabs button[data-tab="review"]').click()
        t2_row = page.locator("#aiVerificationRows tr").first
        expect(t2_row.locator(".summary-reason")).to_contain_text("의심 사유:")
        assert t2_row.locator(".summary-action").count() == 0
        browser.close()


# ==============================================================================
# 항목 8 · 8-1 대조군 (>= 3건): 정상 계산·정당 항변·레거시 fallback 호환성
# ==============================================================================

def test_item8_control_valid_calculations_emit_no_findings():
    """[항목 8 대조군 1] 합계·산식·한글숫자 병기·기간이 모두 일치하면 계산 불일치를 내지 않는다."""
    doc_ok = _make_doc(
        "가상 품목 단가 50,000원에 3회를 곱하면 150,000원이다.\n"
        "보증금은 일금 오백만원(5,000,000원)으로 정한다.\n"
        "2024. 1. 1.부터 2024. 1. 10.까지 총 10일간 지체하였다.",
        tables=[{
            "table_ref": "tbl-ok",
            "page": 1,
            "cells": [
                ["항목", "공급가액", "부가가치세", "합계금액"],
                ["합성 자재 납품", "1,000,000원", "100,000원", "1,100,000원"],
            ],
        }],
    )
    assert CalculationEngine().verify_document(doc_ok) == []
    assert words_digits_mismatches(doc_ok) == []
    assert check_periods(doc_ok) == []


def test_item8_control_quoted_or_properly_grounded_claims_not_flagged():
    """[항목 8-1 대조군 2] 상대방 주장 인용·예외 근거가 적힌 정상 서술은 무리한 주장으로 잡지 않는다."""
    doc_ok = _make_doc(
        "청구원인\n"
        "1. 원고는 '서명 없는 합의는 언제나 무효'라고 주장하나 이는 타당하지 않다.\n"
        "2. 민법 제750조 및 대법원 2020다11111 판결에 따라 손해배상 책임을 구한다.\n"
    )
    rules = review_legal_rules(doc_ok)
    claims = review_claims(doc_ok, skip_sentences=[f.confidence_features.get("claim", "") for f in rules])
    assert rules == [] and claims == []


def test_item8_control_minimal_synthetic_finding_preserves_fallback():
    """[항목 8-1 대조군 3] 추가 메타데이터 없는 합성 Finding도 ReviewItem 생성에서 예외 없이 폴백을 유지한다."""
    from packages.common.enums import EvidenceGrade, Severity, VerificationStatus
    from packages.common.schemas import Finding

    f = Finding.create(
        type=FindingType.MODEL_FACT_REMARK,
        status=VerificationStatus.SUSPICIOUS,
        severity=Severity.LOW,
        evidence_grade=EvidenceGrade.D,
        title="합성 사실관계 확인 요청",
        detail="합성 세부 설명",
        confidence=0.4,
        confidence_features={},
        document_id="doc_ctrl",
    )
    items = build_document_review_items(SimpleNamespace(
        document_id="doc_ctrl",
        findings=[f],
        citations=[],
        ai_hallucination_table=[],
        engine_data={},
    ))
    assert len(items) == 1
    assert items[0].claim_text == "합성 세부 설명"
    assert items[0].reasoning_sections is None
