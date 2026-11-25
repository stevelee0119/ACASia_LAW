"""TK-241 unit tests: REFERENCE_CONTRADICTION type separation, advisory_only=True, per-claim merge, and attribution guard."""
from __future__ import annotations

from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.verification_engine.candidate_verifier import ModelCandidate, verify_rag_candidate
from tests.test_tk70_rag_contradiction_promotion import _setup_pipeline_test


def test_tk241_pos1_19_sources_same_claim_merged_into_one(tmp_path, monkeypatch):
    """양성 1: 단일 주장에 대해 19개 참고자료 모순 관찰이 올라와도 주장 1건당 1건(REFERENCE_CONTRADICTION)으로 병합된다."""
    sources = [
        {"source_id": f"REF{i}", "title": f"참고자료_{i}.pdf", "text": f"규정 {i}: 사전 승인 없이 반출할 수 없다."}
        for i in range(1, 20)
    ]
    observations = [
        {
            "relationship": "CONTRADICTS",
            "claim_id": "C1",
            "claim_quote": "지체상금률 1/1000을 납부한다.",
            "source_id": f"REF{i}",
            "source_quote": "사전 승인 없이 반출할 수 없다.",
            "explanation": f"참고자료 {i}와 상충.",
            "advisory_only": True,
        }
        for i in range(1, 20)
    ]
    pipeline, context, doc_inputs = _setup_pipeline_test(tmp_path, monkeypatch, observations, sources)
    result = pipeline.run("tk241-merge", context, doc_inputs)
    promoted = [
        f for f in result.documents[0].findings
        if f.type == FindingType.REFERENCE_CONTRADICTION
    ]
    assert len(promoted) == 1
    assert promoted[0].advisory_only is True
    assert len(promoted[0].confidence_features["source_provenances"]) == 19
    assert not any(f.type == FindingType.FACT_CONTRADICTION for f in result.documents[0].findings)


def test_tk241_pos2_distinct_claims_remain_separate(tmp_path, monkeypatch):
    """양성 2: 서로 다른 2개 주장에 대한 참고자료 모순은 은폐되지 않고 각각 1건씩(총 2건) 유지된다."""
    sources = [
        {"source_id": "REF1", "title": "규정A.pdf", "text": "지체상금률 0.5/1000 적용."},
        {"source_id": "REF2", "title": "규정B.pdf", "text": "14일 이상 최고 필요."},
    ]
    observations = [
        {
            "relationship": "CONTRADICTS",
            "claim_id": "C1",
            "claim_quote": "지체상금률 1/1000을 납부한다.",
            "source_id": "REF1",
            "source_quote": "지체상금률 0.5/1000 적용.",
            "explanation": "비율 불일치.",
        },
        {
            "relationship": "CONTRADICTS",
            "claim_id": "C2",
            "claim_quote": "즉시 계약을 해제할 수 있다.",
            "source_id": "REF2",
            "source_quote": "14일 이상 최고 필요.",
            "explanation": "최고 기간 누락.",
        },
    ]
    pipeline, context, doc_inputs = _setup_pipeline_test(tmp_path, monkeypatch, observations, sources)
    result = pipeline.run("tk241-distinct", context, doc_inputs)
    promoted = [f for f in result.documents[0].findings if f.type == FindingType.REFERENCE_CONTRADICTION]
    assert len(promoted) == 2


def test_tk241_pos3_reference_contradiction_type_and_advisory():
    """양성 3: verify_rag_candidate(is_reference_contradiction=True)는 REFERENCE_CONTRADICTION·advisory_only=True·LOW/C를 반환한다."""
    cand = ModelCandidate(
        candidate_id="cand1",
        claim_quote="계약금은 반환하지 않는다.",
        defect_type="REFERENCE_CONTRADICTION",
        basis_quote="계약 해제 시 계약금은 반환한다.",
        source_id="REF1",
        explanation="반환 조항 상충",
    )
    f, rej = verify_rag_candidate(
        cand,
        "본 사건에서 계약금은 반환하지 않는다.",
        [{"source_id": "REF1", "title": "기준집", "text": "계약 해제 시 계약금은 반환한다."}],
        is_reference_contradiction=True,
    )
    assert rej is None
    assert f is not None
    assert f.type == FindingType.REFERENCE_CONTRADICTION
    assert f.advisory_only is True
    assert f.severity == Severity.LOW
    assert f.evidence_grade == EvidenceGrade.C


