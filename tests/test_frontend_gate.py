"""배포가능 판정(배포 차단·사람 검토 사유·검증위험 지수)은 화면에 보이지 않는다.

V1.0.0 명세 1-3-2·1-3-3·2·3과 사용자 결정 D3(2026-11-13)로 옛 요구('사유는 누르지 않아도 보여야 한다')를 바꾼
단언이다(사용자 승인). 결과 데이터 scores.release_gate는 그대로 받으며 화면만 그리지 않는다.
"""
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
from frontend_helpers import select_first_project

ROOT = Path(__file__).resolve().parents[1]
GATE = {"release_gate": "BLOCK", "hallucination_risk": 72,
        "hard_block_reasons": ["성립할 수 없는 사건번호 인용 1건", "은닉 텍스트 2건 발견", "Source 미확인 판례가 핵심 주장의 근거"],
        "review_reasons": ["공식 DB 미확인 인용 4건", "AI 작성 정황(일부)", "계산 결과 불일치 1건"],
        "risk_index_note": "검증위험 지수는 확률이 아니라 규칙 기반 점수입니다."}


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 1400)])
def test_gate_reasons_are_not_rendered(width, height):
    static = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static).as_posix()}": p for p in static.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"
    run = {"id": "r1", "project_id": "p1", "state": "COMPLETED", "progress": 1, "stage_message": "",
           "document_ids": ["d"], "scores": {"release_gate": GATE}, "unverified_items": [],
           "input_snapshot": {"scope_revision": 0}, "started_at": "2026-09-23T00:00:00"}
    project = {"id": "p1", "name": "시험 사건", "can_delete": True, "document_count": 1,
               "external_ai_policy": "MASKED", "scope_revision": 0}

    def respond(route):
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        replies = {"/api/health": {"status": "ok", "version": "0.5.0"},
                   "/api/identity/me": {"user_id": "u", "role": "ADMIN", "authentication": "password"},
                   "/api/verification-runs": {"active_count": 0, "runs": []},
                   "/api/projects": [project], "/api/projects/p1": project, "/api/projects/p1/runs": [run]}
        if path in replies:
            return route.fulfill(json=replies[path])
        if path.endswith("/result"):
            return route.fulfill(json={"documents": []})
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
            page.route("**/*", respond)
            page.goto("http://gate.test/")
            select_first_project(page)
            expect(page.locator("#summary .metric")).to_have_count(3)
            expect(page.get_by_role("region", name="배포가능 판정 사유")).to_have_count(0)
            summary = page.locator("#summary")
            for text in ["배포 차단", "배포가능", "검증위험", "사람 검토 사유", GATE["risk_index_note"],
                         *GATE["hard_block_reasons"], *GATE["review_reasons"]]:
                expect(summary).not_to_contain_text(text)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.close()
        finally:
            browser.close()
