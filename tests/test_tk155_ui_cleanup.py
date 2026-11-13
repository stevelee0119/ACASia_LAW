"""TK-155: V1.0.0 화면 정리(사용자 명세 2026-11-13, 결정 D1~D6) 회귀 시험.

문장·사건번호·법령명은 모두 합성이다(실제 서면·판결의 값이 아니다). 엔진이 실제로 내는 코드 꼴만 흉내 낸다.
"""
from __future__ import annotations

import io
import os
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
from frontend_helpers import select_first_project

from packages.common.finding_category_map import (CATEGORY_TO_TAB, FINDING_CATEGORY_MAP, FINDING_TYPE_SCREEN_NAMES,
                                                   get_category_counts)

ROOT = Path(__file__).resolve().parents[1]
CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b|\b[a-z]+_[a-z_]+\b")
LONG_REASON = ("합성 서면은 시행 전 개정 이력을 근거로 소급 적용을 주장한다. " * 12).strip()


def _finding(fid, ftype, title, detail, severity="INFO", engine="legal_engine", review="NEEDS_REVIEW", status="UNVERIFIED"):
    return {"id": fid, "finding_id": fid, "type": ftype, "finding_type": ftype, "title": title, "detail": detail,
            "severity": severity, "status": status, "review_status": review, "engine": engine, "document_id": "d1",
            "page": 3, "run_id": "r1", "project_id": "p1", "tags": [], "evidence": [], "sources": []}


FINDINGS = [
    *[_finding(f"ai{i}", "AI_AUTHORSHIP_LIKELY", "AI 작성 참고 신호 문구 (내용 오류 판정 아님)",
               f"근거: 합성 신호 {i}. 발췌: \"합성 문장 {i}\"", engine="verification_engine.ai_document_detector")
      for i in range(1, 5)],
    _finding("inj1", "META_INSTRUCTION", "META_INSTRUCTION 후보: ROLE_OVERRIDE — 경로: 보이는 본문",
             "visible_text 위치에서 지시형 문자열이 관찰되었다. 분류=INSTRUCTION_LIKE, 점수=1.0, 보조신호=0개.",
             severity="HIGH", engine="adversarial_engine", status="SUSPICIOUS"),
    _finding("c1", "TEMPORAL_LAW_MISMATCH", "법령 적용 시점 검토: 「합성법」 제1조 — 시행일이 기준일 뒤인데 소급 적용 주장 (RETROACTIVE_APPLICATION_ERROR)",
             LONG_REASON, severity="HIGH"),
    _finding("c2", "CASE_NOT_FOUND", "공식 DB 미발견 판례", "합성 판례를 조회 범위에서 찾지 못했다.", severity="MEDIUM"),
]

REVIEW_ITEMS = [
    {"item_id": "i1", "kind": "TEMPORAL", "document_id": "d1", "location": {"page": 3, "display": "3쪽"},
     "claim_text": "합성 개정 이력에 따른 소급 적용 주장", "cited_authority": "「합성법」 제1조",
     "official_status": "OFFICIAL_NOT_FOUND", "reference_status": "NOT_IN_REFERENCE",
     "verdict_label": FINDINGS[5]["title"], "severity": "HIGH", "finding_ids": ["c1"],
     "ai_generation_basis": "[RAG참고자료] 합성 설명 (NOT_ASSESSED)", "legal_reasoning": LONG_REASON},
    {"item_id": "i2", "kind": "CITATION", "document_id": "d1", "location": {"page": 4, "display": "4쪽"},
     "claim_text": "합성 판례에 따른 청구", "cited_authority": "대법원 2019다12345 판결",
     "official_status": "OFFICIAL_NOT_FOUND", "reference_status": "NOT_CHECKED", "verdict_label": "공식 DB 미확인",
     "severity": "MEDIUM", "finding_ids": ["c2"], "ai_generation_basis": "조회 범위에서 찾지 못함 (OFFICIAL_NOT_FOUND)"},
    {"item_id": "i3", "kind": "FACT", "document_id": "d1", "location": {"page": 5},
     "claim_text": "합성 사실관계 주장", "cited_authority": None, "official_status": "NOT_ASSESSED",
     "reference_status": "NOT_MENTIONED", "verdict_label": "참고문헌과 불부합", "severity": "MEDIUM", "finding_ids": [],
     "ai_generation_basis": "[RAG참고자료] 합성 참고자료와 다르다", "legal_reasoning": LONG_REASON},
]

