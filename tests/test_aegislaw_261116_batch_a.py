# -*- coding: utf-8 -*-
"""261116 AegisLAW 개선 배치 A(항목 3·4·5·6·7·7-1·7-2) 종합 회귀 시험.

모든 사건·문구·식별자는 합성 데이터만 사용한다.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
from frontend_helpers import select_first_project
from test_api import client, project  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def _browser_kwargs() -> dict:
    channel = os.getenv("LV_TEST_BROWSER_CHANNEL")
    return {"headless": True, **({"channel": channel} if channel else {})}


def _mount_page(
    p,
    *,
    result_data: dict,
    findings: list | None = None,
    server_store: dict | None = None,
    viewport: dict | None = None,
):
    project_data = {
        "id": "p1",
        "name": "합성UI검증사건",
        "can_delete": True,
        "document_count": len(result_data.get("documents", [])),
        "external_ai_policy": "MASKED",
        "scope_revision": 0,
        "incident_date": "2024-05-01",
        "requested_issues": [],
    }
    run_data = {
        "id": "r1",
        "project_id": "p1",
        "state": "COMPLETED",
        "progress": 1,
        "stage_message": "",
        "document_ids": [d["id"] for d in result_data.get("documents", [])],
        "scores": {},
        "unverified_items": [],
        "errors": [],
        "unavailable_sources": [],
        "input_snapshot": {"scope_revision": 0},
        "started_at": "2026-11-16T00:00:00",
    }
    static_dir = ROOT / "apps/web/static"
    files = {f"/static/{f.relative_to(static_dir).as_posix()}": f for f in static_dir.rglob("*") if f.is_file()}
    files["/"] = ROOT / "apps/web/index.html"
    fixed = {
        "/api/health": {"status": "ok", "version": "0.22.0"},
        "/api/auth/me": {
            "user_id": "u",
            "email": "tester@example.com",
            "display_name": "검토자",
            "role": "ADMIN",
            "authentication": "local",
        },
        "/api/verification-runs": {"active_count": 0, "runs": []},
        "/api/projects": [project_data],
        "/api/projects/p1": project_data,
        "/api/projects/p1/documents": [
            {"id": d["id"], "filename": d["filename"], "included_in_verification": True, "quarantined": bool(d.get("quarantined"))}
            for d in result_data.get("documents", [])
        ],
        "/api/projects/p1/runs": [run_data],
        "/api/projects/p1/findings": findings or [],
        "/api/projects/p1/audit": {"events": []},
        "/api/privacy-notice": {"version": "v1", "bullets": [], "ack_label": "", "report_header": ""},
    }

    def handler(route):
        path = urlsplit(route.request.url).path
        method = route.request.method.upper()
        if path in files:
            return route.fulfill(path=str(files[path]))
        if path == "/api/projects/p1/runs/r1/external-ai-answers":
            if server_store is None:
                return route.fulfill(json={"saved": False, "codes": {}, "answers": {}})
            if method == "PUT":
                body = route.request.post_data_json or {}
                server_store["codes"] = dict(body.get("codes") or {})
                server_store["answers"] = dict(body.get("answers") or {})
                server_store["saved"] = True
                return route.fulfill(json=server_store)
            return route.fulfill(json=server_store)
        if path == "/api/projects/p1/external-ai/prompt-texts":
            body = route.request.post_data_json or {}
            return route.fulfill(json={"policy": "MASKED", "texts": body.get("texts", [])})
        if path.endswith(("/result", "/results")):
            return route.fulfill(json=result_data)
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        if path == "/api/finding-categories":
            from packages.common.finding_category_map import CATEGORY_TO_TAB, FINDING_CATEGORY_MAP, get_category_counts

            return route.fulfill(
                json={
                    "categories": {ft.value: cat.value for ft, cat in FINDING_CATEGORY_MAP.items()},
                    "tabs": {ft.value: CATEGORY_TO_TAB[cat].value for ft, cat in FINDING_CATEGORY_MAP.items()},
                    "counts": get_category_counts(),
                }
            )
        if path in fixed:
            return route.fulfill(json=fixed[path])
        return route.fulfill(json=[])

    browser = p.chromium.launch(**_browser_kwargs())
    context = browser.new_context(viewport=viewport or {"width": 1440, "height": 960})
    context.add_init_script(
        "window.__copied = []; Object.defineProperty(navigator, 'clipboard', "
        "{value: {writeText: async t => { window.__copied.push(t); }}});"
    )
    page = context.new_page()
    page.route("**/*", handler)
    page.goto("http://localhost/")
    select_first_project(page)
    return browser, context, page


def test_security_card_width_model_failure_korean_and_injection_banner():
    """항목 3·4·5: 영문 에러코드 한글화, 인젝션 격리 배너의 본문 검토 안내, 보안 카드 전체 폭을 검증."""
    result_data = {
        "status": "COMPLETED",
        "documents": [
            {
                "id": "d1",
                "filename": "합성준비서면.pdf",
                "quarantined": True,
                "ai_detector_result": {
                    "verdict": "UNCERTAIN",
                    "score": 0.25,
                    "used_llm": False,
                    "reasons": ["규칙 기반 검사 완료"],
                    "signals": {
                        "llm_opinions": [],
                        "llm_failures": {
                            "anthropic": "INPUT_PRIVACY_BLOCKED [MASKING_PII_DETECTED:PII_INPUT_BLOCKED]",
                            "openai": "REQUEST_WIRING_CONTRACT",
                            "gemini": "응답 시간이 제한을 초과했습니다.",
                        },
                        "llm_failure_models": {
                            "anthropic": "claude-sonnet-4",
                            "openai": "gpt-4.1",
                            "gemini": "gemini-2.5-pro",
                        },
                    },
                },
                "engine_data": {"adversarial": {"scanned_layers": ["visible_text", "hidden_text"], "adversarial_risk": "HIGH"}},
                "findings": [
                    {
                        "id": "f_inj",
                        "engine": "adversarial_engine",
                        "type": "HIDDEN_INSTRUCTION",
                        "severity": "HIGH",
                        "page": 2,
                        "title": "은닉 지시문 후보",
                        "detail": "숨김 지시 구문 감지",
                    }
                ],
                "review_items": [
                    {
                        "item_id": "item_q1",
                        "kind": "CITATION",
                        "document_id": "d1",
                        "location": {"display": "3쪽", "page": 3},
                        "claim_text": "격리 문서의 본문 주장은 계속 검토된다",
                        "cited_authority": "대법원 2099다12345 판결",
                        "official_status": "OFFICIAL_NOT_FOUND",
                        "reference_status": "NOT_CHECKED",
                        "verdict_label": "공식 DB 미확인 (원문 확인 필요)",
                        "severity": "CRITICAL",
                        "finding_ids": [],
                        "claim_verdict": {"code": "INSUFFICIENT", "label": "근거 부족", "note": "확인 필요"},
                    }
                ],
            }
        ],
    }
    findings = [
        {
            "id": "f_inj",
            "finding_type": "HIDDEN_INSTRUCTION",
            "type": "HIDDEN_INSTRUCTION",
            "title": "은닉 지시문 후보",
            "detail": "숨김 지시 구문 감지",
            "severity": "HIGH",
            "status": "QUARANTINED",
            "review_status": "NEEDS_REVIEW",
            "document_id": "d1",
            "page": 2,
        },
        {
            "id": "f_sec",
            "finding_type": "AUTHORSHIP_METADATA_LEAK",
            "type": "AUTHORSHIP_METADATA_LEAK",
            "title": "작성자 메타데이터 노출",
            "detail": "파일 속성에 내부 계정명이 남아 있습니다.",
            "severity": "HIGH",
            "status": "FLAGGED",
            "review_status": "NEEDS_REVIEW",
            "document_id": "d1",
            "page": 1,
        },
    ]
    with sync_playwright() as p:
        browser, _ctx, page = _mount_page(p, result_data=result_data, findings=findings)
        page.locator('.tabs button[data-tab="ai-verification"]').click()
        cards = page.locator("#aiSummaryCards")

        # 항목 3: 내부 영문 에러코드 노출 제거 (양성 2종 + 대조 1종 한글 메시지 유지)
        failed_cards = cards.locator(".model-opinion-failed")
        expect(failed_cards).to_have_count(3)
        anthropic_text = failed_cards.filter(has_text="Anthropic").inner_text()
        openai_text = failed_cards.filter(has_text="OpenAI").inner_text()
        gemini_text = failed_cards.filter(has_text="Gemini").inner_text()
        assert "INPUT_PRIVACY_BLOCKED" not in anthropic_text and "PII_INPUT_BLOCKED" not in anthropic_text
        assert "개인정보" in anthropic_text and "차단" in anthropic_text
        assert "REQUEST_WIRING_CONTRACT" not in openai_text and "입력 형식 검증 기준" in openai_text
        assert "응답 시간이 제한을 초과했습니다." in gemini_text  # 대조군: 일반 한글 사유 유지

        # 항목 4: 프롬프트 인젝션 격리 문구 개선 및 본문 검토 결과 유지
        inj_card = cards.locator(".summary-card", has_text="프롬프트 인젝션 속임수 검증")
        expect(inj_card).not_to_contain_text("이 문서는 AI 검토에서 제외")
        expect(inj_card).to_contain_text("나머지 본문 내용 검토는 정상 수행했습니다")
        expect(inj_card).to_contain_text("지시문 구간 격리됨 (본문 검토 진행)")

        # 항목 5: 보안 및 파일 진단 카드 폭이 상단 와이드 카드와 동일
        wide_box = cards.locator(".summary-card-wide").first.bounding_box()
        sec_box = cards.locator(".security-card").bounding_box()
        assert wide_box and sec_box
        assert abs(wide_box["width"] - sec_box["width"]) < 2.0

        # 격리 문서의 본문 인용 검토 행도 '출처가 확인되지 않는 항목' 탭에 그대로 표시
        page.locator('.tabs button[data-tab="review"]').click()
        expect(page.locator("#aiVerificationRows tr", has_text="대법원 2099다12345 판결")).to_be_visible()
        browser.close()


# TK-211: 배지와 근거 배지의 좌표를 한 번에 읽는 JS. 둘 다 레이아웃 박스를 가질 때만 값을
# 돌려주므로 wait_for_function이 재그리기를 기다려 준다. 두 번 나눠 재면 그 사이 패널이 다시
# 그려져 display:none이 되는 창이 남는다(평가 측 실측 근거는 시험 본문 주석에 있다).
_READ_BOXES_JS = """() => {
  const c = document.querySelector('#aiVerificationRows .review-verdict-badges');
  if (!c) return null;
  const b = c.querySelector('span.badge');
  const v = document.querySelector('#aiVerificationRows .claim-verdict');
  if (!b || !v) return null;
  const rb = b.getBoundingClientRect(), rv = v.getBoundingClientRect();
  if (!rb.height || !rv.height) return null;
  return {badge_x: rb.x, badge_y: rb.y, claim_x: rv.x, claim_y: rv.y};
}"""
_BADGE_AND_CLAIM_BOXES = _READ_BOXES_JS
# 래핑된 뒤에는 근거 배지가 배지보다 아래 줄에 있을 때만 값을 돌려준다(재배치 완료 조건).
_BADGE_AND_CLAIM_BOXES_WRAPPED = _READ_BOXES_JS.replace(
    "  return {badge_x",
    "  if (!(rv.top > rb.top + 4)) return null;\n  return {badge_x",
)


def test_review_verdict_badges_left_aligned_when_wrapped():
    """항목 7-2: 데스크톱 표 3열에서 배지가 다음 줄로 넘어갈 때도 1줄 '매우 높음'과 좌측 정렬이 맞아야 함."""
    result_data = {
        "status": "COMPLETED",
        "documents": [
            {
                "id": "d1",
                "filename": "서면.pdf",
                "quarantined": False,
                "review_items": [
                    {
                        "item_id": "item_wrap",
                        "kind": "CITATION",
                        "document_id": "d1",
                        "location": {"display": "2쪽"},
                        "claim_text": "대리인의 권한에 관한 판례 인용",
                        "cited_authority": "대법원 2098다55555 판결",
                        "official_status": "OFFICIAL_NOT_FOUND",
                        "reference_status": "NOT_CHECKED",
                        "verdict_label": "공식 DB 미확인 (원문 확인 필요)",
                        "severity": "CRITICAL",
                        "finding_ids": [],
                        "claim_verdict": {"code": "INSUFFICIENT", "label": "근거 부족", "note": "확인 필요"},
                    }
                ],
            }
        ],
    }
    with sync_playwright() as p:
        # 1024px 데스크톱 폭에서는 3열 너비로 인해 '근거 부족' 배지가 2번째 줄로 래핑됨
        browser, _ctx, page = _mount_page(p, result_data=result_data, viewport={"width": 1024, "height": 900})
        page.locator('.tabs button[data-tab="review"]').click()
        row = page.locator("#aiVerificationRows tr", has_text="대법원 2098다55555 판결")
        container = row.locator(".review-verdict-badges")
        expect(container).to_be_visible()
        # TK-211: 두 좌표를 한 번의 evaluate로 함께 읽는다.
        # 평가 측 실측(2026-11-19): bounding_box()가 None을 돌려주는 것은 그 요소에 레이아웃 박스가
        # 없을 때 — 곧 display:none(또는 그 조상)일 때 — 뿐이다. 0 크기도 visibility:hidden도 박스를
        # 돌려주고, 요소가 떨어진 경우는 None이 아니라 시간초과다. 즉 전에 이 시험이 `assert (None)`로
        # 깨진 것은 가시성 단언이 통과한 뒤 측정 순간에 탭 패널이 다시 그려져 display:none이 된 것이다.
        # 가시성 단언을 앞에 더 놓는 것으로는 그 창을 없앨 수 없다(단언과 측정이 별개 호출이다).
        # 그래서 '둘 다 박스를 가질 때까지 기다려 같은 호출에서 읽기'로 바꾼다. 단언 내용은 같다.
        boxes = page.wait_for_function(_BADGE_AND_CLAIM_BOXES).json_value()
        assert boxes, "배지와 근거 배지의 좌표를 읽지 못했다"
        # 같은 줄이든 다음 줄로 래핑되든 좌측 x 또는 1줄 내 정렬 검증; 1024에서 래핑 강제 확인을 위해 폭 190px로 좁혀도 좌측 정렬 일치
        container.evaluate("el => { el.style.maxWidth = '190px'; }")
        # 폭을 좁혀 2번째 줄로 넘어간 뒤의 좌표도 같은 방식으로 한 번에 읽는다.
        wrapped = page.wait_for_function(_BADGE_AND_CLAIM_BOXES_WRAPPED).json_value()
        assert wrapped["claim_y"] > wrapped["badge_y"] + 4, "테스트 조건상 2번째 줄로 줄바꿈되어야 함"
        assert abs(wrapped["badge_x"] - wrapped["claim_x"]) < 1.5
        browser.close()


def test_external_ai_server_persistence_model_name_and_prefix_overwrite():
    """항목 6·7·7-1: 모델명 파싱(헤더·인라인·수동 입력), 고지 삭제, 새로고침·새 브라우저 영속성 및 접두사별 덮어쓰기."""
    result_data = {
        "status": "COMPLETED",
        "documents": [
            {
                "id": "d1",
                "filename": "서면.pdf",
                "quarantined": False,
                "review_items": [
                    {
                        "item_id": "item_a1",
                        "kind": "CITATION",
                        "document_id": "d1",
                        "location": {"display": "2쪽"},
                        "claim_text": "기한 주장",
                        "cited_authority": "대법원 2097다10001 판결",
                        "official_status": "OFFICIAL_NOT_FOUND",
                        "reference_status": "NOT_CHECKED",
                        "verdict_label": "공식 DB 미확인 (원문 확인 필요)",
                        "severity": "HIGH",
                        "finding_ids": [],
                    },
                    {
                        "item_id": "item_a2",
                        "kind": "CITATION",
                        "document_id": "d1",
                        "location": {"display": "4쪽"},
                        "claim_text": "책임 주장",
                        "cited_authority": "대법원 2097다10002 판결",
                        "official_status": "OFFICIAL_NOT_FOUND",
                        "reference_status": "NOT_CHECKED",
                        "verdict_label": "공식 DB 미확인 (원문 확인 필요)",
                        "severity": "HIGH",
                        "finding_ids": [],
                    },
                    {
                        "item_id": "item_b1",
                        "kind": "FACT",
                        "document_id": "d1",
                        "location": {"display": "6쪽"},
                        "claim_text": "무리한 법리 주장 내용",
                        "official_status": "NOT_ASSESSED",
                        "reference_status": "NOT_CHECKED",
                        "verdict_label": "법리 검토 필요",
                        "severity": "MEDIUM",
                        "finding_ids": [],
                        "tier": 3,
                    },
                ],
            }
        ],
    }
    server_store: dict = {"saved": False, "codes": {}, "answers": {}}

    with sync_playwright() as p:
        # 1) 첫 번째 브라우저 세션: A1·A2 붙여넣기(단독 모델 줄) + B1 붙여넣기(인라인 모델)
        browser1, _ctx1, page1 = _mount_page(p, result_data=result_data, server_store=server_store)
        page1.locator('.tabs [data-tab="review"]').click()
        bar_a = page1.locator("#reviewTableActions")
        bar_a.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()
        bar_a.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        dlg = page1.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
        dlg.locator("textarea").fill(
            "<<<ACAS_RESULT\n"
            "모델: Gemini 2.5 Pro\n"
            "A1 | 판정: 부존재 | 근거: 미검색 | 요지: 1차 답변 A1\n"
            "A2 | 판정: 불명 | 근거: 미공개 | 요지: 1차 답변 A2\n"
            "ACAS_RESULT>>>"
        )
        dlg.get_by_role("button", name="저장").click()
        page1.get_by_role("dialog", name="표에 반영할 답변 2건 확인").get_by_role("button", name="표에 반영").click()

        row_a1 = page1.locator("#aiVerificationRows tr", has_text="2097다10001")
        row_a2 = page1.locator("#aiVerificationRows tr", has_text="2097다10002")
        expect(row_a1.locator(".external-ai-answer")).to_contain_text("Gemini 2.5 Pro 답변 A1")
        expect(row_a2.locator(".external-ai-answer")).to_contain_text("Gemini 2.5 Pro 답변 A2")
        expect(row_a1.locator(".external-ai-answer")).not_to_contain_text("공식 확인 아님")
        expect(row_a1.locator(".external-ai-answer")).not_to_contain_text("공식 DB 판정은 바뀌지 않습니다")
        expect(row_a1.locator(".external-ai-answer")).not_to_contain_text("반영:")

        # B 탭(법률적으로 무리한 주장)에도 인라인 모델로 별도 답변 저장
        page1.locator('.tabs [data-tab="legal-claims"]').click()
        bar_b = page1.locator("#legalClaimsActions")
        bar_b.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()
        bar_b.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        dlg_b = page1.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
        dlg_b.locator("textarea").fill("<<<ACAS_RESULT\nB1 | 모델: 엘박스 | 판정: 불일치 | 근거: 민법 조문 | 요지: B탭 답변\nACAS_RESULT>>>")
        dlg_b.get_by_role("button", name="저장").click()
        page1.get_by_role("dialog", name="표에 반영할 답변 1건 확인").get_by_role("button", name="표에 반영").click()
        expect(page1.locator("#tier3Rows tr", has_text="무리한 법리 주장").locator(".external-ai-answer")).to_contain_text("엘박스 답변 B1")
        browser1.close()

        # 2) 완전히 새로운 브라우저 컨텍스트(빈 localStorage): 서버 DB 저장분으로 A1·A2·B1 모두 복원되어야 함
        assert server_store["saved"] is True
        browser2, _ctx2, page2 = _mount_page(p, result_data=result_data, server_store=server_store)
        page2.locator('.tabs [data-tab="review"]').click()
        expect(page2.locator("#aiVerificationRows tr", has_text="2097다10001").locator(".external-ai-answer")).to_contain_text("Gemini 2.5 Pro 답변 A1")
        expect(page2.locator("#aiVerificationRows tr", has_text="2097다10002").locator(".external-ai-answer")).to_contain_text("1차 답변 A2")
        page2.locator('.tabs [data-tab="legal-claims"]').click()
        expect(page2.locator("#tier3Rows tr", has_text="무리한 법리 주장").locator(".external-ai-answer")).to_contain_text("엘박스 답변 B1")

        # 3) A 탭에 새 답변(A1만) 붙여넣으면 수동 모델명 반영 + 기존 A2는 사라지고, B1은 그대로 유지되어야 함
        page2.locator('.tabs [data-tab="review"]').click()
        bar2 = page2.locator("#reviewTableActions")
        bar2.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        dlg2 = page2.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
        dlg2.get_by_label("사용한 외부 AI 모델명 (선택)").fill("Claude Opus")
        dlg2.locator("textarea").fill("<<<ACAS_RESULT\nA1 | 판정: 확인 | 근거: 대법원 원문 | 요지: 2차 덮어쓰기 A1\nACAS_RESULT>>>")
        dlg2.get_by_role("button", name="저장").click()
        page2.get_by_role("dialog", name="표에 반영할 답변 1건 확인").get_by_role("button", name="표에 반영").click()

        expect(page2.locator("#aiVerificationRows tr", has_text="2097다10001").locator(".external-ai-answer")).to_contain_text("Claude Opus 답변 A1")
        expect(page2.locator("#aiVerificationRows tr", has_text="2097다10001").locator(".external-ai-answer")).to_contain_text("2차 덮어쓰기 A1")
        expect(page2.locator("#aiVerificationRows tr", has_text="2097다10002").locator(".external-ai-answer")).to_have_count(0)
        page2.locator('.tabs [data-tab="legal-claims"]').click()
        expect(page2.locator("#tier3Rows tr", has_text="무리한 법리 주장").locator(".external-ai-answer")).to_contain_text("엘박스 답변 B1")
        browser2.close()


def test_external_ai_store_api_roundtrip_and_controls(client, project):  # noqa: F811
    """항목 6 API DB 영속성(ReviewRevision 저장·재조회) 및 대조군(미저장·없는 실행 404)."""
    from apps.api.db import VerificationRun, get_session_factory

    with get_session_factory()() as session:
        run = VerificationRun(project_id=project["id"], state="COMPLETED")
        session.add(run)
        session.commit()
        run_id = run.id

    base_url = f"/api/projects/{project['id']}/runs/{run_id}/external-ai-answers"
    # 대조군 1: 아직 저장하지 않은 실행
    initial = client.get(base_url)
    assert initial.status_code == 200
    assert initial.json() == {"run_id": run_id, "saved": False, "codes": {}, "answers": {}}

    # 양성: PUT 저장 후 GET 조회(모델명 포함)
    payload = {
        "codes": {"A1": "item_1", "B1": "item_2"},
        "answers": {
            "A1": {"code": "A1", "item_id": "item_1", "model_name": "Gemini 2.5 Pro", "verdict": "확인", "basis": "조문", "summary": "요약"},
            "B1": {"code": "B1", "item_id": "item_2", "model_name": "엘박스", "verdict": "불일치", "basis": "판시", "summary": "반박"},
        },
    }
    saved = client.put(base_url, json=payload)
    assert saved.status_code == 200
    assert saved.json()["saved"] is True
    assert saved.json()["answers"]["A1"]["model_name"] == "Gemini 2.5 Pro"

    loaded = client.get(base_url)
    assert loaded.status_code == 200
    assert loaded.json()["saved"] is True
    assert loaded.json()["codes"] == {"A1": "item_1", "B1": "item_2"}
    assert loaded.json()["answers"]["B1"]["model_name"] == "엘박스"

    # 양성(덮어쓰기): 새 PUT 시 최신 개정본이 반환됨
    updated = client.put(
        base_url,
        json={"codes": {"A1": "item_1"}, "answers": {"A1": {"code": "A1", "item_id": "item_1", "model_name": "Claude", "verdict": "부존재", "basis": "없음", "summary": "새 요약"}}},
    )
    assert updated.status_code == 200
    reloaded = client.get(base_url).json()
    assert list(reloaded["answers"].keys()) == ["A1"]
    assert reloaded["answers"]["A1"]["model_name"] == "Claude"

    # 대조군 2: 없는 run_id 404
    missing = client.get(f"/api/projects/{project['id']}/runs/nonexistent-run/external-ai-answers")
    assert missing.status_code == 404
