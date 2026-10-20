# -*- coding: utf-8 -*-
"""TK-94 출처 미확인 판례·법령 외부 법률 AI/엘박스 검증 프롬프트 생성 기능 테스트.

수용 기준:
1. app.js 내 클립보드 복사 헬퍼(copyToClipboard) 및 프롬프트 생성 함수 구비.
2. 단건 및 일괄 프롬프트 템플릿에 역할, 인용 정보, 주장 요지, 4대 검증 항목, 개인정보 주의 문구 포함.
3. 4열 통합 검토 표(tdClaim) 및 미확인 요약(hallucinationSummary, unverifiedScopeContainer)에 복사 버튼 바인딩.
4. styles.css에 전용 버튼 스타일 구비.
"""
from __future__ import annotations

import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "apps" / "web" / "static" / "app.js"
STYLES_CSS = ROOT / "apps" / "web" / "static" / "styles.css"


def test_app_js_external_ai_prompt_functions_exist():
    """app.js에 프롬프트 생성 및 클립보드 복사 헬퍼가 정의되어 있어야 함."""
    content = APP_JS.read_text(encoding="utf-8")

    assert "function copyToClipboard(" in content or "async function copyToClipboard(" in content
    assert "function buildExternalAiPromptForCitation(" in content
    assert "function buildBatchExternalAiPrompt(" in content


def test_single_prompt_template_structure():
    """단건 검증 프롬프트 템플릿 필수 문구 검증."""
    content = APP_JS.read_text(encoding="utf-8")

    # 1. 역할 정의
    assert "대한민국 법률 및 판례 검증 전문 법률 비서 AI" in content

    # 2. 필수 검증 항목
    assert "판례/법령 실재 여부" in content
    assert "판시사항 부합 여부" in content
    assert "대체/반박 리딩 판례" in content

    # 3. 개인정보 보호 주의 문구
    assert "외부 AI 도구 입력 전 당사자 개인정보" in content


def test_batch_prompt_template_structure():
    """다건 일괄 검증 프롬프트 템플릿 필수 문구 검증."""
    content = APP_JS.read_text(encoding="utf-8")

    assert "공식 DB에서 출처가 확인되지 않은" in content
    assert "검증 대상 목록" in content
    assert "각 항목별로 다음 내용을 일목요연하게" in content
    assert "외부 AI 도구 입력 전 당사자 개인정보" in content


def test_buttons_bound_in_ui():
    """UI 요소(4열 표 2열, 판례 요약, 미확인 범위)에 복사 버튼이 정상 바인딩되어 있어야 함."""
    content = APP_JS.read_text(encoding="utf-8")

    # 1. 4열 표의 인용 항목(tdClaim) 단건 복사 버튼
    assert "external-ai-prompt-btn" in content
    assert "📋 엘박스/AI 검증 프롬프트" in content

    # 2. 판례 요약(hallucinationSummary) 일괄 복사 버튼
    assert "📋 미확인 판례 일괄 검증 프롬프트 복사" in content

    # 3. 미확인 범위(unverifiedScopeContainer) 일괄 복사 버튼
    assert "📋 미확인 항목 전체 검증 프롬프트 복사" in content


def test_styles_css_classes_defined():
    """styles.css에 전용 버튼 스타일 클래스가 정의되어 있어야 함."""
    content = STYLES_CSS.read_text(encoding="utf-8")

    assert ".external-ai-prompt-btn" in content
    assert ".external-ai-batch-btn" in content
