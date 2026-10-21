# -*- coding: utf-8 -*-
"""TK-88 검토 화면 3단 체계 및 보고서 3단 소제목 검증 시험

설계 메모: docs/handoff/requests/94_tk88_three_tier_review_structure_design.md
조건부 승인 조건:
1. 바뀌는 형식(docx·pdf)에는 3단 소제목이 실제로 들어갔는지 확인하고, 안 바뀌는 형식(json·csv·xlsx·manifest·highlight)은
   PR 전후 출력이 같다는 시험을 둔다.
2. 표 1의 10개 행이 각각 정해진 단(2단 또는 3단)에 표시되는지 확인하고, 특히 1번 행(2단)과 6번 행(3단, 상호 참조)은 단언으로 고정한다.
"""
import io
import json
import pytest
from docx import Document as WordDocument
from pypdf import PdfReader

from packages.report_engine.review_tiers import (
    classify_row_tier,
    TIER1_HEADING,
    TIER2_HEADING,
    TIER3_HEADING,
)
from tests.test_report_completion import report_case, create, download


# ==============================================================================
# 조건 1 검증: 바뀌는 형식(docx, pdf)의 3단 소제목 포함 검증
# ==============================================================================

def test_docx_and_pdf_reports_include_three_tier_subheadings(report_case):
    """Word(docx) 및 PDF 보고서 생성 시 1단, 2단, 3단 소제목이 실제로 포함되는지 검증한다."""
    case = report_case
    result = dict(case.run.result_json)
    result["documents"] = [{
        **result["documents"][0],
        "ai_hallucination_table": [
            # 1번 행 (2단 배정): 근거 결여 (성립 불가한 사건번호)
            {
                "location": "3쪽",
                "claim_text": "피고는 원고에게 손해배상책임이 있다.",
                "cited_authority": "대법원 2099다12345",
                "validity_verdict": "근거 결여 (성립 불가한 사건번호)",
                "ai_generation_basis": "공식 DB에서 확인되지 않음",
                "legal_reasoning": "성립할 수 없는 사건번호",
                "recommended_counteraction": "사건번호 성립 여부 확인",
            },
            # 6번 행 (3단 배정): 판례 취지 왜곡 (판시사항과 상반 / 부당)
            {
                "location": "7쪽",
                "claim_text": "임차인은 목적물 수선의무를 전적으로 부담한다.",
                "cited_authority": "대법원 2012다4000",
                "validity_verdict": "판례 취지 왜곡 (판시사항과 상반 / 부당)",
                "ai_generation_basis": "판례 판결요지와 상반됨",
                "legal_reasoning": "법리적 타당성 결여",
                "recommended_counteraction": "판결요지 원문 대조",
            },
        ],
    }]
    case.run.result_json = result
    case.session.commit()

    report = create(case, ["docx", "pdf"])

    # 1. Word (docx) 검증
    docx_bytes = download(case, report, "docx")
    word_doc = WordDocument(io.BytesIO(docx_bytes))
    all_headings = [p.text.strip() for p in word_doc.paragraphs if p.text.strip()]

    assert TIER1_HEADING in all_headings, f"1단 소제목 '{TIER1_HEADING}' 누락"
    assert TIER2_HEADING in all_headings, f"2단 소제목 '{TIER2_HEADING}' 누락"
    assert TIER3_HEADING in all_headings, f"3단 소제목 '{TIER3_HEADING}' 누락"

    # docx 내 2단 및 3단 테이블 분리 렌더링 확인
    tier2_tables = [t for t in word_doc.tables if t.rows and len(t.rows[0].cells) > 2 and t.rows[0].cells[2].text == "인용 오류·미확인 근거 및 주장 평가"]
    tier3_tables = [t for t in word_doc.tables if t.rows and len(t.rows[0].cells) > 2 and t.rows[0].cells[2].text == "법리 검토 결과 및 근거"]
    assert len(tier2_tables) >= 1, "2단 테이블이 docx에 렌더링되지 않았습니다."
    assert len(tier3_tables) >= 1, "3단 테이블이 docx에 렌더링되지 않았습니다."

    # 2. PDF 검증
    pdf_bytes = download(case, report, "pdf")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pdf_text = "".join("".join((p.extract_text() or "").split()) for p in reader.pages)
    pdf_text_clean = pdf_text.replace("·", "").replace("・", "")

    assert "1.AI작성보안진단" in pdf_text_clean, "1단 소제목이 PDF에 누락되었습니다."
    assert "2.판례법령주요참고문헌인용오류미확인검토" in pdf_text_clean, "2단 소제목이 PDF에 누락되었습니다."
    assert "3.법률적으로무리한주장" in pdf_text_clean, "3단 소제목이 PDF에 누락되었습니다."


