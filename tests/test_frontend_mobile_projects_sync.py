"""모바일 환경에서 사이드바 서랍을 열거나 앱이 다시 활성화될 때 프로젝트 목록이 최신 상태로 동기화되어야 한다."""
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def _make_project(pid: str, name: str) -> dict:
    return {
        "id": pid,
        "name": name,
        "can_delete": True,
        "document_count": 0,
        "external_ai_policy": "MASKED",
        "scope_revision": 0,
    }


def test_mobile_sidebar_open_and_wake_refresh_projects():
    static = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static).as_posix()}": p for p in static.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"

    projects = [_make_project("p1", "사건 목록 A")]
    project_fetches = 0

    def respond(route):
        nonlocal project_fetches
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        if path == "/api/projects":
            project_fetches += 1
            return route.fulfill(
                json=projects,
                headers={"Cache-Control": "no-store"},
            )
        replies = {
            "/api/health": {"status": "ok", "version": "0.22.0"},
            "/api/identity/me": {"user_id": "u", "role": "ADMIN", "authentication": "password"},
            "/api/auth/me": {"user_id": "u", "email": "tester@example.com", "display_name": "tester"},
            "/api/verification-runs": {"active_count": 0, "runs": []},
            "/api/projects/p1": projects[0],
            "/api/projects/p1/runs": [],
            "/api/projects/p1/findings": [],
        }
        if path in replies:
            return route.fulfill(json=replies[path])
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        return route.fulfill(json=[])

    with sync_playwright() as playwright:
        options = {"headless": True}
        if os.getenv("LV_TEST_BROWSER_CHANNEL"):
            options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route("**/*", respond)
            page.goto("http://mobile-sync.test/")

            expect(page.locator("#sidebarProjectCount")).to_have_text("(1)")
            expect(page.locator("#projectList")).to_contain_text("사건 목록 A")
            initial_fetches = project_fetches

            # 다른 기기에서 프로젝트가 추가된 뒤 모바일에서 사이드바(햄버거 메뉴)를 연다.
            projects.append(_make_project("p2", "사건 목록 B"))
            page.locator("#menuButton").click()

            expect(page.locator("#sidebar")).to_have_class(re.compile(r"\bopen\b"))
            expect(page.locator("#sidebarProjectCount")).to_have_text("(2)")
            expect(page.locator("#projectList")).to_contain_text("사건 목록 B")
            assert project_fetches > initial_fetches

            # 앱/탭이 백그라운드에서 다시 포커스를 얻을 때도 프로젝트 목록을 갱신한다.
            fetches_before_wake = project_fetches
            projects.append(_make_project("p3", "사건 목록 C"))
            page.evaluate("window.dispatchEvent(new Event('focus'))")

            expect(page.locator("#sidebarProjectCount")).to_have_text("(3)")
            expect(page.locator("#projectList")).to_contain_text("사건 목록 C")
            assert project_fetches > fetches_before_wake
            assert errors == []
            page.close()
        finally:
            browser.close()
