"""TK-189: 같은 프로젝트·실행 내 renderFindings 재렌더 시 참고자료 상세 펼침 상태 보존."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from frontend_helpers import select_first_project

ROOT = Path(__file__).resolve().parents[1]


def _base_data():
    projects = [
        {"id": "p1", "name": "사건 1", "can_delete": True, "document_count": 1,
         "external_ai_policy": "MASKED", "scope_revision": 0},
        {"id": "p2", "name": "사건 2", "can_delete": True, "document_count": 1,
         "external_ai_policy": "MASKED", "scope_revision": 0},
    ]
    runs = {
        "p1": [
            {"id": "r1", "project_id": "p1", "state": "COMPLETED", "progress": 1, "stage_message": "",
             "document_ids": ["d1"], "scores": {}, "unverified_items": [], "errors": [],
             "unavailable_sources": [], "input_snapshot": {"scope_revision": 0}, "started_at": "2026-11-15T01:00:00"},
            {"id": "r2", "project_id": "p1", "state": "COMPLETED", "progress": 1, "stage_message": "",
             "document_ids": ["d1"], "scores": {}, "unverified_items": [], "errors": [],
             "unavailable_sources": [], "input_snapshot": {"scope_revision": 0}, "started_at": "2026-11-15T02:00:00"},
        ],
        "p2": [
            {"id": "r3", "project_id": "p2", "state": "COMPLETED", "progress": 1, "stage_message": "",
             "document_ids": ["d2"], "scores": {}, "unverified_items": [], "errors": [],
             "unavailable_sources": [], "input_snapshot": {"scope_revision": 0}, "started_at": "2026-11-15T03:00:00"},
        ],
    }

    def result_for(run_id: str):
        doc_id = "d2" if run_id == "r3" else "d1"
        return {
            "run_manifest": {
                "reference_library": {
                    "status": "PARTIAL", "files_seen": 2, "files_indexed": 1,
                    "checked_at": "2026-11-15T03:00:00Z",
                    "issues": [{"name": "general.pdf", "reason": "REFERENCE_PARTIALLY_READ"}],
                    "inventory": [{"file_id": "ref1", "name": "참고.pdf", "folder_path": "판례",
                                   "status": "INDEXED", "pages": 5, "read_pages": 5}],
                }
            },
            "documents": [{
                "document_id": doc_id, "filename": "준비서면.pdf",
                "engine_data": {"rag": {
                    "status": "RETRIEVED_ONLY", "reason": "MODEL_UNAVAILABLE",
                    "sources": [{
                        "source_id": "R1", "file_id": "reference000001",
                        "title": "<img onerror=alert(1)> 참고자료",
                        "page": 2, "modified_time": "2026-11-15", "sha256": "a" * 64,
                        "text": "Drive reference text",
                    }],
                }},
            }],
        }

    findings = [
        {"id": "f1", "run_id": "r1", "project_id": "p1", "document_id": "d1",
         "type": "CASE_NOT_FOUND", "status": "NOT_FOUND", "severity": "HIGH",
         "evidence_grade": "B", "confidence": 0.5, "page": 1, "block_id": None,
         "title": "높음 항목", "detail": "", "engine": "legal_engine",
         "meta_message_type": None, "advisory_only": False, "tags": [],
         "review_status": "NEEDS_REVIEW", "review_note": "", "has_sealed_content": False,
         "evidence": [], "sources": [], "citation_id": "c1"},
        {"id": "f2", "run_id": "r1", "project_id": "p1", "document_id": "d1",
         "type": "LAW_CITATION_ERROR", "status": "NOT_FOUND", "severity": "MEDIUM",
         "evidence_grade": "B", "confidence": 0.5, "page": 1, "block_id": None,
         "title": "보통 항목", "detail": "", "engine": "legal_engine",
         "meta_message_type": None, "advisory_only": False, "tags": [],
         "review_status": "NEEDS_REVIEW", "review_note": "", "has_sealed_content": False,
         "evidence": [], "sources": [], "citation_id": "c2"},
    ]
    return projects, runs, result_for, findings


def test_reference_details_preserve_open_and_closed_within_same_run_and_reset_on_switch():
    static = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static).as_posix()}": p for p in static.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"
    projects, runs, result_for, findings = _base_data()

    def respond(route):
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        if path == "/api/health":
            return route.fulfill(json={"status": "ok", "version": "0.22.0"})
        if path == "/api/identity/me":
            return route.fulfill(json={"user_id": "u", "role": "ADMIN", "authentication": "password"})
        if path == "/api/verification-runs":
            return route.fulfill(json={"active_count": 0, "runs": []})
        if path == "/api/projects":
            return route.fulfill(json=projects)
        if path == "/api/projects/p1":
            return route.fulfill(json=projects[0])
        if path == "/api/projects/p2":
            return route.fulfill(json=projects[1])
        if path == "/api/projects/p1/runs":
            return route.fulfill(json=runs["p1"])
        if path == "/api/projects/p2/runs":
            return route.fulfill(json=runs["p2"])
        if path in ("/api/projects/p1/findings", "/api/projects/p2/findings"):
            return route.fulfill(json=findings)
        if path.endswith("/result"):
            run_id = path.split("/")[-2]
            return route.fulfill(json=result_for(run_id))
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        return route.fulfill(json=[])

    with sync_playwright() as playwright:
        options = {"headless": True}
        if os.getenv("LV_TEST_BROWSER_CHANNEL"):
            options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route("**/*", respond)
            page.goto("http://tk189.test/")
            select_first_project(page)
            page.locator('.tabs [data-tab="review"]').click()

            outer = page.locator("#referenceStatus > details")
            expect(outer).to_have_count(1)
            assert not outer.evaluate("e => e.open")

            # 1) 사용자 클릭으로 바깥·내부 상세 펼침
            outer.locator("> summary").click()
            assert outer.evaluate("e => e.open")
            inventory = outer.locator('details[data-ref-detail-key="inventory"]')
            doc_detail = outer.locator('details[data-ref-detail-key="doc:d1"]')
            inventory.locator("> summary").click()
            doc_detail.locator("> summary").click()
            assert inventory.evaluate("e => e.open")
            assert doc_detail.evaluate("e => e.open")
            # XSS/링크 유지 확인
            expect(outer.locator(".reference-section img")).to_have_count(0)
            expect(outer.locator('a[href="https://drive.google.com/file/d/reference000001/view"]')).to_have_count(1)

            # 2) 실제 이벤트 경로(필터 변경) 및 통제된 renderFindings() 호출 뒤 상태 유지
            page.select_option("#severityFilter", "HIGH")
            assert outer.evaluate("e => e.open")
            assert inventory.evaluate("e => e.open")
            assert doc_detail.evaluate("e => e.open")

            page.evaluate("() => { renderFindings(); }")
            assert outer.evaluate("e => e.open")
            assert inventory.evaluate("e => e.open")
            assert doc_detail.evaluate("e => e.open")

            # 3) 사용자 클릭으로 내부 상세 하나를 닫은 뒤 renderFindings() 후에도 닫힘 유지
            inventory.locator("> summary").click()
            assert not inventory.evaluate("e => e.open")
            page.select_option("#severityFilter", "")
            assert outer.evaluate("e => e.open")
            assert not inventory.evaluate("e => e.open")
            assert doc_detail.evaluate("e => e.open")

            # 4) 390px 모바일 폭에서도 접근 및 overflow 없음
            page.set_viewport_size({"width": 390, "height": 900})
            page.evaluate("() => { renderFindings(); }")
            assert outer.evaluate("e => e.open")
            assert outer.locator(".reference-section").evaluate("e => e.scrollWidth <= e.clientWidth + 1")

            # 5) 같은 프로젝트 내 다른 실행으로 전환 시 초기화
            page.evaluate("""() => {
              state.run = state.project ? { id: 'r2', project_id: state.project.id, state: 'COMPLETED' } : null;
              renderFindings();
            }""")
            assert not outer.evaluate("e => e.open")

            # 다시 열고 다른 프로젝트로 전환 시 초기화
            outer.locator("> summary").click()
            assert outer.evaluate("e => e.open")
            page.evaluate("""() => {
              state.project = { id: 'p2', name: '사건 2', external_ai_policy: 'MASKED' };
              state.run = { id: 'r3', project_id: 'p2', state: 'COMPLETED' };
              renderFindings();
            }""")
            assert not outer.evaluate("e => e.open")
            assert errors == []
        finally:
            browser.close()
