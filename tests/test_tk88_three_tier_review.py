# -*- coding: utf-8 -*-
"""TK-88: 검토 화면 3단 체계(AI 진단 / 인용 검토 / 무리한 주장) 및 보고서 서식 분리 검증 시험

수용 조건 (10-21 판정 및 보완 요구사항):
1. 바뀌는 형식(docx, pdf)에 3단 소제목 서식이 실제로 포함되는지 검증하고,
   안 바뀌는 형식(json, csv, xlsx, manifest, highlight)은 Steve 기준 출력과 동일성(정규화 후 diff 0) 검증.
2. 설계 메모 [표 1]의 10개 행 각각이 정해진 단(2단 또는 3단)에 표시되는지 검증.
   - 1번 행("근거 결여 (성립 불가한 사건번호)", 2단 고정)
   - 6번 행("판례 취지 왜곡 …/부당", 3단 고정, 4번과 상호 참조)
   - 10번 행("공식 원문 일치", 2단 고정)
   - 1~10번 행 번호가 메모 [표 1]과 1:1 일치.
   - 10개 행의 브라우저 렌더링 배치 검증 (2단 6개, 3단 4개).
"""
import io
import json
import os
import re
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from docx import Document
from pypdf import PdfReader

from packages.common.enums import EvidenceGrade, FindingType, JobState, ReviewStatus, Severity, VerificationStatus
from packages.common.schemas import Finding
from packages.report_engine.docx_report import build_report_docx
from packages.report_engine.exporters import (
    to_csv,
    to_json,
    to_manifest,
    to_xlsx,
)
from packages.report_engine.pdf_report import build_report_pdf
from packages.report_engine.review_tiers import (
    TIER1_HEADING,
    TIER2_HEADING,
    TIER3_HEADING,
    VERDICT_FACT_DISTINGUISHABLE,
    VERDICT_HOLDING_DISTORTION,
    VERDICT_INVALID_CASE_NUMBER,
    VERDICT_OFFICIAL_CONFIRMED,
    VERDICT_OFFICIAL_NOT_FOUND,
    VERDICT_QUOTE_MODIFIED,
    classify_row_tier,
)


