"""TK-172: 브라우저 탭 아이콘 캐시 갱신(?v= 판 표지) 및 허용 엠블럼 목록 검증."""
import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from lxml import html
from playwright.sync_api import expect, sync_playwright

from apps.api.main import app
from tests.frontend_helpers import privacy_notice_mock_payload


ROOT = Path(__file__).resolve().parents[1]

ALLOWED_BRAND_AND_ICON_PATHS = {
    "/static/acas-law-emblem.jpg",
    "/static/img/favicon.ico",
    "/static/img/emblem.png",
    "/static/img/emblem-192.png",
    "/static/img/acas-law-square-transparent.png",
    "/static/img/acas-law-square.png",
    "/static/img/acas-law-square.jpg",
}


def test_tk172_favicon_links_have_version_and_serve_exact_bytes():
    index_text = (ROOT / "apps/web/index.html").read_text(encoding="utf-8")
    assert "?v=" in index_text

    client = TestClient(app)
    page_resp = client.get("/")
    assert page_resp.status_code == 200

    doc = html.fromstring(page_resp.text)
    icon_links = doc.xpath("//link[@rel='icon' or @rel='apple-touch-icon']")
    assert len(icon_links) == 3

    for link in icon_links:
        href = link.get("href")
        assert href is not None and "?v=" in href, f"icon href missing ?v=: {href}"
        parsed = urlsplit(href)
        assert parsed.path in ALLOWED_BRAND_AND_ICON_PATHS
        assert parsed.query.startswith("v=") and len(parsed.query) > 2

        resp = client.get(href)
        assert resp.status_code == 200
        disk_path = ROOT / "apps/web" / parsed.path.lstrip("/")
        assert disk_path.is_file()
        assert resp.content == disk_path.read_bytes()

    img_elements = doc.xpath("//img")
    assert len(img_elements) >= 2
    for img in img_elements:
        src = img.get("src")
        assert src is not None
        assert urlsplit(src).path in ALLOWED_BRAND_AND_ICON_PATHS


def test_tk172_browser_icons_and_brand_images_in_allowed_set():
    static = ROOT / "apps/web/static"
    files = {
        f"/static/{path.relative_to(static).as_posix()}": path
        for path in static.rglob("*")
        if path.is_file()
    }
    files["/"] = ROOT / "apps/web/index.html"

    def respond(route):
        path = urlsplit(route.request.url).path
        if path in files:
            route.fulfill(path=str(files[path]))
        elif path == "/api/health":
            route.fulfill(json={"status": "ok", "version": "0.20.0"})
        elif path == "/api/privacy-notice":
            route.fulfill(json=privacy_notice_mock_payload())
        else:
            route.fulfill(status=401, json={"detail": "Login required"})

    with sync_playwright() as playwright:
        options = {"headless": True}
        if os.getenv("LV_TEST_BROWSER_CHANNEL"):
            options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
        browser = playwright.chromium.launch(**options)
        try:
            for width, height in ((1440, 900), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height})
                errors = []
                page.on("pageerror", lambda err: errors.append(str(err)))
                page.route("**/*", respond)
                page.goto("http://tk172.test/")
                expect(page).to_have_title("AegisLAW")

                hrefs = page.eval_on_selector_all(
                    "link[rel='icon'], link[rel='apple-touch-icon']",
                    "els => els.map(el => el.getAttribute('href'))",
                )
                assert len(hrefs) == 3
                for href in hrefs:
                    assert "?v=" in href
                    assert urlsplit(href).path in ALLOWED_BRAND_AND_ICON_PATHS

                srcs = page.eval_on_selector_all(
                    "img",
                    "els => els.map(el => el.getAttribute('src'))",
                )
                assert len(srcs) >= 2
                for src in srcs:
                    assert urlsplit(src).path in ALLOWED_BRAND_AND_ICON_PATHS

                assert not errors
                page.close()
        finally:
            browser.close()


