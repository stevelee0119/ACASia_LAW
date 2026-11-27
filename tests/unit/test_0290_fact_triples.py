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

    # Positive 2: 증거목록과 준비서면(PLEADING) 간 비정형 서술 2건 일치
    p_pl2 = _doc(f"준비서면\n{s1}\n{s2}", doc_id="PL2", filename="pl2.txt")
    p_ot2 = _doc(f"증거목록\n{s1}\n{s2}", doc_id="OT2", filename="ot2.txt")
    assert any(f.confidence_features.get("rule_id") == "EVI.COPY_OTHER_PLEADING" for f in cross_document_copies([p_pl2, p_ot2]))

    # Positive 3: 어미·공백이 약간 달라도 shingle 0.85 이상이면 검출
    s1_var = "피고인은 당일 밤 현장 부근에서 큰 소리로 다투며 문을 여러 차례 강하게 두드렸다."
    p_ot3 = _doc(f"증거설명서\n{s1_var}\n{s2}", doc_id="OT3", filename="ot3.txt")
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


def test_cassette_replay_offline_pipeline_and_stage2_nli_positives_and_controls(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    import httpx
    from packages.common.config import reset_settings
    from packages.common.enums import AdapterStatus, CitationType, VerificationProfile
    from packages.common.schemas import Citation
    from packages.source_adapters.academic import KCIAdapter
    from packages.source_adapters.cassette import record_cassette_entry
    from packages.source_adapters.law_go_kr import SEARCH_URL, SERVICE_URL, LawGoKrAdapter
    from packages.source_adapters.local_mirror import LocalLegalMirror
    from packages.verification_engine.pipeline import DocumentResult, VerificationPipeline

    cassette_dir = tmp_path / "cassettes"
    cassette_dir.mkdir(parents=True, exist_ok=True)

    # Record 1: law_go_kr case search + detail snapshots
    case_no = "2099다77001"
    search_payload = {
        "PrecSearch": {
            "totalCnt": 1,
            "prec": [
                {
                    "판례일련번호": "990001",
                    "사건번호": case_no,
                    "법원명": "대법원",
                    "선고일자": "20990115",
                    "사건명": "용역대금",
                    "판시사항": "약정 해지 요건",
                    "판결요지": "서면 최고 없이는 계약을 해지할 수 없다.",
                }
            ],
        }
    }
    detail_payload = {
        "PrecService": {
            "판례정보일련번호": "990001",
            "사건번호": case_no,
            "법원명": "대법원",
            "선고일자": "20990115",
            "사건명": "용역대금",
            "판시사항": "약정 해지 요건",
            "판결요지": "서면 최고 없이는 계약을 해지할 수 없다.",
            "판례내용": "당사자 사이에 서면 최고 없이는 계약을 해지할 수 없다.",
        }
    }
    record_cassette_entry(
        "law_go_kr",
        SEARCH_URL,
        params={"OC": "TEST_OC", "target": "prec", "type": "JSON", "nb": case_no},
        headers={},
        response=httpx.Response(200, content=json.dumps(search_payload, ensure_ascii=False).encode("utf-8")),
        cassette_dir=cassette_dir,
    )
    record_cassette_entry(
        "law_go_kr",
        SERVICE_URL,
        params={"OC": "TEST_OC", "target": "prec", "type": "JSON", "ID": "990001"},
        headers={},
        response=httpx.Response(200, content=json.dumps(detail_payload, ensure_ascii=False).encode("utf-8")),
        cassette_dir=cassette_dir,
    )

    # Record 2: law_go_kr statute history + detail snapshots
    law_name = "가상절차법"
    eflaw_list_payload = {
        "LawSearch": {
            "totalCnt": 1,
            "page": 1,
            "law": [
                {
                    "법령ID": "099999",
                    "법령일련번호": "880001",
                    "법령명한글": law_name,
                    "시행일자": "20200101",
                    "공포일자": "20191201",
                    "공포번호": "10001",
                    "제개정구분명": "제정",
                }
            ],
        }
    }
    eflaw_detail_payload = {
        "법령": {
            "기본정보": {
                "법령ID": "099999",
                "법령명_한글": law_name,
                "시행일자": "20200101",
                "공포일자": "20191201",
                "공포번호": "10001",
            },
            "조문": {
                "조문단위": [
                    {
                        "조문여부": "조문",
                        "조문번호": "5",
                        "조문시행일자": "20200101",
                        "조문내용": "제5조(통지) 신청인은 14일 이내에 서면으로 통지하여야 한다.",
                    }
                ]
            },
            "부칙": {"부칙단위": [{"부칙공포일자": "20191201", "부칙내용": "이 법은 2020년 1월 1일부터 시행한다."}]},
        }
    }
    for extra in ({"query": law_name}, {"LID": "99999"}):
        record_cassette_entry(
            "law_go_kr",
            SEARCH_URL,
            params={"OC": "TEST_OC", "type": "JSON", "target": "eflaw", "display": 100, "page": 1, "nw": "1,2,3", "sort": "efasc", **extra},
            headers={},
            response=httpx.Response(200, content=json.dumps(eflaw_list_payload, ensure_ascii=False).encode("utf-8")),
            cassette_dir=cassette_dir,
        )
    record_cassette_entry(
        "law_go_kr",
        SERVICE_URL,
        params={"OC": "TEST_OC", "type": "JSON", "target": "eflaw", "MST": "880001", "efYd": "20200101"},
        headers={},
        response=httpx.Response(200, content=json.dumps(eflaw_detail_payload, ensure_ascii=False).encode("utf-8")),
        cassette_dir=cassette_dir,
    )

    # Record 3: KCI academic snapshot
    kci_xml = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<MetaData><outputData><record>"
        "<journalInfo><journal-name>법학연구</journal-name><pub-year>2023</pub-year></journalInfo>"
        "<articleInfo><article-title-group><article-title>절차적 통지의무에 관한 고찰</article-title></article-title-group>"
        "<author-group><author>김연구</author></author-group></articleInfo>"
        "</record></outputData></MetaData>"
    )
    record_cassette_entry(
        "kci",
        KCIAdapter.ENDPOINT,
        params={"apiCode": "articleSearch", "key": "TEST_KCI", "title": "절차적 통지의무에 관한 고찰", "displayCount": 10},
        headers={},
        response=httpx.Response(200, content=kci_xml.encode("utf-8")),
        cassette_dir=cassette_dir,
    )

    # Enable strictly offline network (LV_ALLOW_NETWORK=0) + Cassette REPLAY without API keys
    monkeypatch.setenv("LV_ALLOW_NETWORK", "0")
    monkeypatch.setenv("LV_SOURCE_REPLAY_MODE", "REPLAY")
    monkeypatch.setenv("LV_SOURCE_CASSETTE_DIR", str(cassette_dir))
    monkeypatch.delenv("LV_LAW_GO_KR_OC", raising=False)
    monkeypatch.delenv("LV_KCI_KEY", raising=False)
    reset_settings()

    try:
        empty_mirror = LocalLegalMirror(root=tmp_path / "empty_mirror")
        law_adapter = LawGoKrAdapter(mirror=empty_mirror)
        kci_adapter = KCIAdapter()
        assert law_adapter.status() == AdapterStatus.READY
        assert kci_adapter.status() == AdapterStatus.READY

        # Positive 1: pipeline._legal_reviews verifies case citation via cassette & runs Stage 2 NLI on distorted quote
        pipe = VerificationPipeline()
        pipe.registry.law.mirror = empty_mirror
        pipe.legal.registry.law.mirror = empty_mirror
        doc = _doc(f"원고는 2023. 5. 1. 계약을 체결하였다. 대법원 2099. 1. 15. 선고 {case_no} 판결은 \"서면 최고 없이도 계약을 해지할 수 있다\"고 판시하였다.")
        doc_res = DocumentResult(document_id=doc.document_id, filename=doc.filename, normalized=doc)
        cit_distorted = Citation(
            citation_id="CIT_P1",
            type=CitationType.CASE,
            raw_text=f"대법원 2099. 1. 15. 선고 {case_no} 판결",
            document_id=doc.document_id,
            page=1,
            court="대법원",
            decision_date="2099-01-15",
            case_number=case_no,
            canonical_case_number=case_no,
            quoted_text="서면 최고 없이도 계약을 해지할 수 있다.",
        )
        ctx = SimpleNamespace(case_date="2023-05-01", issue_dates={}, profile=VerificationProfile.STANDARD)
        pipe._legal_reviews(doc_res, [cit_distorted], ctx, doc=doc)
        v_p1 = doc_res.engine_data["legal_verdicts"][0]
        assert v_p1["levels"]["level1"] == "VERIFIED"
        assert "stage2_nli" in v_p1["review"]
        assert any(f.type == FindingType.CASE_QUOTE_MISMATCH for f in doc_res.findings)

        # Positive 2: Statute citation verified via cassette REPLAY with Stage 2 NLI attached
        doc_res2 = DocumentResult(document_id=doc.document_id, filename=doc.filename, normalized=doc)
        cit_statute = Citation(
            citation_id="CIT_P2",
            type=CitationType.STATUTE,
            raw_text=f"{law_name} 제5조",
            document_id=doc.document_id,
            page=1,
            law_name=law_name,
            article="5",
            quoted_text="신청인은 14일 이내에 서면으로 통지하여야 한다.",
        )
        pipe._legal_reviews(doc_res2, [cit_statute], ctx, doc=doc)
        v_p2 = doc_res2.engine_data["legal_verdicts"][0]
        assert v_p2["levels"]["existence"] == "VERIFIED"
        assert v_p2["review"]["stage2_nli"]["verdict"] == "SUPPORTED"

        # Positive 3: KCI academic adapter serves from cassette under LV_ALLOW_NETWORK=0 without API key
        kci_resp = kci_adapter.search("절차적 통지의무에 관한 고찰")
        assert kci_resp.status == AdapterStatus.READY and len(kci_resp.records) == 1

        # Control 1: Unrecorded case query in REPLAY mode fails closed (DISABLED) with zero network access
        miss_resp = law_adapter.search_case("2099다77999")
        assert miss_resp.status == AdapterStatus.DISABLED

        # Control 2: Accurate case quote in REPLAY mode yields VERIFIED and 0 findings
        doc_res_ctrl2 = DocumentResult(document_id=doc.document_id, filename=doc.filename, normalized=doc)
        cit_accurate = Citation(
            citation_id="CIT_C2",
            type=CitationType.CASE,
            raw_text=f"대법원 2099. 1. 15. 선고 {case_no} 판결",
            document_id=doc.document_id,
            page=1,
            court="대법원",
            decision_date="2099-01-15",
            case_number=case_no,
            canonical_case_number=case_no,
            quoted_text="서면 최고 없이는 계약을 해지할 수 없다.",
        )
        pipe._legal_reviews(doc_res_ctrl2, [cit_accurate], ctx, doc=doc)
        v_c2 = doc_res_ctrl2.engine_data["legal_verdicts"][0]
        assert v_c2["status"] == "VERIFIED"
        assert v_c2["review"]["stage2_nli"]["verdict"] == "SUPPORTED"
        assert not [f for f in doc_res_ctrl2.findings if f.type == FindingType.CASE_QUOTE_MISMATCH]

        # Control 3: Normal offline mode (LIVE + LV_ALLOW_NETWORK=0) disables adapter without cassette replay
        monkeypatch.setenv("LV_SOURCE_REPLAY_MODE", "LIVE")
        reset_settings()
        live_offline_adapter = LawGoKrAdapter(mirror=empty_mirror)
        assert live_offline_adapter.status() in (AdapterStatus.DISABLED, AdapterStatus.MISSING_KEY)
    finally:
        reset_settings()


