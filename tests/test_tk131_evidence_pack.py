"""TK-131: 판례 의미 검토에 보내는 공식 원문 발췌. 합성 판결문만 쓴다(실제 판결·서면이 아니다)."""
import tempfile
from pathlib import Path

import pytest

from packages.common.enums import CitationType, EvidenceGrade, VerificationStatus
from packages.common.schemas import Citation
from packages.legal_engine.evidence_pack import build_evidence_pack, quote_in_one_segment, render

FILLER = "이 사건 기록에 나타난 여러 사정을 살펴본다. "          # 23자 문장
LATE_RULE = "다만 피해자가 스스로 위험을 인수한 경우에는 배상책임을 지지 아니한다."
QUOTE = "국가는 공무원의 직무상 과실로 인한 손해를 배상할 책임이 있다."


def judgment(late=LATE_RULE, at=26000, total=40000):
    head = "【주문】 상고를 기각한다. 【이유】 "
    body = FILLER * (at // len(FILLER))
    tail = FILLER * ((total - at) // len(FILLER))
    return head + body + QUOTE + " " + late + " " + tail + "【결론】 원심의 판단은 정당하다."


# --- 발췌 구성 ---------------------------------------------------------------------------------------------
def test_short_judgment_is_sent_whole():
    text = "【이유】 " + QUOTE
    pack = build_evidence_pack(text, quotes=[QUOTE])
    assert pack["coverage_status"] == "FULL" and [s["text"] for s in pack["segments"]] == [text]


def test_quote_after_24000_chars_is_selected_with_its_exception():
    text = judgment()
    pack = build_evidence_pack(text, quotes=[QUOTE])
    joined = render([s["text"] for s in pack["segments"]])
    assert QUOTE in joined and LATE_RULE in joined            # 앞 24,000자 절단이면 둘 다 빠진다
    assert pack["coverage_status"] == "SELECTED" and pack["selected_chars"] <= 24000
    assert "【결론】" in joined                                   # 결론부도 함께 보낸다


def test_offsets_round_trip_to_the_original():
    text = judgment()
    for seg in build_evidence_pack(text, quotes=[QUOTE])["segments"]:
        assert text[seg["original_start"]:seg["original_end"]] == seg["text"]


def test_spacing_variant_quote_is_found():
    text = judgment()
    pack = build_evidence_pack(text, quotes=[QUOTE.replace(" ", "")])
    assert QUOTE in render([s["text"] for s in pack["segments"]])


def test_claim_overlap_selects_late_sentence_without_direct_quote():
    text = judgment(late="다만 군인의 훈련 중 사고는 별도 보상 법률이 우선 적용된다.")
    pack = build_evidence_pack(text, claim="군인의 훈련 중 사고에 국가배상법이 적용된다고 주장한다")
    assert "별도 보상 법률이 우선" in render([s["text"] for s in pack["segments"]])


# --- 대조: 찾지 못함·예산 초과 ------------------------------------------------------------------------------
def test_missing_quote_is_recorded_not_assumed():
    pack = build_evidence_pack(judgment(), quotes=["이 판결에 없는 문장이 여기에 있다고 주장한다"])
    assert "DIRECT_QUOTE_NOT_FOUND" in pack["truncation_reasons"]
    assert pack["coverage_status"] == "SELECTED"


def test_quote_context_larger_than_budget_is_insufficient_context():
    pack = build_evidence_pack(judgment(), quotes=[QUOTE], budget=500)
    assert pack["coverage_status"] == "PARTIAL" and "INSUFFICIENT_CONTEXT" in pack["truncation_reasons"]


def test_quotes_spanning_two_segments_or_markers_are_rejected():
    segments = ["첫째 구간의 문장이다.", "둘째 구간의 문장이다."]
    assert quote_in_one_segment("첫째 구간의 문장이다.", segments)
    assert not quote_in_one_segment("문장이다.둘째", segments)
    assert not quote_in_one_segment("생략", segments) and not quote_in_one_segment("", segments)


# --- 실제 진입점: _semantic_review가 보내는 payload와 근거 확인 --------------------------------------------------
def run_review(full_text, model_quotes, quoted_text=QUOTE, pii=None):
    from packages.llm_router.router import CascadeOutcome, ModelExecution
    from packages.pii_engine import PIIEngine, PseudonymStore
    from packages.source_adapters.registry import SourceRegistry
    from packages.verification_engine.pipeline import DocumentResult, ProjectContext, VerificationPipeline

    sent = {}

    class Router:
        async def cascade(self, **kwargs):
            sent.update(kwargs)
            return CascadeOutcome(VerificationStatus.VERIFIED, EvidenceGrade.A, "취지 부합",
                                  stages=[{"used": True, "verdict": {"status": "VERIFIED", "rationale": "취지 부합",
                                                                     "evidence_quotes": model_quotes}}],
                                  executions=[ModelExecution("PRIMARY_REASONER", "stub", "test", True)])

    citation = Citation(citation_id="CIT_TK131", raw_text="대법원 2099다1 판결", type=CitationType.CASE,
                        case_number="2099다1", quoted_text=quoted_text,
                        context=f"대법원 2099다1 판결은 '{quoted_text}'고 판시하였다.", span=(0, 10))
    pipeline = VerificationPipeline(registry=SourceRegistry(), router=Router())
    result = DocumentResult("d", "sample")
    result.engine_data["legal_verdicts"] = [{"citation_id": citation.citation_id, "levels": {"level4": "PENDING_LLM"},
                                             "official_record": {"full_text": full_text}}]
    if pii is not None:                                        # 같은 프로젝트의 가명 저장소를 뒤 단계와 함께 쓴다
        pipeline._semantic_review(result, [citation], ProjectContext("tk131"), pii)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline._semantic_review(result, [citation], ProjectContext("tk131"),
                                      PIIEngine(PseudonymStore("tk131", root=Path(tmp))))
    return sent, result.engine_data["semantic_reviews"][0]


def test_review_sends_excerpt_with_late_quote_and_accepts_its_quote():
    sent, review = run_review(judgment(), [QUOTE])
    official = sent["evidence"]["official"]
    assert "full_text" not in official and QUOTE in official["source_excerpt"]
    assert official["excerpt_coverage"] == "SELECTED"
    assert review["source_quotes_validated"] is True and review["source_truncated"] is True
    assert review["evidence_pack"]["segments"] and "text" not in review["evidence_pack"]["segments"][0]


def test_review_rejects_quote_from_unsent_part():
    unsent = "가나다라마바사 하파타카."            # 문서 주장과 겹치는 글자가 없어 선택되지 않는 원문 문장
    text = judgment()
    claim = f"대법원 2099다1 판결은 '{QUOTE}'고 판시하였다."
    for at in range(6000, 22000, 1000):                         # 발췌에 들지 않는 자리를 찾는다(결정적)
        at = text.index(" ", at) + 1
        candidate = text[:at] + unsent + " " + text[at:]
        pack = build_evidence_pack(candidate, quotes=[QUOTE], claim=claim)
        if unsent not in render([s["text"] for s in pack["segments"]]):
            text = candidate
            break
    else:
        pytest.fail("전제 실패: 보내지 않는 자리가 없다")
    sent, review = run_review(text, [unsent])
    assert unsent not in sent["evidence"]["official"]["source_excerpt"]
    assert review["source_quotes_validated"] is False         # 원본엔 있어도 보내지 않은 문장은 근거로 받지 않는다


def test_short_judgment_is_not_marked_truncated_even_when_masked():
    text = "【이유】 원고 홍길동(010-1234-5678)에 대하여 " + QUOTE
    _, review = run_review(text, [QUOTE])
    assert review["source_truncated"] is False                # 마스킹으로 줄어든 길이를 절단으로 보지 않는다


# --- 2판: 전문 한 번 가리기·맥락 검토 일치·예산 초과 미호출·응답 형식 문구 ------------------------------------------
def masking_engine(tmp):
    from packages.pii_engine import PIIEngine, PseudonymStore
    return PIIEngine(PseudonymStore("tk131", root=Path(tmp)))


def test_projection_matches_whole_text_masking_and_expands_boundaries():
    from packages.legal_engine.evidence_pack import project_masked
    text = judgment().replace(QUOTE, "원고 측 연락처는 010-2345-6789이다. " + QUOTE)
    pack = build_evidence_pack(text, quotes=[QUOTE])
    with tempfile.TemporaryDirectory() as tmp:
        result = masking_engine(tmp).mask_text(text)
    masked, projected = project_masked(text, result, pack["segments"])
    assert masked == result.masked_text
    for seg in projected:
        assert seg["text"] == masked[seg["masked_start"]:seg["masked_end"]]
        assert "010-2345-6789" not in seg["text"]
    # 경계가 연락처 한가운데에 걸린 구간은 연락처 전체를 가린 글자로 넓힌다
    at = text.index("010-2345-6789") + 4
    _, [cut] = project_masked(text, result, [{"segment_id": "S0", "original_start": at, "original_end": at + 200}])
    assert cut["text"].startswith("[") and "2345" not in cut["text"]


def test_context_review_accepts_quotes_from_the_sent_masked_segments():
    from packages.legal_engine.argument_validity_verifier import _context_review
    from packages.common.enums import ExternalAIPolicy
    text = judgment().replace(QUOTE, "담당자 홍길동(010-2345-6789)의 확인에 따르면 " + QUOTE)
    verdict = {"citation_id": "CIT_TK131", "review_id": None, "official_record": {"full_text": text}}
    with tempfile.TemporaryDirectory() as tmp:
        engine = masking_engine(tmp)
        sent, review = run_review(text, [QUOTE], pii=engine)
        assert "010-2345-6789" not in sent["evidence"]["official"]["source_excerpt"]
        context = _context_review(verdict, [review], lambda t: engine.mask_text(t).masked_text)
    assert context["status"] == "ADVISORY_REVIEWED" and context["opinions"]


@pytest.mark.parametrize("start,end,expected", [(8, 12, "UNVERIFIED"), (2, 8, "ADVISORY_REVIEWED")])
def test_context_review_requires_quote_within_one_sent_segment(start, end, expected):
    from packages.legal_engine.argument_validity_verifier import _context_review
    text = "가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허"        # 글자가 겹치지 않는 합성 원문
    quote = text[start:end]
    review = {"citation_id": "C", "review_id": None, "model_executed": True, "source_quotes_validated": True,
              "evidence_quotes": [quote], "reason": "합성",
              "stages": [{"used": True, "verdict": {"status": "VERIFIED", "rationale": "합성", "evidence_quotes": [quote]}}],
              "evidence_pack": {"segments": [{"masked_start": 0, "masked_end": 10}, {"masked_start": 20, "masked_end": 30}]}}
    verdict = {"citation_id": "C", "review_id": None, "official_record": {"full_text": text}}
    assert _context_review(verdict, [review])["status"] == expected


def test_insufficient_context_skips_the_model_call(monkeypatch):
    import packages.legal_engine.evidence_pack as ep
    monkeypatch.setattr(ep, "DEFAULT_BUDGET", 500)
    original = ep.build_evidence_pack
    monkeypatch.setattr(ep, "build_evidence_pack", lambda *a, **k: original(*a, **{**k, "budget": 500}))
    sent, review = run_review(judgment(), [QUOTE])
    assert sent == {}                                          # 모델 호출 0
    assert review["status"] == "UNVERIFIED" and review["model_executed"] is False


def test_verdict_format_no_longer_claims_full_text():
    from packages.llm_router.router import _VERDICT_FORMAT
    assert "공식 전문" not in _VERDICT_FORMAT and "제공된 공식 원문" in _VERDICT_FORMAT
