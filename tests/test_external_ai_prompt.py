# -*- coding: utf-8 -*-
"""TK-94 출처 미확인 판례·법령 외부 법률 AI/엘박스 일괄 검증 프롬프트 생성 기능 테스트.

수용 기준:
1. app.js 내 클립보드 복사 헬퍼(copyToClipboard) 및 일괄 프롬프트 생성 함수(buildExternalAiPromptForUnverifiedAuthorities) 구비.
2. 프롬프트에 당사자 개인정보 및 불필요한 개인정보 주의 안내문구를 일체 배제하고, 순수 판례/법령 목록 및 3대 검증 요청 사항(실재 여부, 판시사항 부합 여부, 대체 판례)으로 정갈하게 구성.
3. 개별 행 버튼이나 요약 배너 버튼을 배제하고, 미확인 판례/법령 표 하단부(reviewTableActions)에 단일 [📋 엘박스/AI 검증 프롬프트] 버튼 배치.
4. index.html에 reviewTableActions 컨테이너 구비 및 styles.css에 전용 스타일 정의.
"""
from __future__ import annotations

from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "apps" / "web" / "index.html"
APP_JS = ROOT / "apps" / "web" / "static" / "app.js"
STYLES_CSS = ROOT / "apps" / "web" / "static" / "styles.css"


def test_index_html_has_review_table_actions():
    """index.html에 검토 표 하단 액션 컨테이너(reviewTableActions)가 구비되어 있어야 함."""
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert '<div id="reviewTableActions" class="review-table-actions"' in content


def test_app_js_external_ai_prompt_function():
    """app.js에 단일화된 일괄 프롬프트 생성 함수 및 클립보드 복사 헬퍼가 정의되어 있어야 함."""
    content = APP_JS.read_text(encoding="utf-8")

    assert "async function copyToClipboard(" in content
    assert "function buildExternalAiPromptForUnverifiedAuthorities(" in content


def test_prompt_template_excludes_pii_and_has_legal_core():
    """프롬프트 템플릿에 당사자 개인정보 안내 문구가 배제되고, 핵심 법률 검증 요구사항이 포함되어야 함."""
    content = APP_JS.read_text(encoding="utf-8")

    # 1. 개인정보 관련 불필요한 사족 안내문 배제 검증
    assert "외부 AI 도구 입력 전 당사자 개인정보" not in content

    # 2. 핵심 역할 및 3대 법률 검증 요구사항 검증
    assert "대한민국 법률 및 판례 검증 전문 AI" in content
    assert "실재 여부: 실제 존재하는 판례/법령인가?" in content
    assert "판시사항 부합 여부: 서면에서 주장하는 법리가 실제 판례의 판시사항/판결요지와 일치하는가" in content
    assert "대체/반박 판례: 해당 주장을 뒷받침하거나 반박할 수 있는 실제 대법원 판례" in content
    assert "종합 검증 결과 요약 표" in content


def test_single_button_bound_at_table_bottom():
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
    """styles.css에 review-table-actions 및 external-ai-prompt-btn 클래스가 정의되어 있어야 함."""
    content = STYLES_CSS.read_text(encoding="utf-8")

    assert ".review-table-actions" in content
    assert ".external-ai-prompt-btn" in content