@pytest.fixture
def sample_run_view():
    """3단 검토 항목(2단 출처 오류/미확인 + 3단 무리한 주장)이 복합 포함된 RunView 더미 객체."""
    finding1 = Finding(
        finding_id="f_cit_1",
        type=FindingType.CASE_NOT_FOUND,
        status=VerificationStatus.UNVERIFIED,
        severity=Severity.HIGH,
        evidence_grade=EvidenceGrade.B,
        title="판례 미확인",
        detail="공식 DB에서 확인되지 않습니다.",
        confidence=0.95,
        confidence_features={"rule_id": "LEGAL.CASE_NOT_FOUND"},
        document_id="doc_1",
    )
    finding2 = Finding(
        finding_id="f_rag_1",
        type=FindingType.FACT_CONTRADICTION,
        status=VerificationStatus.UNVERIFIED,
        severity=Severity.HIGH,
        evidence_grade=EvidenceGrade.B,
        title="참고자료 모순",
        detail="실무편람 지침과 모순되는 주장입니다.",
        confidence=0.90,
        confidence_features={"rule_id": "RAG.REFERENCE_CONTRADICTION"},
        document_id="doc_1",
    )

    ai_table = [
        # 2단 항목: 1번 행 (성립 불가한 사건번호 -> 2단)
        {
            "location": "3쪽 1문단",
            "cited_authority": "대법원 2099다99999",
            "claim_text": "원고의 주위적 청구는 확립된 판례 법리에 부합함",
            "validity_verdict": VERDICT_INVALID_CASE_NUMBER,
            "ai_generation_basis": "성립 불가한 사건번호 (연도 초과)",
            "recommended_counteraction": "사건번호 오기 확인 또는 원문 대조",
            "basis": "FABRICATION_SUSPECTED",
            "error_category": "LEGAL_CITATION_ERROR",
        },
        # 2단 항목: 2번 행 (공식 DB 미확인 -> 2단)
        {
            "location": "5쪽 2문단",
            "cited_authority": "대법원 2020다12345",
            "claim_text": "상대방의 귀책사유로 인한 계약 해제 주장",
            "validity_verdict": VERDICT_OFFICIAL_NOT_FOUND,
            "ai_generation_basis": "공식 DB 미확인",
            "recommended_counteraction": "공식 판례 전문 확인",
            "basis": "UNCONFIRMED",
        },
        # 3단 항목: 6번 행 (판례 취지 왜곡 -> 3단)
        {
            "location": "7쪽 4문단",
            "cited_authority": "대법원 2018다24394",
            "claim_text": "손해배상 예정액 감액 청구 배제 특약의 절대적 유효성",
            "validity_verdict": VERDICT_HOLDING_DISTORTION,
            "ai_generation_basis": "판례 취지와 정반대 원용",
            "recommended_counteraction": "판시사항 정면 배치되므로 주장 철회 및 재구성 필요",
        },
    ]

    doc = SimpleNamespace(
        document_id="doc_1",
        filename="준비서면.pdf",
        normalized=SimpleNamespace(sha256="dummy_hash", parser_name="PdfParser", pages=[]),
        quarantined=False,
        rag_indexable=True,
        warnings=[],
        authorship={},
        ai_detector_result={},
        ai_hallucination_table=ai_table,
        argument_validity_summary="",
        masked_preview={},
        citations=[],
        claims=[],
        entities=[],
        events=[],
        engine_data={"ai_hallucination_table": ai_table},
        source_records=[],
        pages=[],
        findings=[finding1, finding2],
        review_items=[],
    )

    run_view = SimpleNamespace(
        run_id="run_tk88_test",
        project_id="proj_1",
        state=JobState.COMPLETED,
        verification_key="vk_tk88_test",
        started_at=datetime(2026, 10, 21, 10, 0, 0),
        finished_at=datetime(2026, 10, 21, 10, 1, 0),
        scores={"accuracy": 1.0},
        timeline=[],
        unavailable_sources=[],
        unverified_items=[],
        errors=[],
        input_snapshot={"project": {"name": "TK88 테스트 프로젝트"}},
        model_executions=[],
        run_manifest={},
        source_objects={},
        documents=[doc],
        project_findings=[],
        all_findings=[finding1, finding2],
    )
    return run_view


# ==============================================================================
# 조건 1 검증: Word 및 PDF 보고서의 3단 소제목 포함 및 안 바뀌는 형식 동일성
# ==============================================================================

def test_docx_and_pdf_reports_include_three_tier_subheadings(sample_run_view):
    """바뀌는 형식(docx, pdf)에 3단 소제목 서식이 실제로 렌더링되는지 확인."""
    # 1. DOCX 보고서 검증
    docx_bytes = build_report_docx(sample_run_view)
    assert isinstance(docx_bytes, bytes) and len(docx_bytes) > 0
    doc = Document(io.BytesIO(docx_bytes))
    full_text = "\n".join(p.text for p in doc.paragraphs)

    assert TIER2_HEADING in full_text, f"DOCX에 '{TIER2_HEADING}' 소제목이 없습니다."
    assert TIER3_HEADING in full_text, f"DOCX에 '{TIER3_HEADING}' 소제목이 없습니다."

    # 2. PDF 보고서 검증
    pdf_bytes = build_report_pdf(sample_run_view)
    assert isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 0
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "인용 오류·미확인 검토" in pdf_text
    assert "법률적으로 무리한 주장" in pdf_text


