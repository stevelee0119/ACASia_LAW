# -*- coding: utf-8 -*-
"""TK-94 출처 미확인 판례·법령 외부 법률 AI/엘박스 일괄 검증 프롬프트 생성 기능 테스트.

수용 기준:
1. app.js 내 클립보드 복사 헬퍼(copyToClipboard), 복사 실패 시 fallback 대화상자(showCopyFallbackDialog), 일괄 프롬프트 생성 함수(buildExternalAiPromptForUnverifiedAuthorities) 구비.
2. 행동 시험: 프롬프트에 당사자 개인정보(성명, 전화번호, 주소) 및 본문 주장 문맥(claim_text)이 일체 배제되고, 인용 식별자(사건번호/법령명)만 목록화됨.
3. 행동 시험: 필터 경계가 official_status in ('OFFICIAL_NOT_FOUND', 'UNVERIFIED_SCOPE') 기준으로 엄격히 동작하며, 공식 원문 확인 항목은 배제됨.
4. 행동 시험: 프롬프트 및 UI에 '외부 AI 답변은 공식 확인이 아님' 고지 문구 필수 포함.
5. 행동 시험: LOCAL_ONLY 정책 시 외부 전송 버튼 숨김 처리.
6. 개별 행 버튼이나 요약 배너 버튼을 배제하고, 미확인 판례/법령 표 하단부(reviewTableActions)에 단일 [📋 엘박스/AI 검증 프롬프트] 버튼 배치.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "apps" / "web" / "index.html"
APP_JS = ROOT / "apps" / "web" / "static" / "app.js"
STYLES_CSS = ROOT / "apps" / "web" / "static" / "styles.css"


def _extract_js_filter_function() -> str:
    content = APP_JS.read_text(encoding="utf-8")
    m = re.search(r"(function filterUnverifiedAuthorities\([\s\S]+?\n\})", content)
    assert m, "filterUnverifiedAuthorities function definition not found in app.js"
    return m.group(1)


def _extract_js_mask_function() -> str:
    content = APP_JS.read_text(encoding="utf-8")
    m = re.search(r"(function maskAuthorityIdentifier\([\s\S]+?\n\})", content)
    assert m, "maskAuthorityIdentifier function definition not found in app.js"
    return m.group(1)


def _extract_js_prompt_function() -> str:
    content = APP_JS.read_text(encoding="utf-8")
    m = re.search(r"(function buildExternalAiPromptForUnverifiedAuthorities\([\s\S]+?\n\})", content)
    assert m, "buildExternalAiPromptForUnverifiedAuthorities function definition not found in app.js"
    return m.group(1)


def test_index_html_has_review_table_actions():
    """index.html에 검토 표 하단 액션 컨테이너(reviewTableActions)가 구비되어 있어야 함."""
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert '<div id="reviewTableActions" class="review-table-actions"' in content


def test_app_js_external_ai_prompt_function_and_fallback():
    """app.js에 단일화된 일괄 프롬프트 생성 함수, 필터 분리 함수, 클립보드 복사 헬퍼 및 fallback 대화상자가 정의되어 있어야 함."""
    content = APP_JS.read_text(encoding="utf-8")

    assert "async function copyToClipboard(" in content
    assert "function showCopyFallbackDialog(" in content
    assert "function filterUnverifiedAuthorities(" in content
    assert "function buildExternalAiPromptForUnverifiedAuthorities(" in content
    assert "copyFallbackDialog" in content


def test_behavior_prompt_generation_masked_policy_excludes_pii_and_claim_text():
    """행동 시험 (MASKED 정책): 가짜 함수 없이 실제 app.js 함수로 인용 식별자 속 당사자명/괄호 부기 및 claim_text가 실제 제거됨을 검증."""
    mask_fn_code = _extract_js_mask_function()
    prompt_fn_code = _extract_js_prompt_function()

    runner_script = f"""
{mask_fn_code}
{prompt_fn_code}