def test_online_evaluation_export_completeness_positives_and_controls():
    from datetime import datetime
    import json
    from packages.common.enums import JobState
    from packages.report_engine.exporters import to_json, to_payload
    from packages.report_engine.snapshot import shareable_snapshot
    from packages.verification_engine.pipeline import DocumentResult, VerificationRunResult

    def _make_run(doc_results):
        return VerificationRunResult(
            run_id="run_test_0290",
            project_id="proj_test_0290",
            state=JobState.COMPLETED,
            verification_key="vk_0290",
            started_at=datetime(2026, 1, 1, 0, 0, 0),
            finished_at=datetime(2026, 1, 1, 0, 1, 0),
            documents=doc_results,
        )

    # Positive 1: Document with citations, claims, and fact triples serializes full 4D evaluation_dimensions and fact_triples summary
    d1_norm = _doc("원고는 2023. 2. 1. 용역계약을 체결하였습니다.\n이후 2023. 4. 1. 용역계약을 체결하였습니다.", doc_id="D_EXP1")
    d1 = DocumentResult(
        document_id="D_EXP1",
        filename="exp1.txt",
        normalized=d1_norm,
        citations=[{"citation_id": "c1", "raw_text": "민법 제390조", "quoted_text": "채무자가 채무의 내용에 좇은 이행을 하지 아니한 때", "page": 1, "span": [0, 10]}],
        claims=[{"claim_id": "cl1", "text": "채무불이행 책임이 성립한다", "page": 1, "span": [12, 30], "citation_ids": ["c1"], "status": "VERIFIED"}],
        engine_data={
            "legal_verdicts": [
                {
                    "citation_id": "c1",
                    "status": "VERIFIED",
                    "levels": {"existence": "VERIFIED", "content": "VERIFIED"},
                    "source_lookup": {"requests": [{"adapter": "law_go_kr", "status": "READY"}]},
                    "official_record": {"law_name": "민법"},
                    "findings": [],
                }
            ]
        },
    )
    # Positive 2: Document without pre-populated engine_data['fact_triples'] auto-populates summary in to_payload
    d2_norm = _doc("피고는 2024. 1. 10. 통지서를 작성하였습니다.\n피고는 2024. 1. 12. 통지서를 발송하였습니다.", doc_id="D_EXP2")
    d2 = DocumentResult(document_id="D_EXP2", filename="exp2.txt", normalized=d2_norm)
    # Positive 3: JSON export (to_json) and shareable_snapshot preserve 4D evaluation_dimensions item_ids while masking PII
    d3_norm = _doc("신청인은 2023. 7. 1. 합의금 50,000,000원을 지급하였습니다.", doc_id="D_EXP3")
    d3 = DocumentResult(
        document_id="D_EXP3",
        filename="exp3.txt",
        normalized=d3_norm,
        claims=[{"claim_id": "cl3", "text": "신청인의 지급 주장", "page": 1, "span": [0, 20], "status": "CONTRADICTED"}],
    )

    run = _make_run([d1, d2, d3])
    payload = to_payload(run)
    raw_json = json.loads(to_json(run).decode("utf-8"))

    for doc_payload in (payload["documents"][0], raw_json["documents"][0]):
        ed = doc_payload["engine_data"]
        assert "evaluation_dimensions" in ed and "fact_triples" in ed
        dims = ed["evaluation_dimensions"]
        assert set(dims.keys()) == {"identity", "quote", "claim_applicability", "source_retrieval"}
        assert len(dims["identity"]) == 1 and dims["identity"][0]["status"] == "VERIFIED"
        assert len(dims["quote"]) == 1 and dims["quote"][0]["status"] == "VERIFIED"
        # TK-248: 법령 존재 확인(VERIFIED)과 주장 상태는 주장 지지가 아니다(적용성 검토 없음 -> INSUFFICIENT).
        assert len(dims["claim_applicability"]) == 1 and dims["claim_applicability"][0]["judgment"] == "INSUFFICIENT"
        assert dims["claim_applicability"][0]["judgment_basis"] == "NOT_ASSESSED"
        assert len(dims["source_retrieval"]) == 1 and dims["source_retrieval"][0]["source_name"] == "law_go_kr"
        ft = ed["fact_triples"]
        assert ft["count"] >= 2 and ft["asserted_self_count"] >= 2 and "CONTRACT" in ft["stages"]

    assert payload["documents"][1]["engine_data"]["fact_triples"]["count"] >= 2
    assert payload["documents"][2]["engine_data"]["evaluation_dimensions"]["claim_applicability"][0]["judgment"] == "INSUFFICIENT"

    # Control 1: Empty document with no citations/claims produces empty 4D lists and count=0 without errors
    d_empty = DocumentResult(document_id="D_EMPTY", filename="empty.txt", normalized=_doc("단순 안내문입니다.", doc_id="D_EMPTY"))
    p_empty = to_payload(_make_run([d_empty]))["documents"][0]["engine_data"]
    assert p_empty["fact_triples"]["count"] == 0
    assert all(p_empty["evaluation_dimensions"][k] == [] for k in ("identity", "quote", "claim_applicability", "source_retrieval"))

    # Control 2: Frozen report snapshot (with report_metadata) is not mutated by _serialize_engine_data
    frozen_run = _make_run([d_empty])
    frozen_run.report_metadata = {"state": "FINAL", "label": "확정본"}
    frozen_run.review_snapshot = {"engine_result": {}}
    d_empty.engine_data = {"custom_frozen_only": True}
    p_frozen = to_payload(frozen_run)["documents"][0]["engine_data"]
    assert p_frozen == {"custom_frozen_only": True}

    # Control 3: shareable_snapshot preserves evaluation_dimensions item_ids and masks PII in claims
    snap = {
        "report": {"state": "DRAFT", "audience": "SHAREABLE"},
        "engine_result": payload,
        "workflow": [],
        "matrix": {"claims": [], "issues": []},
        "preflight": {},
    }
    shared = shareable_snapshot(snap)
    shared_dims = shared["engine_result"]["documents"][0]["engine_data"]["evaluation_dimensions"]
    assert shared_dims["identity"][0]["item_id"].startswith("identity-")
    assert shared_dims["claim_applicability"][0]["item_id"].startswith("claim-")