RESULT = {"status": "PARTIAL_COMPLETED", "documents": [{
    "document_id": "d1", "id": "d1", "filename": "합성서면.pdf", "quarantined": False,
    "findings": FINDINGS, "review_items": REVIEW_ITEMS,
    "ai_hallucination_table": [{"basis": "UNCONFIRMED", "cited_authority": "대법원 2019다12345 판결"},
                               {"basis": "FABRICATION_SUSPECTED", "cited_authority": "대법원 2099다1 판결"}],
    "ai_detector_result": {"verdict": "AI_PARTIAL_GENERATION", "score": 0.6, "filename": "합성서면.pdf",
                           "reasons": ["AI 교차검증 다수 모델이 지적하여 AI_PARTIAL_GENERATION로 최종 확정함(다수결)"],
                           "signals": {"score_definition": "응답한 모델들이 낸 ai_score의 중앙값이다.",
                                       "confidence_definition": "계산한 finding.confidence이다."}},
    "engine_data": {"adversarial": {"scanned_layers": ["encoded_text", "outline", "visible_text"], "adversarial_risk": "HIGH"}},
}]}

GATE = {"release_gate": "BLOCK", "hallucination_risk": 72, "risk_index_note": "합성 지수 설명",
        "hard_block_reasons": ["CASE_NOT_FOUND: 합성 차단 사유"], "review_reasons": ["합성 검토 사유"]}


def _serve(page, project):
    static = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static).as_posix()}": p for p in static.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"
    run = {"id": "r1", "project_id": "p1", "state": "PARTIAL_COMPLETED", "progress": 1, "stage_message": "",
           "document_ids": ["d1"], "scores": {"release_gate": GATE}, "errors": [], "unavailable_sources": [],
           "unverified_items": [{"kind": "citation", "raw_text": "「합성법」 제1조", "document_id": "d1", "reason": "합성"},
                                {"kind": "reference_library", "document_id": "d1", "reason": "합성"}],
           "input_snapshot": {"scope_revision": 0}, "started_at": "2026-11-13T00:00:00"}
    cats = {"categories": {t.value: c.value for t, c in FINDING_CATEGORY_MAP.items()},
            "tabs": {t.value: CATEGORY_TO_TAB[c].value for t, c in FINDING_CATEGORY_MAP.items()},
            "counts": get_category_counts(), "names": {t.value: n for t, n in FINDING_TYPE_SCREEN_NAMES.items()}}

    def respond(route):
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        replies = {"/api/health": {"status": "ok", "version": "0.20.0"},
                   "/api/identity/me": {"user_id": "u", "role": "ADMIN", "authentication": "password"},
                   "/api/verification-runs": {"active_count": 0, "runs": []}, "/api/projects": [project],
                   "/api/projects/p1": project, "/api/projects/p1/runs": [run], "/api/projects/p1/findings": FINDINGS,
                   "/api/finding-categories": cats}
        if path in replies:
            return route.fulfill(json=replies[path])
        if path.endswith(("/result", "/results")):
            return route.fulfill(json=RESULT)
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        return route.fulfill(json=[])

    page.route("**/*", respond)
    page.goto("http://tk155.test/")
    select_first_project(page)


@pytest.fixture
def browser():
    options = {"headless": True}
    if os.getenv("LV_TEST_BROWSER_CHANNEL"):
        options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
    with sync_playwright() as playwright:
        b = playwright.chromium.launch(**options)
        yield b
        b.close()


BASE_PROJECT = {"id": "p1", "name": "합성 사건", "can_delete": True, "document_count": 1,
                "external_ai_policy": "MASKED", "scope_revision": 0}


def _codes(text):
    return sorted(set(CODE_RE.findall(text)))