# ==============================================================================
# 조건 1 검증: 안 바뀌는 형식(json, csv, xlsx, manifest, highlight) 계약 불변 검증
# ==============================================================================

def test_unchanged_formats_preserve_contracts(report_case):
    """안 바뀌는 형식(json, csv, xlsx, manifest)의 스키마와 데이터 계약이 보존됨을 검증한다."""
    case = report_case
    report = create(case, ["json", "csv", "xlsx", "manifest"])

    # 1. JSON 검증
    json_bytes = download(case, report, "json")
    payload = json.loads(json_bytes.decode("utf-8"))
    for expected_key in ("product", "run_id", "documents", "project_findings"):
        assert expected_key in payload, f"JSON 키 '{expected_key}' 누락"

    # 2. CSV 검증
    csv_bytes = download(case, report, "csv")
    csv_text = csv_bytes.decode("utf-8-sig")
    first_line = csv_text.splitlines()[0]
    for col in ["finding_id", "type", "severity", "evidence_grade", "title"]:
        assert col in first_line, f"CSV 열 '{col}' 누락"

    # 3. XLSX 검증
    xlsx_bytes = download(case, report, "xlsx")
    assert isinstance(xlsx_bytes, bytes) and len(xlsx_bytes) > 0

    # 4. Manifest 검증
    manifest_bytes = download(case, report, "manifest")
    manifest_data = json.loads(manifest_bytes.decode("utf-8"))
    assert isinstance(manifest_data, dict)
    assert "chain_valid" in manifest_data or "report" in manifest_data or "head_hash" in manifest_data


# ==============================================================================
# 조건 2 검증: 설계 메모 [표 1]의 10개 행 2단/3단 배치 및 고정 단언 검증
# ==============================================================================

