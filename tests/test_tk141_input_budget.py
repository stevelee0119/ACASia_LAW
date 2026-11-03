"""TK-141: 판례 의미 검토 발췌를 공급자 입력 한도에 맞추고, 보낸 발췌의 해시를 리뷰에 남긴다. 합성 판결문만 쓴다."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from packages.common.enums import CitationType, EvidenceGrade, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.evidence_pack import DEFAULT_BUDGET

FILLER = "이 사건 기록에 나타난 여러 사정을 살펴본다. "
QUOTE = "국가는 공무원의 직무상 과실로 인한 손해를 배상할 책임이 있다."


def judgment(total=60000):
    body = FILLER * (total // len(FILLER) // 2)
    return "【이유】 " + body + QUOTE + " " + body + "【결론】 원심의 판단은 정당하다."


def run(full_text, input_cap=None, patch=None):
    from packages.llm_router.router import CascadeOutcome, ModelExecution
    from packages.pii_engine import PIIEngine, PseudonymStore
    from packages.source_adapters.registry import SourceRegistry
    from packages.verification_engine import pipeline as pl

    calls = []

    class Router:
        limits = {"max_input_tokens": input_cap} if input_cap else None

        async def cascade(self, **kwargs):
            calls.append(kwargs)
            return CascadeOutcome(VerificationStatus.VERIFIED, EvidenceGrade.A, "취지 부합",
                                  stages=[{"used": True, "verdict": {"status": "VERIFIED", "rationale": "취지 부합",
                                                                     "evidence_quotes": [QUOTE]}}],
                                  executions=[ModelExecution("PRIMARY_REASONER", "stub", "test", True)])

    c = Citation(citation_id="CIT_TK141", raw_text="대법원 2099다1 판결", type=CitationType.CASE, case_number="2099다1",
                 quoted_text=QUOTE, context=f"대법원 2099다1 판결은 '{QUOTE}'고 판시하였다.", span=(0, 10))
    pipeline = pl.VerificationPipeline(registry=SourceRegistry(), router=Router())
    result = pl.DocumentResult("d", "sample")
    result.engine_data["legal_verdicts"] = [{"citation_id": c.citation_id, "levels": {"level4": "PENDING_LLM"},
                                             "official_record": {"full_text": full_text}}]
    saved = {}
    if patch:
        for name, value in patch.items():
            saved[name] = getattr(pl, name)
            setattr(pl, name, value)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline._semantic_review(result, [c], pl.ProjectContext("tk141"),
                                      PIIEngine(PseudonymStore("tk141", root=Path(tmp))))
    finally:
        for name, value in saved.items():
            setattr(pl, name, value)
    return calls, result.engine_data["semantic_reviews"][0]


def test_default_limit_keeps_existing_budget_and_records_sent_hash():
    calls, review = run(judgment())
    assert review["input_budget"]["pack_budget_chars"] == DEFAULT_BUDGET
    sent = calls[0]["evidence"]["official"]["source_excerpt"]
    assert review["evidence_pack"]["sent_sha256"] == hashlib.sha256(sent.encode("utf-8")).hexdigest()
    assert review["input_budget"]["estimated_bytes"] <= review["input_budget"]["input_cap"]


def test_lower_provider_limit_shrinks_excerpt_so_request_fits():
    from packages.verification_engine.pipeline import _request_bytes
    cap = 32768                                   # CI 실연동 시험 설정값
    calls, review = run(judgment(), input_cap=cap)
    assert review["input_budget"]["pack_budget_chars"] < DEFAULT_BUDGET
    assert calls and _request_bytes(calls[0]["question"], calls[0]["evidence"]) <= cap
    assert QUOTE in calls[0]["evidence"]["official"]["source_excerpt"]     # 인용 대응 구간은 남는다
    assert review["source_quotes_validated"] is True


def test_limit_too_small_for_required_context_does_not_call_model():
    calls, review = run(judgment(), input_cap=12000)
    assert calls == [] and review["model_executed"] is False and review["status"] == "UNVERIFIED"
    assert "공급자 입력 한도 12000" in review["reason"]


def test_final_size_check_blocks_oversize_request_instead_of_provider_failure():
    # 예산 계산을 일부러 넘치게 해도 보내기 직전 크기 검사가 막는다(가림으로 길어진 경우 등의 방어).
    calls, review = run(judgment(), input_cap=20000, patch={"_excerpt_budget_chars": lambda *a, **k: DEFAULT_BUDGET})
    assert calls == [] and review["model_executed"] is False
    assert review["reason"].startswith("공급자 입력 한도(20000)를 넘어")
    assert review["evidence_pack"]["sent_sha256"] is None