def test_p1_p2_generalized_rules_positives_and_controls():
    from packages.claim_engine.evidence_consistency import (
        check_evidence_form_structure,
        check_evidence_overreach,
    )
    from packages.legal_engine.claim_review import review_claims

    # 1. PRECEDENT_OVERGENERALIZATION & UNCONDITIONAL_LEGAL_OVERCLAIM: 3 positives, 3 controls
    ovr_pos1 = _doc("대법원 2018다12345 판결에 의하면 어떠한 경우에도 예외 없이 계약은 당연히 해제된다.")
    ovr_pos2 = _doc("피고는 대법원 2020두54321 판결에 따라 일체의 사정을 불문하고 언제나 손해배상책임이 면책된다.")
    ovr_pos3 = _doc("신청인은 무조건 예외 없이 전액 손해배상책임이 당연히 성립한다.")
    for d in (ovr_pos1, ovr_pos2, ovr_pos3):
        res = review_claims(d)
        assert any(
            f.type in (FindingType.OVERCLAIM, FindingType.CASE_HOLDING_DISTORTION, FindingType.UNSUPPORTED_GENERALIZATION)
            for f in res
        ), d.full_text
    assert any(f.type == FindingType.CASE_HOLDING_DISTORTION for f in review_claims(ovr_pos1))
    assert any(f.type == FindingType.CASE_HOLDING_DISTORTION for f in review_claims(ovr_pos2))

    ovr_ctrl1 = _doc("원고는 특별한 사정이 없는 한 원칙적으로 피고에게 손해배상책임이 인정된다.")
    ovr_ctrl2 = _doc("상대방은 어떠한 경우에도 예외 없이 계약이 해제된다고 주장하나 이는 부당하다.")
    ovr_ctrl3 = _doc("대법원 2018다12345 판결은 원칙적으로 특별한 사정이 없는 한 계약이 해제된다고 판시하였다.")
    for d in (ovr_ctrl1, ovr_ctrl2, ovr_ctrl3):
        res = review_claims(d)
        assert not [
            f for f in res
            if (f.confidence_features or {}).get("claim_type") in ("UNCONDITIONAL_LEGAL_OVERCLAIM", "PRECEDENT_OVERGENERALIZATION")
        ], d.full_text

    # 2. Inline EVI-OVR & EVI-FORM: 3 positives, 3 controls
    evi_pos1 = _doc("소장\n원고는 현장 사진에 의하여 피고의 기망 의도와 전체 계약 합의가 명백히 증명됩니다.")
    evi_pos2 = _doc("준비서면\n원고의 일방 통지서만으로도 상대방의 승낙 및 합의가 성립하였음이 확인됩니다.")
    evi_pos3 = _doc("답변서\n피고는 별첨 1 내역을 증거로 첨부하였다고 하나 실제로는 미첨부 상태이다.")
    for d in (evi_pos1, evi_pos2, evi_pos3):
        findings = check_evidence_overreach(d) + check_evidence_form_structure(d)
        assert findings, d.full_text

    evi_ctrl1 = _doc("소장\n원고는 현장 사진에 의하여 당시 건물의 외형 상태를 입증합니다.")
    evi_ctrl2 = _doc("준비서면\n피고는 일방 통지서만으로 상대방의 승낙이 증명된다고 주장하나 이는 부당하다.")
    evi_ctrl3 = _doc("답변서\n피고는 별첨 1 내역을 정상적으로 첨부하여 제출합니다.")
    for d in (evi_ctrl1, evi_ctrl2, evi_ctrl3):
        findings = check_evidence_overreach(d) + check_evidence_form_structure(d)
        assert not [
            f for f in findings
            if (f.confidence_features or {}).get("rule_id", "").startswith(("claim_engine.evidence_consistency:", "EVI.INLINE_FORM_DEFECT"))
        ], d.full_text