def test_top_summary_three_cards_and_no_empty_meta(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    _serve(page, BASE_PROJECT)
    expect(page.locator("#summary .metric")).to_have_count(3)
    expect(page.locator(".metric", has_text="출처 미확인 인용")).to_contain_text("2건")
    expect(page.locator(".metric", has_text="출처 미확인 인용")).to_contain_text("사건번호 형식 오류 1건 포함")
    for gone in ("검토에 포함", "배포가능", "배포 가능", "검증위험", "확인 전 항목", "진행 상태", "합성 차단 사유", "합성 지수 설명"):
        expect(page.locator("#summary")).not_to_contain_text(gone)
    expect(page.locator(".run-status-line")).to_contain_text("일부 미확인")
    expect(page.locator(".eyebrow")).to_have_count(0)
    expect(page.locator("#projectMeta")).to_be_hidden()
    expect(page.locator("#projectList")).not_to_contain_text("미지정")
    assert _codes(page.locator("#summary").inner_text()) == []


def test_project_meta_shows_only_entered_values(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    _serve(page, {**BASE_PROJECT, "case_number": "2026가합1", "incident_date": "2025-01-02"})
    expect(page.locator("#projectMeta")).to_have_text("2026가합1 · 적용법령 기준 2025-01-02")


def test_ai_tab_groups_signals_and_has_no_codes(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    _serve(page, BASE_PROJECT)
    page.locator('.tabs button[data-tab="ai-verification"]').click()
    panel = page.locator('section[data-panel="ai-verification"]')
    group = panel.locator(".ai-finding-list > .security-finding-item", has_text="AI 작성 참고 신호 문구")
    expect(group).to_have_count(1)
    expect(group.locator("ol.finding-group-reasons > li")).to_have_count(4)
    expect(group).to_contain_text("(4건)")
    expect(panel).to_contain_text("프롬프트 인젝션 속임수 검증")
    expect(panel.locator("#aiTabNoticeBanner")).to_have_count(0)
    page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    assert _codes(panel.locator("#aiSummaryCards").inner_text()) == []


@pytest.mark.parametrize("tab,table", [("review", "#reviewTable"), ("legal-claims", "section[data-panel=legal-claims] table")])
def test_tables_have_no_codes_and_badges_stay_in_cells(browser, tab, table):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    _serve(page, BASE_PROJECT)
    page.locator(f'.tabs button[data-tab="{tab}"]').click()
    tbl = page.locator(table)
    expect(tbl.locator("tbody tr").first).to_be_visible()
    assert _codes(tbl.inner_text()) == []
    assert "[RAG참고자료]" not in tbl.inner_text()
    assert "구속력 없음" not in tbl.inner_text()
    overflow = tbl.evaluate("""t => [...t.querySelectorAll('td .badge')].filter(b => {
        const td = b.closest('td').getBoundingClientRect(), r = b.getBoundingClientRect();
        return r.right > td.right + 1; }).length""")
    assert overflow == 0
    expect(page.locator(f'section[data-panel="{tab}"] .reference-legend')).to_contain_text("법적 구속력은 없습니다")


def test_long_reason_is_not_cut_and_expands(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    _serve(page, BASE_PROJECT)
    page.locator('.tabs button[data-tab="legal-claims"]').click()
    panel = page.locator('section[data-panel="legal-claims"]')
    expect(panel.locator(".summary-reason").first).to_be_visible()
    expect(panel).not_to_contain_text("…")
    assert LONG_REASON[-30:] in panel.text_content()  # 전문이 DOM에 있다
    toggle = panel.locator(".clamp-toggle").first
    expect(toggle).to_have_text("더보기")
    toggle.click()
    expect(toggle).to_have_text("접기")


def test_search_box_and_security_banner_removed(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    _serve(page, BASE_PROJECT)
    page.locator('.tabs button[data-tab="review"]').click()
    expect(page.locator("#findingSearch")).to_have_count(0)
    expect(page.locator("#highSecurityAlertBanner")).to_have_count(0)
    card = page.locator("details.unverified-card")
    expect(card).to_contain_text("미확인 범위 2건")
    expect(card).to_contain_text("인용 1")
    expect(card).to_contain_text("참고자료 1")


def test_readable_source_message_and_particles():
    from packages.legal_engine.verifier import _readable_source_message
    from packages.verification_engine.review_items import HUMAN_READABLE_UNVERIFIED_REASONS
    english, korean = next((k, v) for k, v in HUMAN_READABLE_UNVERIFIED_REASONS.items() if re.search(r"[A-Za-z]{4,} [a-z]", k))
    assert _readable_source_message(english).rstrip(".") == korean
    assert _readable_source_message("합성 메시지") == "합성 메시지"
    source = (ROOT / "packages/legal_engine/argument_validity_verifier.py").read_text(encoding="utf-8")
    assert "{noun}을(를)" not in source and "{noun}이(가)" not in source


def test_xlsx_summary_has_no_release_gate_rows():
    openpyxl = pytest.importorskip("openpyxl")
    from packages.report_engine.exporters import to_xlsx
    from datetime import datetime
    from packages.common.enums import JobState
    run = SimpleNamespace(run_id="r1", project_id="p1", verification_key="k", state=JobState.COMPLETED,
                          started_at=datetime(2026, 11, 13), finished_at=datetime(2026, 11, 13), scores={"release_gate": GATE},
                          timeline=[], unavailable_sources=[], unverified_items=[], errors=[], findings=[],
                          project_findings=[], all_findings=[], model_executions=[], run_manifest={}, documents=[])
    data = to_xlsx(run)
    sheet = openpyxl.load_workbook(io.BytesIO(data)).worksheets[0]
    labels = [row[0] for row in sheet.iter_rows(values_only=True) if row]
    for gone in ("배포가능 상태", "검증위험 지수", "지수 성격", "차단 사유", "사람 검토 사유"):
        assert gone not in labels


def test_finding_categories_api_serves_screen_names():
    from fastapi.testclient import TestClient
    from apps.api.main import app
    from packages.common.enums import ADVERSARIAL_FINDING_TYPES

    names = TestClient(app).get("/api/finding-categories").json()["names"]
    assert set(names) == {t.value for t in ADVERSARIAL_FINDING_TYPES}
    assert all(re.search(r"[가-힣]", n) for n in names.values())
