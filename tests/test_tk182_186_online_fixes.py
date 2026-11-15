"""TK-182, TK-183, TK-184, TK-186 회귀 및 일반화 시험 (합성 데이터 전용)."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from io import BytesIO
import zipfile

import pytest

from packages.claim_engine.calculation import CalculationEngine
from packages.common.enums import ExternalAIPolicy, LLMRole
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.document_engine.ocr import OCRAdapter, OCRLine, reset_ocr_adapter, set_ocr_adapter
from packages.document_engine.registry import parse_document
from packages.common.config import ProviderConfig
from packages.llm_router.cascade_source import build_cascade_request
from packages.llm_router.providers import LLMProvider, LLMRequest, LLMResponse
from packages.llm_router.router import LLMRouter
from packages.rag_engine.extract import extract


# ---------------------------------------------------------------------------
# TK-182: 빈 비밀번호 PDF 허용 / 진짜 암호화 PDF 거절 / 쪽별 진단 / 제한 OCR / 재개
# ---------------------------------------------------------------------------
def _make_pdf_bytes(pages: int = 1, *, user_password: str | None = None, owner_password: str | None = None) -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    if user_password is not None or owner_password is not None:
        writer.encrypt(user_password=user_password or "", owner_password=owner_password or "owner")
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_image_pdf(tmp_path, name: str = "scan.pdf", pages: int = 1):
    from PIL import Image, ImageDraw

    imgs = []
    for idx in range(pages):
        img = Image.new("RGB", (300, 120), "white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), f"PAGE {idx + 1}", fill="black")
        imgs.append(img)
    path = tmp_path / name
    imgs[0].save(path, "PDF", save_all=True, append_images=imgs[1:])
    return path


class _FakeOCR(OCRAdapter):
    name = "fake_ocr"
    available = True

    def recognize(self, path: str, page_numbers=None):
        return []

    def recognize_image(self, image, *, page: int = 1, scale: float = 1.0):
        return [OCRLine(text=f"인식된 문장 제{page}쪽", page=page, confidence=0.95)]


def test_tk182_empty_password_pdf_allowed_and_real_password_rejected(tmp_path):
    empty_pw = tmp_path / "empty_pw.pdf"
    empty_pw.write_bytes(_make_pdf_bytes(1, user_password="", owner_password="secret"))
    res = extract(empty_pw, "empty_pw.pdf", "application/pdf")
    assert res["pages"] == 1
    assert res["blank_pages"] == [1]

    real_pw = tmp_path / "real_pw.pdf"
    real_pw.write_bytes(_make_pdf_bytes(1, user_password="secret", owner_password="secret"))
    with pytest.raises(ValueError, match="ENCRYPTED_REFERENCE"):
        extract(real_pw, "real_pw.pdf", "application/pdf")


def test_tk182_page_diagnostics_distinguish_blank_and_scanned(tmp_path, monkeypatch):
    monkeypatch.setenv("LV_REFERENCE_OCR_MAX_PAGES", "0")
    blank_pdf = tmp_path / "blank.pdf"
    blank_pdf.write_bytes(_make_pdf_bytes(1))
    blank_res = extract(blank_pdf, "blank.pdf", "application/pdf")
    assert blank_res["blank_pages"] == [1]
    assert blank_res["scanned_pages"] == []
    assert blank_res["page_diagnostics"]["1"]["status"] == "blank"

    scan_pdf = _make_image_pdf(tmp_path, "scan.pdf", pages=1)
    scan_res = extract(scan_pdf, "scan.pdf", "application/pdf")
    assert scan_res["scanned_pages"] == [1]
    assert scan_res["blank_pages"] == []
    assert scan_res["page_diagnostics"]["1"]["status"] == "scanned"


def test_tk182_bounded_ocr_with_checkpoint_continuation(tmp_path, monkeypatch):
    monkeypatch.setenv("LV_REFERENCE_OCR_MAX_PAGES", "2")
    set_ocr_adapter(_FakeOCR())
    try:
        scan_pdf = _make_image_pdf(tmp_path, "multi_scan.pdf", pages=3)
        batch1 = extract(scan_pdf, "multi_scan.pdf", "application/pdf")
        assert batch1["ocr_pages"] == [1, 2]
        assert batch1["partial"] is True
        assert batch1["continuation"] is not None
        assert batch1["continuation"]["next_page"] == 3
        assert len(batch1["chunks"]) == 2

        batch2 = extract(scan_pdf, "multi_scan.pdf", "application/pdf", continuation=batch1["continuation"])
        assert batch2["resumed"] is True
        assert batch2["ocr_pages"] == [1, 2, 3]
        assert batch2["continuation"] is None
        assert batch2["partial"] is False
        assert batch2["read_pages"] == 3
        assert len(batch2["chunks"]) == 1
        assert "제3쪽" in batch2["chunks"][0]["text"]
    finally:
        reset_ocr_adapter()


# ---------------------------------------------------------------------------
# TK-183: HWPX 표 셀 다중 문단 경계 보존 (양성 3건 + 대조 3건)
# ---------------------------------------------------------------------------
_NS = ('xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
       'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"')


def _hwpx_doc(tmp_path, body: str, name: str = "t.hwpx") -> NormalizedDocument:
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        z.writestr("Contents/section0.xml", f'<?xml version="1.0" encoding="UTF-8"?><hs:sec {_NS}>{body}</hs:sec>')
    return parse_document(str(path), document_id="d", filename=name, mime_type="", sha256="x")


@pytest.mark.parametrize(
    "paragraphs,expected",
    [
        (["갑 항목", "을 항목"], "갑 항목\n을 항목"),
        (["첫째 줄", "둘째 줄", "셋째 줄"], "첫째 줄\n둘째 줄\n셋째 줄"),
        (["첫 문단", "", "   ", "다음 문단"], "첫 문단\n다음 문단"),
    ],
)
def test_tk183_hwpx_cell_preserves_paragraph_boundaries(tmp_path, paragraphs, expected):
    p_xml = "".join(f"<hp:p><hp:run><hp:t>{p}</hp:t></hp:run></hp:p>" for p in paragraphs)
    tbl = (f'<hp:p><hp:run><hp:tbl rowCnt="1" colCnt="1"><hp:tr>'
           f'<hp:tc><hp:subList>{p_xml}</hp:subList><hp:cellAddr colAddr="0" rowAddr="0"/></hp:tc>'
           f'</hp:tr></hp:tbl></hp:run></hp:p>')
    doc = _hwpx_doc(tmp_path, tbl)
    assert doc.structure["tables"][0]["cells"][0][0] == expected


def test_tk183_hwpx_cell_controls(tmp_path):
    # 대조 1: 단일 문단은 개행 없음
    single = ('<hp:p><hp:run><hp:tbl rowCnt="1" colCnt="1"><hp:tr>'
              '<hp:tc><hp:subList><hp:p><hp:run><hp:t>단일 문단</hp:t></hp:run></hp:p></hp:subList>'
              '<hp:cellAddr colAddr="0" rowAddr="0"/></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>')
    assert _hwpx_doc(tmp_path, single, "c1.hwpx").structure["tables"][0]["cells"][0][0] == "단일 문단"

    # 대조 2: 한 문단 안 여러 run은 한 줄로 결합
    multi_run = ('<hp:p><hp:run><hp:tbl rowCnt="1" colCnt="1"><hp:tr>'
                 '<hp:tc><hp:subList><hp:p><hp:run><hp:t>앞부분 </hp:t></hp:run>'
                 '<hp:run><hp:t>뒷부분</hp:t></hp:run></hp:p></hp:subList>'
                 '<hp:cellAddr colAddr="0" rowAddr="0"/></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>')
    assert _hwpx_doc(tmp_path, multi_run, "c2.hwpx").structure["tables"][0]["cells"][0][0] == "앞부분 뒷부분"

    # 대조 3: 중첩 표 텍스트는 바깥 셀에 섞이지 않음
    nested = ('<hp:p><hp:run><hp:tbl rowCnt="1" colCnt="1"><hp:tr>'
              '<hp:tc><hp:subList><hp:p><hp:run><hp:t>바깥</hp:t></hp:run></hp:p>'
              '<hp:p><hp:run><hp:tbl rowCnt="1" colCnt="1"><hp:tr><hp:tc><hp:subList>'
              '<hp:p><hp:run><hp:t>안쪽</hp:t></hp:run></hp:p></hp:subList>'
              '<hp:cellAddr colAddr="0" rowAddr="0"/></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>'
              '</hp:subList><hp:cellAddr colAddr="0" rowAddr="0"/></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>')
    tables = _hwpx_doc(tmp_path, nested, "c3.hwpx").structure["tables"]
    assert tables[0]["cells"][0][0] == "바깥"
    assert tables[1]["cells"][0][0] == "안쪽"


# ---------------------------------------------------------------------------
# TK-184: 비율 지적 구조화 증거 연결 & 문장별 재계산 (양성 3건 + 대조 3건)
# ---------------------------------------------------------------------------
def test_tk184_table_ratio_links_structured_row_evidence():
    doc = NormalizedDocument("doc1", "sample.hwp", "application/x-hwp", "sha")
    doc.structure["tables"] = [{
        "table_ref": "t0",
        "page": 1,
        "cells": [
            ["항목", "금액", "비율"],
            ["항목A", "1,000,000원", "25%"],
            ["항목B", "3,000,000원", "60%"],
            ["합계", "4,000,000원", "100%"],
        ],
    }]
    findings = CalculationEngine().verify_document(doc)
    percent = [f for f in findings if f.confidence_features.get("rule_id") == "CALC.PERCENT_MISMATCH"]
    assert len(percent) == 1
    f = percent[0]
    row_ev = f.confidence_features["row_evidence"]
    assert len(row_ev) == 1  # 일치하는 항목A는 제외(보존)
    assert row_ev[0]["row"] == "항목B"
    assert row_ev[0]["amount"] == "3000000"
    assert row_ev[0]["stated_percent"] == "60"
    assert row_ev[0]["computed_percent"] == "75.00"
    assert row_ev[0]["computed_total"] == "4000000"
    assert any("3,000,000원" in ev.excerpt and "60%" in ev.excerpt and "75.00%" in ev.excerpt for ev in f.evidence)


def test_tk184_table_stated_total_cause_links_row_evidence():
    doc = NormalizedDocument("doc2", "sample.hwp", "application/x-hwp", "sha")
    doc.structure["tables"] = [{
        "table_ref": "t0",
        "page": 1,
        "cells": [
            ["항목", "금액", "비율"],
            ["항목1", "1,000,000원", "20%"],
            ["항목2", "3,000,000원", "60%"],
            ["합계", "5,000,000원", "100%"],
        ],
    }]
    findings = CalculationEngine().verify_document(doc)
    percent = [f for f in findings if f.confidence_features.get("rule_id") == "CALC.PERCENT_MISMATCH"]
    assert len(percent) == 1
    assert percent[0].confidence_features["cause"] == "STATED_TOTAL"
    assert len(percent[0].confidence_features["row_evidence"]) == 2
    assert percent[0].confidence_features["row_evidence"][0]["stated_total"] == "5000000"


def test_tk184_sentence_ratio_recalculation_and_controls():
    # 양성: 문장 내 명시적 총액-부분-비율 불일치
    pos_doc = NormalizedDocument("doc3", "sample.hwpx", "application/hwpx", "sha")
    pos_doc.pages = [Page(1, blocks=[
        Block("b1", "총 10,000,000원 중 3,000,000원은 40%에 해당한다. 한편 그 비율이 과다하다는 포괄적 의견이 있다.", 1),
    ])]
    findings = CalculationEngine().verify_document(pos_doc)
    sent_findings = [f for f in findings if f.confidence_features.get("rule_id") == "CALC.SENTENCE_PERCENT_MISMATCH"]
    assert len(sent_findings) == 1
    ev = sent_findings[0].confidence_features["row_evidence"][0]
    assert ev["amount"] == "3000000"
    assert ev["stated_percent"] == "40"
    assert ev["computed_percent"] == "30.00"
    assert ev["computed_total"] == "10000000"

    # 대조 1~3: 일치 문장, 근사치/범위 문장, 수치 근거 없는 포괄 의견은 오탐 없이 보존
    ctrl_doc = NormalizedDocument("doc4", "ctrl.hwpx", "application/hwpx", "sha")
    ctrl_doc.pages = [Page(1, blocks=[
        Block("b1", "전체 8,000,000원 중 2,000,000원은 25%이다.", 1),
        Block("b2", "총 10,000,000원 중 3,000,000원은 약 40%이다.", 1),
        Block("b3", "총 10,000,000원 중 3,000,000원은 20~40%이다.", 1),
        Block("b4", "배분 비율이 합리적이지 않다는 포괄 의견이다.", 1),
    ])]
    ctrl_findings = CalculationEngine().verify_document(ctrl_doc)
    assert not [f for f in ctrl_findings if "PERCENT" in str(f.confidence_features.get("rule_id", ""))]


# ---------------------------------------------------------------------------
# TK-186: 공식 Source cascade INPUT_PRIVACY_BLOCKED 원인 진단 사유 코드
# ---------------------------------------------------------------------------
class _DummyProvider(LLMProvider):
    def __init__(self):
        from packages.common.config import get_settings
        super().__init__(ProviderConfig(name="openai", kind="cloud", model=get_settings().providers["openai"].model, enabled=True))

    @property
    def available(self) -> bool:
        return True

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(ok=True, text='{"status": "VERIFIED", "rationale": "ok", "confidence": 0.9}',
                           provider=self.name, model=self.config.model)


def test_tk186_cascade_privacy_diagnostic_categories(monkeypatch):
    async def _run():
        router = LLMRouter(providers={"openai": _DummyProvider()})

        # 1. 마스킹 누락(PII 탐지) -> MASKING_PII_DETECTED, 원문 미노출
        pii_req = build_cascade_request("primary", "인용 대조", {"official": {"full_text": "대법원 판시"}, "document": "원고 홍길동이 주장한다"})
        r1 = await router.run_any(LLMRole.PRIMARY_REASONER, pii_req, policy=ExternalAIPolicy.MASKED)
        assert r1.executions and not r1.executions[0].ok
        assert "MASKING_PII_DETECTED:PII_INPUT_BLOCKED" in r1.executions[0].error
        assert "홍길동" not in r1.executions[0].error
        assert r1.executions[0].input_privacy["diagnostic_category"] == "MASKING_PII_DETECTED"

        # 2. 요청 연결 계약 위반(cascade_source) -> REQUEST_WIRING_CONTRACT
        tampered = replace(build_cascade_request("primary", "인용 대조", {"official": {}, "document": "마스킹된 문서"}), user="변조된 사용자 프롬프트")
        r2 = await router.run_any(LLMRole.PRIMARY_REASONER, tampered, policy=ExternalAIPolicy.MASKED)
        assert r2.executions and not r2.executions[0].ok
        assert "REQUEST_WIRING_CONTRACT:INPUT_CONTRACT_VIOLATION/cascade_source" in r2.executions[0].error
        assert r2.executions[0].input_privacy["contract_failures"] == ["cascade_source"]

        # 3. 검사 예외 -> INSPECTION_EXCEPTION
        import packages.llm_router.privacy as priv_mod
        monkeypatch.setattr(priv_mod, "inspect_request", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        clean_req = build_cascade_request("primary", "인용 대조", {"official": {"full_text": "대법원 판시"}, "document": "[PERSON_001]이 주장한다"})
        r3 = await router.run_any(LLMRole.PRIMARY_REASONER, clean_req, policy=ExternalAIPolicy.MASKED)
        assert r3.executions and not r3.executions[0].ok
        assert "INSPECTION_EXCEPTION:INSPECTION_EXCEPTION/RuntimeError" in r3.executions[0].error

    asyncio.run(_run())


def test_tk186_clean_cascade_request_passes_inspection(tmp_path):
    async def _run():
        from packages.common.config import get_settings
        settings = replace(get_settings(), storage_root=tmp_path)
        router = LLMRouter(settings=settings, providers={"openai": _DummyProvider()})
        clean_req = build_cascade_request(
            "primary",
            "인용 대조",
            {"official": {"full_text": "피고는 원고에게 지급할 의무가 있다."}, "document": "[PERSON_001]이 지급을 청구하였다."},
        )
        res = await router.run_any(LLMRole.PRIMARY_REASONER, clean_req, policy=ExternalAIPolicy.MASKED)
        assert res.executions[0].input_privacy["status"] == "PASSED"
        assert res.used is True

    asyncio.run(_run())
