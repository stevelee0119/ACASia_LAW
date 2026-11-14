"""검토 결정 대기(탭 머리 배지)와 실행 상태 안내(사유 보기)를 누르면 뜻과 세부 내역·대책이 보여야 한다.

V1.0.0 명세 1-3-5·1-3-6과 사용자 결정 D1·D2(2026-11-13)로 옛 요구(상단 카드 '확인 전 항목'·'진행 상태')를
바꾼 단언이다(사용자 승인). 설명 대화상자의 내용 단언은 그대로 둔다.
"""
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
from frontend_helpers import select_first_project

ROOT = Path(__file__).resolve().parents[1]
UNVERIFIED = [
    {"kind": "citation", "raw_text": "대법원 2011모1839 결정", "document_id": "d1", "scope": "PARTIAL", "status": "PARTIALLY_VERIFIED",
     "reason": "판례 존재·메타데이터 확인과 취지·사건 적용 가능성 검토는 별도이다"},
    {"kind": "citation", "raw_text": "대법원 2015모2524 결정", "document_id": "d1", "scope": "UNVERIFIED", "status": "UNVERIFIED",
     "reason": "외부 출처 자동 재조회 후에도 확인하지 못한 요청이 남아 있다", "source_lookup": {"retryable": True}},
    {"kind": "page", "document_id": "d1", "page": 3, "status": "UNVERIFIED", "reason": "스캔 쪽 글자 인식 실패"},
    {"kind": "citation", "raw_text": "민법 제750조", "document_id": "d1", "scope": "UNVERIFIED", "status": "UNVERIFIED",
     "reason": "법령 적용 기준일이 입력되지 않았다"},
]
FINDINGS = [
    {"id": f"f{i}", "run_id": "r1", "project_id": "p1", "document_id": "d1", "type": t, "status": st, "severity": sev,
     "evidence_grade": "C", "confidence": 0.5, "page": 1, "block_id": None, "title": f"항목 {i}", "detail": "",
     "engine": "legal_engine", "meta_message_type": None, "advisory_only": False, "tags": [], "review_status": rs,
     "review_note": "", "has_sealed_content": False, "evidence": [], "sources": []}
    for i, (t, st, sev, rs) in enumerate([
        ("CASE_NOT_FOUND", "UNVERIFIED", "MEDIUM", "NEEDS_REVIEW"),
        ("CITATION_MISMATCH", "CONTRADICTED", "HIGH", "NEEDS_REVIEW"),
        ("METADATA_ANOMALY", "SUSPICIOUS", "LOW", "NEEDS_REVIEW"),
        ("CITATION_MISMATCH", "CONTRADICTED", "HIGH", "ACCEPTED")])
]


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 1400)])
def test_pending_and_status_metrics_explain_themselves(width, height):
    static = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static).as_posix()}": p for p in static.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"
    run = {"id": "r1", "project_id": "p1", "state": "PARTIAL_COMPLETED", "progress": 1, "stage_message": "",
           "document_ids": ["d1"], "scores": {}, "unverified_items": UNVERIFIED, "errors": [],
           "unavailable_sources": [{"name": "semantic_scholar", "status": "RATE_LIMITED", "note": "요청 한도"}],
           "input_snapshot": {"scope_revision": 0}, "started_at": "2026-09-24T00:00:00"}
    project = {"id": "p1", "name": "시험 사건", "can_delete": True, "document_count": 1,
               "external_ai_policy": "MASKED", "scope_revision": 0}

    def respond(route):
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        replies = {"/api/health": {"status": "ok", "version": "0.5.0"},
                   "/api/identity/me": {"user_id": "u", "role": "ADMIN", "authentication": "password"},
                   "/api/verification-runs": {"active_count": 0, "runs": []},
                   "/api/projects": [project], "/api/projects/p1": project, "/api/projects/p1/runs": [run],
                   "/api/projects/p1/findings": FINDINGS}
        if path in replies:
            return route.fulfill(json=replies[path])
        if path.endswith("/result"):
            return route.fulfill(json={"documents": [{"document_id": "d1", "filename": "준비서면.pdf", "review_items": [
                {"item_id": "i1", "kind": "CITATION", "cited_authority": "대법원 2011모1839 결정", "claim_text": "대법원 2011모1839 결정",
                 "severity": "HIGH", "finding_ids": ["f0", "f1"], "location": "1쪽"}]}]})
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        return route.fulfill(json=[])

    with sync_playwright() as playwright:
        options = {"headless": True}
        if os.getenv("LV_TEST_BROWSER_CHANNEL"):
            options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route("**/*", respond)
            page.goto("http://metrics.test/")
            select_first_project(page)
            expect(page.locator("#summary .metric")).to_have_count(3)
            expect(page.locator(".metric-explain", has_text="확인 전 항목")).to_have_count(0)
            expect(page.locator(".metric-explain", has_text="진행 상태")).to_have_count(0)
            page.locator('.tabs button[data-tab="review"]').click()
            pending = page.locator("#reviewPendingBadge")
            expect(pending).to_have_text("검토 결정 대기 2")
            pending.click()
            dialog = page.get_by_role("dialog", name="검토 결정 대기란")
            expect(dialog).to_contain_text("검사를 하지 못했다는 뜻이 아니라")
            expect(dialog).to_contain_text("문제가 의심되는 항목(검토 후 조치 필요): 1건")
            expect(dialog).to_contain_text("시스템이 확인하지 못한 항목(원문 확인 필요): 1건")
            dialog.get_by_role("button", name="닫기").first.click() if dialog.get_by_role("button", name="닫기").count() else page.keyboard.press("Escape")

            if width <= 700:
                page.evaluate("window.scrollTo(0, 0)")
            line = page.locator(".run-status-line")
            expect(line).to_contain_text("일부 미확인")
            line.get_by_role("button", name="사유 보기").click()
            status = page.get_by_role("dialog", name="진행 상태: 일부 미확인")
            expect(status).to_contain_text("확인하지 못한 항목 3건 — 원인별")
            expect(status.locator(".unverified-cause", has_text="외부 출처 연결 장애")).to_contain_text("대법원 2015모2524 결정")
            expect(status.locator(".unverified-cause", has_text="스캔 쪽의 글자를 읽지 못함")).to_contain_text("3쪽")
            expect(status.locator(".unverified-cause", has_text="적용 기준일 미입력")).to_contain_text("민법 제750조")
            expect(status).to_contain_text("공식 원문 확인됨 · 사람 검토 필요 1건")
            expect(status).to_contain_text("semantic_scholar")
            expect(status.get_by_role("button", name="다시 검증")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert errors == []
            page.close()
        finally:
            browser.close()