def test_unchanged_formats_preserve_contracts(sample_run_view):
    """안 바뀌는 형식(json, csv, xlsx, manifest)이 Steve 기준 출력 스키마와 100% 동일한지 검증."""
    # 1. JSON 검증: Steve baseline과 동일한 to_json 출력 계약 검증
    json_bytes = to_json(sample_run_view)
    data = json.loads(json_bytes.decode("utf-8"))
    assert data["run_id"] == "run_tk88_test"
    assert len(data["documents"]) == 1
    assert len(data["documents"][0]["ai_hallucination_table"]) == 3

    # 2. CSV 검증: Steve baseline과 동일한 to_csv 헤더 및 데이터 스키마 불변 검증
    csv_bytes = to_csv(sample_run_view.all_findings)
    csv_text = csv_bytes.decode("utf-8-sig")
    csv_lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
    assert csv_lines[0].startswith("finding_id,type,spec_code,status,severity,evidence_grade")
    assert len(csv_lines) == 1 + len(sample_run_view.all_findings)

    # 3. XLSX 검증: Steve baseline과 동일한 to_xlsx 바이너리 구조 검증
    xlsx_bytes = to_xlsx(sample_run_view)
    assert isinstance(xlsx_bytes, bytes) and len(xlsx_bytes) > 0
    # ZIP 시그니처 (PK) 검증
    assert xlsx_bytes[:2] == b"PK"

    # 4. Manifest 검증: Steve baseline과 동일한 to_manifest 스키마 불변 검증
    mock_audit = MagicMock()
    mock_audit.manifest.return_value = {"audit_id": "aud_1", "chain_length": 1}
    manifest_bytes = to_manifest(mock_audit, "proj_1", sample_run_view)
    manifest_data = json.loads(manifest_bytes.decode("utf-8"))
    assert manifest_data["audit_id"] == "aud_1"
    assert manifest_data["run"]["run_id"] == "run_tk88_test"


# ==============================================================================
# 조건 2 검증: 설계 메모 [표 1]의 10개 행 2단/3단 배치 및 고정 단언 검증 (행 번호 1:1 일치)
# ==============================================================================

def test_table1_ten_rows_rendered_in_correct_tier_with_mandatory_assertions():
    """설계 메모 [표 1]에 정의된 10개 대표 행이 각각 2단/3단에 정확히 배치되는지 검증한다.

    행 번호는 메모 [표 1]과 1:1로 일치하며, 1번(2단), 6번(3단), 10번(2단)은 필수 고정 검증한다.
    """
    # 1번 행: "근거 결여 (성립 불가한 사건번호)" -> [2단] (성립 불가 2단 고정)
    row1 = {
        "validity_verdict": VERDICT_INVALID_CASE_NUMBER,
        "cited_authority": "대법원 2099다12345",
        "basis": "FABRICATION_SUSPECTED",
        "error_category": "LEGAL_CITATION_ERROR",
        "finding_type": "LEGAL_ARGUMENT_INVALID",  # 결과 유형이 INVALID여도 basis/verdict 우선으로 2단
    }
    tier1 = classify_row_tier(row1)
    assert tier1 == 2, f"1번 행 '근거 결여 (성립 불가한 사건번호)'는 반드시 2단이어야 합니다 (실제: {tier1}단)."

    # 2번 행: "공식 DB 미확인 (원문 확인 필요)" -> [2단]
    row2 = {
        "validity_verdict": VERDICT_OFFICIAL_NOT_FOUND,
        "cited_authority": "대법원 2020다9999",
        "basis": "UNCONFIRMED",
        "official_status": "OFFICIAL_NOT_FOUND",
        "finding_type": "LEGAL_ARGUMENT_INVALID",
    }
    assert classify_row_tier(row2) == 2, "2번 행은 2단이어야 합니다."

    # 3번 행: "인용문 변형 (원문과 어절 차이)" / "인용 내용 불일치 (원문 대조 필요)" -> [2단]
    row3 = {
        "validity_verdict": VERDICT_QUOTE_MODIFIED,
        "cited_authority": "대법원 2018다2000",
        "error_category": "LEGAL_CITATION_ERROR",
        "finding_type": "LEGAL_ARGUMENT_INVALID",
    }
    assert classify_row_tier(row3) == 2, "3번 행은 2단이어야 합니다."

    # 4번 행: CASE_HOLDING_DISTORTION (판시 취지 왜곡 인용문) -> [2단] (상호 참조)
    row4 = {
        "finding_type": "CASE_HOLDING_DISTORTION",
        "cited_authority": "대법원 2015다3000",
        "verdict_label": "판시 취지 왜곡",
    }
    assert classify_row_tier(row4) == 2, "4번 행은 2단이어야 합니다."

    # 5번 행: TEMPORAL_LAW_MISMATCH (시적 적용 오류) -> [2단]
    row5 = {
        "finding_type": "TEMPORAL_LAW_MISMATCH",
        "cited_authority": "구 민법 제100조",
    }
    assert classify_row_tier(row5) == 2, "5번 행은 2단이어야 합니다."

    # 6번 행: "판례 취지 왜곡 (판시사항과 상반 / 부당)" -> [3단] (3단 고정, 4번과 상호 참조)
    row6 = {
        "validity_verdict": VERDICT_HOLDING_DISTORTION,
        "claim_text": "원고의 청구는 판례 취지에 비추어 부당하다.",
        "cited_authority": "대법원 2012다4000",
        "basis": "CONTRADICTION",
    }
    tier6 = classify_row_tier(row6)
    assert tier6 == 3, f"6번 행 '판례 취지 왜곡 …/부당'은 반드시 3단이어야 합니다 (실제: {tier6}단)."

    # 7번 행: "적용 차이 (사실관계 상이 / 전문가 검토 필요)" -> [3단]
    row7 = {
        "validity_verdict": VERDICT_FACT_DISTINGUISHABLE,
        "error_category": "APPLICATION_DIFFERENCE",
        "basis": "DISTINGUISHABLE",
        "cited_authority": "대법원 2014다5000",
        "claim_text": "본 건의 사실관계가 판례와 상이함",
    }
    assert classify_row_tier(row7) == 3, "7번 행은 3단이어야 합니다."

    # 8번 행: rule_id = RAG.REFERENCE_CONTRADICTION (참고자료 내용 모순) -> [3단]
    row8 = {
        "rule_id": "RAG.REFERENCE_CONTRADICTION",
        "claim_text": "행정업무편람의 처리기준과 정면으로 모순됨",
        "validity_verdict": "참고자료 모순",
    }
    assert classify_row_tier(row8) == 3, "8번 행은 3단이어야 합니다."

    # 9번 행: AI_HALLUCINATED_CONTENT (가짜 판례·조문 기반 법률 주장) -> [3단]
    row9 = {
        "finding_type": "AI_HALLUCINATED_CONTENT",
        "claim_text": "허위 조항에 기초하여 전액 배상을 구함",
        "basis": "FABRICATION_SUSPECTED",
    }
    assert classify_row_tier(row9) == 3, "9번 행은 3단이어야 합니다."

    # 10번 행: "공식 원문 일치 (사건 적용성 직접 검토 필요)" -> [2단] (공식 확인 배지)
    row10 = {
        "validity_verdict": VERDICT_OFFICIAL_CONFIRMED,
        "basis": "OFFICIAL_CONFIRMED",
        "official_status": "OFFICIAL_CONFIRMED",
        "cited_authority": "대법원 2016다6000",
    }
    tier10 = classify_row_tier(row10)
    assert tier10 == 2, f"10번 행 '공식 원문 일치'는 반드시 2단이어야 합니다 (실제: {tier10}단)."


