"""Tests for TK-209 (3-stage RAG SUPPORTS diagnostics: excerpt delivery, model response, promotion/attachment).

All test documents, filenames, and responses are synthetic.
"""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from packages.common.config import get_settings
from packages.common.enums import ExternalAIPolicy, VerificationProfile
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.llm_router.router import RouterResult
from packages.rag_engine.review import review_document


class _FakeLibrary:
    def __init__(self, sources):
        self._sources = sources
        self.summary = {"status": "READY", "snapshot_hash": "snap_tk209"}

    def select(self, text, limit=12):
        return {
            "decision": "SELECTED",
            "reason": "RELEVANT",
            "sources": [dict(s) for s in self._sources],
            "coverage": {"files_selected": len(self._sources)},
        }

    def case_table_status(self):
        return {"status": "NO_CASE_TABLE", "candidates": [], "indexed_rows": 0}

    def has_case_tables(self):
        return False

    def search_claim(self, text, citations=None, limit=5):
        return []


class _FakeRouter:
    def __init__(self, batch_parsed, claim_parsed=None):
        self.settings = replace(get_settings(), korean_law_review_profile=False)
        self.batch_parsed = batch_parsed
        self.claim_parsed = claim_parsed
        self.calls = []

    def has_available_provider(self, policy=None):
        return True

    async def run(self, role, req, policy=None, exclude=None, expected_task=None):
        self.calls.append(req)
        stage = (req.metadata or {}).get("stage")
        parsed = self.batch_parsed if stage == "drive_rag_advisory" else (self.claim_parsed or {"observations": []})
        return RouterResult(
            used=True,
            parsed=parsed,
            quarantined=False,
            executions=[],
        )


def _make_doc_result(claim_text: str):
    norm = NormalizedDocument(
        document_id="doc_tk209",
        filename="brief.txt",
        mime_type="text/plain",
        sha256="a" * 64,
        pages=[Page(1, blocks=[Block("b1", claim_text, 1)])],
    )
    return SimpleNamespace(
        normalized=norm,
        findings=[],
        claims=[{"claim_id": "C1", "type": "FACT", "text": claim_text}],
        citations=[],
        engine_data={},
    )


def _make_context():
    return SimpleNamespace(
        profile=VerificationProfile.STANDARD,
        external_ai_policy=ExternalAIPolicy.ORIGINAL,
        requested_issues=[],
        case_date=None,
    )


def _make_pii():
    return SimpleNamespace(mask=lambda t: t, unmask=lambda t: t)


def test_tk209_supports_survives_all_three_stages():
    claim_text = "피고는 관련 규정상 안전관리 의무를 부담하고 이를 이행하여야 한다."
    source_text = "안전관리 지침 제3조에 따라 사업주체는 안전관리 의무를 부담하고 이를 이행하여야 한다."
    sources = [{
        "source_id": "R1",
        "file_id": "file_sup_1",
        "title": "지지_참고자료.pdf",
        "format": "pdf",
        "page": 2,
        "sha256": "b" * 64,
        "text": source_text,
        "relevance": 0.9,
    }]
    parsed = {
        "observations": [{
            "source_id": "R1",
            "claim_quote": "안전관리 의무를 부담하고 이를 이행하여야 한다",
            "source_quote": "안전관리 의무를 부담하고 이를 이행하여야 한다",
            "relationship": "SUPPORTS",
            "explanation": "참고자료가 주장과 같은 방향의 안전관리 의무를 명시하고 있음",
        }]
    }
    res = _make_doc_result(claim_text)
    review = review_document(res, _FakeLibrary(sources), _FakeRouter(parsed), _make_context(), _make_pii())

    diag = review["support_diagnostics"]
    assert "R1" in diag["excerpt_delivery"]["unique_sources_delivered"]
    assert diag["excerpt_delivery"]["batch_deliveries"][0]["file_id"] == "file_sup_1"
    assert diag["excerpt_delivery"]["batch_deliveries"][0]["delivered_chars"] == len(source_text)
    assert diag["excerpt_delivery"]["claim_deliveries"][0]["claim_id"] == "C1"

    assert diag["model_responses"]["raw_total"]["SUPPORTS"] == 1
    assert diag["model_responses"]["by_source"]["R1"]["SUPPORTS"] == 1

    assert diag["promotion_attachment"]["after_grounding"]["SUPPORTS"] == 1
    assert diag["promotion_attachment"]["after_dedup"]["SUPPORTS"] == 1
    assert diag["promotion_attachment"]["after_link_issues"]["SUPPORTS"] == 1
    assert review["issues"][0]["relationship"] == "SUPPORTS"


