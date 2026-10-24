# -*- coding: utf-8 -*-
"""TK-94 출처 미확인 판례·법령 외부 법률 AI/엘박스 일괄 검증 프롬프트 브라우저 시험.

수용 기준 검증:
1. external_ai_policy가 LOCAL_ONLY일 때 검토 표 하단 액션(#reviewTableActions) 숨김 처리.
2. external_ai_policy가 MASKED일 때 버튼 및 공식 확인 필수 안내 문구 노출.
3. 클립보드 API 실패 시 프롬프트 직접 복사 fallback 모달 대화상자(#copyFallbackDialog) 노출 및 텍스트 검증.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
from frontend_helpers import select_first_project

ROOT = Path(__file__).resolve().parents[1]


def _build_test_page(external_ai_policy: str = "MASKED", clipboard_fail: bool = False):
    launch_kwargs = {"headless": True}
    channel = os.environ.get("LV_TEST_BROWSER_CHANNEL")
    if not channel:
        if Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe").exists():
            channel = "chrome"
        elif Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe").exists():
            channel = "msedge"
    if channel:
        launch_kwargs["channel"] = channel

    project_data = {
        "id": "p_prompt",
        "name": "외부 AI 프롬프트 검증 프로젝트",
        "can_delete": True,
        "document_count": 1,
        "external_ai_policy": external_ai_policy,
        "scope_revision": 0,
        "incident_date": "2024-05-01",
        "requested_issues": ["판례 확인"],
    }

    run_data = {
        "id": "r_prompt",
        "project_id": "p_prompt",
        "state": "COMPLETED",
        "progress": 1,
        "stage_message": "",
        "document_ids": ["d_prompt"],
        "scores": {},
        "unverified_items": [],
        "errors": [],
        "unavailable_sources": [],
        "input_snapshot": {"scope_revision": 0},
        "started_at": "2026-10-24T00:00:00",
    }

    # 미확인 판례 1건과 공식 확인 판례 1건
    synthetic_review_items = [
        {
            "item_id": "item_unverified",
            "kind": "CITATION",
            "document_id": "d_prompt",
            "location": {"page": 2, "display": "2쪽 1문단"},
            "claim_text": "원고의 청구권 행사 기한 주장",
            "cited_authority": "대법원 2022다99999 판결",
            "official_status": "OFFICIAL_NOT_FOUND",
            "reference_status": "NOT_CHECKED",
            "verdict_label": "공식 DB 미확인 (원문 확인 필요)",
            "severity": "CRITICAL",
            "finding_ids": [],
            "citation_id": "cit_1",
            "reasoning_sections": None,
            "counteraction": "원문 확인 요청",
        },
        {
            "item_id": "item_confirmed",
            "kind": "CITATION",
            "document_id": "d_prompt",
            "location": {"page": 3, "display": "3쪽"},
            "claim_text": "민법 일반원칙 주장",
            "cited_authority": "민법 제2조",
            "official_status": "OFFICIAL_CONFIRMED",
            "reference_status": "NOT_CHECKED",
            "verdict_label": "공식 원문 일치",
            "severity": "INFO",
            "finding_ids": [],
            "citation_id": "cit_2",
            "reasoning_sections": None,
            "counteraction": "",
        },
    ]

    result_data = {
        "status": "COMPLETED",
        "run_manifest": {
            "reference_library": {
                "status": "READY",
                "files_indexed": 1,
                "files_seen": 1,
                "checked_at": "2026-10-24T12:00:00",
            }
        },
        "documents": [
            {
                "id": "d_prompt",
                "filename": "소송서면.pdf",
                "quarantined": False,
                "findings": [],
                "review_items": synthetic_review_items,
            }
        ],
    }

    static_dir = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static_dir).as_posix()}": p for p in static_dir.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"

    def route_handler(route):
        req = route.request
        path = urlsplit(req.url).path

        if path in files:
            route.fulfill(path=str(files[path]))
            return
        if path == "/api/health":
            route.fulfill(json={"status": "ok", "version": "0.10.0"})
            return
        if path in ("/api/auth/me", "/api/identity/me"):
            route.fulfill(json={"user_id": "u", "email": "t@example.com", "display_name": "검토자", "role": "ADMIN", "authentication": "local"})
            return
        if path == "/api/verification-runs":
            route.fulfill(json={"active_count": 0, "runs": []})
            return
        if path == "/api/projects":
            route.fulfill(json=[project_data])
            return
        if path == "/api/projects/p_prompt":
            route.fulfill(json=project_data)
            return
        if path == "/api/projects/p_prompt/documents":
            route.fulfill(json=[{"id": "d_prompt", "filename": "소송서면.pdf", "included_in_verification": True}])
            return
        if path == "/api/projects/p_prompt/runs":
            route.fulfill(json=[run_data])
            return
        if path == "/api/projects/p_prompt/findings":
            route.fulfill(json=[])
            return
        if path.endswith(("/result", "/results")):
            route.fulfill(json=result_data)
            return
        if path == "/api/projects/p_prompt/audit":
            route.fulfill(json={"events": []})
            return
        if path == "/api/privacy-notice":
            route.fulfill(json={"version": "v1.0", "bullets": [], "ack_label": "", "report_header": ""})
            return
        if path == "/api/finding-categories":
            route.fulfill(json={"categories": {}, "tabs": {}, "counts": {}})
            return
        if path == "/api/projects/p_prompt/review-workflows":
            route.fulfill(json=[])
            return
        if path.endswith("/case-matrix"):
            route.fulfill(body="null", content_type="application/json")
            return

        route.fulfill(status=200, json=[])

    return launch_kwargs, route_handler, clipboard_fail


def test_external_ai_prompt_button_hidden_when_local_only():
    """external_ai_policy가 LOCAL_ONLY일 경우 표 하단 프롬프트 버튼이 숨겨져 있어야 함."""
    launch_kwargs, route_handler, _ = _build_test_page(external_ai_policy="LOCAL_ONLY")

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route("**/*", route_handler)

        page.goto("http://localhost/")
        select_first_project(page)

        page.get_by_role("button", name="검증·검토", exact=True).click()
        page.locator('.tabs button[data-tab="review"]').click()

        # #reviewTableActions 엘리먼트가 숨겨져 있는지(hidden) 검증
        actions = page.locator("#reviewTableActions")
        expect(actions).to_be_hidden()

        browser.close()


def test_external_ai_prompt_button_visible_when_masked_with_notice():
    """external_ai_policy가 MASKED일 경우 버튼, 건수 배지, 공식 확인 필수 안내 문구가 노출되어야 함."""
    launch_kwargs, route_handler, _ = _build_test_page(external_ai_policy="MASKED")

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route("**/*", route_handler)

        page.goto("http://localhost/")
        select_first_project(page)

        page.get_by_role("button", name="검증·검토", exact=True).click()
        page.locator('.tabs button[data-tab="review"]').click()

        actions = page.locator("#reviewTableActions")
        expect(actions).to_be_visible()

        # 버튼 확인
        btn = actions.locator(".external-ai-prompt-btn")
        expect(btn).to_be_visible()
        expect(btn).to_contain_text("📋 엘박스/AI 검증 프롬프트")

        # 건수 배지 확인 (미확인 항목 1건)
        badge = actions.locator(".review-prompt-count")
        expect(badge).to_be_visible()
        expect(badge).to_contain_text("(미확인 판례·법령 1건)")

        # 공식 확인 필수 고지 문구 확인
        notice = actions.locator(".review-prompt-notice")
        expect(notice).to_be_visible()
        expect(notice).to_contain_text("※ 외부 AI 답변은 공식 확인이 아니므로 원문 확인이 필요합니다.")

        browser.close()


def test_external_ai_prompt_copy_fallback_dialog_on_failure():
    """클립보드 API가 거부/실패할 경우 fallback 대화상자가 열리고 프롬프트 원문이 textarea에 표시되어야 함."""
    launch_kwargs, route_handler, _ = _build_test_page(external_ai_policy="MASKED", clipboard_fail=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route("**/*", route_handler)

        # 클립보드 복사 실패 모의 (writeText 거부 및 execCommand 실패)
        page.add_init_script("""
            Object.defineProperty(navigator, 'clipboard', {
                value: {
                    writeText: () => Promise.reject(new Error("클립보드 권한 거부 모의")),
                },
                configurable: true,
            });
            document.execCommand = () => false;
        """)

        page.goto("http://localhost/")
        select_first_project(page)

        page.get_by_role("button", name="검증·검토", exact=True).click()
        page.locator('.tabs button[data-tab="review"]').click()

        actions = page.locator("#reviewTableActions")
        btn = actions.locator(".external-ai-prompt-btn")
        btn.click()

        # Fallback 대화상자 노출 검증
        dialog = page.locator("#copyFallbackDialog")
        expect(dialog).to_be_visible()

        textarea = page.locator("#copyFallbackTextarea")
        expect(textarea).to_be_visible()

        val = textarea.input_value()
        # 프롬프트 필수 구성요소 검증
        assert "대법원 2022다99999 판결" in val
        assert "2024-05-01" in val
        assert "외부 AI 답변은 법적 효력이 있는 공식 확인이 아니며" in val
        assert "법원 판결서 사본 또는 국가법령정보센터 공식 원문으로 반드시 확인" in val

        # 닫기 버튼 클릭 시 대화상자 닫힘 검증
        dialog.get_by_role("button", name="닫기").first.click()
        expect(dialog).not_to_be_visible()

        browser.close()
