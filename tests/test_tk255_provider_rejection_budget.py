"""TK-255: 공급자 거절(HTTP 오류 응답)이 참고자료 대조의 호출 상한·비용 예산을 소진하지 않는다.

0.31.0 운영 m3: Anthropic 사용 한도로 Sonnet이 HTTP 400을 내자
- Drive 대조: 실패 시도가 호출 상한(2*ceil(N/6))의 절반을 써 참고자료 33/83이 미대조
- 주장 대조: 실패 예약액(RESERVED_UNCERTAIN)이 단계 비용 예산을 채워 19개 중 4개에서 COST 중단
합성 입력(사건 무관)으로 두 증상을 재현하고, 응답 시간 초과는 계속 예산에 세는지(Fail-Closed) 확인한다.
"""
from __future__ import annotations

from types import SimpleNamespace

from packages.common.enums import ExternalAIPolicy, VerificationProfile
from packages.rag_engine.review import review_document

_WORD = "계약 대금 지급 의무 이행 기한 "


def _sources(n=12, chars=1900):
    body = (_WORD * (chars // len(_WORD) + 1))[:chars]
    return [{"file_id": f"fid_{i:02d}", "source_id": f"R{i}", "title": f"참고자료{i}.txt",
             "folder_path": "", "page": 1, "text": body} for i in range(n)]


def _exec(ok, provider, cost, status, error=""):
    d = {"ok": ok, "provider": provider, "cost_usd": cost, "cost_status": status, "error": error}
    return SimpleNamespace(**d, to_dict=lambda d=d: dict(d))


class _Router:
    def __init__(self, failure_error="HTTP 400: usage limit reached"):
        self.failure_error = failure_error
        self.drive_calls = []
        self.claim_calls = 0

    def has_available_provider(self, **kwargs):
        return True

    async def run(self, role, request, **kwargs):
        stage = request.metadata.get("stage")
        empty = {"observations": []}
        if stage == "drive_rag_advisory":
            exclude = kwargs.get("exclude")
            self.drive_calls.append(exclude)
            if not exclude:
                return SimpleNamespace(used=False, quarantined=False, parsed=None,
                                       executions=[_exec(False, "anthropic", 0.30, "RESERVED_UNCERTAIN", self.failure_error)])
            return SimpleNamespace(used=True, quarantined=False, parsed=empty,
                                   executions=[_exec(True, "openai", 0.02, "REPORTED")])
        if stage == "claim_rag_advisory":
            self.claim_calls += 1
            return SimpleNamespace(used=True, quarantined=False, parsed=empty, executions=[
                _exec(False, "anthropic", 0.30, "RESERVED_UNCERTAIN", self.failure_error),
                _exec(True, "openai", 0.02, "REPORTED")])
        return SimpleNamespace(used=True, quarantined=False, executions=[], parsed=empty)

    run_any = run


def _review(router, n_claims=8):
    sources = _sources()
    text = _WORD * 20
    library = SimpleNamespace(
        summary={"status": "READY", "snapshot_hash": "h"}, folder="f",
        select=lambda t: {"decision": "USED", "reason": "RELEVANT_REFERENCE_FOUND",
                          "coverage": "CHECKED_INDEXED_CORPUS", "sources": sources})
    result = SimpleNamespace(
        document_id="doc_tk255", findings=[], citations=[], engine_data={},
        normalized=SimpleNamespace(visible_text=text, pages=[SimpleNamespace(text=text)], blocks=[]),
        claims=[{"claim_id": f"C{i}", "text": f"피고는 계약 대금 지급 의무를 이행 기한 안에 이행하여야 한다 {i}."}
                for i in range(n_claims)])
    context = SimpleNamespace(requested_issues=[], profile=VerificationProfile.STANDARD,
                              external_ai_policy=ExternalAIPolicy.ORIGINAL)
    pii = SimpleNamespace(mask_text=lambda t: SimpleNamespace(masked_text=t))
    return review_document(result, library, router, context, pii)


def test_tk255_provider_rejection_does_not_consume_drive_call_cap(monkeypatch):
    monkeypatch.setattr("packages.rag_engine.review.analysis_text", lambda d, f: (_WORD * 20, {"omitted_chars": 0}))
    router = _Router()
    review = _review(router)
    assert not review.get("unreviewed_drive_sources"), review.get("unreviewed_drive_sources")
    first = [c for c in router.drive_calls if not c]
    failover = [c for c in router.drive_calls if c]
    assert len(first) == len(failover) == 4  # 12개 자료 → 3개씩 4묶음, 묶음마다 거절 1회 + 대체 1회


def test_tk255_provider_rejection_does_not_halt_claim_budget(monkeypatch):
    monkeypatch.setattr("packages.rag_engine.review.analysis_text", lambda d, f: (_WORD * 20, {"omitted_chars": 0}))
    router = _Router()
    budget = _review(router)["claim_coverage"]["budget"]
    assert budget["halt_reason"] is None
    assert router.claim_calls == 8
    assert budget["provider_rejected_usd"] == round(0.30 * 8, 4)
    assert budget["uncertain_usd"] == round(0.30 * 8, 4)  # 기록은 그대로 남는다


def test_tk255_timeouts_still_count_toward_claim_budget(monkeypatch):
    """대조: 응답 시간 초과(과금 여부 불확실)는 종전대로 단계 예산에 센다(Fail-Closed)."""
    monkeypatch.setattr("packages.rag_engine.review.analysis_text", lambda d, f: (_WORD * 20, {"omitted_chars": 0}))
    router = _Router(failure_error="PROVIDER_TIMEOUT: AI 응답 시간 초과. 해당 검토는 미검증입니다")
    budget = _review(router)["claim_coverage"]["budget"]
    assert budget["halt_reason"] == "COST"
    assert router.claim_calls < 8
    assert budget["provider_rejected_usd"] == 0.0
