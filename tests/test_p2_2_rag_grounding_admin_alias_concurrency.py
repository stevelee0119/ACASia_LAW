"""Synthetic unit tests for P2-2: full-doc analysis_text grounding, chunked/concurrent RAG review,
document-wide ADMIN_RULE alias matching, and bounded LLM opinion concurrency.

Strictly synthetic fixtures and controls only — zero test brief or case literals.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

from packages.common.enums import (
    AdapterStatus,
    CitationType,
    ExternalAIPolicy,
    LLMRole,
    VerificationProfile,
    VerificationStatus,
)
from packages.common.schemas import Block, Citation, NormalizedDocument, Page
from packages.document_engine.analysis_text import analysis_text
from packages.legal_engine.argument_validity_verifier import (
    ArgumentValidityResult,
    _attach_ai_opinions,
)
from packages.legal_engine.citation_extractor import extract_citations
from packages.legal_engine.source_review import verify_admin_rule_source
from packages.legal_engine.verifier import LegalVerifier
from packages.llm_router.router import ModelExecution, RouterResult
from packages.rag_engine.provision_quotes import check_quoted_provisions
from packages.rag_engine.reference_binding import identifier, identifier_match
from packages.rag_engine.review import review_document
from packages.source_adapters.base import AdapterResponse
from packages.verification_engine.pipeline import DocumentResult, ProjectContext


ROOT = Path(__file__).resolve().parents[1]


def _make_long_doc(front_len: int, tail_sentence: str, doc_id: str = "doc_long") -> NormalizedDocument:
    filler = "합성 준비서면의 일반적인 경위 설명 문장입니다. " * (front_len // 26 + 1)
    front = filler[:front_len]
    blocks = [
        Block("b1", front, 1),
        Block("b2", tail_sentence, 2),
    ]
    return NormalizedDocument(
        doc_id,
        "synthetic_long.txt",
        "text/plain",
        hashlib.sha256((front + tail_sentence).encode("utf-8")).hexdigest(),
        pages=[Page(1, blocks=[blocks[0]]), Page(2, blocks=[blocks[1]])],
    )


# ---------------------------------------------------------------------------
# 1. analysis_text default full-document grounding & explicit limit controls
# ---------------------------------------------------------------------------
def test_analysis_text_default_grounds_beyond_12000_chars_with_limit_controls():
    tails = [
        "제2쪽 후반부 결론: 보관 절차 미이행으로 인한 시정 의무가 인정된다.",
        "제2쪽 후반부 요지: 기록 보존 기간 5년 준수 여부가 쟁점이다.",
        "제2쪽 후반부 정리: 운송 점검표 서명 누락이 확인된다.",
    ]
    for idx, tail in enumerate(tails, 1):
        doc = _make_long_doc(29000, tail, doc_id=f"doc_p_{idx}")
        selected, meta = analysis_text(doc)
        assert tail in selected
        assert meta["omitted_chars"] == 0
        assert meta["inspected_chars"] == meta["available_chars"] > 29000
        assert meta["is_full_document"] is True

        # Controls: explicit limit=100, limit=5000, limit=12000 still truncate deterministically
        for lim in (100, 5000, 12000):
            trunc, tmeta = analysis_text(doc, limit=lim)
            assert len(trunc) == lim
            assert tail not in trunc
            assert tmeta["omitted_chars"] == tmeta["available_chars"] - lim
            assert tmeta["is_full_document"] is False


# ---------------------------------------------------------------------------
# 2. Chunked >40k RAG review + late-document grounding + bounded concurrency
# ---------------------------------------------------------------------------
def test_review_document_covers_full_29k_and_chunks_over_40k_concurrently():
    tail_claim = "후반부 핵심 주장: 가상전송규정 제9조는 사전 서면 동의를 필수 요건으로 정한다."
    doc_norm = _make_long_doc(29000, tail_claim, doc_id="doc_29k")
    res = DocumentResult("doc_29k", "synthetic_29k.txt", normalized=doc_norm)
    res.claims = [{"claim_id": "CLM_TAIL", "type": "LEGAL_ARGUMENT", "text": tail_claim}]
    res.citations = []

    sources = [
        {
            "file_id": f"f{i}",
            "source_id": f"R{i}",
            "title": f"가상규정_{i}.txt",
            "folder_path": "",
            "page": 1,
            "relevance": 0.9,
            "text": "가상전송규정 제9조 사전 서면 동의 필수 요건에 관한 참고 원문 내용이다.",
        }
        for i in range(1, 5)
    ]

    lib = SimpleNamespace(
        summary={"status": "READY", "snapshot_hash": "hash_29k"},
        select=lambda _q: {
            "decision": "USED",
            "reason": "RELEVANT_REFERENCE_FOUND",
            "coverage": "FULL",
            "sources": list(sources),
        },
        has_case_tables=lambda: False,
    )

    class Router29k:
        def __init__(self):
            self.reqs = []

        def has_available_provider(self, **kwargs):
            return True

        async def run(self, role, request, **kwargs):
            self.reqs.append(request)
            stage = (request.metadata or {}).get("stage")
            obs = []
            if stage == "drive_rag_advisory":
                obs = [{
                    "claim_quote": tail_claim,
                    "source_id": "R1",
                    "source_quote": "가상전송규정 제9조 사전 서면 동의 필수 요건에 관한 참고 원문 내용이다.",
                    "relationship": "SUPPORTS",
                    "explanation": "후반부 주장이 참고자료와 일치함.",
                }]
            return RouterResult(
                used=True,
                parsed={"observations": obs},
                executions=[ModelExecution("PRIMARY_REASONER", "stub", "m", True)],
            )

    router = Router29k()
    context = ProjectContext("p2_2", profile=VerificationProfile.STANDARD, external_ai_policy=ExternalAIPolicy.ORIGINAL)
    pii = SimpleNamespace(mask_text=lambda t: SimpleNamespace(masked_text=t))
    review = review_document(res, lib, router, context, pii)

    assert not review["document_truncated"]
    drive_reqs = [r for r in router.reqs if (r.metadata or {}).get("stage") == "drive_rag_advisory"]
    assert len(drive_reqs) == 1
    sent_doc = json.loads(drive_reqs[0].user)["document"]
    assert tail_claim in sent_doc
    assert review["status"] == "ADVISORY_REVIEWED"
    assert any(o["claim_quote"] == tail_claim for o in review["observations"])

    # Over 40,000 chars: split into overlapping chunks and execute chunks concurrently
    tail_45k = "최종쪽 청크 결론: 가상검증지침 제12조의 점검 주기 위반이 인정된다."
    doc_45k = _make_long_doc(45000, tail_45k, doc_id="doc_45k")
    res_45k = DocumentResult("doc_45k", "synthetic_45k.txt", normalized=doc_45k)
    res_45k.claims = []
    res_45k.citations = []

    active = [0]
    peak = [0]

    class ConcurrentRouter:
        def __init__(self):
            self.docs_seen = []

        def has_available_provider(self, **kwargs):
            return True

        async def run(self, role, request, **kwargs):
            active[0] += 1
            peak[0] = max(peak[0], active[0])
            await asyncio.sleep(0.02)
            active[0] -= 1
            body = json.loads(request.user)["document"]
            self.docs_seen.append(body)
            obs = []
            if tail_45k in body:
                obs = [{
                    "claim_quote": tail_45k,
                    "source_id": "R1",
                    "source_quote": "가상전송규정 제9조 사전 서면 동의 필수 요건에 관한 참고 원문 내용이다.",
                    "relationship": "CONTEXT",
                    "explanation": "둘째 청크 후반부 확인.",
                }]
            return RouterResult(
                used=True,
                parsed={"observations": obs},
                executions=[ModelExecution("PRIMARY_REASONER", "stub", "m", True)],
            )

    c_router = ConcurrentRouter()
    rev_45k = review_document(res_45k, lib, c_router, context, pii)
    assert len(c_router.docs_seen) == 2
    assert tail_45k in c_router.docs_seen[-1]
    assert peak[0] == 2
    assert any(o["claim_quote"] == tail_45k for o in rev_45k["observations"])


def test_review_document_claim_wave_runs_concurrently_bounded():
    claims = [
        {"claim_id": f"CLM_{i}", "type": "FACT", "text": f"합성 주장 번호 {i}의 보관 절차 이행 주장입니다."}
        for i in range(1, 7)
    ]
    doc_text = "\n".join(c["text"] for c in claims)
    doc_norm = _make_long_doc(200, claims[0]["text"], doc_id="doc_claims")
    doc_norm.pages[0].blocks[0].text = doc_text
    doc_norm.pages = doc_norm.pages[:1]
    res = DocumentResult("doc_claims", "claims.txt", normalized=doc_norm)
    res.claims = claims
    res.citations = []

    lib = SimpleNamespace(
        summary={"status": "READY", "snapshot_hash": "h"},
        select=lambda _q: {
            "decision": "USED", "reason": "OK", "coverage": "FULL",
            "sources": [{"file_id": "f1", "source_id": "R1", "title": "가상규정.txt", "page": 1,
                         "text": "보관 절차 이행 기준은 모든 항목에 동일하게 적용된다."}],
        },
        has_case_tables=lambda: False,
    )

    active_claims = [0]
    peak_claims = [0]

    class WaveRouter:
        def has_available_provider(self, **kwargs):
            return True

        async def run(self, role, request, **kwargs):
            is_claim = (request.metadata or {}).get("stage") == "claim_rag_advisory"
            if is_claim:
                active_claims[0] += 1
                peak_claims[0] = max(peak_claims[0], active_claims[0])
            await asyncio.sleep(0.02)
            if is_claim:
                active_claims[0] -= 1
            return RouterResult(used=True, parsed={"observations": []},
                                executions=[ModelExecution("PRIMARY_REASONER", "stub", "m", True, cost_usd=0.0)])

    t0 = time.monotonic()
    context = ProjectContext("p2_2", profile=VerificationProfile.STANDARD, external_ai_policy=ExternalAIPolicy.ORIGINAL)
    pii = SimpleNamespace(mask_text=lambda t: SimpleNamespace(masked_text=t))
    rev = review_document(res, lib, WaveRouter(), context, pii)
    elapsed = time.monotonic() - t0

    assert rev["status"] == "REVIEWED_NO_ADVICE"
    assert peak_claims[0] == 4  # Semaphore caps claim wave concurrency at 4
    assert elapsed < 0.5


# ---------------------------------------------------------------------------
# 3. ADMIN_RULE alias resolution across extraction, source_review, binding, quotes
# ---------------------------------------------------------------------------
def test_admin_rule_alias_extraction_and_source_review():
    # 3+ positive cases across long gap, explicit definition, and Drive match
    filler = "본문 설명 단락입니다. " * 60  # > 700 chars gap (beats old 600-char cap)
    text = (
        "「가상 야간 점검 안전 운영지침」(이하 '점검지침'이라 한다) 제3조는 기본 절차를 정한다.\n"
        + filler +
        "또한 '점검지침' 제5조는 예외를 두며, 위 지침 제7조는 기록 의무를 정한다.\n"
        "'가상 교육 훈련 예규'(이하 '훈련예규'이라 한다) 제2조 및 '훈련예규' 제4조를 본다.\n"
        "「가상 시설 보안 훈령」은 기준을 두고 " + filler + " 동 훈령 제9조는 승인 절차를 정한다."
    )
    doc = NormalizedDocument(
        "doc_alias", "alias.txt", "text/plain", "h",
        pages=[Page(1, blocks=[Block("b1", text, 1)])],
    )
    citations = extract_citations(doc)
    by_art = {(c.article, c.law_name): c for c in citations if c.type == CitationType.ADMIN_RULE}

    assert ("5", "점검지침") in by_art
    assert by_art[("5", "점검지침")].attributes.get("law_alias_candidate") == "가상 야간 점검 안전 운영지침"
    assert by_art[("5", "점검지침")].attributes.get("law_alias_basis") == "DOCUMENT_DEFINITION"
    assert ("7", "가상 야간 점검 안전 운영지침") in by_art
    assert ("9", "가상시설보안훈령") in by_art
    assert ("4", "훈련예규") in by_art
    assert by_art[("4", "훈련예규")].attributes.get("law_alias_candidate") == "가상교육훈련예규"

    # Source review retry via alias + fallback to read Drive references (positive + negative controls)
    queries = []

    class FakeLawAdapter:
        def search_admin_rule(self, name):
            queries.append(name)
            if name == "가상 야간 점검 안전 운영지침":
                return AdapterResponse(AdapterStatus.READY, [{
                    "source_id": "10", "rule_name": "가상 야간 점검 안전 운영지침",
                    "agency": "가상부", "rule_kind": "지침", "effective_from": "2025-01-01",
                }], complete=True)
            return AdapterResponse(AdapterStatus.READY, [], complete=True)

        def fetch_admin_rule(self, rec):
            return AdapterResponse(AdapterStatus.READY, [{
                "full_text": "제5조(예외) 본문", "articles": ["5"], "article_texts": {"5": "제5조(예외) 본문"},
            }], complete=True)

    verifier = LegalVerifier(SimpleNamespace(law=FakeLawAdapter()))
    verdict = verify_admin_rule_source(verifier, by_art[("5", "점검지침")])
    assert queries == ["점검지침", "가상 야간 점검 안전 운영지침"]
    assert verdict.levels["existence"] == "VERIFIED"
    assert verdict.levels["article"] == "VERIFIED"

    # Drive read reference fallback for internal guideline absent from official DB
    verifier_drive = LegalVerifier(SimpleNamespace(law=FakeLawAdapter()))
    verifier_drive.user_references = ["[RAG참고자료] 가상 교육 훈련 예규.pdf"]
    v_drive = verify_admin_rule_source(verifier_drive, by_art[("4", "훈련예규")])
    assert v_drive.levels["existence"] == "FOUND_IN_USER_REFERENCES"
    assert v_drive.status == VerificationStatus.PARTIALLY_VERIFIED

    # Controls: unknown rule with no alias and no matching Drive ref stays NOT_FOUND
    for neg_name in ("미등록 가상 지침", "없는 보안 예규", "가상 내부 요령"):
        c_neg = Citation.create(CitationType.ADMIN_RULE, f"{neg_name} 제1조", document_id="d",
                                law_name=neg_name, article="1")
        v_neg = verify_admin_rule_source(verifier_drive, c_neg)
        assert v_neg.status == VerificationStatus.NOT_FOUND


def test_reference_binding_and_app_js_admin_rule_alias_parity():
    app_js = (ROOT / "apps/web/static/app.js").read_text(encoding="utf-8")
    start = app_js.index("const EXPLICIT_WHITESPACE_RE")
    end = app_js.index("function referenceObservationBlock", start)
    js_helpers = app_js[start:end]

    pos_cases = [
        ({"citation_id": "c1", "law_name": "운영지침", "article": "5",
          "attributes": {"law_alias_candidate": "가상안전운영지침"}},
         "「가상안전운영지침」 제5조는 사전 보고 의무를 정한다.", True, False),
        ({"citation_id": "c2", "raw_text": "가상보안예규 제3조"},
         "「가상보안예규」 제3조에 따라 승인한다.", True, False),
        ({"citation_id": "c3", "law_name": "가상점검훈령", "article": "8", "paragraph": "1"},
         "가상점검훈령 제8조(점검) ① 매월 점검한다.", True, False),
    ]
    neg_cases = [
        ({"citation_id": "n1", "law_name": "운영지침", "article": "5",
          "attributes": {"law_alias_candidate": "가상안전운영지침"}},
         "다른가상안전운영지침 제5조는 별개의 규정이다.", False, False),
        ({"citation_id": "n2", "law_name": "운영지침", "article": "5",
          "attributes": {"law_alias_candidate": "가상안전운영지침"}},
         "「가상안전운영지침」 제12조는 다른 조항이다.", False, True),
        ({"citation_id": "n3", "raw_text": "가상보안예규 제3조"},
         "가상보안예규률 제3조는 다른 규정이다.", False, False),
    ]

    all_cases = pos_cases + neg_cases
    py_results = [identifier_match(c, exc) for c, exc, _, _ in all_cases]
    for (c, _exc, exp_full, exp_conflict), py_res in zip(all_cases, py_results):
        assert identifier(c) is not None
        assert py_res["full"] is exp_full
        assert py_res["conflict"] is exp_conflict

    runner = js_helpers + """