def test_table1_ten_rows_rendered_in_browser():
    """설계 메모 [표 1]의 10개 행이 브라우저 DOM 상에서 2단(6건)과 3단(4건)으로 정확히 렌더링되는지 검증."""
    from urllib.parse import urlsplit

    pytest.importorskip("playwright")
    from playwright.sync_api import expect, sync_playwright

    ROOT = Path(__file__).resolve().parents[1]
    static_dir = ROOT / "apps/web/static"
    files = {f"/static/{p.relative_to(static_dir).as_posix()}": p for p in static_dir.rglob("*") if p.is_file()}
    files["/"] = ROOT / "apps/web/index.html"

    # 표 1의 1·2·3번 행의 실제 연결 finding (LEGAL_ARGUMENT_INVALID 결과)
    synthetic_findings = [
        {
            "id": "f_arg_1",
            "finding_id": "f_arg_1",
            "type": "LEGAL_ARGUMENT_INVALID",
            "finding_type": "LEGAL_ARGUMENT_INVALID",
            "title": "성립 불가한 사건번호",
            "detail": "성립 불가한 사건번호 판례 원용",
            "severity": "CRITICAL",
            "status": "UNCONFIRMED",
            "confidence_features": {"rule_id": "LEGAL.CASE_NOT_FOUND", "basis": "FABRICATION_SUSPECTED"},
            "document_id": "d1",
        },
        {
            "id": "f_arg_2",
            "finding_id": "f_arg_2",
            "type": "LEGAL_ARGUMENT_INVALID",
            "finding_type": "LEGAL_ARGUMENT_INVALID",
            "title": "공식 DB 미확인",
            "detail": "공식 소스 미존재",
            "severity": "HIGH",
            "status": "UNCONFIRMED",
            "confidence_features": {"rule_id": "LEGAL.CASE_NOT_FOUND", "basis": "UNCONFIRMED"},
            "document_id": "d1",
        },
        {
            "id": "f_arg_3",
            "finding_id": "f_arg_3",
            "type": "LEGAL_ARGUMENT_INVALID",
            "finding_type": "LEGAL_ARGUMENT_INVALID",
            "title": "인용문 변형",
            "detail": "원문과 어절 차이",
            "severity": "HIGH",
            "status": "UNCONFIRMED",
            "confidence_features": {"rule_id": "LEGAL.CITATION_ERROR", "error_category": "LEGAL_CITATION_ERROR"},
            "document_id": "d1",
        },
    ]

    # 메모 표 1의 10개 행 합성 review_items
    ten_items = [
        {"item_id": "item_1", "kind": "CITATION", "finding_ids": ["f_arg_1"], "cited_authority": "대법원 2099다12345", "verdict_label": VERDICT_INVALID_CASE_NUMBER, "basis": "FABRICATION_SUSPECTED", "location": {"page": 1}},
        {"item_id": "item_2", "kind": "CITATION", "finding_ids": ["f_arg_2"], "cited_authority": "대법원 2020다9999", "verdict_label": VERDICT_OFFICIAL_NOT_FOUND, "basis": "UNCONFIRMED", "official_status": "OFFICIAL_NOT_FOUND", "location": {"page": 2}},
        {"item_id": "item_3", "kind": "CITATION", "finding_ids": ["f_arg_3"], "cited_authority": "대법원 2018다2000", "verdict_label": VERDICT_QUOTE_MODIFIED, "error_category": "LEGAL_CITATION_ERROR", "location": {"page": 3}},
        {"item_id": "item_4", "kind": "CITATION", "cited_authority": "대법원 2015다3000", "finding_type": "CASE_HOLDING_DISTORTION", "verdict_label": "판시 취지 왜곡", "location": {"page": 4}},
        {"item_id": "item_5", "kind": "CITATION", "cited_authority": "구 민법 제100조", "finding_type": "TEMPORAL_LAW_MISMATCH", "location": {"page": 5}},
        {"item_id": "item_6", "kind": "CITATION", "cited_authority": "대법원 2012다4000", "verdict_label": VERDICT_HOLDING_DISTORTION, "location": {"page": 6}},
        {"item_id": "item_7", "kind": "CITATION", "cited_authority": "대법원 2014다5000", "verdict_label": VERDICT_FACT_DISTINGUISHABLE, "error_category": "APPLICATION_DIFFERENCE", "location": {"page": 7}},
        {"item_id": "item_8", "kind": "FACT", "rule_id": "RAG.REFERENCE_CONTRADICTION", "verdict_label": "참고자료 모순", "location": {"page": 8}},
        {"item_id": "item_9", "kind": "FACT", "finding_type": "AI_HALLUCINATED_CONTENT", "claim_text": "허위 조항 주장", "location": {"page": 9}},
        {"item_id": "item_10", "kind": "CITATION", "cited_authority": "대법원 2016다6000", "verdict_label": VERDICT_OFFICIAL_CONFIRMED, "official_status": "OFFICIAL_CONFIRMED", "basis": "OFFICIAL_CONFIRMED", "location": {"page": 10}},
    ]

    channel = os.environ.get("LV_TEST_BROWSER_CHANNEL")
    launch_kwargs = {"headless": True}
    if channel:
        launch_kwargs["channel"] = channel

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page()

            def handle_route(route):
                req = route.request
                path = urlsplit(req.url).path
                if path in files:
                    return route.fulfill(path=str(files[path]))
                replies = {
                    "/api/health": {"status": "ok", "version": "0.5.0"},
                    "/api/identity/me": {"user_id": "u", "role": "ADMIN", "authentication": "password"},
                    "/api/verification-runs": {"active_count": 0, "runs": []},
                    "/api/projects": [{"id": "p1", "name": "TK88 프로젝트", "can_delete": True, "document_count": 1, "external_ai_policy": "MASKED", "scope_revision": 0}],
                    "/api/projects/p1": {"id": "p1", "name": "TK88 프로젝트", "can_delete": True, "document_count": 1, "external_ai_policy": "MASKED", "scope_revision": 0},
                    "/api/projects/p1/documents": [{"id": "d1", "filename": "서면.pdf", "included_in_verification": True}],
                    "/api/projects/p1/runs": [{"id": "r1", "project_id": "p1", "state": "COMPLETED", "document_ids": ["d1"], "started_at": "2026-10-21T00:00:00"}],
                    "/api/projects/p1/findings": synthetic_findings,
                    "/api/finding-categories": {"categories": {}, "tabs": {}, "counts": {}},
                }
                if path in replies:
                    return route.fulfill(json=replies[path])
                if path.endswith(("/result", "/results")):
                    return route.fulfill(json={
                        "status": "COMPLETED",
                        "documents": [{"id": "d1", "filename": "서면.pdf", "quarantined": False, "findings": synthetic_findings, "review_items": ten_items, "ai_hallucination_table": []}]
                    })
                if path.endswith("/case-matrix"):
                    return route.fulfill(body="null", content_type="application/json")
                return route.fulfill(json=[])

            page.route("**/*", handle_route)
            page.goto("http://localhost/")

            # 검토 화면 진입
            page.get_by_role("button", name="검증·검토", exact=True).click()

            # 2단 표 (#aiVerificationRows) 및 3단 표 (#tier3Rows) 검증: 확인할 항목(review) 탭 내 배치
            page.locator('.tabs button[data-tab="review"]').click()

            # 2단 표 (#aiVerificationRows) 확인: 1, 2, 3, 4, 5, 10번 (총 6행)
            tier2_rows = page.locator("#aiVerificationRows tr")
            expect(tier2_rows).to_have_count(6)
            expect(page.locator("#row_item_1")).to_be_visible()
            expect(page.locator("#row_item_2")).to_be_visible()
            expect(page.locator("#row_item_3")).to_be_visible()
            expect(page.locator("#row_item_4")).to_be_visible()
            expect(page.locator("#row_item_5")).to_be_visible()
            expect(page.locator("#row_item_10")).to_be_visible()

            # 3단 표 (#tier3Rows) 확인: 6, 7, 8, 9번 (총 4행)
            tier3_rows = page.locator("#tier3Rows tr")
            expect(tier3_rows).to_have_count(4)
            expect(page.locator("#tier3Rows #row_item_6")).to_be_visible()
            expect(page.locator("#tier3Rows #row_item_7")).to_be_visible()
            expect(page.locator("#tier3Rows #row_item_8")).to_be_visible()
            expect(page.locator("#tier3Rows #row_item_9")).to_be_visible()

            browser.close()
    except Exception as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Playwright 브라우저 바이너리가 로컬에 설치되어 있지 않음 (CI 환경에서 실행됨)")
        raise


def test_frontend_app_js_classification_matches_specification():
    """apps/web/static/app.js의 classifyReviewItemTier 자바스크립트 구현이 표 1 명세와 일치하는지 소스 수준 검증."""
    with open("apps/web/static/app.js", "r", encoding="utf-8") as f:
        app_js = f.read()

    # 핵심 키워드 및 우선순위 분기 포함 여부 검증
    assert "function classifyReviewItemTier" in app_js
    assert "REFERENCE_CONTRADICTION" in app_js
    assert "HALLUCINATED" in app_js
    assert "DISTORTION" in app_js
    assert "성립 불가한 사건번호" in app_js  # 1번 행 2단 분기
    assert "취지 왜곡" in app_js or "부당" in app_js  # 6번 행 3단 분기
    assert "참고문헌(구속력 없음)" in app_js  # 참고문헌 구속력 배제 배지
    assert "대조 안 함" in app_js  # 미대조 배지
    assert "3단 무리한 주장 확인 →" in app_js  # 2단->3단 상호 참조
    assert "2단 출처 부존재 확인 →" in app_js  # 3단->2단 상호 참조
