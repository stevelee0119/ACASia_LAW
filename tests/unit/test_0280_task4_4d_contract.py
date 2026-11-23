from __future__ import annotations

import json

from packages.verification_engine.eval_contract import build_evaluation_dimensions
from packages.verification_engine.pipeline import DocumentResult


def _sample_doc_result() -> DocumentResult:
    return DocumentResult(
        document_id="doc_4d_1",
        filename="brief.pdf",
        citations=[
            {
                "citation_id": "CIT_1",
                "raw_text": "대법원 2020다12345 판결",
                "quoted_text": "손해배상 책임이 인정된다.",
                "page": 2,
                "span": [100, 125],
            },
            {
                "citation_id": "CIT_2",
                "raw_text": "민법 제750조",
                "quoted_text": "",
                "page": 3,
                "span": [10, 20],
            },
        ],
        claims=[
            {
                "claim_id": "CL_1",
                "text": "원고 홍길동의 청구는 이유 있다.",
                "page": 2,
                "span": [80, 140],
                "status": "VERIFIED",
            },
            {
                "claim_id": "CL_2",
                "text": "피고 김철수의 주장은 배척된다.",
                "page": 4,
                "span": [200, 250],
                "status": "CONTRADICTED",
            },
        ],
        engine_data={
            "legal_verdicts": [
                {
                    "citation_id": "CIT_1",
                    "status": "VERIFIED",
                    "levels": {"level1": "VERIFIED", "level3": "CONTRADICTED"},
                    "source_lookup": {"source": "law_go_kr", "status": "READY", "matched_count": 1, "cause": "MATCHED"},
                    "findings": [],
                },
                {
                    "citation_id": "CIT_2",
                    "status": "UNVERIFIED",
                    "levels": {"level1": "UNVERIFIED"},
                    "source_lookup": {"source": "law_go_kr", "status": "DISABLED", "matched_count": 0, "cause": "DISABLED"},
                    "findings": [],
                },
            ],
            "case_applicability_reviews": [
                {"verdict": "VERIFIED"},
                {"verdict": "CONTRADICTED"},
            ],
        },
    )


def test_4d_contract_positives():
    res = _sample_doc_result()
    dims = build_evaluation_dimensions(res, doc_sha256="abc123")

    # Pos 1: All 4 independent dimensions present
    assert set(dims.keys()) == {"identity", "quote", "claim_applicability", "source_retrieval"}
    assert len(dims["identity"]) == 2
    assert len(dims["quote"]) == 1  # only CIT_1 has quoted_text

    # Pos 2: claim_applicability maps to SUPPORTS / CONTRADICTS with evidence_spans
    judgments = [c["judgment"] for c in dims["claim_applicability"]]
    assert judgments == ["SUPPORTS", "CONTRADICTS"]
    assert dims["claim_applicability"][0]["evidence_spans"][0] == {
        "document_id": "doc_4d_1",
        "page": 2,
        "span": [80, 140],
        "length": 60,
    }

    # Pos 3: source_retrieval carries source_name, status, matched_count, cause, official_span
    assert dims["source_retrieval"][0]["source_name"] == "law_go_kr"
    assert dims["source_retrieval"][0]["matched_count"] == 1
    assert dims["source_retrieval"][0]["cause"] == "MATCHED"
    assert dims["source_retrieval"][0]["official_span"]["length"] == 25


def test_4d_contract_controls_and_pii_masking():
    res = _sample_doc_result()
    dims = build_evaluation_dimensions(res, doc_sha256="abc123")
    serialized = json.dumps(dims, ensure_ascii=False)

    # Ctrl 1: No raw PII / party names / raw claim text leaked into exported 4D structure
    assert "홍길동" not in serialized
    assert "김철수" not in serialized
    assert "손해배상 책임이 인정된다" not in serialized

    # Ctrl 2: item_ids are unique and dimension-prefixed across all 4 dimensions
    all_ids = [item["item_id"] for rows in dims.values() for item in rows]
    assert len(all_ids) == len(set(all_ids))

    # Ctrl 3: Empty DocumentResult produces empty 4D lists without error, unknown claim status maps to INSUFFICIENT
    empty_dims = build_evaluation_dimensions(DocumentResult(document_id="empty", filename="e.pdf"), doc_sha256="000")
    assert empty_dims == {"identity": [], "quote": [], "claim_applicability": [], "source_retrieval": []}
    unk = build_evaluation_dimensions(
        DocumentResult(document_id="u", filename="u.pdf", claims=[{"claim_id": "C0", "text": "x", "status": "PENDING"}]),
        doc_sha256="000",
    )
    assert unk["claim_applicability"][0]["judgment"] == "INSUFFICIENT"
