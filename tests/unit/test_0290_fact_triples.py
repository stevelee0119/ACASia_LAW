from __future__ import annotations

from packages.claim_engine.fact_triples import (
    extract_fact_triples,
    verify_fact_triples,
    verify_project_fact_triples,
)
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(text: str, *, doc_id: str = "D1", filename: str = "brief.txt") -> NormalizedDocument:
    blocks = [
        Block(
            block_id=f"B{i}",
            page=1,
            block_type="paragraph",
            text=line,
            visible=True,
            source_layer="visible_text",
        )
        for i, line in enumerate(text.splitlines())
        if line.strip()
    ]
    return NormalizedDocument(
        document_id=doc_id,
        filename=filename,
        mime_type="text/plain",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=blocks)],
    )


def test_fact_triple_value_conflict_positives_and_controls():
    pos1 = _doc("원고는 2022. 3. 10. 매매계약을 체결하였습니다.\n이후 2022. 5. 15. 매매계약을 체결하였습니다.")
    pos2 = _doc("피고는 2023. 1. 5. 내용증명을 발송하였습니다.\n결론적으로 2023. 2. 10. 내용증명을 발송하였습니다.")
    pos3 = _doc("원고는 매매대금 300,000,000원으로 약정하였습니다.\n결론에서 원고는 매매대금 450,000,000원으로 약정하였습니다.")
    for d in (pos1, pos2, pos3):
        triples = extract_fact_triples(d)
        findings = verify_fact_triples(d, triples)
        assert any(f.type == FindingType.FACT_CONTRADICTION for f in findings), d.full_text

    # Controls: distinct action stages (DRAFT -> SEND -> RECEIVE), opponent claim, planned/amended
    ctrl1 = _doc("피고는 2024년 4월 10일 회신서를 작성하여 2024년 4월 11일 발송하였고, 위 회신서는 2024년 4월 12일 원고에게 도착하였다.")
    ctrl2 = _doc("원고 소송대리인 제출.\n원고는 2022. 3. 10. 매매계약을 체결하였습니다.\n피고는 2022. 5. 15. 매매계약을 체결하였다고 주장합니다.")
    ctrl3 = _doc("당초 2022. 3. 10. 매매대금 300,000,000원으로 계약하였으나, 2022. 6. 1. 변경 합의로 매매대금을 350,000,000원으로 증액하였습니다.")
    for d in (ctrl1, ctrl2, ctrl3):
        triples = extract_fact_triples(d)
        findings = verify_fact_triples(d, triples)
        assert not findings, d.full_text


def test_fact_triple_stage_inversion_positives_and_controls():
    pos1 = _doc("위 내용증명은 2023. 4. 1. 도달하였고, 원고는 2023. 4. 10. 내용증명을 발송하였습니다.")
    pos2 = _doc("피고는 2022. 1. 10. 도급계약을 해지하였고, 2022. 3. 1. 도급계약을 체결하였습니다.")
    pos3 = _doc("회신서는 2024. 5. 2. 수신되었으며, 2024. 5. 15. 회신서를 발신하였습니다.")
    for d in (pos1, pos2, pos3):
        triples = extract_fact_triples(d)
        findings = verify_fact_triples(d, triples)
        assert any(f.type == FindingType.EVIDENCE_TIMELINE_INVERSION for f in findings), d.full_text

    ctrl1 = _doc("원고는 2023. 4. 1. 내용증명을 발송하였고, 2023. 4. 5. 도달하였습니다.")
    ctrl2 = _doc("2022. 1. 10. 도급계약을 체결하였고, 2022. 6. 1. 도급계약을 해지하였습니다.")
    ctrl3 = _doc("만약 2023. 4. 1. 도달하였다고 가정하더라도 2023. 4. 10. 내용증명을 발송할 예정이었습니다.")
    for d in (ctrl1, ctrl2, ctrl3):
        triples = extract_fact_triples(d)
        findings = verify_fact_triples(d, triples)
        assert not findings, d.full_text


def test_project_fact_triple_cross_doc_positives_and_controls():
    d1 = _doc("원고는 2022. 3. 10. 매매계약을 체결하였습니다.", doc_id="A", filename="a.txt")
    d2 = _doc("피고는 2022. 4. 20. 매매계약을 체결하였습니다.", doc_id="B", filename="b.txt")
    # Note: different explicit subjects (원고 vs 피고) are skipped; same or unspecified subject conflicts
    d3 = _doc("2022. 3. 10. 매매계약을 체결하였습니다.", doc_id="C", filename="c.txt")
    d4 = _doc("2022. 4. 20. 매매계약을 체결하였습니다.", doc_id="D", filename="d.txt")
    f_pos = verify_project_fact_triples([(d3, extract_fact_triples(d3)), (d4, extract_fact_triples(d4))])
    assert any(f.confidence_features.get("rule_id") == "FACT_TRIPLE.CROSS_DOC_CONFLICT" for f in f_pos)

    d5 = _doc("2022. 3. 10. 매매계약을 체결하였습니다.", doc_id="E", filename="e.txt")
    f_ctrl = verify_project_fact_triples([(d3, extract_fact_triples(d3)), (d5, extract_fact_triples(d5))])
    assert not f_ctrl