def test_tk209_pinpoints_stage2_when_model_returns_only_context():
    claim_text = "피고는 계약상 보수 지급 의무를 부담한다."
    source_text = "보수 산정 기준에 관한 일반 참고 안내서 본문이다."
    sources = [{
        "source_id": "R1",
        "file_id": "file_ctx_1",
        "title": "일반_참고자료.pdf",
        "format": "pdf",
        "page": 1,
        "sha256": "c" * 64,
        "text": source_text,
        "relevance": 0.6,
    }]
    parsed = {
        "observations": [{
            "source_id": "R1",
            "claim_quote": "계약상 보수 지급 의무를 부담한다",
            "source_quote": "보수 산정 기준에 관한 일반 참고 안내서 본문",
            "relationship": "CONTEXT",
            "explanation": "배경 설명에 해당함",
        }]
    }
    res = _make_doc_result(claim_text)
    review = review_document(res, _FakeLibrary(sources), _FakeRouter(parsed), _make_context(), _make_pii())

    diag = review["support_diagnostics"]
    assert diag["excerpt_delivery"]["unique_sources_delivered"] == ["R1"]
    assert diag["model_responses"]["raw_total"]["SUPPORTS"] == 0
    assert diag["model_responses"]["raw_total"]["CONTEXT"] == 1
    assert diag["promotion_attachment"]["after_link_issues"]["SUPPORTS"] == 0


def test_tk209_pinpoints_stage3_when_supports_rejected_at_grounding():
    claim_text = "원고는 정당한 사유 없이 계약을 해지할 수 없다."
    source_text = "계약 일반조건 제5조는 해지 절차를 규정한다."
    sources = [{
        "source_id": "R1",
        "file_id": "file_rej_1",
        "title": "해지_참고자료.pdf",
        "format": "pdf",
        "page": 4,
        "sha256": "d" * 64,
        "text": source_text,
        "relevance": 0.7,
    }]
    parsed = {
        "observations": [{
            "source_id": "R1",
            "claim_quote": "정당한 사유 없이 계약을 해지할 수 없다",
            "source_quote": "원문에 존재하지 않는 인용 문구",
            "relationship": "SUPPORTS",
            "explanation": "근거 없는 지지 의견",
        }]
    }
    res = _make_doc_result(claim_text)
    review = review_document(res, _FakeLibrary(sources), _FakeRouter(parsed), _make_context(), _make_pii())

    diag = review["support_diagnostics"]
    assert diag["model_responses"]["raw_total"]["SUPPORTS"] == 1
    assert diag["model_responses"]["rejected_count"] >= 1
    assert diag["model_responses"]["rejected_reasons"].get("QUOTE_NOT_GROUNDED", 0) >= 1
    assert diag["promotion_attachment"]["after_grounding"]["SUPPORTS"] == 0
    assert diag["promotion_attachment"]["after_link_issues"]["SUPPORTS"] == 0


def test_tk209_unrelated_control_produces_zero_supports_and_zero_contradicts():
    claim_text = "원고는 손해배상 채권의 소멸시효가 완성되지 않았다고 주장한다."
    source_text = "청사 시설물 관리 및 주차장 운영 지침에 관한 규정이다."
    sources = [{
        "source_id": "R1",
        "file_id": "file_unrel_1",
        "title": "무관_자료.pdf",
        "format": "pdf",
        "page": 1,
        "sha256": "e" * 64,
        "text": source_text,
        "relevance": 0.2,
    }]
    parsed = {
        "observations": [{
            "source_id": "R1",
            "claim_quote": "소멸시효가 완성되지 않았다고 주장한다",
            "source_quote": "청사 시설물 관리 및 주차장 운영 지침에 관한 규정",
            "relationship": "INSUFFICIENT",
            "explanation": "주장과 무관한 자료임",
        }]
    }
    res = _make_doc_result(claim_text)
    review = review_document(res, _FakeLibrary(sources), _FakeRouter(parsed), _make_context(), _make_pii())

    diag = review["support_diagnostics"]
    assert diag["model_responses"]["raw_total"]["SUPPORTS"] == 0
    assert diag["model_responses"]["raw_total"]["CONTRADICTS"] == 0
    assert diag["promotion_attachment"]["after_link_issues"]["SUPPORTS"] == 0
    assert diag["promotion_attachment"]["after_link_issues"]["CONTRADICTS"] == 0
