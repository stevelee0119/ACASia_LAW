"""F2 통합 '검토 항목' 탭 화면 브라우저 시험.

수용 기준 검증:
1. 4열 통합 표(위치 / 문서 주장·인용 내용 / 근거 확인 결과 / 법리 타당성·반박·대응) 렌더링
2. 행 안 검토 상태 조작 (실제 계약 workflow_state, decision, revision, priority, assignee, note 보존):
   - 단일 finding 연결 행: PUT /api/findings/{id}/workflow 호출
   - 복수 finding 연결 행: POST /api/projects/{id}/reviews 호출
   - 순수 인용 행: 저장 불가 안내(정보 전용) 표시
3. 검색어, 심각도, 검토 상태, 진행 상태, 담당자 필터 동작 및 행 수 검증
4. 행 체크박스, 전체 선택 체크박스, 일괄 검토(batchReview) 동작 검증
5. 복수 finding 연결 행의 파생 항목 묶음(.derived-findings) 노출 검증
6. RAG 참고문헌 및 추가 관련 법조문, 미확인 범위 섹션 하단 표시 (정보 손실 0)
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


@pytest.fixture
def f2_browser_page():
    launch_kwargs = {"headless": True}
    channel = os.environ.get("LV_TEST_BROWSER_CHANNEL")
    if channel:
        launch_kwargs["channel"] = channel

    project_data = {
        "id": "p1",
        "name": "F2 통합 검토 검증 프로젝트",
        "can_delete": True,
        "document_count": 1,
        "external_ai_policy": "MASKED",
        "scope_revision": 0,
        "requested_issues": ["손해배상"],
    }

    run_data = {
        "id": "r1",
        "project_id": "p1",
        "state": "COMPLETED",
        "progress": 1,
        "stage_message": "",
        "document_ids": ["d1"],
        "scores": {},
        "unverified_items": [
            {"document_id": "d1", "page": 2, "raw_text": "관련 별지 서증", "reason": "DOCUMENT_UNREADABLE"}
        ],
        "errors": [],
        "unavailable_sources": [],
        "input_snapshot": {"scope_revision": 0},
        "started_at": "2026-10-04T00:00:00",
    }

    synthetic_findings = [
        # 행 1에 연결된 법리 finding 1 (CRITICAL)
        {
            "id": "f_cit_1",
            "finding_id": "f_cit_1",
            "finding_type": "CASE_NOT_FOUND",
            "type": "CASE_NOT_FOUND",
            "title": "공식 DB 미발견 판례",
            "detail": "합성 사건번호 판례가 공식 DB에 존재하지 않습니다.",
            "severity": "CRITICAL",
            "status": "UNCONFIRMED",
            "review_status": "NEEDS_REVIEW",
            "priority": 2,
            "assignee": "변호사A",
            "document_id": "d1",
            "page": 3,
            "citation_id": "cit_1",
        },
        # 행 1에 함께 연결된 법리 finding 2 (HIGH - 복수 finding 묶음)
        {
            "id": "f_cit_2",
            "finding_id": "f_cit_2",
            "finding_type": "CASE_HOLDING_DISTORTION",
            "type": "CASE_HOLDING_DISTORTION",
            "title": "판시사항 왜곡 의심",
            "detail": "판시사항의 핵심 요지가 원문과 상이합니다.",
            "severity": "HIGH",
            "status": "UNCONFIRMED",
            "review_status": "NEEDS_REVIEW",
            "priority": 2,
            "assignee": "변호사A",
            "document_id": "d1",
            "page": 3,
            "citation_id": "cit_1",
        },
        # 행 2에 연결된 사실관계 finding (MEDIUM)
        {
            "id": "f_fact_1",
            "finding_id": "f_fact_1",
            "finding_type": "TIMELINE_ORDER_INCONSISTENCY",
            "type": "TIMELINE_ORDER_INCONSISTENCY",
            "title": "일자 선후 모순",
            "detail": "처분일자가 신청일자보다 앞서 기재되어 있습니다.",
            "severity": "MEDIUM",
            "status": "FLAGGED",
            "review_status": "ACCEPTED",
            "priority": 1,
            "assignee": "홍길동",
            "document_id": "d1",
            "page": 5,
        },
    ]

    # F2 단일 판정 review_items
    synthetic_review_items = [
        # 행 1: 복수 finding(f_cit_1, f_cit_2)이 연결된 인용 행
        {
            "item_id": "d1_CITATION_cit_1",
            "kind": "CITATION",
            "document_id": "d1",
            "location": {"page": 3, "display": "3쪽 2문단"},
            "claim_text": "원고의 청구는 판례 법리에 부합함",
            "cited_authority": "대법원 2022다99999 판결",
            "official_status": "OFFICIAL_NOT_FOUND",
            "reference_status": "NOT_CHECKED",
            "verdict_label": "공식 DB 미확인",
            "severity": "CRITICAL",
            "finding_ids": ["f_cit_1", "f_cit_2"],
            "citation_id": "cit_1",
            "reasoning_sections": {
                "review": "타당성 검토 결과: 해당 판례 미존재에 따른 심각한 법리 왜곡 가능성이 있으며 원고의 주장은 선행 판결의 판시 내용과 상치되는 것으로 분석되어 추가적인 사실관계 및 원문 전수 조사가 반드시 필요하다고 판단됩니다",
                "ai_label": "3개 모델 일치",
                "opinions": [],
            },
            "counteraction": "원문 확인 요청",
        },
        # 행 2: 단일 finding(f_fact_1)이 연결된 사실관계 행
        {
            "item_id": "d1_FINDING_f_fact_1",
            "kind": "FACT",
            "document_id": "d1",
            "location": {"page": 5},
            "claim_text": "처분일자 2023.01.01에 따른 이행 청구",
            "cited_authority": None,
            "official_status": "NOT_ASSESSED",
            "reference_status": "NOT_CHECKED",
            "verdict_label": "일자 선후 모순",
            "severity": "MEDIUM",
            "finding_ids": ["f_fact_1"],
            "citation_id": None,
            "reasoning_sections": None,
            "counteraction": "입증서증 확인 필요",
        },
        # 행 3: finding이 연결되지 않은 순수 인용 행 (정보 전용)
        {
            "item_id": "d1_CITATION_cit_pure",
            "kind": "CITATION",
            "document_id": "d1",
            "location": {"page": 1, "display": "1쪽"},
            "claim_text": "헌법상 기본권에 근거한 정당한 주장",
            "cited_authority": "헌법 제10조",
            "official_status": "OFFICIAL_CONFIRMED",
            "reference_status": "NOT_CHECKED",
            "verdict_label": "공식 원문 일치",
            "severity": "INFO",
            "finding_ids": [],
            "citation_id": "cit_pure",
            "reasoning_sections": None,
            "counteraction": "",
        },
    ]

    result_data = {
        "status": "COMPLETED",
        "run_manifest": {
            "reference_library": {
                "status": "READY",
                "files_indexed": 3,
                "files_seen": 3,
                "checked_at": "2026-10-04T12:00:00",
            }
        },
        "documents": [
            {
                "id": "d1",
                "filename": "통합검토서면.pdf",
                "quarantined": False,
                "findings": synthetic_findings,
                "review_items": synthetic_review_items,
                "ai_hallucination_table": [
                    {
                        "location": "3쪽 2문단",
                        "cited_authority": "대법원 2022다99999 판결",
                        "claim_text": "원고의 청구는 판례 법리에 부합함",
                        "validity_verdict": "공식 DB 미확인",
                        "ai_generation_basis": "공식 소스 미존재",
                        "recommended_counteraction": "원문 확인 요청",
                    }
                ],
                "engine_data": {
                    "related_authorities": {
                        "note": "추가 검토 필요",
                        "candidates": [{"raw_text": "민법 제750조", "citation_id": "cit_rel_1"}],
                        "verdicts": [{"citation_id": "cit_rel_1", "status": "CONFIRMED"}],
                    }
                },
            }
        ],
    }

    workflow_store = {
        "f_cit_1": {
            "finding_id": "f_cit_1",
            "revision": 1,
            "workflow_state": "NOT_STARTED",
            "decision": "UNDECIDED",
            "priority": 2,
            "assignee": "변호사A",
            "note": "초기메모",
        },
        "f_cit_2": {
            "finding_id": "f_cit_2",
            "revision": 1,
            "workflow_state": "NOT_STARTED",
            "decision": "UNDECIDED",
            "priority": 2,
            "assignee": "변호사A",
            "note": "초기메모",
        },
        "f_fact_1": {
            "finding_id": "f_fact_1",
            "revision": 1,
            "workflow_state": "COMPLETED",
            "decision": "AGREED",
            "priority": 1,
            "assignee": "홍길동",
            "note": "초기메모",
        },
    }

    static_dir = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static_dir).as_posix()}": p for p in static_dir.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"

    workflow_put_calls = []
    bulk_review_calls = []

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
        if path == "/api/projects/p1":
            route.fulfill(json=project_data)
            return
        if path == "/api/projects/p1/documents":
            route.fulfill(json=[{"id": "d1", "filename": "통합검토서면.pdf", "included_in_verification": True}])
            return
        if path == "/api/projects/p1/runs":
            route.fulfill(json=[run_data])
            return
        if path == "/api/projects/p1/findings":
            route.fulfill(json=synthetic_findings)
            return
        if path.endswith(("/result", "/results")):
            route.fulfill(json=result_data)
            return
        if path == "/api/projects/p1/audit":
            route.fulfill(json={"events": []})
            return
        if path == "/api/privacy-notice":
            route.fulfill(json={"version": "v1.0", "bullets": [], "ack_label": "", "report_header": ""})
            return
        if path == "/api/finding-categories":
            from packages.common.finding_category_map import CATEGORY_TO_TAB, FINDING_CATEGORY_MAP, get_category_counts
            route.fulfill(json={
                "categories": {ft.value: cat.value for ft, cat in FINDING_CATEGORY_MAP.items()},
                "tabs": {ft.value: CATEGORY_TO_TAB[cat].value for ft, cat in FINDING_CATEGORY_MAP.items()},
                "counts": get_category_counts(),
            })
            return
        if path.startswith("/api/findings/") and path.endswith("/workflow"):
            fid = path.split("/")[3]
            if req.method == "GET":
                data = workflow_store.get(fid, {
                    "finding_id": fid, "revision": 1, "workflow_state": "NOT_STARTED",
                    "decision": "UNDECIDED", "priority": 2, "assignee": "변호사A", "note": "초기메모",
                })
                route.fulfill(json=data)
                return
            if req.method == "PUT":
                payload = json.loads(req.post_data)
                workflow_put_calls.append({"path": path, "payload": payload})
                updated = {
                    "finding_id": fid,
                    "revision": payload.get("revision", 0) + 1,
                    "workflow_state": payload.get("workflow_state", "NOT_STARTED"),
                    "decision": payload.get("decision", "UNDECIDED"),
                    "priority": payload.get("priority", 2),
                    "assignee": payload.get("assignee", ""),
                    "note": payload.get("note", ""),
                }
                workflow_store[fid] = updated
                route.fulfill(json=updated)
                return
        if path == "/api/projects/p1/reviews" and req.method == "POST":
            payload = json.loads(req.post_data)
            bulk_review_calls.append({"path": path, "payload": payload})
            results = []
            vals = payload.get("values", {})
            for fid in payload.get("finding_ids", []):
                rev = payload.get("expected_revisions", {}).get(fid, 0) + 1
                item_res = {
                    "finding_id": fid,
                    "revision": rev,
                    "workflow_state": vals.get("workflow_state", "NOT_STARTED"),
                    "decision": vals.get("decision", "UNDECIDED"),
                    "priority": vals.get("priority", 2),
                    "assignee": vals.get("assignee", ""),
                    "note": vals.get("note", ""),
                }
                workflow_store[fid] = item_res
                results.append(item_res)
            route.fulfill(json=results)
            return
        if path == "/api/projects/p1/review-workflows":
            route.fulfill(json=list(workflow_store.values()))
            return
        if path.endswith("/case-matrix"):
            route.fulfill(body="null", content_type="application/json")
            return

        route.fulfill(status=200, json=[])

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route("**/*", route_handler)
        page._workflow_put_calls = workflow_put_calls
        page._bulk_review_calls = bulk_review_calls
        yield page
        browser.close()


def test_f2_review_table_renders_four_columns(f2_browser_page):
    """F2 확인할 항목 탭은 위치/문서 주장·인용 내용/근거 확인 결과/확인이 필요한 내용 4열 통합 표를 렌더링해야 합니다."""
    page = f2_browser_page
    page.goto("http://localhost/")
    select_first_project(page)

    page.locator('.tabs button[data-tab="review"]').click()

    panel = page.locator('section[data-panel="review"]')
    expect(panel).to_be_visible()

    # 4열 헤더 검증 (2단 인용 표)
    headers = panel.locator(".review-items-table thead th")
    expect(headers).to_have_count(4)
    expect(headers.nth(0)).to_have_text("위치")
    expect(headers.nth(1)).to_have_text("문서 주장 및 인용 내용")
    expect(headers.nth(2)).to_have_text("인용 오류·미확인 근거 및 주장 평가 (작성 주체 판단에 쓰지 않음)")
    expect(headers.nth(3)).to_have_text("확인이 필요한 내용")

    # 3단 법률적으로 무리한 주장 표는 독립 탭(legal-claims)에 있다 (2026-10-25 보완, 사용자 10-19 개선안 4항)
    expect(panel.locator(".tier3-table")).to_have_count(0)
    page.locator('.tabs button[data-tab="legal-claims"]').click()
    claims_panel = page.locator('section[data-panel="legal-claims"]')
    tier3_headers = claims_panel.locator(".tier3-table thead th")
    expect(tier3_headers).to_have_count(4)
    expect(tier3_headers.nth(0)).to_have_text("위치")
    expect(tier3_headers.nth(1)).to_have_text("문서 주장 및 인용 내용")
    expect(tier3_headers.nth(2)).to_have_text("법리 검토 결과 및 근거")
    expect(tier3_headers.nth(3)).to_have_text("확인이 필요한 내용")

    # 2단 인용 표(2개 행) 및 3단 무리한 주장 표(1개 행) 분리 노출 검증 (TK-88, 3단은 독립 탭)
    tier3_rows = claims_panel.locator("#tier3Rows tr")
    expect(tier3_rows).to_have_count(1)
    page.locator('.tabs button[data-tab="review"]').click()
    rows = panel.locator("#aiVerificationRows tr")
    expect(rows).to_have_count(2)

    # 4열 확인이 필요한 내용 요약 박스 검증
    summary_box = rows.first.locator(".review-summary-box")
    expect(summary_box).to_be_visible()
    expect(summary_box.locator(".summary-target")).to_contain_text("확인 대상")
    expect(summary_box.locator(".summary-reason")).to_contain_text("의심 사유")
    expect(summary_box.locator(".summary-action")).to_have_count(0)  # 2026-10-25 보완: 반복되는 '확인 방법' 줄 삭제(사용자 요구)


def test_f2_review_summary_box_renders_instead_of_inline_workflow(f2_browser_page):
    """행 안의 검토 상태·우선순위·담당자 입력 컨트롤이 제거되고 확인이 필요한 내용 요약 박스가 렌더링되어야 합니다."""
    page = f2_browser_page
    page.goto("http://localhost/")
    select_first_project(page)

    page.locator('.tabs button[data-tab="review"]').click()

    panel = page.locator('section[data-panel="review"]')
    rows = panel.locator("#aiVerificationRows tr")

    # 행 안의 워크플로우 컨트롤(select, input)이 존재하지 않음을 확인
    expect(panel.locator(".inline-workflow-select")).to_have_count(0)
    expect(panel.locator(".inline-priority-select")).to_have_count(0)
    expect(panel.locator(".inline-assignee-input")).to_have_count(0)
    expect(panel.locator(".inline-workflow-note")).to_have_count(0)

    # 2단 표 2개 행 및 3단 표 1개 행 전수에서 4열에 확인 요약 박스가 렌더링되어 있음을 확인
    for i in range(2):
        expect(rows.nth(i).locator(".review-summary-box")).to_be_visible()

    page.locator('.tabs button[data-tab="legal-claims"]').click()
    tier3_rows = page.locator('section[data-panel="legal-claims"] #tier3Rows tr')
    expect(tier3_rows.first.locator(".review-summary-box")).to_be_visible()


def test_f2_review_summary_content_elements(f2_browser_page):
    """확인이 필요한 내용 요약은 무엇을(인용·주장), 왜(판정 사유), 어떻게(원문 대조 위치)를 포함해야 합니다."""
    page = f2_browser_page
    page.goto("http://localhost/")
    select_first_project(page)

    page.locator('.tabs button[data-tab="review"]').click()

    panel = page.locator('section[data-panel="review"]')
    rows = panel.locator("#aiVerificationRows tr")

    # 1번째 행 확인 요약 검증 (라벨뿐만 아니라 기존 필드값으로부터 조합되었는지 실제 내용 검증 - TK-87)
    box = rows.nth(0).locator(".review-summary-box")
    expect(box.locator(".summary-target")).to_be_visible()
    expect(box.locator(".summary-target")).to_contain_text("대법원 2022다99999 판결")
    expect(box.locator(".summary-reason")).to_be_visible()
    expect(box.locator(".summary-reason")).to_contain_text("타당성 검토 결과: 해당 판례 미존재")
    expect(box.locator(".summary-action")).to_have_count(0)  # 2026-10-25 보완: '확인 방법' 줄 삭제


def test_f2_review_summary_reason_truncation_and_location_display(f2_browser_page):
    """의심 사유는 100자 이내 2~3줄로 축약되고, 상세 법리 의견은 기본 접혀 있으며, 확인 방법은 권위명과 쪽/위치가 조합되어야 합니다 (TK-87)."""
    page = f2_browser_page
    page.goto("http://localhost/")
    select_first_project(page)

    page.locator('.tabs button[data-tab="review"]').click()

    panel = page.locator('section[data-panel="review"]')
    rows = panel.locator("#aiVerificationRows tr")

    # 1. 1번째 행 상세 법리 의견 details 요소가 무조건 존재하고 기본적으로 접혀 있는지 검증 (TK-87 요구사항 2)
    box = rows.nth(0).locator(".review-summary-box")
    details = box.locator("details.summary-details")
    expect(details).to_be_visible()
    expect(details).not_to_have_attribute("open", "")

    # 2. 1번째 행 의심 사유 텍스트가 100자 상한으로 '…' 축약되어 노출되는지 검증
    reason_elem = box.locator(".summary-reason")
    expect(reason_elem).to_be_visible()
    expect(reason_elem).to_contain_text("…")
    reason_text = reason_elem.inner_text()
    assert len(reason_text) <= 120, f"의심 사유 텍스트가 과도하게 길지 않아야 함: {len(reason_text)}자"

    # 3. 2단 표의 2번째 행(counteraction 없는 위치 행: 헌법 제10조, 1쪽)의 확인 방법 텍스트 검증: '권위명 원문 대조 (N쪽)' 분기
    box3 = rows.nth(1).locator(".review-summary-box")
    expect(box3.locator(".summary-action")).to_have_count(0)  # 2026-10-25 보완: '확인 방법' 줄 삭제


def test_f2_filters_search_severity_review_status(f2_browser_page):
    """검색어와 중요도 필터가 동작하고, 제거된 검토상태/진행상태/담당자 필터는 화면에 없어야 합니다 (TK-87)."""
    page = f2_browser_page
    page.goto("http://localhost/")
    select_first_project(page)

    page.locator('.tabs button[data-tab="review"]').click()

    panel = page.locator('section[data-panel="review"]')
    rows = panel.locator("#aiVerificationRows tr")
    expect(rows).to_have_count(2)

    # 1. 중요도 필터: CRITICAL 선택 -> 1개 행 노출
    sev_select = panel.locator("#severityFilter")
    sev_select.select_option("CRITICAL")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("대법원 2022다99999 판결")
    sev_select.select_option("")
    expect(rows).to_have_count(2)

    # 2. 2단 표 검색어 필터: '2022다99999' 검색 -> 1개 행 노출
    search_input = panel.locator("#findingSearch")
    search_input.fill("2022다99999")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("대법원 2022다99999 판결")
    search_input.fill("")
    expect(rows).to_have_count(2)

    # 3단 표의 사실관계 항목('일자 선후 모순') 확인 (독립 탭)
    page.locator('.tabs button[data-tab="legal-claims"]').click()
    tier3_rows = page.locator('section[data-panel="legal-claims"] #tier3Rows tr')
    expect(tier3_rows).to_have_count(1)
    expect(tier3_rows.first).to_contain_text("일자 선후 모순")

    # 3. 제거된 필터(진행 상태, 담당자, 검토 상태)는 DOM에 없어야 함 (TK-87 요구 1)
    expect(panel.locator("#workflowFilter")).to_have_count(0)
    expect(panel.locator("#assigneeFilter")).to_have_count(0)
    expect(panel.locator("#reviewFilter")).to_have_count(0)


def test_f2_checkboxes_and_batch_review(f2_browser_page):
    """행 체크박스 및 일괄 검토/전체 선택 컨트롤이 화면에서 제거되었음을 검증합니다 (TK-87)."""
    page = f2_browser_page
    page.goto("http://localhost/")
    select_first_project(page)

    page.locator('.tabs button[data-tab="review"]').click()

    panel = page.locator('section[data-panel="review"]')

    # 행 체크박스, 전체 선택 체크박스, 일괄 검토 버튼이 존재하지 않아야 함
    expect(panel.locator("#batchReview")).to_have_count(0)
    expect(panel.locator(".row-checkbox")).to_have_count(0)
    expect(panel.locator("#selectAllFindings")).to_have_count(0)


def test_f2_derived_findings_bundle_and_multi_save(f2_browser_page):
    """복수 finding이 연결된 행은 파생 항목 묶음(.derived-findings)이 노출되고, 행 안 입력 대신 요약 블록이 노출되어야 합니다 (TK-87)."""
    page = f2_browser_page
    page.goto("http://localhost/")
    select_first_project(page)

    page.locator('.tabs button[data-tab="review"]').click()

    panel = page.locator('section[data-panel="review"]')
    rows = panel.locator("#aiVerificationRows tr")

    # 복수 finding (f_cit_1, f_cit_2) 연결 행: .derived-findings를 가진 행
    row_multi = rows.filter(has=page.locator(".derived-findings")).first

    # 2열 파생 항목 묶음 details 확인
    derived = row_multi.locator(".derived-findings")
    expect(derived).to_be_visible()
    expect(derived.locator("summary")).to_contain_text("같은 인용에서 파생된 항목 1건")

    # 행 안 입력(검토 상태·우선순위·담당자)이 없음을 확인 (TK-87 요구 1)
    expect(row_multi.locator(".inline-workflow-select")).to_have_count(0)
    expect(row_multi.locator(".inline-priority-select")).to_have_count(0)
    expect(row_multi.locator(".inline-assignee-input")).to_have_count(0)

    # 대신 4열에 확인이 필요한 내용 요약 블록(.review-summary-box)이 렌더링되어 있어야 함 (TK-87 요구 2)
    summary_box = row_multi.locator(".review-summary-box")
    expect(summary_box).to_be_visible()
    expect(summary_box.locator(".summary-target")).to_be_visible()


def test_f2_references_and_unverified_scope_rendered(f2_browser_page):
    """RAG 주요 참고문헌 및 미확인 범위, 추가 법조문이 통합 탭 하단에 온전히 표시되어야 합니다 (정보 손실 0)."""
    page = f2_browser_page
    page.goto("http://localhost/")
    select_first_project(page)

    page.locator('.tabs button[data-tab="review"]').click()

    panel = page.locator('section[data-panel="review"]')

    # 미확인 범위 확인
    unverified = panel.locator("#unverifiedScopeContainer")
    expect(unverified).to_contain_text("미확인 범위 1건")
    expect(unverified).to_contain_text("관련 별지 서증")

    # RAG 주요 참고문헌 및 관련 법조문 확인
    # 2026-10-25 사용자 요구(평가 측 개정): 참고문헌 처리 기록은 하단 절이 아니라 표 위 상태 줄(펼침)에 둔다.
    status = panel.locator("#referenceStatus")
    status.locator("summary").first.click()
    expect(status).to_contain_text("주요 참고문헌 검토 결과(RAG)")
    ref_container = panel.locator("#reviewReferencesContainer")
    expect(ref_container).to_contain_text("추가 관련 법조문 검토")
    expect(ref_container).to_contain_text("민법 제750조")
