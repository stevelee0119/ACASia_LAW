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


def test_fact_triple_exhibit_table_and_extended_stages_positives_and_controls():
    # Positive 1: exhibit-anchored DRAFT date conflict across different noun phrasing
    pos_ex = _doc("갑 제1호증 확인서를 2023. 3. 1. 작성하였습니다.\n위 서류는 2023. 3. 15. 작성되었다고 기재되어 있습니다(갑 제1호증).")
    # Positive 2: WORK_START > WORK_END causal inversion
    pos_work = _doc("근로자는 2022. 5. 10. 퇴사하였습니다.\n근로자의 입사일은 2022. 8. 1.입니다.")
    # Positive 3: Table/KV line vs prose conflict
    pos_kv = NormalizedDocument(
        document_id="KV1",
        filename="kv.txt",
        mime_type="text/plain",
        sha256="0" * 64,
        pages=[
            Page(
                page_number=1,
                blocks=[
                    Block(block_id="B1", page=1, block_type="table", text="계약일 | 2021. 2. 1.", visible=True, source_layer="visible_text"),
                    Block(block_id="B2", page=1, block_type="paragraph", text="원고는 2021. 4. 1. 계약을 체결하였습니다.", visible=True, source_layer="visible_text"),
                ],
            )
        ],
    )
    for d in (pos_ex, pos_work, pos_kv):
        findings = verify_fact_triples(d, extract_fact_triples(d))
        assert findings, d.full_text

    # Controls: distinct exhibits, normal WORK_START < WORK_END, table distinct stages
    ctrl_ex = _doc("갑 제1호증 확인서를 2023. 3. 1. 작성하였습니다.\n갑 제2호증 진술서를 2023. 3. 15. 작성하였습니다.")
    ctrl_work = _doc("근로자는 2022. 2. 1. 입사하였고, 2022. 5. 10. 퇴사하였습니다.")
    ctrl_kv = NormalizedDocument(
        document_id="KV2",
        filename="kv2.txt",
        mime_type="text/plain",
        sha256="0" * 64,
        pages=[
            Page(
                page_number=1,
                blocks=[
                    Block(block_id="B1", page=1, block_type="table", text="작성일 | 2021. 2. 1.", visible=True, source_layer="visible_text"),
                    Block(block_id="B2", page=1, block_type="paragraph", text="원고는 2021. 2. 5. 문서를 발송하였습니다.", visible=True, source_layer="visible_text"),
                ],
            )
        ],
    )
    for d in (ctrl_ex, ctrl_work, ctrl_kv):
        findings = verify_fact_triples(d, extract_fact_triples(d))
        assert not findings, d.full_text


def test_cross_doc_copy_other_vs_pleading_positives_and_controls():
    from packages.claim_engine.evidence_consistency import cross_document_copies

    s1 = "피고인은 당일 밤 현장 부근에서 큰 소리로 다투며 문을 여러 차례 강하게 두드렸습니다."
    s2 = "피해자는 즉시 경찰에 신고하였고 현장에 출동한 경찰관이 관련 경위를 청취하였습니다."

    # Positive 1: 증거설명서(OTHER)가 소장(PLEADING)의 서술 문장 2건을 그대로 복사
    p_pl = _doc(f"소장\n원고 대리인\n청구원인\n{s1}\n{s2}", doc_id="PL1", filename="pl1.txt")
    p_ex = _doc(f"증거설명서\n서증목록\n{s1}\n{s2}", doc_id="EX1", filename="ex1.txt")
    assert any(f.confidence_features.get("rule_id") == "EVI.COPY_OTHER_PLEADING" for f in cross_document_copies([p_pl, p_ex]))

    # Positive 2: 기타 서증(OTHER)과 준비서면(PLEADING) 간 비정형 서술 2건 일치
    p_pl2 = _doc(f"준비서면\n{s1}\n{s2}", doc_id="PL2", filename="pl2.txt")
    p_ot2 = _doc(f"거래내역 메모\n{s1}\n{s2}", doc_id="OT2", filename="ot2.txt")
    assert any(f.confidence_features.get("rule_id") == "EVI.COPY_OTHER_PLEADING" for f in cross_document_copies([p_pl2, p_ot2]))

    # Positive 3: 어미·공백이 약간 달라도 shingle 0.85 이상이면 검출
    s1_var = "피고인은 당일 밤 현장 부근에서 큰 소리로 다투며 문을 여러 차례 강하게 두드렸다."
    p_ot3 = _doc(f"참고자료\n{s1_var}\n{s2}", doc_id="OT3", filename="ot3.txt")
    assert any(f.confidence_features.get("rule_id") == "EVI.COPY_OTHER_PLEADING" for f in cross_document_copies([p_pl, p_ot3]))

    # Control 1: 정식 서증 원용 표기(갑 제1호증)가 포함된 문장은 제외
    c_pl1 = _doc(f"준비서면\n갑 제1호증에 의하면 {s1}\n을 제2호증에 의하면 {s2}", doc_id="CPL1", filename="cpl1.txt")
    assert not cross_document_copies([c_pl1, p_ot2])

    # Control 2: 3개 이상 문서에 공통 등장하는 상투 문구(boilerplate)는 제외
    c_pl2 = _doc(f"준비서면\n{s1}\n{s2}", doc_id="CPL2", filename="cpl2.txt")
    c_ot2 = _doc(f"참고자료\n{s1}\n{s2}", doc_id="COT2", filename="cot2.txt")
    c_ot3 = _doc(f"안내자료\n{s1}\n{s2}", doc_id="COT3", filename="cot3.txt")
    assert not cross_document_copies([c_pl2, c_ot2, c_ot3])

    # Control 3: 1문장만 일치하는 경우는 제외
    c_ot1 = _doc(f"참고자료\n{s1}", doc_id="COT1", filename="cot1.txt")
    assert not cross_document_copies([p_pl, c_ot1])