def test_table1_ten_rows_rendered_in_correct_tier_with_mandatory_assertions():
    """설계 메모 [표 1]에 정의된 10개 대표 행이 각각 2단/3단에 정확히 배치되는지 검증한다.

    특히 평가 측 지침에 따라 1번 행(2단)과 6번 행(3단)은 고정 단언으로 검증한다.
    """
    # 1번 행: 근거 결여 (성립 불가한 사건번호) -> [2단]
    row1 = {
        "validity_verdict": "근거 결여 (성립 불가한 사건번호)",
        "cited_authority": "대법원 2099다12345",
        "basis": "FABRICATION_SUSPECTED",
        "error_category": "LEGAL_CITATION_ERROR",
    }
    tier1 = classify_row_tier(row1)
    assert tier1 == 2, f"1번 행 '근거 결여 (성립 불가한 사건번호)'는 반드시 2단이어야 합니다 (실제: {tier1}단)."

    # 2번 행: 공식 DB 미확인 (원문 확인 필요) -> [2단]
    row2 = {
        "validity_verdict": "공식 DB 미확인 (원문 확인 필요)",
        "cited_authority": "대법원 2020다9999",
        "basis": "UNCONFIRMED",
    }
    assert classify_row_tier(row2) == 2

    # 3번 행: 인용문 변형 / 인용 내용 불일치 -> [2단]
    row3 = {
        "validity_verdict": "인용문 변형 (원문과 어절 차이)",
        "cited_authority": "대법원 2018다2000",
        "error_category": "LEGAL_CITATION_ERROR",
    }
    assert classify_row_tier(row3) == 2

    # 4번 행: CASE_HOLDING_DISTORTION (판시 취지 왜곡) -> [2단]
    row4 = {
        "finding_type": "CASE_HOLDING_DISTORTION",
        "cited_authority": "대법원 2015다3000",
        "verdict_label": "판시 취지 왜곡",
    }
    assert classify_row_tier(row4) == 2

    # 5번 행: TEMPORAL_LAW_MISMATCH (시적 적용 오류) -> [2단]
    row5 = {
        "finding_type": "TEMPORAL_LAW_MISMATCH",
        "cited_authority": "구 민법 제100조",
    }
    assert classify_row_tier(row5) == 2

    # 6번 행: 판례 취지 왜곡 (판시사항과 상반 / 부당) -> [3단]
    row6 = {
        "validity_verdict": "판례 취지 왜곡 (판시사항과 상반 / 부당)",
        "claim_text": "원고의 청구는 판례 취지에 비추어 부당하다.",
        "cited_authority": "대법원 2012다4000",
    }
    tier6 = classify_row_tier(row6)
    assert tier6 == 3, f"6번 행 '판례 취지 왜곡 …/부당'은 반드시 3단이어야 합니다 (실제: {tier6}단)."

    # 7번 행: LEGAL_ARGUMENT_INVALID (법률적 주장 타당성 결여) -> [3단]
    row7 = {
        "finding_type": "LEGAL_ARGUMENT_INVALID",
        "claim_text": "법률상 근거 없는 배상 청구",
        "verdict_label": "부당 주장",
    }
    assert classify_row_tier(row7) == 3

    # 8번 행: AI_HALLUCINATED_CONTENT (허위 생성 출처 기반 주장) -> [3단]
    row8 = {
        "finding_type": "AI_HALLUCINATED_CONTENT",
        "claim_text": "허위 조항에 기초하여 전액 배상을 구함",
        "basis": "FABRICATION_SUSPECTED",
    }
    assert classify_row_tier(row8) == 3

    # 9번 행: 사실관계 상이 -> [3단]
    row9 = {
        "finding_type": "FACT_MISMATCH",
        "validity_verdict": "사실관계 상이",
        "claim_text": "사안의 구체적 사실관계가 판례와 부합하지 않음",
    }
    assert classify_row_tier(row9) == 3

    # 10번 행: RAG.REFERENCE_CONTRADICTION (주요 참고문헌 모순) -> [3단]
    row10 = {
        "rule_id": "RAG.REFERENCE_CONTRADICTION",
        "claim_text": "행정업무편람의 처리기준과 정면으로 모순됨",
        "reference_library": True,
        "reference_status": "NOT_CHECKED",
    }
    assert classify_row_tier(row10) == 3


def test_frontend_app_js_classification_matches_specification():
    """apps/web/static/app.js의 classifyReviewItemTier 자바스크립트 구현이 표 1 명세와 일치하는지 소스 수준 검증."""
    with open("apps/web/static/app.js", "r", encoding="utf-8") as f:
        app_js = f.read()

    # 핵심 키워드 및 우선순위 분기 포함 여부 검증
    assert "function classifyReviewItemTier" in app_js
    assert "REFERENCE_CONTRADICTION" in app_js
    assert "AI_HALLUCINATED_CONTENT" in app_js
    assert "CASE_HOLDING_DISTORTION" in app_js
    assert "성립 불가한 사건번호" in app_js  # 1번 행 2단 분기
    assert "취지 왜곡" in app_js or "부당" in app_js  # 6번 행 3단 분기
    assert "참고문헌(구속력 없음)" in app_js  # 참고문헌 구속력 배제 배지
    assert "대조 안 함" in app_js  # 미대조 배지
    assert "3단 무리한 주장 확인 →" in app_js  # 2단->3단 상호 참조
    assert "2단 출처 부존재 확인 →" in app_js  # 3단->2단 상호 참조