const sampleItems = [
  {{
    cited_authority: "대법원 2021다12345 판결 (홍길동 관련)",
    claim_text: "원고 홍길동(010-9876-5432, 서울 강남구 테헤란로 123)은 피고에게 5천만원을 대여하였다고 주장",
    verdict_label: "공식 DB 미확인 (원문 확인 필요)",
    official_status: "OFFICIAL_NOT_FOUND"
  }},
  {{
    cited_authority: "민법 제398조 제2항 (원고 김철수 손해배상 사건)",
    claim_text: "피고 주식회사 갑을(대표이사 이몽룡, 주민등록번호 750101-1234567)의 손해배상 예정액 감액 주장",
    verdict_label: "공식 DB 미확인",
    official_status: "OFFICIAL_NOT_FOUND"
  }}
];

const result = buildExternalAiPromptForUnverifiedAuthorities(sampleItems, "2023-05-10", "MASKED");
process.stdout.write(JSON.stringify(result));
"""
    proc = subprocess.run(["node"], input=runner_script.encode("utf-8"), capture_output=True, check=True)
    generated_prompt = json.loads(proc.stdout.decode("utf-8"))

    # 1. 인용 식별자의 본체는 포함되어 있어야 함
    assert "대법원 2021다12345 판결" in generated_prompt
    assert "민법 제398조 제2항" in generated_prompt

    # 2. 식별자 내부의 괄호 부기 및 인명은 MASKED 정책에 따라 실제 제거되어야 함
    assert "홍길동" not in generated_prompt
    assert "(홍길동 관련)" not in generated_prompt
    assert "김철수" not in generated_prompt
    assert "(원고 김철수 손해배상 사건)" not in generated_prompt

    # 3. 본문 문맥(claim_text) 및 개인정보(전화번호, 주소, 주민등록번호, 대표자명, 주장 내용)는 100% 배제
    assert "010-9876-5432" not in generated_prompt
    assert "테헤란로" not in generated_prompt
    assert "이몽룡" not in generated_prompt
    assert "750101-1234567" not in generated_prompt
    assert "대여하였다고 주장" not in generated_prompt


def test_behavior_prompt_generation_original_policy_preserves_authority_but_excludes_claim_text():
    """행동 시험 (ORIGINAL 정책): 가짜 함수 없이 실제 app.js 함수로 식별자 원본은 보존되되 claim_text는 배제됨을 검증."""
    mask_fn_code = _extract_js_mask_function()
    prompt_fn_code = _extract_js_prompt_function()

    runner_script = f"""
{mask_fn_code}
{prompt_fn_code}

const sampleItems = [
  {{
    cited_authority: "대법원 2021다12345 판결 (홍길동 관련)",
    claim_text: "원고 홍길동(010-9876-5432, 서울 강남구 테헤란로 123)은 피고에게 5천만원을 대여하였다고 주장",
    verdict_label: "공식 DB 미확인 (원문 확인 필요)",
    official_status: "OFFICIAL_NOT_FOUND"
  }}
];

const result = buildExternalAiPromptForUnverifiedAuthorities(sampleItems, "2023-05-10", "ORIGINAL");
process.stdout.write(JSON.stringify(result));
"""
    proc = subprocess.run(["node"], input=runner_script.encode("utf-8"), capture_output=True, check=True)
    generated_prompt = json.loads(proc.stdout.decode("utf-8"))

    # ORIGINAL 정책에서는 괄호 부기를 포함한 원본 식별자가 그대로 보존됨
    assert "대법원 2021다12345 판결 (홍길동 관련)" in generated_prompt

    # 그러나 claim_text 본문 문맥(전화번호, 주소, 주장 문구)은 여전히 프롬프트에 들어가지 않음
    assert "010-9876-5432" not in generated_prompt
    assert "테헤란로" not in generated_prompt
    assert "대여하였다고 주장" not in generated_prompt


def test_behavior_prompt_includes_official_notice():
    """행동 시험: 외부 AI 답변은 공식 확인이 아니라는 필수 고지 문구가 프롬프트에 포함되어야 함."""
    mask_fn_code = _extract_js_mask_function()
    prompt_fn_code = _extract_js_prompt_function()

    runner_script = f"""
{mask_fn_code}
{prompt_fn_code}

