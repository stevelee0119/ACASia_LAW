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
                "citation_ids": ["CIT_1"],
            },
            {
                "claim_id": "CL_2",
                "text": "피고 김철수의 주장은 배척된다.",
                "page": 4,
                "span": [200, 250],
                "status": "CONTRADICTED",
                "citation_ids": ["CIT_2"],
            },
        ],
        engine_data={
            "legal_verdicts": [
                {
                    "citation_id": "CIT_1",
                    "status": "VERIFIED",
                    "levels": {"level1": "VERIFIED", "level3": "CONTRADICTED"},
                    "review": {"quote_span": {"field": "full_text+holding+summary", "normalization": "normalize_quote",
                                              "start": 300, "end": 312, "similarity": 1.0}},
                    "reference_date": "2024-01-01",
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
            # TK-248: 생산 함수(source_review.case_applicability_review)와 같은 꼴. 결론은 applies_to_case로만 표시된다.
            "case_applicability_reviews": [
                {"citation_id": "CIT_1", "status": "REVIEW_NEEDED", "applies_to_case": True,
                 "source_record_ids": ["SR_1"], "sections": {"rules": [{"excerpt": "e", "span": [40, 60]}]}},
                {"citation_id": "CIT_2", "status": "REVIEW_NEEDED", "applies_to_case": False,
                 "source_record_ids": [], "sections": {}},
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

    # Pos 2 (TK-248): 주장 판정은 사건 적용성 검토의 명시적 결론(applies_to_case)에서만 온다.
    judgments = [c["judgment"] for c in dims["claim_applicability"]]
    assert judgments == ["SUPPORTS", "CONTRADICTS"]
    assert [c["judgment_basis"] for c in dims["claim_applicability"]] == ["APPLICABILITY_REVIEW"] * 2
    # 근거 구간은 공식 원문 좌표(적용성 검토가 고정한 발췌)이고, 서면 위치는 submitted_span에 따로 둔다.
    assert dims["claim_applicability"][0]["evidence_spans"] == [
        {"citation_id": "CIT_1", "section": "rules", "span": [40, 60], "length": 20, "source_record_ids": ["SR_1"]}
    ]
    assert dims["claim_applicability"][1]["evidence_spans"] == []
    assert dims["claim_applicability"][0]["submitted_span"] == {
        "document_id": "doc_4d_1",
        "page": 2,
        "span": [80, 140],
        "length": 60,
    }
    assert dims["claim_applicability"][0]["citation_identity"] == [{"citation_id": "CIT_1", "status": "VERIFIED"}]
    assert dims["claim_applicability"][0]["as_of"] == "2024-01-01"

    # Pos 3: source_retrieval carries source_name, status, matched_count, cause, official_span
    assert dims["source_retrieval"][0]["source_name"] == "law_go_kr"
    assert dims["source_retrieval"][0]["matched_count"] == 1
    assert dims["source_retrieval"][0]["cause"] == "MATCHED"
    # TK-248: official_span은 공식 원문 좌표만 담는다. 서면 위치는 submitted_span.
    assert dims["source_retrieval"][0]["official_span"] == {
        "field": "full_text+holding+summary", "normalization": "normalize_quote", "start": 300, "end": 312, "similarity": 1.0}
    assert dims["source_retrieval"][0]["official_span_status"] == "AVAILABLE"
    assert dims["source_retrieval"][0]["submitted_span"]["length"] == 25
    assert dims["source_retrieval"][1]["official_span"] is None
    assert dims["source_retrieval"][1]["official_span_status"] == "NOT_AVAILABLE"


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


def test_tk248_existence_is_not_claim_support():
    """TK-248 대조: 인용 존재·주장 상태·순번만으로는 SUPPORTS/CONTRADICTS가 나오지 않는다."""
    cits = [{"citation_id": "C1", "raw_text": "판례", "page": 1, "span": [0, 4]},
            {"citation_id": "C2", "raw_text": "판례2", "page": 1, "span": [5, 9]}]
    verdicts = [{"citation_id": "C1", "status": "VERIFIED", "levels": {"level1": "VERIFIED"}},
                {"citation_id": "C2", "status": "NOT_FOUND", "levels": {"level1": "NOT_FOUND"}}]
    # Ctrl A: 존재 확인 + 적용성 미정(운영 꼴) -> INSUFFICIENT
    # Ctrl B: 존재 없음 -> CONTRADICTS 아님
    # Ctrl C: 주장 자체 status VERIFIED만 -> SUPPORTS 아님
    # Ctrl D: 적용성 결과가 다른 인용 것이면 순번이 같아도 쓰지 않는다
    res = DocumentResult(document_id="d", filename="d.pdf", citations=cits, claims=[
        {"claim_id": "A", "text": "a", "citation_ids": ["C1"]},
        {"claim_id": "B", "text": "b", "citation_ids": ["C2"]},
        {"claim_id": "C", "text": "c", "status": "VERIFIED"},
    ], engine_data={"legal_verdicts": verdicts, "case_applicability_reviews": [
        {"citation_id": "C9", "status": "REVIEW_NEEDED", "applies_to_case": True},
        {"citation_id": "C1", "status": "REVIEW_NEEDED", "applies_to_case": None},
    ]})
    rows = {c["claim_id"]: c for c in build_evaluation_dimensions(res, doc_sha256="x")["claim_applicability"]}
    assert {k: v["judgment"] for k, v in rows.items()} == {"A": "INSUFFICIENT", "B": "INSUFFICIENT", "C": "INSUFFICIENT"}
    assert rows["A"]["judgment_basis"] == "APPLICABILITY_NOT_DETERMINED"
    assert rows["A"]["applicability_statuses"] == ["REVIEW_NEEDED"]
    assert rows["B"]["judgment_basis"] == "NOT_ASSESSED"
    assert rows["B"]["citation_identity"] == [{"citation_id": "C2", "status": "NOT_FOUND"}]
    # Ctrl E: 같은 주장에 적용·비적용이 함께 있으면 INSUFFICIENT(충돌)
    res2 = DocumentResult(document_id="d", filename="d.pdf", citations=cits,
                          claims=[{"claim_id": "K", "text": "k", "citation_ids": ["C1", "C2"]}],
                          engine_data={"legal_verdicts": verdicts, "case_applicability_reviews": [
                              {"citation_id": "C1", "applies_to_case": True}, {"citation_id": "C2", "applies_to_case": False}]})
    k = build_evaluation_dimensions(res2, doc_sha256="x")["claim_applicability"][0]
    assert (k["judgment"], k["judgment_basis"]) == ("INSUFFICIENT", "APPLICABILITY_CONFLICT")
