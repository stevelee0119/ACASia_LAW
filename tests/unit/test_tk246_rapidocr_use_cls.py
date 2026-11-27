"""TK-246 unit & fixture tests: Disable RapidOCR line orientation classifier (Global.use_cls=False), expose use_cls diagnostics, recover low_quality_scanned.pdf, and guard 180-degree rotated pages (including short 3-line unassessed pages)."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from packages.common.config import REPO_ROOT
from packages.common.schemas import BBox
import packages.document_engine.ocr as ocr_mod
from packages.document_engine.ocr import (
    CompositeOCRAdapter,
    OCRAdapter,
    OCRLine,
    RapidOCRAdapter,
    TesseractOCRAdapter,
    build_ocr_page_telemetry,
    page_quality,
)
from packages.document_engine.ocr_readiness import korean_font_path, ocr_readiness, probe_tesseract


def _rapidocr_korean_weights_cached() -> bool:
    try:
        import rapidocr  # type: ignore

        models_dir = Path(rapidocr.__file__).resolve().parent / "models"
        return (
            (models_dir / "korean_PP-OCRv5_rec_mobile.onnx").is_file()
            and any(models_dir.glob("*det*.onnx"))
        )
    except Exception:
        return False


def test_tk246_config_rapidocr_adapter_disables_use_cls_and_exposes_diagnostics(monkeypatch):
    """설정 회귀 방지 + 진단 노출: RapidOCRAdapter._ensure_engine()이 Global.use_cls=False를 전달하고, check_ocr_runtime(ocr_readiness) 및 폴백 원격 측정에 실제 use_cls 상태를 노출한다."""
    captured_params: list[dict] = []

    fake_mod = ModuleType("rapidocr")
    fake_mod.LangRec = SimpleNamespace(KOREAN="korean")  # type: ignore[attr-defined]
    fake_mod.OCRVersion = SimpleNamespace(PPOCRV5="PP-OCRv5")  # type: ignore[attr-defined]
    fake_mod.ModelType = SimpleNamespace(MOBILE="mobile")  # type: ignore[attr-defined]

    class _SpyRapidOCR:
        def __init__(self, params=None):
            captured_params.append(dict(params or {}))
            self.use_cls = bool((params or {}).get("Global.use_cls", True))
            self.cfg = {"Global": {"use_cls": self.use_cls}}
            self.text_cls = object() if self.use_cls else None

        def __call__(self, _img):
            box = [[10, 10], [200, 10], [200, 35], [10, 35]]
            return SimpleNamespace(boxes=[box], txts=["계약 이행 조건 확인 본문"], scores=[0.91])

    fake_mod.RapidOCR = _SpyRapidOCR  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rapidocr", fake_mod)
    monkeypatch.delitem(sys.modules, "rapidocr_onnxruntime", raising=False)

    adapter = RapidOCRAdapter(lazy=False)
    assert len(captured_params) == 1
    assert captured_params[0].get("Global.use_cls") is False

    diag = adapter.engine_config_diagnostics()
    assert diag["engine_loaded"] is True
    assert diag["use_cls"] is False
    assert diag["configured_use_cls"] is False
    assert diag["text_cls_loaded"] is False

    img = np.full((120, 240, 3), 240, dtype=np.uint8)
    img[20:45, 20:180] = 30
    lines = adapter.recognize_image(img, preprocess=True)
    assert len(lines) == 1
    assert adapter.last_preprocess_telemetry["rapidocr_use_cls"] is False

    # 다음 판에서 패키지 내부가 use_cls=True로 바뀐 상황을 모사하면 진단에 즉시 True로 드러난다
    adapter._engine.use_cls = True
    assert adapter.engine_config_diagnostics()["use_cls"] is True

    # ocr_readiness(check_ocr_runtime) 노출 확인
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")
    monkeypatch.setattr(ocr_mod, "_adapter", None)
    state = ocr_readiness(refresh=False)
    assert "fallback" in state
    assert state["fallback"]["configured_engine"] == "rapidocr"
    assert state["fallback"]["rapidocr"]["use_cls"] is False
    monkeypatch.setattr(ocr_mod, "_adapter", None)


def test_tk246_real_engine_use_cls_off_when_weights_present():
    """실제 rapidocr 패키지·가중치가 있는 환경(Docker OCR readiness)에서 생성된 엔진의 use_cls와 text_cls가 비활성인지 검증한다."""
    if not _rapidocr_korean_weights_cached():
        pytest.skip("RapidOCR ONNX weights not pre-cached locally; verified in Docker OCR readiness")
    adapter = RapidOCRAdapter(lazy=False)
    assert adapter._engine is not None
    assert getattr(adapter._engine, "use_cls", None) is False
    assert adapter._engine.cfg["Global"]["use_cls"] is False
    assert getattr(adapter._engine, "text_cls", None) is None
    assert adapter.engine_config_diagnostics()["use_cls"] is False


def test_tk246_pos1_upright_multiline_korean_returns_all_lines(monkeypatch):
    """양성 1: 정방향 한국어 다줄 쪽에서 방향 분류기 오판으로 줄이 소실되지 않고 모든 줄을 돌려준다."""
    sample_lines = [
        "제1조 공급자는 약정 기일까지 물품을 지정 장소에 인도한다.",
        "제2조 매수인은 검수 완료 후 대금을 계좌로 지급한다.",
        "제3조 하자 보수 기간은 인도일로부터 일 년으로 정한다.",
        "제4조 불가항력으로 인한 지연은 지체 책임을 면제한다.",
        "제5조 분쟁 발생 시 관할 법원은 합의에 따라 정한다.",
        "제6조 특약 사항은 별지 합의서 기재 내용에 따른다.",
    ]

    if _rapidocr_korean_weights_cached() and korean_font_path() is not None:
        from PIL import Image, ImageDraw, ImageFont

        font = ImageFont.truetype(str(korean_font_path()), 28)
        img = Image.new("RGB", (1654, 1200), "white")
        draw = ImageDraw.Draw(img)
        for idx, txt in enumerate(sample_lines):
            draw.text((120, 120 + idx * 70), txt, font=font, fill="black")

        adapter = RapidOCRAdapter()
        out = adapter.recognize_image(img, page=1, preprocess=True)
        assert len(out) == len(sample_lines)
        q = page_quality(out, lang="kor+eng")
        assert q["low_quality"] is False
        assert q["confidence"] >= 0.90
        return

    # 가중치 미설치 단위 시험 환경: use_cls=True일 때 절반의 줄을 0.5 미만으로 탈락시키는 엔진 모사로 회귀 검증
    fake_mod = ModuleType("rapidocr")
    fake_mod.LangRec = SimpleNamespace(KOREAN="korean")  # type: ignore[attr-defined]
    fake_mod.OCRVersion = SimpleNamespace(PPOCRV5="PP-OCRv5")  # type: ignore[attr-defined]
    fake_mod.ModelType = SimpleNamespace(MOBILE="mobile")  # type: ignore[attr-defined]

    class _SimRapidOCR:
        def __init__(self, params=None):
            self.use_cls = bool((params or {}).get("Global.use_cls", True))

        def __call__(self, _img):
            kept = sample_lines[:3] if self.use_cls else sample_lines
            boxes = [[[10, 20 * i], [300, 20 * i], [300, 20 * i + 16], [10, 20 * i + 16]] for i in range(len(kept))]
            return SimpleNamespace(boxes=boxes, txts=list(kept), scores=[0.96] * len(kept))

    fake_mod.RapidOCR = _SimRapidOCR  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rapidocr", fake_mod)
    monkeypatch.delitem(sys.modules, "rapidocr_onnxruntime", raising=False)

    adapter = RapidOCRAdapter()
    out = adapter.recognize_image(np.full((200, 400, 3), 255, dtype=np.uint8), page=1, preprocess=False)
    assert len(out) == 6


def test_tk246_pos2_low_quality_scanned_fixture_recovers_to_ocr_extracted(monkeypatch):
    """양성 2: 저장소 고정 저품질 픽스처(low_quality_scanned.pdf, 8d0347b7…)가 PdfParser 경로에서 OCR_EXTRACTED로 복구된다."""
    from packages.document_engine.registry import parse_document

    fixture_path = REPO_ROOT / "docs" / "handoff" / "online" / "materials" / "v2" / "low_quality_scanned.pdf"
    assert fixture_path.is_file()
    digest = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    assert digest.startswith("8d0347b7")

    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")
    monkeypatch.setattr(ocr_mod, "_adapter", None)

    if not _rapidocr_korean_weights_cached():
        # 가중치 미설치 CI 잡(test-sqlite 등)에서는 Docker OCR readiness로 실제 가중치 복구를 검증한다.
        pytest.skip("RapidOCR ONNX weights not pre-cached in this job; verified in Docker OCR readiness")

    try:
        doc = parse_document(
            str(fixture_path),
            document_id="tk246_low_quality",
            filename="low_quality_scanned.pdf",
            mime_type="application/pdf",
            sha256=digest,
        )
        cov = doc.structure["page_coverage"][0]
        tel = cov["ocr_fallback"]
        assert cov["status"] == "OCR_EXTRACTED"
        assert tel["fallback_attempted"] is True
        assert tel["fallback_adopted"] is True
        assert tel["selected_engine"] == "rapidocr"
        assert tel["selected_variant"] == "raw"
        assert tel["rapidocr_use_cls"] is False
        assert tel["raw_confidence"] >= 0.70
        assert tel["raw_hangul_ratio"] >= 0.90
        assert tel["raw_chars"] >= 50
        assert tel["recovered"] is True
    finally:
        monkeypatch.setattr(ocr_mod, "_adapter", None)


def test_tk246_pos3_mixed_numbers_and_dates_lines_preserved(monkeypatch):
    """양성 3: 날짜·수량·금액 숫자가 섞인 한국어 줄이 빠지지 않고 모두 반환된다."""
    mixed_lines = [
        "합성 점검 계약 일자 2025년 3월 4일 확인",
        "납품 수량 총 10개 중 5개 우선 인도 완료",
        "잔금 12,500,000원은 검수 후 14일 이내 지급",
    ]
    if _rapidocr_korean_weights_cached() and korean_font_path() is not None:
        from PIL import Image, ImageDraw, ImageFont

        font = ImageFont.truetype(str(korean_font_path()), 30)
        img = Image.new("RGB", (1654, 800), "white")
        draw = ImageDraw.Draw(img)
        for idx, txt in enumerate(mixed_lines):
            draw.text((120, 120 + idx * 80), txt, font=font, fill="black")

        adapter = RapidOCRAdapter()
        out = adapter.recognize_image(img, page=1, preprocess=True)
        assert len(out) == 3
        joined = " ".join(line.text for line in out)
        assert "2025" in joined and "10" in joined and "14" in joined
        return

    fake_mod = ModuleType("rapidocr")
    fake_mod.LangRec = SimpleNamespace(KOREAN="korean")  # type: ignore[attr-defined]
    fake_mod.OCRVersion = SimpleNamespace(PPOCRV5="PP-OCRv5")  # type: ignore[attr-defined]
    fake_mod.ModelType = SimpleNamespace(MOBILE="mobile")  # type: ignore[attr-defined]

    class _SimRapidOCR:
        def __init__(self, params=None):
            self.use_cls = bool((params or {}).get("Global.use_cls", True))

        def __call__(self, _img):
            # use_cls=True일 때 숫자 섞인 줄이 회전 오판으로 누락되던 현상 모사
            kept = [mixed_lines[0]] if self.use_cls else mixed_lines
            boxes = [[[10, 25 * i], [320, 25 * i], [320, 25 * i + 18], [10, 25 * i + 18]] for i in range(len(kept))]
            return SimpleNamespace(boxes=boxes, txts=list(kept), scores=[0.95] * len(kept))

    fake_mod.RapidOCR = _SimRapidOCR  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rapidocr", fake_mod)
    monkeypatch.delitem(sys.modules, "rapidocr_onnxruntime", raising=False)

    adapter = RapidOCRAdapter()
    out = adapter.recognize_image(np.full((200, 400, 3), 255, dtype=np.uint8), page=1, preprocess=False)
    assert len(out) == 3
    assert any("2025" in line.text for line in out)
    assert any("12,500,000" in line.text for line in out)


def test_tk246_ctrl1_clean_scanned_fixture_unchanged_without_fallback(monkeypatch):
    """대조 1: 정상 스캔 픽스처(clean_scanned.pdf, 4b062f82…)는 폴백 시도 없이 1차 Tesseract 결과 그대로 불변이다."""
    if not probe_tesseract("kor+eng").get("available"):
        pytest.skip("tesseract kor+eng unavailable")
    from packages.document_engine.registry import parse_document

    fixture_path = REPO_ROOT / "docs" / "handoff" / "online" / "materials" / "v2" / "clean_scanned.pdf"
    assert fixture_path.is_file()
    digest = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    assert digest.startswith("4b062f82")

    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")
    monkeypatch.setattr(ocr_mod, "_adapter", None)
    try:
        doc = parse_document(
            str(fixture_path),
            document_id="tk246_clean",
            filename="clean_scanned.pdf",
            mime_type="application/pdf",
            sha256=digest,
        )
        cov = doc.structure["page_coverage"][0]
        tel = cov["ocr_fallback"]
        assert cov["status"] == "OCR_EXTRACTED"
        assert tel["fallback_attempted"] is False
        assert tel["fallback_adopted"] is False
        assert tel["selected_engine"] == "tesseract"
        assert tel["primary_confidence"] >= 0.85
    finally:
        monkeypatch.setattr(ocr_mod, "_adapter", None)


def test_tk246_ctrl2_rotated_180_page_including_short_3_lines_never_adopts_fallback_garbage_as_normal(tmp_path, monkeypatch):
    """대조 2: 쪽 전체가 180° 뒤집힌 입력(다줄 본문 및 한글 비율 미평가 짧은 3줄 1/96 사례 포함)에서 폴백이 쓰레기 본문을 정상으로 채택하지 않는다."""
    # (A) 결정론적 단위 검증: 짧은 3줄(1차 3줄·22자 저품질 vs 폴백 1줄·7자 미평가 고신뢰도 단편)에서 폴백 단편 채택 차단
    class _Rot180Pri(OCRAdapter):
        name = "tesseract"
        available = True

        def recognize(self, path, page_numbers=None):
            return [
                OCRLine(text="f$000'S 2", page=1, bbox=BBox(0, 0, 80, 20), confidence=0.22),
                OCRLine(text="LE 79002", page=1, bbox=BBox(0, 25, 80, 45), confidence=0.57),
                OCRLine(text="by 16 #8", page=1, bbox=BBox(0, 50, 80, 70), confidence=0.60),
            ]

    class _Rot180Fb(OCRAdapter):
        name = "rapidocr"
        available = True

        def recognize(self, path, page_numbers=None):
            # 180° 뒤집힌 짧은 3줄에서 2줄은 0.5 미만으로 버려지고 7자 단편 1줄만 0.755로 남은 실제 현상
            return [OCRLine(text="공000's은", page=1, bbox=BBox(0, 0, 60, 20), confidence=0.755)]

    comp = CompositeOCRAdapter(_Rot180Pri(), _Rot180Fb(), mode="auto")
    out = comp.recognize("rot180_short.pdf")
    q_out = page_quality(out, lang="kor+eng")
    tel = build_ocr_page_telemetry(comp, q_out, page=1)
    assert tel["fallback_attempted"] is True
    assert tel["fallback_adopted"] is False
    assert tel["route_deciding_key"] == "UNASSESSED_SEVERE_TRUNCATION"
    assert q_out["low_quality"] is True  # 정상으로 오판되지 않아 PdfParser._reoriented()가 발동할 수 있음

    # (B) 실제 PDF 파서 + RapidOCR 가중치 환경(Docker OCR readiness): 짧은 3줄 180° 스캔 PDF가 쓰레기 단편 대신 정방향 3줄을 복원
    if _rapidocr_korean_weights_cached() and probe_tesseract("kor+eng").get("available") and korean_font_path() is not None:
        from packages.document_engine.registry import parse_document
        from scripts.audit.corpus import _append_scan_page, build_pdf

        monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
        monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")
        monkeypatch.setattr(ocr_mod, "_adapter", None)
        try:
            pdf_path = build_pdf(
                {"name": "rot180_short", "header": "합성 시험 문서", "footer": "시험용 가상 문서", "body": [("h", "첨부")]},
                tmp_path / "rot180_short.pdf",
            )
            _append_scan_page(pdf_path, ["합 의 서", "2026. 4. 31.", "금 5,000원"], rotate=180)
            doc = parse_document(
                str(pdf_path),
                document_id="tk246_rot180",
                filename="rot180_short.pdf",
                mime_type="application/pdf",
                sha256="0" * 64,
            )
            p2_texts = [b.text for b in doc.body_blocks() if b.page == 2]
            joined = " ".join(p2_texts)
            assert "2026" in joined
            assert "공000" not in joined
            assert doc.structure.get("ocr_rotation", {}).get("2") in (90, 180, 270)
        finally:
            monkeypatch.setattr(ocr_mod, "_adapter", None)


def test_tk246_ctrl3_broken_hangul_still_loses_under_tk244_rank():
    """대조 3: 깨진 한글(20자 이상 로마자 오인식, 높은 신뢰도)은 여전히 정상 한글 변형에 지고, 20자 미만 미평가 규칙(TK-244 보완 7)도 유지된다."""
    adapter = RapidOCRAdapter()
    adapter.available = True
    adapter._ensure_engine = lambda: True  # type: ignore[method-assign]
    box = [[0, 0], [120, 0], [120, 22], [0, 22]]
    calls = 0

    def _engine(_img):
        nonlocal calls
        calls += 1
        if calls == 1:
            # 한글 1 + 영문 25 = 26자 -> hangul_assessed=True, hangul_ok=False, conf=0.83
            return ([[box, "가 abcdefghijklmnopqrstuvwxy", 0.83]], None)
        # 한글 22자 -> hangul_assessed=True, hangul_ok=True, conf=0.61
        return ([[box, "계약해지통지서원문내용확인절차안내문장입니다", 0.61]], None)

    adapter._engine = _engine
    img = np.full((120, 220, 3), 235, dtype=np.uint8)
    img[20:45, 20:150] = 35
    lines = adapter.recognize_image(img, preprocess=True)
    assert len(lines) == 1
    assert lines[0].confidence == 0.61
    assert adapter.last_preprocess_telemetry["selected_variant"] == "preprocessed"
    assert adapter.last_preprocess_telemetry["deciding_key"] == "HANGUL_RATIO_THRESHOLD"
