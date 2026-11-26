"""TK-244 (+ supplement round 1) unit tests: OCR variant selection rank, deciding_key, variant audit fields, and unified hangul_ok assessment."""
from __future__ import annotations

import numpy as np

from packages.common.schemas import BBox
from packages.document_engine.ocr import (
    CompositeOCRAdapter,
    OCRAdapter,
    OCRLine,
    RapidOCRAdapter,
    _fallback_improved,
    build_ocr_page_telemetry,
    page_quality,
)


def _sample_image() -> np.ndarray:
    img = np.full((120, 200, 3), 235, dtype=np.uint8)
    img[20:45, 20:140] = 35
    return img


def _make_rapid(raw_items: list[tuple[str, float]], pre_items: list[tuple[str, float]]) -> RapidOCRAdapter:
    adapter = RapidOCRAdapter()
    adapter.available = True
    adapter._ensure_engine = lambda: True  # type: ignore[method-assign]
    box = [[0, 0], [100, 0], [100, 20], [0, 20]]
    calls = 0

    def _engine(_img):
        nonlocal calls
        calls += 1
        items = raw_items if calls == 1 else pre_items
        return ([[box, text, conf] for text, conf in items], None)

    adapter._engine = _engine
    return adapter


def test_tk244_pos1_both_low_quality_hangul_ok_selects_higher_confidence():
    """양성 1: 둘 다 저품질·한글 기준 통과일 때 한글 비율이 소폭 낮아도 신뢰도가 높은 원본(0.582 > 0.534)을 고르고 CONFIDENCE를 기록한다."""
    # raw: 한글 18자 + 로마자 6자 = 24자 (hangul_ratio = 0.75 >= 0.5), conf = 0.582 (< 0.70 -> low_quality)
    raw_txt = "임대차계약해지통지서원문본문확인절차 ABCDEF"
    # pre: 한글 17자 + 로마자 3자 = 20자 (hangul_ratio = 0.85 >= 0.5), conf = 0.534 (< 0.70 -> low_quality)
    pre_txt = "임대차계약해지통지서원문본문확인절 ABC"
    adapter = _make_rapid([(raw_txt, 0.582)], [(pre_txt, 0.534)])
    lines = adapter.recognize_image(_sample_image(), preprocess=True)
    assert lines[0].confidence == 0.582
    tel = adapter.last_preprocess_telemetry
    assert tel["selected_variant"] == "raw"
    assert tel["deciding_key"] == "CONFIDENCE"
    assert tel["raw_hangul_ratio"] == 0.75
    assert tel["preprocessed_hangul_ratio"] == 0.85
    assert tel["raw_low_quality"] is True
    assert tel["preprocessed_low_quality"] is True


def test_tk244_pos2_fallback_improved_follows_new_rank_on_both_low_quality():
    """양성 2: 1차↔폴백 비교(_fallback_improved / CompositeOCRAdapter)도 둘 다 저품질·한글 통과면 신뢰도 우선 순위를 따른다."""
    # primary: ratio 0.85, conf 0.483; fallback: ratio 0.75, conf 0.582 -> 폴백 채택(CONFIDENCE)
    pri_line = OCRLine(text="임대차계약해지통지서원문본문확인절 ABC", page=1, bbox=BBox(0, 0, 80, 20), confidence=0.483)
    fb_line = OCRLine(text="임대차계약해지통지서원문본문확인절차 ABCDEF", page=1, bbox=BBox(0, 0, 80, 20), confidence=0.582)
    q_pri = page_quality([pri_line], lang="kor+eng")
    q_fb = page_quality([fb_line], lang="kor+eng")
    assert q_pri["low_quality"] is True and q_fb["low_quality"] is True
    assert _fallback_improved([pri_line], q_pri, [fb_line], q_fb) is True
    # 역방향(1차 신뢰도가 더 높고 폴백 한글 비율만 조금 높음)은 기각
    assert _fallback_improved([fb_line], q_fb, [pri_line], q_pri) is False

    class _Pri(OCRAdapter):
        name = "tesseract"
        available = True

        def recognize(self, path, page_numbers=None):
            return [fb_line]

    class _Fb(OCRAdapter):
        name = "rapidocr"
        available = True

        def recognize(self, path, page_numbers=None):
            return [pri_line]

    comp = CompositeOCRAdapter(_Pri(), _Fb(), mode="auto")
    out = comp.recognize("low.pdf")
    tel = build_ocr_page_telemetry(comp, page_quality(out, lang="kor+eng"), page=1)
    assert tel["fallback_adopted"] is False
    assert tel["route_deciding_key"] == "CONFIDENCE"


