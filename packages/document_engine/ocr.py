"""OCR Adapter (제3.2장 교체 가능한 OCR Adapter).

한글·레이아웃·bbox 보존이 필수이므로 인터페이스에 bbox를 강제한다.
엔진이 설치되지 않은 환경에서는 NullOCRAdapter가 UNVERIFIED를 유도한다.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, List, Optional

from packages.common.config import get_settings
from packages.common.schemas import BBox


# 의미 있는 문자(한글·영숫자)가 2자 미만인 라인은 인식 노이즈로 본다.
MEANINGFUL_RE = re.compile(r"[0-9A-Za-z가-힣]")
MIN_MEANINGFUL_CHARS = 2


def is_noise(text: str) -> bool:
    return len(MEANINGFUL_RE.findall(text)) < MIN_MEANINGFUL_CHARS


SINGLE_SYLLABLE_RE = re.compile(r"^[가-힣]$")


def normalize_ocr_spacing(text: str) -> str:
    """한글 OCR이 음절마다 띄어 읽은 부분을 붙인다('헌 법 재판소' → '헌법 재판소', '2020 헌 마 1127' → '2020 헌마 1127').

    한 글자짜리 한글 어절이 둘 이상 이어지면 한 어절로 합친다. 두 글자 이상 어절 사이의 띄어쓰기는 그대로 둔다.
    OCR 층에만 쓴다(원래 띄어 쓴 한 글자 어절이 붙을 수 있으나, 인용·날짜 추출이 깨지는 것보다 낫다).
    """
    tokens = text.split(" ")
    out: List[str] = []
    run: List[str] = []
    for token in tokens + [""]:
        if SINGLE_SYLLABLE_RE.match(token):
            run.append(token)
            continue
        if run:
            out.append("".join(run) if len(run) >= 2 else run[0])
            run = []
        if token:
            out.append(token)
    return " ".join(out)


HANGUL_RE = re.compile(r"[가-힣]")
LATIN_RE = re.compile(r"[A-Za-z]")
MIN_LETTERS_FOR_RATIO = 20


def page_quality(lines, *, lang: Optional[str] = None, min_confidence: Optional[float] = None,
                 min_hangul_ratio: Optional[float] = None) -> dict:
    """한 쪽의 OCR 품질(추가지시 G2).

    - confidence: 인식한 라인의 평균 신뢰도(0~1).
    - hangul_ratio: 글자(한글+로마자) 가운데 한글 비율. 한국어 모델로 읽었는데 한글이 거의 없으면
      "의 xj ot AOO"처럼 한글이 깨져 로마자로 읽힌 것이다. 글자가 적으면 비율을 판단하지 않는다.
    둘 중 하나라도 기준에 못 미치면 low_quality=True. 그 쪽에서 '결함 없음'을 결론 내리지 않는다.
    """
    settings = get_settings()
    lang = lang or settings.ocr_lang
    min_confidence = settings.ocr_quality_min_confidence if min_confidence is None else min_confidence
    min_hangul_ratio = settings.ocr_min_hangul_ratio if min_hangul_ratio is None else min_hangul_ratio
    texts = [line for line in lines if (line.text or "").strip() and not is_noise(line.text)]
    chars = sum(len("".join((line.text or "").split())) for line in texts)
    joined = " ".join(line.text for line in texts)
    hangul, latin = len(HANGUL_RE.findall(joined)), len(LATIN_RE.findall(joined))
    confidence = sum(line.confidence for line in texts) / len(texts) if texts else 0.0
    ratio = hangul / (hangul + latin) if hangul + latin else None
    reasons = []
    if texts and confidence < min_confidence:
        reasons.append(f"평균 신뢰도 {confidence:.2f} < {min_confidence:.2f}")
    if "kor" in lang and ratio is not None and hangul + latin >= MIN_LETTERS_FOR_RATIO and ratio < min_hangul_ratio:
        reasons.append(f"한글 비율 {ratio:.2f} < {min_hangul_ratio:.2f}")
    return {"lines": len(texts), "chars": chars, "confidence": round(confidence, 3),
            "hangul_ratio": None if ratio is None else round(ratio, 3),
            "low_quality": bool(reasons), "reasons": reasons}


@dataclass
class OCRLine:
    text: str
    page: int
    bbox: Optional[BBox] = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "page": self.page,
            "bbox": self.bbox.as_tuple() if self.bbox else None,
            "confidence": round(self.confidence, 3),
        }


class OCRAdapter(ABC):
    name = "base"
    available = False

    @abstractmethod
    def recognize(self, path: str, page_numbers: Optional[List[int]] = None) -> List[OCRLine]:
        """파일 경로에서 텍스트를 인식한다."""

    def recognize_image(self, image: Any, *, page: int = 1, scale: float = 1.0) -> List[OCRLine]:
        """PIL Image에서 인식한다. scale은 이미지 좌표를 canonical 좌표로 되돌리는 비율이다."""
        raise NotImplementedError


class NullOCRAdapter(OCRAdapter):
    """OCR 엔진 미설치 환경. 실패시키지 않고 빈 결과를 반환한다(제10장 원칙)."""

    name = "null"
    available = False

    def __init__(self, diagnostics=None):
        self.diagnostics = diagnostics

    def recognize(self, path: str, page_numbers: Optional[List[int]] = None) -> List[OCRLine]:
        return []

    def recognize_image(self, image: Any, *, page: int = 1, scale: float = 1.0) -> List[OCRLine]:
        return []


class TesseractOCRAdapter(OCRAdapter):
    """Tesseract 기반 구현. 단어가 아니라 라인 단위로 묶어 bbox를 보존한다."""

    name = "tesseract"

    def __init__(self, lang: Optional[str] = None, psm: Optional[int] = None) -> None:
        settings = get_settings()
        self.lang = lang or settings.ocr_lang
        self.psm = psm if psm is not None else settings.ocr_psm
        from .ocr_readiness import probe_tesseract
        self.diagnostics = probe_tesseract(self.lang)
        self.available = self.diagnostics["available"]
        self.version = self.diagnostics["version"]

    @property
    def config(self) -> str:
        return f"--psm {self.psm}"

    def recognize(self, path: str, page_numbers: Optional[List[int]] = None) -> List[OCRLine]:
        if not self.available:
            return []
        from PIL import Image

        try:
            with Image.open(path) as image:
                return self.recognize_image(image.convert("RGB"), page=1)
        except Exception:
            return []

    def detect_rotation(self, image: Any) -> Optional[int]:
        """Tesseract OSD로 바로 세우는 데 필요한 회전 각도(시계 방향, 0·90·180·270). 판단하지 못하면 None."""
        if not self.available:
            return None
        import pytesseract

        try:
            osd = pytesseract.image_to_osd(image, config="--psm 0", output_type=pytesseract.Output.DICT,
                                           timeout=max(1, get_settings().ocr_timeout_seconds))
        except Exception:
            return None
        rotate = int(osd.get("rotate") or 0) % 360
        return rotate if float(osd.get("orientation_conf") or 0) >= 1.0 else None

    last_error: Optional[str] = None

    def recognize_image(self, image: Any, *, page: int = 1, scale: float = 1.0,
                        timeout: Optional[float] = None) -> List[OCRLine]:
        """라인 단위로 그룹핑해 텍스트·bbox·평균 신뢰도를 만든다.

        인식 실패는 빈 목록을 돌려주되 사유를 last_error에 남긴다('TIMEOUT' 또는 예외 이름). 빈 결과만으로는
        '글자가 없는 쪽'과 '시간 초과로 읽지 못한 쪽'을 구분할 수 없어, 시간 초과가 신뢰도 미달로 기록됐다."""
        self.last_error = None
        if not self.available:
            return []
        import pytesseract

        try:
            data = pytesseract.image_to_data(
                image, lang=self.lang, config=self.config, output_type=pytesseract.Output.DICT,
                timeout=max(1, timeout or get_settings().ocr_timeout_seconds),
            )
        except Exception as exc:
            # pytesseract는 시간 초과를 RuntimeError('Tesseract process timeout')로 알린다
            self.last_error = "TIMEOUT" if "timeout" in str(exc).lower() else type(exc).__name__
            return []

        grouped: dict = defaultdict(list)
        for index, text in enumerate(data.get("text", [])):
            if not str(text).strip():
                continue
            key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
            grouped[key].append(index)

        lines: List[OCRLine] = []
        for indices in grouped.values():
            text = normalize_ocr_spacing(" ".join(str(data["text"][i]).strip() for i in indices).strip())
            if not text or is_noise(text):
                continue
            confidences = [float(data["conf"][i]) for i in indices if str(data["conf"][i]) not in ("-1",)]
            lines.append(
                OCRLine(
                    text=text,
                    page=page,
                    bbox=BBox(
                        x0=min(float(data["left"][i]) for i in indices) / scale,
                        y0=min(float(data["top"][i]) for i in indices) / scale,
                        x1=max(float(data["left"][i] + data["width"][i]) for i in indices) / scale,
                        y1=max(float(data["top"][i] + data["height"][i]) for i in indices) / scale,
                    ),
                    confidence=(sum(confidences) / len(confidences) / 100.0) if confidences else 0.0,
                )
            )
        lines.sort(key=lambda line: (line.bbox.y0 if line.bbox else 0, line.bbox.x0 if line.bbox else 0))
        return lines


def _adapter_version(adapter: Optional[OCRAdapter]) -> Optional[str]:
    if adapter is None:
        return None
    ver = getattr(adapter, "version", None)
    if ver:
        return str(ver)
    pkg_map = {
        "rapidocr": ("rapidocr", "rapidocr-onnxruntime"),
        "paddleocr": ("paddleocr",),
        "tesseract": ("pytesseract",),
    }
    pkgs = pkg_map.get(str(getattr(adapter, "name", "") or "").lower(), ())
    if pkgs:
        from importlib.metadata import version as pkg_version

        for pkg in pkgs:
            try:
                return str(pkg_version(pkg))
            except Exception:
                continue
    return None


def build_ocr_page_telemetry(adapter: Any, quality: dict, *, page: Optional[int] = None) -> dict:
    """Return sanitized per-page OCR fallback telemetry for reports and diagnostics."""
    route = getattr(adapter, "last_route", None) if adapter is not None else None
    if isinstance(route, dict) and route.get("decision_reason"):
        telemetry = {
            "primary_engine": route.get("primary_engine"),
            "primary_version": route.get("primary_version"),
            "primary_confidence": route.get("primary_confidence"),
            "fallback_attempted": bool(route.get("fallback_attempted")),
            "fallback_adopted": bool(route.get("fallback_adopted")),
            "fallback_engine": route.get("fallback_engine"),
            "fallback_version": route.get("fallback_version"),
            "fallback_confidence": route.get("fallback_confidence"),
            "fallback_error": route.get("fallback_error"),
            "decision_reason": route.get("decision_reason"),
            "selected_engine": route.get("selected_engine") or route.get("selected"),
            "selected_version": route.get("selected_version"),
            "selected_confidence": route.get("selected_confidence"),
            "recovered": not bool((quality or {}).get("low_quality")) and bool(route.get("fallback_adopted")),
        }
        pre_tel = route.get("preprocess_telemetry")
        if isinstance(pre_tel, dict):
            telemetry.update(pre_tel)
    else:
        engine_name = getattr(adapter, "name", None) or "unknown"
        engine_ver = _adapter_version(adapter)
        conf = round(float((quality or {}).get("confidence") or 0.0), 3)
        low_q = bool((quality or {}).get("low_quality")) or not int((quality or {}).get("lines") or 0)
        telemetry = {
            "primary_engine": engine_name,
            "primary_version": engine_ver,
            "primary_confidence": conf,
            "fallback_attempted": False,
            "fallback_adopted": False,
            "fallback_engine": None,
            "fallback_version": None,
            "fallback_confidence": None,
            "fallback_error": None,
            "decision_reason": "FALLBACK_NOT_CONFIGURED" if low_q else "PRIMARY_QUALITY_SUFFICIENT",
            "selected_engine": engine_name,
            "selected_version": engine_ver,
            "selected_confidence": conf,
            "recovered": False,
        }
    if page is not None:
        telemetry["page"] = int(page)
    return telemetry


def summarize_ocr_fallback_telemetry(per_page: dict[str, dict]) -> dict:
    """Aggregate per-page OCR fallback telemetry without exposing secrets or raw text."""
    attempted_pages: list[int] = []
    adopted_pages: list[int] = []
    rejected_pages: list[int] = []
    failed_pages: list[int] = []
    unconfigured_pages: list[int] = []
    sufficient_pages: list[int] = []
    engines: dict[str, Optional[str]] = {}
    reason_counts: dict[str, int] = {}
    for page_key, item in sorted((per_page or {}).items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0):
        if not isinstance(item, dict):
            continue
        pno = int(item.get("page") if item.get("page") is not None else page_key) if str(page_key).isdigit() or item.get("page") is not None else None
        reason = str(item.get("decision_reason") or "")
        if reason:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if item.get("primary_engine"):
            engines[str(item["primary_engine"])] = item.get("primary_version")
        if item.get("fallback_engine"):
            engines[str(item["fallback_engine"])] = item.get("fallback_version")
        if item.get("fallback_attempted") and pno is not None:
            attempted_pages.append(pno)
        if item.get("fallback_adopted") and pno is not None:
            adopted_pages.append(pno)
        elif reason in ("FALLBACK_NOT_IMPROVED", "FALLBACK_EMPTY") and pno is not None:
            rejected_pages.append(pno)
        elif reason == "FALLBACK_FAILED" and pno is not None:
            failed_pages.append(pno)
        elif reason in ("FALLBACK_NOT_CONFIGURED", "FALLBACK_UNAVAILABLE") and pno is not None:
            unconfigured_pages.append(pno)
        elif reason == "PRIMARY_QUALITY_SUFFICIENT" and pno is not None:
            sufficient_pages.append(pno)
    return {
        "total_pages": len(per_page or {}),
        "attempted_pages": attempted_pages,
        "adopted_pages": adopted_pages,
        "rejected_pages": rejected_pages,
        "failed_pages": failed_pages,
        "unconfigured_pages": unconfigured_pages,
        "sufficient_pages": sufficient_pages,
        "reason_counts": reason_counts,
        "engines": engines,
        "pages": dict(per_page or {}),
    }


class CompositeOCRAdapter(OCRAdapter):
    """Adaptive OCR router: runs primary adapter, checks `page_quality()`, and falls back only on low quality."""

    name = "composite"

    def __init__(self, primary: OCRAdapter, fallback: Optional[OCRAdapter] = None, *, mode: str = "auto") -> None:
        self.primary = primary
        self.fallback = fallback
        self.mode = (mode or "auto").strip().lower()
        self.available = bool(primary.available or (fallback and fallback.available))
        self.last_error: Optional[str] = None
        self.last_route: dict = {}

    def _route(self, pri_fn, fb_fn) -> List[OCRLine]:
        self.last_error = None
        lines: List[OCRLine] = []
        pri_err: Optional[str] = None
        if self.primary.available:
            try:
                lines = pri_fn()
                pri_err = getattr(self.primary, "last_error", None)
            except Exception as exc:
                lines = []
                pri_err = type(exc).__name__
        q_pri = page_quality(lines)
        pri_ver = _adapter_version(self.primary)
        fb_ver = _adapter_version(self.fallback)
        needs_fallback = bool(not lines or q_pri["low_quality"] or pri_err)

        if self.mode == "off":
            self.last_error = pri_err
            self.last_route = {
                "selected": self.primary.name,
                "primary": q_pri,
                "primary_engine": self.primary.name,
                "primary_version": pri_ver,
                "primary_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
                "primary_error": pri_err,
                "fallback_attempted": False,
                "fallback_adopted": False,
                "fallback_engine": self.fallback.name if self.fallback else None,
                "fallback_version": fb_ver,
                "fallback_confidence": None,
                "fallback_error": None,
                "decision_reason": "FALLBACK_DISABLED_BY_MODE",
                "selected_engine": self.primary.name,
                "selected_version": pri_ver,
                "selected_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
            }
            return lines

        if not needs_fallback and self.mode != "force":
            self.last_error = pri_err
            self.last_route = {
                "selected": self.primary.name,
                "primary": q_pri,
                "primary_engine": self.primary.name,
                "primary_version": pri_ver,
                "primary_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
                "primary_error": pri_err,
                "fallback_attempted": False,
                "fallback_adopted": False,
                "fallback_engine": self.fallback.name if self.fallback else None,
                "fallback_version": fb_ver,
                "fallback_confidence": None,
                "fallback_error": None,
                "decision_reason": "PRIMARY_QUALITY_SUFFICIENT",
                "selected_engine": self.primary.name,
                "selected_version": pri_ver,
                "selected_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
            }
            return lines

        if self.fallback is None or not self.fallback.available:
            reason = "FALLBACK_NOT_CONFIGURED" if self.fallback is None else "FALLBACK_UNAVAILABLE"
            self.last_error = pri_err
            self.last_route = {
                "selected": self.primary.name,
                "primary": q_pri,
                "primary_engine": self.primary.name,
                "primary_version": pri_ver,
                "primary_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
                "primary_error": pri_err,
                "fallback_attempted": False,
                "fallback_adopted": False,
                "fallback_engine": self.fallback.name if self.fallback else None,
                "fallback_version": fb_ver,
                "fallback_confidence": None,
                "fallback_error": None,
                "decision_reason": reason,
                "selected_engine": self.primary.name,
                "selected_version": pri_ver,
                "selected_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
            }
            return lines

        fb_lines: List[OCRLine] = []
        fb_err: Optional[str] = None
        try:
            fb_lines = fb_fn()
            fb_err = getattr(self.fallback, "last_error", None)
        except Exception as exc:
            fb_lines = []
            fb_err = type(exc).__name__
        q_fb = page_quality(fb_lines)
        fb_conf = round(float(q_fb.get("confidence") or 0.0), 3)

        if self.mode == "shadow":
            self.last_error = pri_err
            self.last_route = {
                "selected": self.primary.name,
                "primary": q_pri,
                "fallback": q_fb,
                "primary_engine": self.primary.name,
                "primary_version": pri_ver,
                "primary_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
                "primary_error": pri_err,
                "fallback_attempted": True,
                "fallback_adopted": False,
                "fallback_engine": self.fallback.name,
                "fallback_version": fb_ver,
                "fallback_confidence": fb_conf,
                "fallback_error": fb_err,
                "decision_reason": "SHADOW_MODE",
                "selected_engine": self.primary.name,
                "selected_version": pri_ver,
                "selected_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
            }
            return lines

        fb_pre = getattr(self.fallback, "last_preprocess_telemetry", None)
        if not fb_err and _fallback_improved(lines, q_pri, fb_lines, q_fb):
            self.last_error = None
            self.last_route = {
                "selected": self.fallback.name,
                "primary": q_pri,
                "fallback": q_fb,
                "primary_engine": self.primary.name,
                "primary_version": pri_ver,
                "primary_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
                "primary_error": pri_err,
                "fallback_attempted": True,
                "fallback_adopted": True,
                "fallback_engine": self.fallback.name,
                "fallback_version": fb_ver,
                "fallback_confidence": fb_conf,
                "fallback_error": None,
                "decision_reason": "FALLBACK_IMPROVED_QUALITY",
                "selected_engine": self.fallback.name,
                "selected_version": fb_ver,
                "selected_confidence": fb_conf,
                **({"preprocess_telemetry": fb_pre} if isinstance(fb_pre, dict) else {}),
            }
            return fb_lines

        reason = "FALLBACK_FAILED" if fb_err else ("FALLBACK_EMPTY" if not fb_lines else "FALLBACK_NOT_IMPROVED")
        self.last_error = pri_err
        self.last_route = {
            "selected": self.primary.name,
            "primary": q_pri,
            "fallback": q_fb,
            "primary_engine": self.primary.name,
            "primary_version": pri_ver,
            "primary_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
            "primary_error": pri_err,
            "fallback_attempted": True,
            "fallback_adopted": False,
            "fallback_engine": self.fallback.name,
            "fallback_version": fb_ver,
            "fallback_confidence": fb_conf,
            "fallback_error": fb_err,
            "decision_reason": reason,
            "selected_engine": self.primary.name,
            "selected_version": pri_ver,
            "selected_confidence": round(float(q_pri.get("confidence") or 0.0), 3),
            **({"preprocess_telemetry": fb_pre} if isinstance(fb_pre, dict) else {}),
        }
        return lines

    def recognize(self, path: str, page_numbers: Optional[List[int]] = None) -> List[OCRLine]:
        return self._route(
            lambda: self.primary.recognize(path, page_numbers=page_numbers),
            lambda: self.fallback.recognize(path, page_numbers=page_numbers),  # type: ignore[union-attr]
        )

    def recognize_image(self, image: Any, *, page: int = 1, scale: float = 1.0, **kwargs: Any) -> List[OCRLine]:
        def _fb_call() -> List[OCRLine]:
            try:
                return self.fallback.recognize_image(image, page=page, scale=scale, preprocess=True)  # type: ignore[union-attr]
            except TypeError:
                return self.fallback.recognize_image(image, page=page, scale=scale)  # type: ignore[union-attr]

        return self._route(
            lambda: self.primary.recognize_image(image, page=page, scale=scale, **kwargs),
            _fb_call,
        )


def _quality_rank(q: dict) -> tuple[bool, float, float, int]:
    return (
        not bool(q.get("low_quality")),
        float(q.get("hangul_ratio") or 0.0),
        float(q.get("confidence") or 0.0),
        int(q.get("lines") or 0),
    )


def _fallback_improved(
    pri_lines: List[OCRLine],
    q_pri: dict,
    fb_lines: List[OCRLine],
    q_fb: dict,
) -> bool:
    if not fb_lines:
        return False
    if not pri_lines:
        return True
    if q_pri["low_quality"] and not q_fb["low_quality"]:
        return True
    if not q_pri["low_quality"] and q_fb["low_quality"]:
        return False
    fb_conf = float(q_fb.get("confidence") or 0.0)
    pri_conf = float(q_pri.get("confidence") or 0.0)
    if fb_conf > pri_conf and float(q_fb.get("hangul_ratio") or 0.0) >= float(q_pri.get("hangul_ratio") or 0.0):
        return True
    return _quality_rank(q_fb) > _quality_rank(q_pri)


def _recognize_path_via_adapter(
    adapter: OCRAdapter,
    path: str,
    page_numbers: Optional[List[int]] = None,
) -> List[OCRLine]:
    """Recognize either a multi-page PDF (rendering requested pages at canonical scale) or an image file."""
    from contextlib import closing
    from pathlib import Path
    from PIL import Image

    if Path(path).suffix.lower() == ".pdf":
        import pypdfium2 as pdfium  # type: ignore

        dpi = max(72, int(get_settings().ocr_dpi or 200))
        scale = dpi / 72.0
        lines: List[OCRLine] = []
        with closing(pdfium.PdfDocument(path)) as pdf:
            total_pages = len(pdf)
            targets = (
                [p for p in page_numbers if 1 <= int(p) <= total_pages]
                if page_numbers is not None
                else list(range(1, total_pages + 1))
            )
            for page_no in targets:
                with closing(pdf[page_no - 1]) as page:
                    bitmap = page.render(scale=scale)
                    pil_img = bitmap.to_pil()
                    try:
                        lines.extend(adapter.recognize_image(pil_img.convert("RGB"), page=int(page_no), scale=scale))
                    finally:
                        if hasattr(pil_img, "close"):
                            pil_img.close()
        return lines

    page_no = int(page_numbers[0]) if page_numbers else 1
    with Image.open(path) as img:
        return adapter.recognize_image(img.convert("RGB"), page=page_no, scale=1.0)


class RapidOCRAdapter(OCRAdapter):
    """Optional RapidOCR ONNX fallback adapter (lazy-loaded to avoid startup RAM overhead)."""

    name = "rapidocr"

    def __init__(self, *, lazy: bool = True) -> None:
        import importlib.util
        import sys

        self._engine: Any = None
        self._v3_api = False
        has_legacy_mock = "rapidocr_onnxruntime" in sys.modules
        if has_legacy_mock and sys.modules["rapidocr_onnxruntime"] is None and "rapidocr" not in sys.modules:
            self.available = False
        elif has_legacy_mock and sys.modules["rapidocr_onnxruntime"] is not None:
            self.available = True
        elif "rapidocr" in sys.modules:
            self.available = sys.modules["rapidocr"] is not None
        else:
            self.available = bool(
                importlib.util.find_spec("rapidocr") is not None
                or importlib.util.find_spec("rapidocr_onnxruntime") is not None
            )
        if not lazy and self.available:
            self._ensure_engine()

    def _ensure_engine(self) -> bool:
        import importlib.util
        import sys

        if self._engine is not None:
            return True
        if not self.available:
            return False
        # Respect test mocks or explicit legacy module in sys.modules["rapidocr_onnxruntime"]
        if sys.modules.get("rapidocr_onnxruntime") is not None:
            try:
                from rapidocr_onnxruntime import RapidOCR as LegacyRapidOCR  # type: ignore

                self._engine = LegacyRapidOCR()
                self._v3_api = False
                return True
            except Exception:
                self._engine = None
                self.available = False
                return False
        try:
            from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR  # type: ignore

            self._engine = RapidOCR(
                params={
                    "Rec.lang_type": LangRec.KOREAN,
                    "Rec.ocr_version": OCRVersion.PPOCRV5,
                    "Rec.model_type": ModelType.MOBILE,
                }
            )
            self._v3_api = True
            return True
        except Exception:
            try:
                from rapidocr_onnxruntime import RapidOCR as LegacyRapidOCR  # type: ignore

                self._engine = LegacyRapidOCR()
                self._v3_api = False
                return True
            except Exception:
                self._engine = None
                self.available = False
                return False

    def _parse_raw_output(self, raw: Any, *, page: int, scale: float) -> List[OCRLine]:
        entries = []
        if hasattr(raw, "boxes") and hasattr(raw, "txts") and hasattr(raw, "scores"):
            boxes = raw.boxes if raw.boxes is not None else []
            txts = raw.txts if raw.txts is not None else []
            scores = raw.scores if raw.scores is not None else []
            entries = list(zip(boxes, txts, scores))
        elif isinstance(raw, tuple) and raw and isinstance(raw[0], list):
            entries = raw[0]
        elif isinstance(raw, list):
            entries = raw

        lines: List[OCRLine] = []
        for entry in entries:
            if not isinstance(entry, (list, tuple)) or len(entry) < 3:
                continue
            pts, text, conf = entry[0], str(entry[1] or "").strip(), float(entry[2] or 0.0)
            norm = normalize_ocr_spacing(text)
            if not norm or is_noise(norm):
                continue
            xs = [float(p[0]) / scale for p in pts]
            ys = [float(p[1]) / scale for p in pts]
            lines.append(OCRLine(text=norm, page=page, bbox=BBox(min(xs), min(ys), max(xs), max(ys)), confidence=conf))
        return lines

    @staticmethod
    def _preprocess_low_quality_image_with_status(image: Any) -> Tuple[Any, float, str]:
        """Apply adaptive grayscale + upscale + contrast/sharpen; return (image, scale, status)."""
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore

            arr = np.asarray(image)
            if arr.ndim == 2:
                gray = arr
            elif arr.ndim == 3 and arr.shape[2] >= 3:
                gray = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2GRAY)
            else:
                return image, 1.0, "SKIPPED"

            h, w = gray.shape[:2]
            contrast_std = float(np.std(gray))
            up = 1.0
            if min(h, w) > 0 and max(h, w) < 1800:
                up = min(2.0, 1800.0 / float(max(h, w)))
                if up > 1.05:
                    gray = cv2.resize(gray, (int(round(w * up)), int(round(h * up))), interpolation=cv2.INTER_CUBIC)
                else:
                    up = 1.0

            if contrast_std < 35.0:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
            elif contrast_std < 55.0:
                clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
            else:
                enhanced = gray

            if contrast_std < 45.0:
                blurred = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.0)
                sharpened = cv2.addWeighted(enhanced, 1.25, blurred, -0.25, 0)
            else:
                sharpened = enhanced
            rgb = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)
            return rgb, up, "APPLIED"
        except Exception:
            return image, 1.0, "UNAVAILABLE"

    @staticmethod
    def _preprocess_low_quality_image(image: Any) -> Tuple[Any, float]:
        """Apply adaptive grayscale + upscale + contrast/sharpen based on image contrast and resolution."""
        img, up, _ = RapidOCRAdapter._preprocess_low_quality_image_with_status(image)
        return img, up

    def recognize(self, path: str, page_numbers: Optional[List[int]] = None) -> List[OCRLine]:
        if not self.available:
            return []
        return _recognize_path_via_adapter(self, path, page_numbers=page_numbers)

    def recognize_image(
        self,
        image: Any,
        *,
        page: int = 1,
        scale: float = 1.0,
        preprocess: bool = False,
    ) -> List[OCRLine]:
        if not self._ensure_engine() or self._engine is None:
            return []
        raw_lines = self._parse_raw_output(self._engine(image), page=page, scale=scale)
        q_raw = page_quality(raw_lines)
        raw_conf = round(float(q_raw.get("confidence") or 0.0), 3)
        raw_chars = int(q_raw.get("chars") or 0)
        if not preprocess or image is None:
            self.last_preprocess_telemetry = {
                "preprocess_applied": False,
                "raw_confidence": raw_conf,
                "preprocessed_confidence": None,
                "raw_chars": raw_chars,
                "preprocessed_chars": None,
                "selected_variant": "raw",
                "selection_reason": "PREPROCESS_DISABLED",
            }
            return raw_lines
        try:
            pre_img, up, pre_status = self._preprocess_low_quality_image_with_status(image)
        except Exception:
            pre_img, up, pre_status = image, 1.0, "UNAVAILABLE"
        if pre_status != "APPLIED" or (pre_img is image and up == 1.0):
            reason = "PREPROCESS_UNAVAILABLE" if pre_status == "UNAVAILABLE" else "PREPROCESS_SKIPPED"
            self.last_preprocess_telemetry = {
                "preprocess_applied": False,
                "raw_confidence": raw_conf,
                "preprocessed_confidence": None,
                "raw_chars": raw_chars,
                "preprocessed_chars": None,
                "selected_variant": "raw",
                "selection_reason": reason,
            }
            return raw_lines
        pre_lines = self._parse_raw_output(self._engine(pre_img), page=page, scale=scale * up)
        q_pre = page_quality(pre_lines)
        pre_conf = round(float(q_pre.get("confidence") or 0.0), 3)
        pre_chars = int(q_pre.get("chars") or 0)
        choose_pre = bool(pre_lines) and (not raw_lines or _quality_rank(q_pre) > _quality_rank(q_raw))
        self.last_preprocess_telemetry = {
            "preprocess_applied": True,
            "raw_confidence": raw_conf,
            "preprocessed_confidence": pre_conf,
            "raw_chars": raw_chars,
            "preprocessed_chars": pre_chars,
            "selected_variant": "preprocessed" if choose_pre else "raw",
            "selection_reason": (
                "PREPROCESSED_NO_RAW" if (choose_pre and not raw_lines)
                else "PREPROCESSED_HIGHER_QUALITY" if choose_pre
                else "RAW_HIGHER_OR_EQUAL_QUALITY"
            ),
        }
        return pre_lines if choose_pre else raw_lines


class PaddleOCRAdapter(OCRAdapter):
    """Optional PaddleOCR fallback adapter."""

    name = "paddleocr"

    def __init__(self, lang: str = "korean") -> None:
        try:
            from paddleocr import PaddleOCR  # type: ignore

            self._engine = PaddleOCR(lang=lang, show_log=False)
            self.available = True
        except Exception:
            self._engine = None
            self.available = False

    def recognize(self, path: str, page_numbers: Optional[List[int]] = None) -> List[OCRLine]:
        if not self.available:
            return []
        return _recognize_path_via_adapter(self, path, page_numbers=page_numbers)

    def recognize_image(self, image: Any, *, page: int = 1, scale: float = 1.0) -> List[OCRLine]:
        if not self.available or self._engine is None:
            return []
        raw = self._engine.ocr(image) or []
        items = raw[0] if raw and isinstance(raw[0], list) else raw
        lines: List[OCRLine] = []
        for entry in items or []:
            if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                continue
            pts = entry[0]
            txt_conf = entry[1]
            if not isinstance(txt_conf, (list, tuple)) or len(txt_conf) < 2:
                continue
            norm = normalize_ocr_spacing(str(txt_conf[0] or "").strip())
            if not norm or is_noise(norm):
                continue
            xs = [float(p[0]) / scale for p in pts]
            ys = [float(p[1]) / scale for p in pts]
            lines.append(OCRLine(text=norm, page=page, bbox=BBox(min(xs), min(ys), max(xs), max(ys)), confidence=float(txt_conf[1] or 0.0)))
        return lines


def _build_optional_fallback(engine_name: str) -> Optional[OCRAdapter]:
    name = (engine_name or "none").strip().lower()
    if name in ("", "none", "off"):
        return None
    if name == "rapidocr":
        adapter = RapidOCRAdapter()
        return adapter if adapter.available else None
    if name == "paddleocr":
        adapter = PaddleOCRAdapter()
        return adapter if adapter.available else None
    return None



_adapter: Optional[OCRAdapter] = None


def get_ocr_adapter() -> OCRAdapter:
    global _adapter
    if _adapter is None:
        import os

        candidate = TesseractOCRAdapter()
        primary: OCRAdapter = candidate if candidate.available else NullOCRAdapter(candidate.diagnostics)
        engine_name = (os.getenv("LV_OCR_FALLBACK_ENGINE") or "none").strip().lower()
        mode = (
            os.getenv("LV_OCR_FALLBACK_MODE")
            or ("auto" if engine_name not in ("", "none", "off") else "off")
        ).strip().lower()
        fallback = None if mode == "off" else _build_optional_fallback(engine_name)
        _adapter = CompositeOCRAdapter(primary, fallback, mode=mode) if fallback is not None else primary
    return _adapter


def set_ocr_adapter(adapter: OCRAdapter) -> None:
    global _adapter
    _adapter = adapter


def reset_ocr_adapter() -> None:
    global _adapter
    _adapter = None

