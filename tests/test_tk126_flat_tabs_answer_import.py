# -*- coding: utf-8 -*-
"""TK-126·127·128 (2026-10-25 사용자 요구) 화면 시험.

1. 상단 탭은 하위 탭 없이 다섯 개다(자료·AI 작성·보안 진단·출처가 확인되지 않는 항목·법률적으로 무리한 주장·보고서).
2. 주요 참고문헌(RAG) 대조 의견은 하단 절이 아니라 표의 행에 붙고, 행과 연결되지 않은 '불부합' 의견은 3번째 탭의 행이 된다.
3. 두 표 모두 엘박스/AI 검증 프롬프트와 '외부 AI 답변 붙여넣기'가 있고, 붙여넣은 답변은 번호로 행에 반영되되
   공식 확인 배지는 바뀌지 않는다.
4. 3번째 탭 프롬프트의 주장 문장은 서버의 프로젝트 정책 가림을 거친다.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from frontend_helpers import select_first_project
from test_api import client, project  # noqa: F401  (fixture 재사용)

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_CLAIM = "원고 홍길동(010-9876-5432)은 해지 통보 없이 계약이 소멸하였다고 주장한다"
MASKED_CLAIM = "원고 [인물1]([전화1])은 해지 통보 없이 계약이 소멸하였다고 주장한다"


def _result():
    items = [
        {"item_id": "item_a", "kind": "CITATION", "document_id": "d1", "location": {"display": "2쪽"},
         "claim_text": "청구권 행사 기한이 지났다는 주장", "cited_authority": "대법원 2022다99999 판결",
         "official_status": "OFFICIAL_NOT_FOUND", "reference_status": "NOT_CHECKED",
         "verdict_label": "공식 DB 미확인 (원문 확인 필요)", "severity": "HIGH", "finding_ids": [], "citation_id": "cit_1"},
        {"item_id": "item_b", "kind": "FACT", "document_id": "d1", "location": {"display": "4쪽"},
         "claim_text": ORIGINAL_CLAIM, "official_status": "NOT_ASSESSED", "reference_status": "NOT_CHECKED",
         "verdict_label": "사실관계 상이", "severity": "MEDIUM", "finding_ids": []},
    ]
    rag = {"status": "ADVISORY_REVIEWED", "sources": [{"source_id": "R1", "title": "표준판례집", "page": 12, "text": "발췌"}],
           "observations": [
               {"claim_id": "c1", "claim_quote": "청구권 행사 기한", "source_id": "R1", "source_quote": "기한 기산점 설명",
                "relationship": "CONTRADICTS", "explanation": "기산점이 다르다", "advisory_only": True},
               {"claim_id": "c9", "claim_quote": "표에 없는 별도 주장 문장입니다", "source_id": "R1", "source_quote": "다른 설명",
                "relationship": "CONTRADICTS", "explanation": "참고문헌과 다르다", "advisory_only": True}]}
    return {"status": "COMPLETED",
            "run_manifest": {"reference_library": {"status": "READY", "files_indexed": 1, "files_seen": 1, "checked_at": "2026-10-25"}},
            "documents": [{"id": "d1", "filename": "서면.pdf", "quarantined": False, "findings": [], "review_items": items,
                           "claims": [{"claim_id": "c1", "citation_ids": ["cit_1"]}], "engine_data": {"rag": rag}}]}


def _page(p, prompt_calls):
    project_data = {"id": "p1", "name": "합성 사건", "can_delete": True, "document_count": 1, "external_ai_policy": "MASKED",
                    "scope_revision": 0, "incident_date": "2024-05-01", "requested_issues": []}
    run = {"id": "r1", "project_id": "p1", "state": "COMPLETED", "progress": 1, "stage_message": "", "document_ids": ["d1"],
           "scores": {}, "unverified_items": [], "errors": [], "unavailable_sources": [], "input_snapshot": {"scope_revision": 0},
           "started_at": "2026-10-25T00:00:00"}
    static_dir = ROOT / "apps/web/static"
    files = {f"/static/{f.relative_to(static_dir).as_posix()}": f for f in static_dir.rglob("*") if f.is_file()}
    files["/"] = ROOT / "apps/web/index.html"
    fixed = {"/api/health": {"status": "ok", "version": "0.14.0"},
             "/api/auth/me": {"user_id": "u", "email": "t@example.com", "display_name": "검토자", "role": "ADMIN", "authentication": "local"},
             "/api/verification-runs": {"active_count": 0, "runs": []}, "/api/projects": [project_data], "/api/projects/p1": project_data,
             "/api/projects/p1/documents": [{"id": "d1", "filename": "서면.pdf", "included_in_verification": True}],
             "/api/projects/p1/runs": [run], "/api/projects/p1/audit": {"events": []},
             "/api/privacy-notice": {"version": "v1", "bullets": [], "ack_label": "", "report_header": ""},
             "/api/finding-categories": {"categories": {}, "tabs": {}, "counts": {}}}

    def handler(route):
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        if path == "/api/projects/p1/external-ai/prompt-texts":
            body = route.request.post_data_json
            prompt_calls.append(body)
            return route.fulfill(json={"policy": "MASKED", "texts": [MASKED_CLAIM if t == ORIGINAL_CLAIM else t for t in body["texts"]]})
        if path.endswith(("/result", "/results")):
            return route.fulfill(json=_result())
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        if path in fixed:
            return route.fulfill(json=fixed[path])
        route.fulfill(json=[])

    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    context.add_init_script("""window.__copied = [];
      Object.defineProperty(navigator, 'clipboard', {value: {writeText: async t => { window.__copied.push(t); }}});""")
    page = context.new_page()
    page.route("**/*", handler)
    page.goto("http://localhost/")
    select_first_project(page)
    return browser, page


def test_rag_observations_attach_to_rows_and_bottom_section_is_gone():
    with sync_playwright() as p:
        browser, page = _page(p, [])
        page.locator('.tabs [data-tab="review"]').click()
        row = page.locator("#aiVerificationRows tr", has_text="대법원 2022다99999 판결")
        expect(row.locator(".reference-observations")).to_contain_text("불부합")
        expect(row.locator(".reference-observations")).to_contain_text("표준판례집 · 12쪽")
        expect(page.locator("#reviewReferencesContainer .reference-section")).to_have_count(0)
        expect(page.locator("#referenceStatus")).to_contain_text("표의 행에 반영한 의견 1건")
        page.locator('.tabs [data-tab="legal-claims"]').click()
        expect(page.locator("#tier3Rows tr", has_text="표에 없는 별도 주장 문장입니다")).to_contain_text("참고문헌과 불부합")
        browser.close()


def test_answer_import_applies_to_row_without_changing_official_badge():
    with sync_playwright() as p:
        browser, page = _page(p, [])
        page.locator('.tabs [data-tab="review"]').click()
        bar = page.locator("#reviewTableActions")
        bar.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()
        prompt = page.evaluate("window.__copied.at(-1)")
        assert "A1. 대법원 2022다99999 판결" in prompt and "<<<ACAS_RESULT" in prompt
        bar.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        answer = "요약 생략\n<<<ACAS_RESULT\nA1 | 판정: 부존재 | 근거: 해당 사건번호 없음 | 요지: 유사 판례는 2021다1\nA7 | 판정: 확인\nACAS_RESULT>>>"
        page.get_by_role("dialog", name="외부 AI 답변 붙여넣기").locator("textarea").fill(answer)
        page.get_by_role("dialog", name="외부 AI 답변 붙여넣기").get_by_role("button", name="저장").click()
        preview = page.get_by_role("dialog", name="표에 반영할 답변 1건 확인")
        expect(preview).to_contain_text("A1 → 대법원 2022다99999 판결")
        expect(preview).to_contain_text("A7")
        preview.get_by_role("button", name="표에 반영").click()
        row = page.locator("#aiVerificationRows tr", has_text="대법원 2022다99999 판결")
        expect(row.locator(".external-ai-answer")).to_contain_text("외부 AI 답변 A1 (공식 확인 아님)")
        expect(row.locator(".external-ai-answer")).to_contain_text("판정: 부존재")
        expect(row.locator(".validity-verdict")).to_have_text("공식 DB 미확인 (원문 확인 필요)")
        # 2026-10-25 사용자 결정: 공식 DB는 검증 실행 때 이미 조회하므로 '다시 조회' 버튼을 두지 않는다.
        expect(row.locator(".external-ai-answer")).to_contain_text("참고용이며 위 공식 DB 판정은 바뀌지 않습니다")
        expect(row.get_by_role("button", name="공식 DB로 다시 조회")).to_have_count(0)
        browser.close()


def test_legal_claims_tab_prompt_uses_server_masked_claims_and_imports_answers():
    calls = []
    with sync_playwright() as p:
        browser, page = _page(p, calls)
        page.locator('.tabs [data-tab="legal-claims"]').click()
        bar = page.locator("#legalClaimsActions")
        expect(bar).to_be_visible()
        bar.get_by_role("button", name="📋 엘박스/AI 검증 프롬프트 만들기").click()
        page.wait_for_function("window.__copied.length > 0")
        prompt = page.evaluate("window.__copied.at(-1)")
        assert calls and ORIGINAL_CLAIM in calls[0]["texts"]
        assert MASKED_CLAIM in prompt and "010-9876-5432" not in prompt and "홍길동" not in prompt
        assert "B1." in prompt and "<<<ACAS_RESULT" in prompt
        code = next(line.split(".")[0] for line in prompt.splitlines() if MASKED_CLAIM in line)
        bar.get_by_role("button", name="📥 외부 AI 답변 붙여넣기").click()
        dialog = page.get_by_role("dialog", name="외부 AI 답변 붙여넣기")
        dialog.locator("textarea").fill(f"<<<ACAS_RESULT\n{code.strip()} | 판정: 불일치 | 근거: 민법 제543조 | 요지: 해지 의사표시가 필요\nACAS_RESULT>>>")
        dialog.get_by_role("button", name="저장").click()
        page.get_by_role("dialog", name="표에 반영할 답변 1건 확인").get_by_role("button", name="표에 반영").click()
        row = page.locator("#tier3Rows tr", has_text="해지 통보 없이")
        expect(row.locator(".external-ai-answer")).to_contain_text("근거: 민법 제543조")
        browser.close()


def test_prompt_texts_endpoint_follows_project_policy(client, project):  # noqa: F811
    from apps.api.db import Project, get_session_factory
    url = f"/api/projects/{project['id']}/external-ai/prompt-texts"

    def set_policy(policy):
        with get_session_factory()() as session:
            session.get(Project, project["id"]).external_ai_policy = policy
            session.commit()

    set_policy("LOCAL_ONLY")
    assert client.post(url, json={"texts": [ORIGINAL_CLAIM]}).status_code == 403
    set_policy("MASKED")
    masked = client.post(url, json={"texts": [ORIGINAL_CLAIM]}).json()
    assert masked["policy"] == "MASKED" and "010-9876-5432" not in masked["texts"][0]
    set_policy("ORIGINAL")
    assert client.post(url, json={"texts": [ORIGINAL_CLAIM]}).json()["texts"] == [ORIGINAL_CLAIM]