def test_tk244_pos3_equal_confidence_breaks_tie_by_hangul_ratio():
    """양성 3: 저품질·한글 기준 통과·신뢰도가 모두 같으면 한글 비율 값(HANGUL_RATIO)으로 결정한다."""
    raw_txt = "임대차계약해지통지서원문본문확인절차 ABCDEF"  # 18 / 24 = 0.75
    pre_txt = "임대차계약해지통지서원문본문확인절 ABC"     # 17 / 20 = 0.85
    adapter = _make_rapid([(raw_txt, 0.60)], [(pre_txt, 0.60)])
    lines = adapter.recognize_image(_sample_image(), preprocess=True)
    tel = adapter.last_preprocess_telemetry
    assert tel["selected_variant"] == "preprocessed"
    assert tel["deciding_key"] == "HANGUL_RATIO"
    assert len(lines) == 1


def test_tk244_ctrl1_garbled_hangul_raw_loses_despite_higher_confidence():
    """대조 1: 원본이 깨진 한글(20자 이상, 한글 기준 미달)이면 신뢰도가 더 높아도 기준 통과 전처리본에 진다."""
    raw_garbled = "의 xj ot AOO ll ahd tk sjdl dkf ekt"  # 한글 1 + 영문 25 = 26자 -> hangul_ok=False
    pre_clean = "임대차계약해지통지서원문본문확인절차입니다"          # 한글 21자 -> hangul_ok=True, conf=0.58 (low_quality=True)
    adapter = _make_rapid([(raw_garbled, 0.68)], [(pre_clean, 0.58)])
    lines = adapter.recognize_image(_sample_image(), preprocess=True)
    tel = adapter.last_preprocess_telemetry
    assert tel["selected_variant"] == "preprocessed"
    assert tel["deciding_key"] == "HANGUL_RATIO_THRESHOLD"
    assert lines[0].confidence == 0.58


def test_tk244_ctrl2_one_not_low_quality_wins_on_low_quality_key():
    """대조 2: 한쪽만 비저품질(>=0.70)이면 LOW_QUALITY 칸에서 비저품질 변형이 선택되고, 저품질(0.582) 단독은 low_quality=True를 유지한다."""
    raw_low = "임대차계약해지통지서원문본문확인절차입니다"
    pre_high = "임대차계약해지통지서원문본문확인절차입니다"
    adapter = _make_rapid([(raw_low, 0.582)], [(pre_high, 0.84)])
    adapter.recognize_image(_sample_image(), preprocess=True)
    tel = adapter.last_preprocess_telemetry
    assert tel["selected_variant"] == "preprocessed"
    assert tel["deciding_key"] == "LOW_QUALITY"
    assert tel["raw_low_quality"] is True
    assert tel["preprocessed_low_quality"] is False


def test_tk244_ctrl3_preprocess_disabled_records_raw_audit_fields_and_null_preprocessed():
    """대조 3: 전처리 비활성 시 원본의 hangul_ratio·low_quality는 기록되고 전처리 측 필드와 deciding_key는 None이다."""
    adapter = _make_rapid([("정상적인법률서면본문내용확인문장입니다", 0.91)], [("미호출", 0.5)])
    adapter.recognize_image(_sample_image(), preprocess=False)
    tel = adapter.last_preprocess_telemetry
    assert tel["preprocess_applied"] is False
    assert tel["raw_hangul_ratio"] == 1.0
    assert tel["raw_low_quality"] is False
    assert tel["preprocessed_hangul_ratio"] is None
    assert tel["preprocessed_low_quality"] is None
    assert tel["deciding_key"] is None