const sampleItems = [{{ cited_authority: "대법원 2018다99999 판결" }}];
const result = buildExternalAiPromptForUnverifiedAuthorities(sampleItems, "2024-01-01");
process.stdout.write(JSON.stringify(result));
"""
    proc = subprocess.run(["node"], input=runner_script.encode("utf-8"), capture_output=True, check=True)
    generated_prompt = json.loads(proc.stdout.decode("utf-8"))

    assert "외부 AI 답변은 법적 효력이 있는 공식 확인이 아니며" in generated_prompt
    assert "법원 판결서 사본 또는 국가법령정보센터 공식 원문으로 반드시 확인" in generated_prompt


def test_behavior_filter_boundary_official_status():
    """행동 시험: app.js의 실제 filterUnverifiedAuthorities 함수를 실행하여 official_status in ('OFFICIAL_NOT_FOUND', 'UNVERIFIED_SCOPE')만 엄격히 수집하는지 검증."""
    filter_fn_code = _extract_js_filter_function()

    runner_script = f"""
{filter_fn_code}

const filteredItems = [
  {{ cited_authority: "대법원 2020다1111 판결", official_status: "OFFICIAL_NOT_FOUND", verdict_label: "공식 DB 미확인" }},
  {{ cited_authority: "상가임대차보호법 제10조의4", official_status: "UNVERIFIED_SCOPE", verdict_label: "미확인 범위" }},
  // 공식 확인된 항목은 '부당', '왜곡' 라벨이 붙어있더라도 필터에서 반드시 제외되어야 함
  {{ cited_authority: "대법원 2015다2222 판결", official_status: "OFFICIAL_CONFIRMED", verdict_label: "판례 취지 왜곡 (부당)" }},
  {{ cited_authority: "민법 제565조", official_status: "OFFICIAL_CONFIRMED", verdict_label: "공식 원문 일치" }},
  // cited_authority가 없는 항목은 제외
  {{ cited_authority: "", official_status: "OFFICIAL_NOT_FOUND", verdict_label: "미확인" }}
];

// app.js에서 추출한 실제 함수 실행
const unverifiedAuthorities = filterUnverifiedAuthorities(filteredItems);

process.stdout.write(JSON.stringify(unverifiedAuthorities.map(it => it.cited_authority)));
"""
    proc = subprocess.run(["node"], input=runner_script.encode("utf-8"), capture_output=True, check=True)
    collected_authorities = json.loads(proc.stdout.decode("utf-8"))

    # OFFICIAL_NOT_FOUND와 UNVERIFIED_SCOPE만 수집
    assert "대법원 2020다1111 판결" in collected_authorities
    assert "상가임대차보호법 제10조의4" in collected_authorities

    # OFFICIAL_CONFIRMED(취지 왜곡/부당 포함) 및 빈 값은 엄격히 제외
    assert "대법원 2015다2222 판결" not in collected_authorities
    assert "민법 제565조" not in collected_authorities
    assert len(collected_authorities) == 2


def test_behavior_local_only_policy_hides_button():
    """행동 시험: external_ai_policy가 LOCAL_ONLY일 경우 버튼 컨테이너가 hidden 처리되어야 함."""
    content = APP_JS.read_text(encoding="utf-8")

    assert 'const policy = state.project?.external_ai_policy || "LOCAL_ONLY";' in content
    assert 'if (policy === "LOCAL_ONLY") {' in content
    assert "tableActions.hidden = true;" in content


def test_single_button_bound_at_table_bottom_without_row_duplicates():
    """미확인 판례/법령 표 하단부에 단일 버튼으로 바인딩되고, 개별 행이나 배너의 중복 버튼은 없어야 함."""
    content = APP_JS.read_text(encoding="utf-8")

    # 표 하단부 reviewTableActions에 버튼 바인딩 확인
    assert '$("reviewTableActions")' in content
    assert 'button("📋 엘박스/AI 검증 프롬프트"' in content
    assert "buildExternalAiPromptForUnverifiedAuthorities(" in content

    # 개별 행(tdClaim) 및 요약 배너에는 프롬프트 버튼이 없어야 함 (단일화)
    assert 'tdClaim.append(promptBtn);' not in content
    assert 'summary.append(batchBtn);' not in content


def test_styles_css_classes_defined():
    """styles.css에 review-table-actions, external-ai-prompt-btn, copy-fallback 클래스가 정의되어 있어야 함."""
    content = STYLES_CSS.read_text(encoding="utf-8")

    assert ".review-table-actions" in content
    assert ".external-ai-prompt-btn" in content
    assert ".review-prompt-notice" in content
    assert ".copy-fallback-dialog" in content
    assert ".copy-fallback-textarea" in content
