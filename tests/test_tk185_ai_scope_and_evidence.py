"""TK-185: AI 관여·범위 분리, 모델 간 범위 이견, 표본 범위 및 근거 강도 보존 시험."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from packages.common.schemas import Block, NormalizedDocument, Page
from packages.verification_engine import scoring
from packages.verification_engine.ai_document_detector import (
    create_ai_detector_findings,
    detect_ai_document,
)


def _doc(text: str, doc_id: str = "doc-tk185") -> NormalizedDocument:
    doc = NormalizedDocument(
        document_id=doc_id,
        filename="sample_brief.pdf",
        mime_type="application/pdf",
        sha256="tk185testsha",
    )
    page = Page(page_number=1)
    page.blocks.append(Block(block_id="b1", text=text, page=1, source_layer="visible_text"))
    doc.pages.append(page)
    doc.raw_layers["visible_text"] = text
    return doc


class _FakeRouter:
    def __init__(self, answers):
        self.answers = answers

    def has_available_provider(self, policy=None):
        return True

    async def consult_all(self, role, request, *, policy=None, expected_task=""):
        out = []
        for provider, parsed in self.answers.items():
            if parsed is None:
                continue
            out.append(
                SimpleNamespace(
                    used=True,
                    parsed=parsed,
                    text="",
                    provider=provider,
                    model=f"{provider}-test-model",
                    error=None,
                    executions=[
                        SimpleNamespace(
                            provider=provider,
                            model=f"{provider}-test-model",
                            error=None,
                        )
                    ],
                )
            )
        return out


def _sample_prose() -> str:
    return (
        "원고는 계약 체결 경위와 대금 지급 내역을 시간순으로 정리하여 주장합니다. "
        "피고는 해당 약정의 효력을 다투며 관련 자료를 제출하였습니다. "
        "양 당사자의 주장은 주요 사실관계의 해석에서 차이를 보입니다. "
        "법원은 제출된 서증의 신빙성과 입증 책임을 종합적으로 판단하여야 합니다. "
        "이 사건 서면은 다섯 문장 이상으로 구성된 일반 법률 주장 문단입니다."
    )


def test_scope_disagreement_and_heuristic_only_preserved_across_detector_and_scoring():
    doc = _doc(_sample_prose())
    router = _FakeRouter(
        {
            "anthropic": {"verdict": "AI_PARTIAL_GENERATION", "ai_score": 0.65, "reasons": ["일부 문단 문체 균질"]},
            "openai": {"verdict": "AI_FULL_GENERATION_LIKELY", "ai_score": 0.85, "reasons": ["전체 문체 균질"]},
            "gemini": {"verdict": "AI_FULL_GENERATION_LIKELY", "ai_score": 0.80, "reasons": ["전반적 LLM 문체"]},
        }
    )
    res = asyncio.run(detect_ai_document(doc, [], router=router))
    assert res.verdict == "AI_FULL_GENERATION_LIKELY"
    assert res.signals["scope"] == "WHOLE_DOCUMENT"
    assert res.signals["involvement"] == "NO_OBJECTIVE_TRACES"
    assert res.signals["evidence_strength"] == "HEURISTIC_ONLY"
    assert res.signals["scope_disagreement"] is True
    assert res.signals["model_scope_opinions"] == {
        "anthropic": "PART_OF_DOCUMENT",
        "openai": "WHOLE_DOCUMENT",
        "gemini": "WHOLE_DOCUMENT",
    }
    assert "객관적 생성 흔적 미확인" in res.reasons[0]

    findings = create_ai_detector_findings(doc, res)
    main = [f for f in findings if f.confidence_features.get("scope") == "WHOLE_DOCUMENT"][0]
    assert main.confidence_features["scope_disagreement"] is True
    assert main.confidence_features["evidence_strength"] == "HEURISTIC_ONLY"
    assert main.confidence_features["coverage"]["is_full_coverage"] is True
    assert "모델 간 범위 이견" in main.detail

    axis = scoring.unified_authorship(
        SimpleNamespace(document_id=doc.document_id, ai_detector_result=res.to_dict(), authorship=None)
    )
    assert axis["involvement"] == "NO_OBJECTIVE_TRACES"
    assert axis["scope"] == "WHOLE_DOCUMENT"
    assert axis["evidence_strength"] == "HEURISTIC_ONLY"
    assert axis["scope_disagreement"] is True
    assert axis["coverage"]["sampling_mode"] == "full_text"


def test_partial_sampling_coverage_preserved_end_to_end(monkeypatch):
    long_text = (_sample_prose() + " ") * 40
    doc = _doc(long_text)
    monkeypatch.setattr(
        "packages.verification_engine.ai_document_detector.get_settings",
        lambda: SimpleNamespace(authorship_max_chars=300),
    )
    router = _FakeRouter(
        {
            "anthropic": {"verdict": "AI_PARTIAL_GENERATION", "ai_score": 0.62, "reasons": ["일부 구간 추정"]},
            "openai": {"verdict": "AI_PARTIAL_GENERATION", "ai_score": 0.68, "reasons": ["일부 구간 추정"]},
        }
    )
    res = asyncio.run(detect_ai_document(doc, [], router=router))
    cov = res.signals["coverage"]
    assert cov["is_full_coverage"] is False
    assert cov["sampling_mode"] == "head_middle_tail"
    assert cov["omitted_chars"] > 0

    findings = create_ai_detector_findings(doc, res)
    assert findings[0].confidence_features["coverage"]["sampling_mode"] == "head_middle_tail"
    axis = scoring.unified_authorship(
        SimpleNamespace(document_id=doc.document_id, ai_detector_result=res.to_dict(), authorship=None)
    )
    assert axis["coverage"]["is_full_coverage"] is False
    assert axis["coverage"]["omitted_chars"] > 0


def test_control_agreed_scope_has_no_scope_disagreement():
    doc = _doc(_sample_prose())
    router = _FakeRouter(
        {
            "anthropic": {"verdict": "AI_FULL_GENERATION_LIKELY", "ai_score": 0.9},
            "openai": {"verdict": "AI_FULL_GENERATION_LIKELY", "ai_score": 0.88},
        }
    )
    res = asyncio.run(detect_ai_document(doc, [], router=router))
    assert res.signals["scope_disagreement"] is False
    assert res.signals["model_scope_opinions"] == {
        "anthropic": "WHOLE_DOCUMENT",
        "openai": "WHOLE_DOCUMENT",
    }
    findings = create_ai_detector_findings(doc, res)
    assert all("모델 간 범위 이견" not in f.detail for f in findings)


def test_control_objective_traces_marks_objective_evidence_strength():
    prose_with_residue = _sample_prose() + " 물론입니다! 요청하신 내용을 정리해 드리겠습니다."
    doc = _doc(prose_with_residue)
    router = _FakeRouter(
        {
            "anthropic": {"verdict": "AI_FULL_GENERATION_LIKELY", "ai_score": 0.92},
            "openai": {"verdict": "AI_FULL_GENERATION_LIKELY", "ai_score": 0.91},
        }
    )
    res = asyncio.run(detect_ai_document(doc, [], router=router))
    assert res.signals["objective_traces"] >= 1
    assert res.signals["evidence_strength"] == "OBJECTIVE_TRACES"
    assert res.signals["involvement"] == "TRACES_FOUND"
    assert "객관적 생성 흔적 미확인" not in res.reasons[0]

    axis = scoring.unified_authorship(
        SimpleNamespace(document_id=doc.document_id, ai_detector_result=res.to_dict(), authorship=None)
    )
    assert axis["involvement"] == "TRACES_FOUND"
    assert axis["evidence_strength"] == "OBJECTIVE_TRACES"


def test_control_split_uncertain_has_not_applicable_scope():
    doc = _doc(_sample_prose())
    router = _FakeRouter(
        {
            "anthropic": {"verdict": "AI_FULL_GENERATION_LIKELY", "ai_score": 0.8},
            "openai": {"verdict": "HUMAN_AUTHORED_LIKELY", "ai_score": 0.1},
            "gemini": {"verdict": "UNCERTAIN", "ai_score": 0.4},
        }
    )
    res = asyncio.run(detect_ai_document(doc, [], router=router))
    assert res.verdict == "UNCERTAIN"
    assert res.signals["scope"] == "NOT_APPLICABLE"
    assert res.signals["scope_disagreement"] is False