def test_tk244_supp5_numeric_primary_rejects_garbled_hangul_fallback():
    """보완 5: 1차가 숫자뿐(hangul_ratio=None -> hangul_ok=True)이고 폴백이 로마자 20자 이상 깨진 한글이면 신뢰도가 높아도 폴백을 거부한다."""
    class _Pri(OCRAdapter):
        name = "tesseract"
        available = True

        def recognize(self, path, page_numbers=None):
            return [OCRLine(text="2024. 05. 12. 15,000,000", page=1, bbox=BBox(0, 0, 80, 20), confidence=0.48)]

    class _Fb(OCRAdapter):
        name = "rapidocr"
        available = True

        def recognize(self, path, page_numbers=None):
            # 24 latin letters, 1 hangul -> hangul_assessed=True, hangul_ok=False, higher conf 0.65
            return [OCRLine(text="가 abcdefghijklmnopqrstuvwx", page=1, bbox=BBox(0, 0, 80, 20), confidence=0.65)]

    comp = CompositeOCRAdapter(_Pri(), _Fb(), mode="auto")
    out = comp.recognize("num.pdf")
    assert out[0].confidence == 0.48
    tel = build_ocr_page_telemetry(comp, page_quality(out, lang="kor+eng"), page=1)
    assert tel["fallback_attempted"] is True
    assert tel["fallback_adopted"] is False
    assert tel["route_deciding_key"] == "HANGUL_RATIO_THRESHOLD"


def test_tk244_supp6_unrounded_boundary_04997_marks_hangul_not_ok():
    """보완 6: 실제 비율 0.4997(반올림 표시 0.5)은 반올림 전 값으로 평가해 hangul_ok=False·low_quality=True로 일치한다."""
    # 1666 / (1666 + 1668) = 1666 / 3334 = 0.499700059988... -> round(..., 3) == 0.5
    text = ("가" * 1666) + ("a" * 1668)
    q = page_quality([OCRLine(text=text, page=1, confidence=0.90)], lang="kor+eng", min_hangul_ratio=0.5)
    assert q["hangul_ratio"] == 0.5
    assert q["hangul_assessed"] is True
    assert q["hangul_ok"] is False
    assert q["low_quality"] is True
    assert any("한글 비율" in r for r in q["reasons"])


def test_tk244_supp7_under_20_letters_not_assessed_treated_as_ok():
    """보완 7: 한글+로마자가 20자 미만(13자, 비율 0.154)이면 hangul_assessed=False·hangul_ok=True로 미평가 통과 취급된다."""
    # 한글 2자 + 로마자 11자 = 13자 (< MIN_LETTERS_FOR_RATIO=20)
    q_short = page_quality([OCRLine(text="제조 abcdefghijk", page=1, confidence=0.62)], lang="kor+eng")
    assert q_short["hangul_assessed"] is False
    assert q_short["hangul_ok"] is True
    assert not any("한글 비율" in r for r in q_short["reasons"])

    # 20자 이상 통과 변형과 비교할 때도 HANGUL_RATIO_THRESHOLD에서 밀리지 않고 CONFIDENCE로 비교된다
    adapter = _make_rapid(
        [("제조 abcdefghijk", 0.64)],
        [("임대차계약해지통지서원문본문확인절차입니다", 0.55)],
    )
    lines = adapter.recognize_image(_sample_image(), preprocess=True)
    tel = adapter.last_preprocess_telemetry
    assert tel["selected_variant"] == "raw"
    assert tel["deciding_key"] == "CONFIDENCE"
    assert lines[0].confidence == 0.64


def test_tk244_hangul_assessed_and_ok_match_low_quality_reasons():
    """보완 불변식: 모든 경우에서 (not hangul_ok)와 low_quality의 '한글 비율' 사유 유무가 1:1 일치한다."""
    samples = [
        ([], "kor+eng"),
        ([OCRLine(text="12345-67890", page=1, confidence=0.8)], "kor+eng"),
        ([OCRLine(text="재량권 abuse", page=1, confidence=0.8)], "kor+eng"),
        ([OCRLine(text=("가" * 1666) + ("a" * 1668), page=1, confidence=0.85)], "kor+eng"),
        ([OCRLine(text="가 abcdefghijklmnopqrstuvwx", page=1, confidence=0.85)], "kor+eng"),
        ([OCRLine(text="가 abcdefghijklmnopqrstuvwx", page=1, confidence=0.85)], "eng"),
        ([OCRLine(text="원고는 피고에게 손해배상금을 지급하라 청구원인", page=1, confidence=0.85)], "kor+eng"),
    ]
    for lines, lang in samples:
        q = page_quality(lines, lang=lang, min_hangul_ratio=0.5)
        has_hangul_reason = any("한글 비율" in r for r in q["reasons"])
        assert (not q["hangul_ok"]) == has_hangul_reason
        if not q["hangul_assessed"]:
            assert q["hangul_ok"] is True
