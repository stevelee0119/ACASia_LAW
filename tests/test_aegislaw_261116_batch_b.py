# -*- coding: utf-8 -*-
"""261116 AegisLAW 개선 배치 B(항목 1·2) 회귀·일반화 시험.

항목 1: AI 작성 주체 검토 범위(규칙 전수 검사 글자 수 vs 외부 AI 모델 검토 글자 수 분리 표시)
항목 2: PII 마스킹 멱등성·경계 보완(가명 토큰 인접 날짜, 슬래시 다중 전화번호, ISO 날짜 범위)
모든 사건·문구·식별자는 합성 데이터만 사용한다.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
from frontend_helpers import select_first_project

from packages.common.enums import ExternalAIPolicy, LLMRole
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.common.source_trace import model_input_renderer
from packages.legal_engine.evidence_pack import project_masked
from packages.llm_router import router as router_module
from packages.llm_router.budget import BudgetLedger
from packages.llm_router.input_contracts import valid_input_contract
from packages.llm_router.privacy import inspect_request
from packages.llm_router.providers import LLMRequest, LLMResponse
from packages.pii_engine import engine as engine_mod
from packages.pii_engine.detector import PIIMatch, detect
from packages.pii_engine.engine import PIIEngine
from packages.pii_engine.pseudonym import PseudonymStore
from packages.verification_engine.ai_document_detector import detect_ai_document

ROOT = Path(__file__).resolve().parents[1]


def _doc(text: str, doc_id: str = "doc-batch-b") -> NormalizedDocument:
    doc = NormalizedDocument(
        document_id=doc_id,
        filename="합성준비서면.pdf",
        mime_type="application/pdf",
        sha256="batchbtestsha",
        pages=[Page(page_number=1, blocks=[Block(block_id="b1", text=text, page=1, source_layer="visible_text")])],
    )
    doc.raw_layers["visible_text"] = text
    return doc


# ---------------------------------------------------------------------------
# 양성 1: 가명 토큰 인접 숫자/괄호, 슬래시 다중 전화번호, ISO 날짜 범위 + 멱등성/트레이스
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "sample",
    [
        "피고 강민호(19800101-1234567)와 원고 이수진[1980-01-01]의 약정",
        "연락처: 010-2468-1357 / 02-123-4567, 팩스 010-1111-2222 ~ 02-345-6789",
        "이행 기간: 2024-01-01 ~ 2024-12-31 (정산 기준일: 2025-03-15)",
    ],
)
def test_masked_adjacent_numbers_slash_phones_and_iso_ranges_are_idempotent(tmp_path, sample):
    engine = PIIEngine(PseudonymStore("batch_b_1", root=tmp_path))
    first = engine.mask_text(sample)
    second = engine.mask_text(first.masked_text)

    assert second.masked_text == first.masked_text
    assert [m for m in detect(first.masked_text) if m.confidence >= 0.6] == []

    req = LLMRequest(
        system="검토 시스템",
        user=json.dumps({"본문": first.masked_text}, ensure_ascii=False),
    )
    verdict = inspect_request(req)
    assert verdict["status"] == "PASSED", verdict


def test_multipass_masking_works_with_source_trace_and_projection(tmp_path, monkeypatch):
    text = "앞 AB-TARGET-CDEF-TAIL 뒤"

    def fake_detect(s, *, block_id=None, page=None):
        hits = []
        idx1 = s.find("AB-TARGET")
        if idx1 >= 0:
            hits.append(PIIMatch("PHONE", s[idx1:idx1 + 9], idx1, idx1 + 9, block_id, page, 0.95))
            hits.append(PIIMatch("ACCOUNT", s[idx1 + 2:idx1 + 14], idx1 + 2, idx1 + 14, block_id, page, 0.9))
        idx2 = s.find("-CDEF-TAIL")
        if idx2 >= 0 and s[idx2 - 1] == "]":
            hits.append(PIIMatch("PII", s[idx2:idx2 + 10], idx2, idx2 + 10, block_id, page, 0.9))
        return hits

    monkeypatch.setattr(engine_mod, "detect", fake_detect)
    engine = PIIEngine(PseudonymStore("batch_b_trace", root=tmp_path))
    renderer = model_input_renderer(engine, excluded=())
    rendered, piece = renderer._excerpt(text, len(text))

    assert "TARGET" not in rendered and "TAIL" not in rendered
    assert "[PHONE_001]" in rendered and "[PII_001]" in rendered
    source, ranges, out_rendered, origins, status = piece._data()
    assert status == "CAPTURED"
    assert len(origins) == len(out_rendered)

    res = engine.mask_text(text)
    proj_text, segs = project_masked(
        text, res, [{"segment_id": "S0", "original_start": 0, "original_end": len(text)}],
    )
    assert proj_text == res.masked_text
    assert "TARGET" not in segs[0]["text"] and "TAIL" not in segs[0]["text"]


def test_detect_ai_document_synthetic_brief_passes_real_privacy_gate(tmp_path, monkeypatch):
    body = (
        "준비서면\n"
        "원고 강태민(19800101-1234567) 및 피고 박준형[1985-11-24] 사이의 분쟁.\n"
        "연락처: 010-2468-1357 / 02-123-4567\n"
        "계약 기간: 2024-01-01 ~ 2024-12-31\n"
        "문서 전반에 걸쳐 사실관계를 정리하고 청구의 당부를 논증합니다.\n"
    )
    doc = _doc(body)
    engine = PIIEngine(PseudonymStore("batch_b_e2e", root=tmp_path))
    monkeypatch.setattr(router_module, "estimate_call", lambda *a: (Decimal("0.01"), {}))

    dispatched = []

    class FakeProvider:
        def __init__(self, name: str):
            self.name = name
            self.available = True
            self.config = SimpleNamespace(name=name, kind="cloud", model=f"{name}-v1", enabled=True)

        async def generate(self, request):
            dispatched.append(self.name)
            return LLMResponse(
                True,
                text=json.dumps(
                    {
                        "verdict": "UNCERTAIN",
                        "ai_score": 0.40,
                        "reasons": [{"kind": "style", "text": "합성 교차검증 응답"}],
                    },
                    ensure_ascii=False,
                ),
            )

    rtr = router_module.LLMRouter(
        providers={p: FakeProvider(p) for p in ("anthropic", "openai", "gemini")},
        ledger=BudgetLedger(),
    )
    res = asyncio.run(
        detect_ai_document(
            doc,
            citation_findings=[],
            router=rtr,
            mask=lambda s: engine.mask_text(s).masked_text,
            external_ai_policy=ExternalAIPolicy.MASKED,
        )
    )
    assert set(dispatched) == {"anthropic", "openai", "gemini"}
    assert res.used_llm is True
    assert res.signals.get("llm_failures") == {}
    assert res.signals["coverage"]["model_executed"] is True
    assert res.signals["coverage"]["rule_inspected_chars"] > 0


# ---------------------------------------------------------------------------
# 양성 2: AI 작성 주체 rule_inspected_chars 기록 및 ai_document_v1 스키마 호환성
# ---------------------------------------------------------------------------
def test_detect_ai_document_records_rule_inspected_chars_and_keeps_closed_input_contract():
    sample = "합성 법률 주장 문장입니다. 다섯 문장 이상 필요합니다. 세번째 문장. 네번째 문장. 다섯번째 문장."
    res_local = asyncio.run(detect_ai_document(_doc(sample), [], external_ai_policy=ExternalAIPolicy.LOCAL_ONLY))
    cov_local = res_local.signals["coverage"]
    assert cov_local["inspected_chars"] == 0
    assert cov_local["model_executed"] is False
    assert cov_local["sampling_mode"] == "not_run"
    assert cov_local["rule_inspected_chars"] == len(sample)

    captured = {}

    class FailingRouter:
        def has_available_provider(self, **kwargs):
            return True

        async def consult_all(self, role, req, **kwargs):
            captured["valid_contract"] = valid_input_contract(req)
            captured["coverage_keys"] = set(json.loads(req.user)["document_coverage"].keys())
            raise RuntimeError("boom")

    res_fail = asyncio.run(detect_ai_document(_doc(sample), [], router=FailingRouter()))
    assert captured["valid_contract"] is True
    assert "rule_inspected_chars" not in captured["coverage_keys"]
    cov_fail = res_fail.signals["coverage"]
    assert cov_fail["inspected_chars"] == 0
    assert cov_fail["model_executed"] is False
    assert cov_fail["rule_inspected_chars"] == len(sample)


# ---------------------------------------------------------------------------
# 양성 3: 브라우저 UI — AI 작성 주체 검토 범위 표시 3종(규칙 전수/표본/전체)
# ---------------------------------------------------------------------------
def test_browser_ai_scope_text_for_rule_only_sample_and_full():
    result_data = {
        "status": "COMPLETED",
        "documents": [
            {
                "id": "d_blocked",
                "filename": "장문서면_AI차단.pdf",
                "quarantined": False,
                "ai_detector_result": {
                    "verdict": "UNCERTAIN",
                    "score": 0.20,
                    "used_llm": False,
                    "reasons": ["규칙 기반 검사 완료"],
                    "signals": {
                        "coverage": {
                            "total_chars": 35674,
                            "inspected_chars": 0,
                            "rule_inspected_chars": 35674,
                            "sampling_mode": "full_text",
                            "is_full_coverage": False,
                            "model_executed": False,
                        },
                        "llm_opinions": [],
                        "llm_failures": {"openai": "TIMEOUT"},
                    },
                },
            },
            {
                "id": "d_sample",
                "filename": "장문서면_표본검토.pdf",
                "quarantined": False,
                "ai_detector_result": {
                    "verdict": "UNCERTAIN",
                    "score": 0.55,
                    "used_llm": True,
                    "reasons": ["일부 표본 모델 검토"],
                    "signals": {
                        "coverage": {
                            "total_chars": 35674,
                            "inspected_chars": 24000,
                            "rule_inspected_chars": 35674,
                            "sampling_mode": "head_middle_tail",
                            "is_full_coverage": False,
                            "model_executed": True,
                        },
                        "llm_opinions": [{"provider": "openai", "model": "gpt-4.1", "verdict": "UNCERTAIN", "score": 0.55, "reasons": ["유보"]}],
                    },
                },
            },
            {
                "id": "d_full",
                "filename": "단문서면_전체검토.pdf",
                "quarantined": False,
                "ai_detector_result": {
                    "verdict": "AI_PARTIAL_GENERATION",
                    "score": 0.78,
                    "used_llm": True,
                    "reasons": ["전체 본문 검토"],
                    "signals": {
                        "coverage": {
                            "total_chars": 8803,
                            "inspected_chars": 8803,
                            "rule_inspected_chars": 8803,
                            "sampling_mode": "full_text",
                            "is_full_coverage": True,
                            "model_executed": True,
                        },
                        "llm_opinions": [{"provider": "gemini", "model": "gemini-2.5-pro", "verdict": "AI_PARTIAL_GENERATION", "score": 0.78, "reasons": ["부분 흔적"]}],
                    },
                },
            },
        ],
    }

    static_dir = ROOT / "apps/web/static"
    files = {f"/static/{f.relative_to(static_dir).as_posix()}": f for f in static_dir.rglob("*") if f.is_file()}
    files["/"] = ROOT / "apps/web/index.html"
    project_data = {"id": "p1", "name": "배치B검토사건", "can_delete": True, "document_count": 3, "external_ai_policy": "MASKED", "scope_revision": 0, "requested_issues": []}
    run_data = {"id": "r1", "project_id": "p1", "state": "COMPLETED", "progress": 1, "document_ids": ["d_blocked", "d_sample", "d_full"], "scores": {}, "unverified_items": [], "errors": [], "unavailable_sources": [], "input_snapshot": {"scope_revision": 0}, "started_at": "2026-11-16T00:00:00"}

    def handler(route):
        path = urlsplit(route.request.url).path
        if path in files:
            return route.fulfill(path=str(files[path]))
        if path == "/api/health":
            return route.fulfill(json={"status": "ok", "version": "0.22.0"})
        if path == "/api/auth/me":
            return route.fulfill(json={"user_id": "u", "email": "t@e.com", "display_name": "검토자", "role": "ADMIN", "authentication": "local"})
        if path == "/api/verification-runs":
            return route.fulfill(json={"active_count": 0, "runs": []})
        if path == "/api/projects":
            return route.fulfill(json=[project_data])
        if path == "/api/projects/p1":
            return route.fulfill(json=project_data)
        if path == "/api/projects/p1/documents":
            return route.fulfill(json=[{"id": d["id"], "filename": d["filename"], "included_in_verification": True} for d in result_data["documents"]])
        if path == "/api/projects/p1/runs":
            return route.fulfill(json=[run_data])
        if path == "/api/projects/p1/findings":
            return route.fulfill(json=[])
        if path.endswith(("/result", "/results")):
            return route.fulfill(json=result_data)
        if path.endswith("/case-matrix"):
            return route.fulfill(body="null", content_type="application/json")
        if path == "/api/finding-categories":
            from packages.common.finding_category_map import CATEGORY_TO_TAB, FINDING_CATEGORY_MAP, get_category_counts
            return route.fulfill(json={"categories": {ft.value: cat.value for ft, cat in FINDING_CATEGORY_MAP.items()}, "tabs": {ft.value: CATEGORY_TO_TAB[cat].value for ft, cat in FINDING_CATEGORY_MAP.items()}, "counts": get_category_counts()})
        return route.fulfill(json=[])

    launch_kwargs = {"headless": True}
    if os.getenv("LV_TEST_BROWSER_CHANNEL"):
        launch_kwargs["channel"] = os.getenv("LV_TEST_BROWSER_CHANNEL")

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route("**/*", handler)
        page.goto("http://localhost/")
        select_first_project(page)
        page.locator('button[data-tab="ai-verification"]').click()
        ai_panel = page.locator('section[data-panel="ai-verification"]')
        expect(ai_panel).to_contain_text("규칙 기반 35674자 전수 검사 완료 · 외부 AI 모델 0/35674자 (호출 실패·차단)")
        ai_text = ai_panel.inner_text()
        assert "외부 AI 모델 표본 24000/35674자 · 일부 표본 (규칙 기반 35674자 전수 검사 완료)" in ai_text
        assert "8803/8803자 · 대상 본문 전체 (규칙 전수 8803자)" in ai_text
        browser.close()


# ---------------------------------------------------------------------------
# 대조군 1·2·3: Fail-Closed 및 기존 PII/커버리지 계약 보존
# ---------------------------------------------------------------------------
def test_dob_and_slash_rrn_still_detected_despite_iso_and_slash_phone_guards():
    assert any(m.kind == "DOB" for m in detect("생년월일: 1985-11-24"))
    assert any(m.kind == "DOB" for m in detect("참고인 박준형(1998-03-04생)"))
    assert any(m.kind == "RRN" for m in detect("주민등록번호 800101/1234567"))
    assert any(m.kind == "PHONE" for m in detect("연락처: 010-2468-1357 / 02-123-4567"))


@pytest.mark.parametrize(
    "payload",
    [
        {"성명": "[PERSON_001] 김철수"},
        {"연락처": "010-9876-5432"},
        {"본문": "[UNKNOWN_001] 800101-1234567"},
    ],
)
def test_fail_closed_still_blocks_unmasked_or_spoofed_pii(payload):
    verdict = inspect_request(LLMRequest(system="s", user=json.dumps(payload, ensure_ascii=False)))
    assert verdict["status"] == "BLOCKED"
    assert verdict["failure_code"] == "PII_INPUT_BLOCKED"


def test_long_document_coverage_invariants_preserved(monkeypatch):
    long_text = ("원고는 합리적 이유 없이 청구하고 있습니다. " * 1500).strip()

    class MockRouter:
        def has_available_provider(self, **kwargs):
            return True

        async def consult_all(self, role, req, **kwargs):
            assert valid_input_contract(req)
            return [
                SimpleNamespace(
                    used=True,
                    parsed={"verdict": "AI_FULL_GENERATION_LIKELY", "ai_score": 0.95},
                    text="",
                    executions=[SimpleNamespace(provider=name, model="test")],
                )
                for name in ("openai", "gemini")
            ]

    res = asyncio.run(detect_ai_document(_doc(long_text), [], router=MockRouter()))
    cov = res.signals["coverage"]
    assert res.verdict == "UNCERTAIN"
    assert res.signals["decision_rule"] == "HELD_INCOMPLETE_COVERAGE"
    assert cov["inspected_chars"] == 24000
    assert cov["model_executed"] is True
    assert cov["is_full_coverage"] is False
    assert cov["rule_inspected_chars"] == len(long_text)
