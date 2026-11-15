"""TK-174: Drive 참고자료 AI 대조가 끝나지 못했을 때 미확인 항목 사유에 실제 원인을 적는다(0.20.0 온라인 case9 관찰 O2).

온라인 실행에서 모델 의견 1건이 원문에 없는 발췌를 대서 버려졌는데(QUOTE_NOT_GROUNDED), 미확인 항목 사유는 상태 사유
'원문 발췌 일치만 확인(…)'으로 나와 원인을 알 수 없었다. 문장·자료는 시험용 합성이다.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from packages.common.config import get_settings
from packages.common.storage import sha256_file
from packages.rag_engine.library import ReferenceLibrary
from packages.rag_engine.review import incomplete_reason
from packages.verification_engine.pipeline import DocumentInput, ProjectContext, VerificationPipeline, VerificationProfile


def test_rejected_opinions_are_counted_by_reason():
    review = {"reason": "EXACT_QUOTES_CHECKED_NOT_ENTAILMENT_OR_LEGAL_VALIDITY", "document_truncated": False,
              "rejected_observations": [{"index": 0, "reason": "QUOTE_NOT_GROUNDED"},
                                        {"index": 3, "reason": "QUOTE_NOT_GROUNDED"},
                                        {"index": 4, "reason": "INVALID_ITEM_SCHEMA"}]}
    text = incomplete_reason(review)
    assert text == "모델 의견 3건을 근거 확인에서 제외(인용 발췌가 원문에서 확인되지 않음 2건, 의견 항목 형식 오류 1건)"
    assert "EXACT_QUOTES" not in text and "원문 발췌 일치만 확인" not in text


def test_truncated_document_names_the_inspected_share():
    review = {"reason": "EXACT_QUOTES_CHECKED_NOT_ENTAILMENT_OR_LEGAL_VALIDITY", "document_truncated": True,
              "rejected_observations": [], "input": {"inspected_chars": 12000, "available_chars": 30500}}
    assert incomplete_reason(review) == "서면이 길어 앞부분(12,000자/30,500자)만 대조"


def test_both_causes_are_listed_together():
    review = {"document_truncated": True, "rejected_observations": [{"reason": "INVALID_ENVELOPE"}], "input": {}}
    assert incomplete_reason(review) == "모델 의견 1건을 근거 확인에서 제외(응답 전체 형식 오류 1건); 서면이 길어 앞부분(일부)만 대조"


@pytest.mark.parametrize("reason", ["MODEL_NOT_AVAILABLE_OR_QUICK_PROFILE", "REFERENCE_REVIEW_FAILED", ""])
def test_other_incomplete_states_keep_their_status_reason_in_korean_words(reason):
    text = incomplete_reason({"reason": reason, "document_truncated": False, "rejected_observations": []})
    assert text and "_" not in text


def test_pipeline_unverified_item_names_the_dropped_opinion(tmp_path: Path, monkeypatch):
    doc_path = tmp_path / "synthetic_brief.txt"
    doc_path.write_text("원고는 가상 규정 제3조에 따라 위약금 전액을 청구한다.", encoding="utf-8")

    def fake_sync(self, query=None):
        self.summary.update(status="READY", files_seen=1, files_indexed=1, checked_at="2026-11-14T00:00:00Z", issues=[])

    def fake_review_document(document_result, references, router, context, pii):
        review = {"status": "ADVISORY_REVIEWED", "reason": "EXACT_QUOTES_CHECKED_NOT_ENTAILMENT_OR_LEGAL_VALIDITY",
                  "sources": [], "observations": [], "rejected_observations": [{"index": 1, "reason": "QUOTE_NOT_GROUNDED"}],
                  "model_executed": True, "review_completed": False, "document_truncated": False}
        document_result.engine_data["rag"] = review
        return review

    monkeypatch.setattr(ReferenceLibrary, "sync", fake_sync)
    monkeypatch.setattr("packages.rag_engine.review.review_document", fake_review_document)
    pipeline = VerificationPipeline()
    pipeline.settings = replace(get_settings(), rag_drive_folder_id="synthetic_folder", allow_network=False)
    doc = DocumentInput("doc1", str(doc_path), doc_path.name, sha256=sha256_file(doc_path), mime_type="text/plain")
    result = pipeline.run("tk174", ProjectContext("tk174", profile=VerificationProfile.QUICK), [doc])
    [item] = [i for i in result.unverified_items if i.get("kind") == "reference_review"]
    assert item["reason"] == ("Drive 참고자료 AI 대조 미완료: 모델 의견 1건을 근거 확인에서 제외"
                              "(인용 발췌가 원문에서 확인되지 않음 1건)")