const inputs = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = inputs.map(([c, exc]) => referenceIdentifierMatch(c, exc));
process.stdout.write(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "-e", runner],
        input=json.dumps([[c, exc] for c, exc, _, _ in all_cases], ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    js_results = json.loads(proc.stdout)
    assert js_results == py_results


def test_provision_quotes_resolves_admin_aliases_and_preserves_controls():
    ref_text = """가상 야간 보관 관리 지침
제5조 (외부 반출 제한)
① 담당자는 승인 없이 자료를 외부로 반출할 수 없다.
② 반출 승인 이력은 대장에 기록한다.
"""
    sources = [{"file_id": "f1", "source_id": "R1", "title": "[RAG참고자료] 가상 야간 보관 관리 지침.pdf", "text": ref_text}]

    # Positive 1: explicit alias definition + single-quoted alias citation
    doc_p1 = (
        "「가상 야간 보관 관리 지침」(이하 '보관지침'이라 한다)을 살펴본다.\n"
        "'보관지침' 제5조 제1항은 \"담당자가 자료를 외부로 반출할 수 있다\"고 정한다."
    )
    # Positive 2: unbracketed alias citation
    doc_p2 = (
        "「가상 야간 보관 관리 지침」(이하 '보관지침'이라 한다)에 의할 때, "
        "보관지침 제5조 제1항은 \"자료를 외부로 반출할 수 있다\"고 규정한다."
    )
    # Positive 3: anaphor ("위 지침") resolved past single-quoted intro
    doc_p3 = (
        "'가상 야간 보관 관리 지침'에 따르면 다음과 같다.\n"
        "위 지침 제5조 제1항은 \"승인 없이 외부로 반출할 수 있다\"고 정한다."
    )
    for doc in (doc_p1, doc_p2, doc_p3):
        obs = check_quoted_provisions(doc, sources)
        assert len(obs) == 1
        assert obs[0]["relationship"] == "CONTRADICTS"

    # Negative controls: mismatched quotes, different rule title, matching modal direction
    assert not check_quoted_provisions(
        "'보관지침」 제5조 제1항은 \"외부로 반출할 수 있다\"고 정한다.", sources
    )
    assert not check_quoted_provisions(
        "「다른 기관 보관 지침」(이하 '보관지침'이라 한다) '보관지침' 제5조 제1항은 \"외부로 반출할 수 있다\"고 정한다.",
        sources,
    )
    assert not check_quoted_provisions(
        "「가상 야간 보관 관리 지침」(이하 '보관지침'이라 한다) '보관지침' 제5조 제1항은 \"승인 없이 자료를 외부로 반출할 수 없다\"고 정한다.",
        sources,
    )


# ---------------------------------------------------------------------------
# 4. Bounded concurrency in _attach_ai_opinions preserves item ordering
# ---------------------------------------------------------------------------
def test_attach_ai_opinions_concurrent_batches_preserve_item_order():
    from packages.legal_engine.argument_validity_verifier import HallucinationTableRow

    items_count = 10  # 5 batches of _OPINION_BATCH=2 -> exceeds Semaphore(4)
    unverified_cases = [
        {
            "citation": Citation.create(CitationType.CASE, f"2098다{100 + i}", case_number=f"2098다{100 + i}", page=i),
            "basis": "UNCONFIRMED",
            "context": f"가상 판결 2098다{100 + i} 관련 주장 문맥입니다.",
        }
        for i in range(1, items_count + 1)
    ]

    active = [0]
    peak = [0]

    class FakeRouter:
        async def consult_all(self, role, request, **kwargs):
            active[0] += 1
            peak[0] = max(peak[0], active[0])
            req_items = json.loads(request.user)["items"]
            # Reverse sleep so later items finish faster if unguarded; gather must keep order
            await asyncio.sleep(0.01 * max(1, (items_count - req_items[0]["item_id"]) // 2))
            active[0] -= 1
            rows = [
                {
                    "item_id": it["item_id"],
                    "claim_text": f"주장 {it['item_id']}",
                    "validity_verdict": "판단 불가",
                    "legal_reasoning": f"검토 의견 {it['item_id']}",
                    "recommended_check": "확인 요망",
                }
                for it in req_items
            ]
            return [RouterResult(
                used=True,
                parsed={"overall_summary": f"요약 {req_items[0]['item_id']}", "rows": rows},
                executions=[ModelExecution("PRIMARY_REASONER", "stub", "m", True)],
            )]

    res = ArgumentValidityResult()
    res.rows = [
        HallucinationTableRow(
            location=f"{i}p",
            claim_text=f"초기 주장 {i}",
            cited_authority=f"2098다{100 + i}",
            authority_exists=False,
            ai_generation_basis="UNCONFIRMED",
            validity_verdict="미확인",
            legal_reasoning=f"초기 이유 {i}",
            recommended_counteraction="",
            item_id=i,
        )
        for i in range(1, items_count + 1)
    ]
    asyncio.run(
        _attach_ai_opinions(res, unverified_cases, FakeRouter(), ExternalAIPolicy.MASKED, mask=None)
    )
    assert peak[0] == 4  # Bounded by Semaphore(4)
    assert len(res.rows) == items_count
    for idx, row in enumerate(res.rows, start=1):
        assert row.ai_opinions[0]["reasoning"] == f"검토 의견 {idx}"