def test_tk241_ctrl1_opponent_reported_claim_not_promoted(tmp_path, monkeypatch):
    """대조 1: 상대방 주장을 전언·반박하는 문장의 참고자료 대조는 승격하지 않는다."""
    sources = [{"source_id": "REF1", "title": "규정.pdf", "text": "원상회복 의무를 부담한다."}]
    observations = [
        {
            "relationship": "CONTRADICTS",
            "claim_id": "C_OPP",
            "claim_quote": "피고는 원상회복 의무가 없다고 주장하나, 이는 타당하지 않습니다.",
            "source_id": "REF1",
            "source_quote": "원상회복 의무를 부담한다.",
            "explanation": "상대방 전언",
        }
    ]
    pipeline, context, doc_inputs = _setup_pipeline_test(tmp_path, monkeypatch, observations, sources)
    # Override doc text to include the opponent reported claim
    doc_inputs[0].content = b"dummy"
    from packages.common.schemas import Block, NormalizedDocument, Page
    norm = NormalizedDocument(document_id=doc_inputs[0].document_id, filename="brief.txt", mime_type="text/plain", sha256="x")
    p = Page(page_number=1)
    p.blocks.append(Block(block_id="b1", text="피고는 원상회복 의무가 없다고 주장하나, 이는 타당하지 않습니다.", page=1, source_layer="visible_text"))
    norm.pages.append(p)
    norm.raw_layers["visible_text"] = "피고는 원상회복 의무가 없다고 주장하나, 이는 타당하지 않습니다."
    monkeypatch.setattr("packages.verification_engine.pipeline.parse_document", lambda *a, **kw: norm)
    result = pipeline.run("tk241-opp", context, doc_inputs)
    assert not any(f.type == FindingType.REFERENCE_CONTRADICTION for f in result.documents[0].findings)


def test_tk241_ctrl2_supports_observation_not_promoted(tmp_path, monkeypatch):
    """대조 2: SUPPORTS 관계 관찰은 REFERENCE_CONTRADICTION으로 승격하지 않는다."""
    sources = [{"source_id": "REF1", "title": "규정.pdf", "text": "지체상금률 1/1000을 납부한다."}]
    observations = [
        {
            "relationship": "SUPPORTS",
            "claim_id": "C1",
            "claim_quote": "지체상금률 1/1000을 납부한다.",
            "source_id": "REF1",
            "source_quote": "지체상금률 1/1000을 납부한다.",
            "explanation": "부합",
        }
    ]
    pipeline, context, doc_inputs = _setup_pipeline_test(tmp_path, monkeypatch, observations, sources)
    result = pipeline.run("tk241-sup", context, doc_inputs)
    assert not any(f.type == FindingType.REFERENCE_CONTRADICTION for f in result.documents[0].findings)


def test_tk241_ctrl3_non_reference_candidate_keeps_b_grade():
    """대조 3: 일반 후보 승격(is_reference_contradiction=False)은 기존 B등급·advisory_only=False를 유지한다."""
    cand = ModelCandidate(
        candidate_id="cand2",
        claim_quote="지체상금률 1/1000을 납부한다.",
        defect_type="FACT_CONTRADICTION",
        basis_quote="지체상금률 0.5/1000 적용.",
        source_id="REF1",
        explanation="불일치",
    )
    f, rej = verify_rag_candidate(
        cand,
        "지체상금률 1/1000을 납부한다.",
        [{"source_id": "REF1", "title": "규정", "text": "지체상금률 0.5/1000 적용."}],
        is_reference_contradiction=False,
    )
    assert rej is None
    assert f is not None
    assert f.type == FindingType.FACT_CONTRADICTION
    assert f.evidence_grade == EvidenceGrade.B
    assert f.advisory_only is False