def test_tk171_template_a_and_mobile_responsive_navigation():
    static = ROOT / "apps/web/static"
    files = {
        f"/static/{path.relative_to(static).as_posix()}": path
        for path in static.rglob("*")
        if path.is_file()
    }
    files["/"] = ROOT / "apps/web/index.html"

    project = {
        "id": "proj_synth_1",
        "name": "합성 검증 테스트 사건",
        "case_number": "TEST-01",
        "court": "합성법원",
        "verification_profile": "STANDARD",
        "external_ai_policy": "LOCAL_ONLY",
        "document_count": 1,
        "scope_revision": 1,
        "can_delete": True,
        "parties": [],
        "requested_issues": [],
    }
    docs = [
        {
            "id": "doc_synth_1",
            "filename": "합성문서_샘플.pdf",
            "document_kind": "준비서면",
            "parse_status": "PARSED",
            "page_count": 3,
            "file_size": 20480,
            "evidence_number": "갑 제1호증",
            "submitted_by": "OWN",
            "included_in_scope": True,
        }
    ]

    def respond(route):
        path = urlsplit(route.request.url).path
        if path in files:
            route.fulfill(path=str(files[path]))
        elif path == "/api/health":
            route.fulfill(json={"status": "ok", "version": "0.20.0"})
        elif path == "/api/privacy-notice":
            route.fulfill(json=privacy_notice_mock_payload())
        elif path == "/api/identity/me":
            route.fulfill(json={"user_id": "u_synth", "role": "MEMBER", "authentication": "password"})
        elif path == "/api/auth/me":
            route.fulfill(
                json={
                    "email": "synth@example.test",
                    "affiliation": "합성 소속 부서",
                    "display_name": "합성담당자",
                }
            )
        elif path == "/api/verification-runs":
            route.fulfill(json={"runs": [], "active_count": 0})
        elif path == "/api/projects":
            route.fulfill(json=[project])
        elif path == "/api/projects/proj_synth_1":
            route.fulfill(json=project)
        elif path == "/api/projects/proj_synth_1/documents":
            route.fulfill(json=docs)
        elif path.endswith("/latest-run"):
            route.fulfill(body="null", content_type="application/json")
        elif path.endswith("/case-matrix"):
            route.fulfill(body="null", content_type="application/json")
        else:
            route.fulfill(json=[])

    with sync_playwright() as playwright:
        options = {"headless": True}
        if os.getenv("LV_TEST_BROWSER_CHANNEL"):
            options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
        browser = playwright.chromium.launch(**options)
        try:
            for width, height in ((1440, 900), (768, 1024), (390, 844), (320, 640)):
                page = browser.new_page(viewport={"width": width, "height": height})
                errors = []
                page.on("pageerror", lambda err: errors.append(str(err)))
                page.route("**/*", respond)
                page.goto("http://tk171.test/")

                if width <= 700:
                    menu_btn = page.locator("#menuButton")
                    expect(menu_btn).to_be_visible()
                    menu_btn.click()
                    expect(page.locator("#sidebar")).to_be_visible()
                    expect(menu_btn).to_have_attribute("aria-expanded", "true")
                    page.keyboard.press("Escape")
                    expect(page.locator("#sidebar")).not_to_be_visible()
                    expect(menu_btn).to_have_attribute("aria-expanded", "false")
                    menu_btn.click()

                page.locator("#projectList button").first.click()
                expect(page.locator("#projectView")).to_be_visible()

                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

                bottom_nav = page.locator("#mobileBottomNav")
                if width <= 700:
                    expect(bottom_nav).to_be_visible()
                    bottom_nav.locator("[data-mobile-nav='review']").click()
                    expect(page.locator("section[data-panel='review']")).to_be_visible()
                    expect(bottom_nav.locator("[data-mobile-nav='review']")).to_have_attribute(
                        "aria-current", "page"
                    )
                    bottom_nav.locator("[data-mobile-nav='reports']").click()
                    expect(page.locator("section[data-panel='reports']")).to_be_visible()
                    bottom_nav.locator("[data-mobile-nav='documents']").click()
                    expect(page.locator("section[data-panel='documents']")).to_be_visible()
                else:
                    expect(bottom_nav).not_to_be_visible()

                assert not errors
                page.close()
        finally:
            browser.close()

