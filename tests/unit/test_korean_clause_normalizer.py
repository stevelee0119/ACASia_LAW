"""Unit tests for Korean Legal Clause Normalizer (P1 PR-05).

Covers >= 3 positive and >= 3 control cases across polarity, speaker attribution,
modality, temporal aspect, and reading-text span traceability.
"""
from __future__ import annotations

from packages.common.schemas import Block, NormalizedDocument, Page
from packages.korean_nlp import get_tokenizer, normalize_document_clauses, normalize_sentence


def test_polarity_and_double_negation_resolution():
    # 3 positive/asserted (including double negation)
    asserted = [
        "당사자 사이의 약정은 유효하다.",
        "이 조항이 적용되지 않는다고 볼 수 없다.",
        "책임을 면할 수 있는 사유가 전혀 없지 아니하다.",
        "채무가 없지 않다.",
    ]
    for idx, sent in enumerate(asserted):
        clauses = normalize_sentence(sent, sentence_index=idx)
        assert clauses[0].polarity in ("ASSERTED", "DOUBLE_NEGATED_ASSERTED")

    # 3 negated controls
    negated = [
        "이 사건 계약은 유효하지 않다.",
        "상대방의 청구에는 정당한 사유가 없다.",
        "그 행위를 위법하다고 단정할 수 없다.",
    ]
    for idx, sent in enumerate(negated):
        clauses = normalize_sentence(sent, sentence_index=idx)
        assert clauses[0].polarity == "NEGATED"

    # Parallel / coordinated negations must split and stay NEGATED (never DOUBLE_NEGATED_ASSERTED)
    parallel_negated = [
        "피고는 서명하지 않았고 날인하지 않았다.",
        "당사자는 통지하지 않고 이행하지도 않았다.",
        "신청인은 출석하지 않았으며 답변서도 제출하지 않았다.",
    ]
    for idx, sent in enumerate(parallel_negated):
        clauses = normalize_sentence(sent, sentence_index=idx)
        assert len(clauses) >= 2
        assert all(c.polarity == "NEGATED" for c in clauses)


def test_speaker_attribution_and_opponent_summary():
    # 3 opponent / court reported speech cases
    reported = [
        ("피고는 이 사건 계약이 무효라고 주장하나, 이는 이유 없다.", "OPPONENT", "OPPONENT_SUMMARY"),
        ("원고 측은 시효가 완성되었다고 항변하지만 받아들이기 어렵다.", "OPPONENT", "OPPONENT_SUMMARY"),
        ("대법원 2019다12345 판결은 신의칙 위반에 해당한다고 판시하였다.", "COURT", "QUOTED_PRECEDENT"),
    ]
    for sent, exp_role, exp_attr in reported:
        clauses = normalize_sentence(sent)
        assert clauses[0].speaker_role == exp_role
        assert clauses[0].attribution_type == exp_attr

    # 3 direct author assertions
    direct = [
        "본 원고는 계약상 의무를 모두 이행하였다.",
        "당 소송대리인은 이 사건 처분의 취소를 구한다.",
        "임대차 보증금 반환 의무가 인정된다.",
    ]
    for sent in direct:
        clauses = normalize_sentence(sent)
        assert clauses[0].speaker_role == "AUTHOR"
        assert clauses[0].attribution_type == "DIRECT_ASSERTION"


def test_modality_and_temporal_aspect():
    # 3 hypothetical / interrogative (non-definitive)
    non_definitive = [
        ("설령 채무불이행이 인정된다 하더라도 손해는 발생하지 않았다.", "HYPOTHETICAL"),
        ("만약 기한이 도과되었다면 이행지체가 성립한다.", "HYPOTHETICAL"),
        ("이 사건 청구가 적법한지 여부가 문제된다.", "INTERROGATIVE"),
    ]
    for sent, exp_mod in non_definitive:
        clauses = normalize_sentence(sent)
        assert clauses[0].modality == exp_mod

    # 3 future plan vs past fact
    future_sents = [
        "관련 영수증은 추후 제출할 예정이다.",
        "잔금은 다음 기일에 지급하기로 한 바 있다.",
        "추가 준비서면은 향후 제출할 것이다.",
    ]
    for sent in future_sents:
        clauses = normalize_sentence(sent)
        assert clauses[0].temporal_aspect == "FUTURE_PLAN"

    past_sents = [
        "계약서는 정식으로 체결하였다.",
        "대금은 이미 지급하였다.",
        "이 사건 사고는 현장에서 발생하였다.",
    ]
    for sent in past_sents:
        clauses = normalize_sentence(sent)
        assert clauses[0].temporal_aspect == "PAST_FACT"


def test_omitted_subject_uncertainty_and_document_spans():
    doc = NormalizedDocument(
        document_id="doc_norm_1",
        filename="sample.pdf",
        mime_type="application/pdf",
        sha256="a" * 64,
        pages=[
            Page(
                page_number=1,
                width=595.0,
                height=842.0,
                blocks=[
                    Block(
                        block_id="b1",
                        text="위법성이 조각된다고 볼 수 없다. 다만 예외적으로 허용된다.",
                        page=1,
                    )
                ],
            )
        ],
    )
    clauses = normalize_document_clauses(doc, tokenizer=get_tokenizer(use_kiwi=False))
    assert len(clauses) >= 2
    assert clauses[0].block_id == "b1"
    assert clauses[0].page == 1
    assert "OMITTED_SUBJECT" in clauses[0].uncertainty_reasons
    assert clauses[0].parse_confidence < 1.0
    s0, e0 = clauses[0].reading_span
    assert doc.visible_text[s0:e0] == clauses[0].raw_text
    assert "normalized_clauses" in doc.structure
    assert doc.structure["clause_normalizer_backend"] == "regex_fallback"
