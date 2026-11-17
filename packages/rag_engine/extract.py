"""Isolated reference extraction. PDF text only; unread/scanned pages are disclosed."""
from __future__ import annotations

import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sys

from packages.adversarial_engine import AdversarialScanner
from packages.common.enums import MetaMessageType, Severity
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.document_engine.registry import parse_document

MAX_CHARS = 3_000_000
MAX_PAGES = 1500
EXTRACTOR_VERSION = "drive-text-v9-tk182"  # TK-182: visual blank verification, OCR quality states, completed vs text-extracted counts
EXCLUDE_MIN_TOTAL = 10       # 이보다 짧은 파일은 쪽 단위로 빼지 않고 전체를 격리한다
EXCLUDE_MAX_SHARE = 0.02     # 전체 쪽수의 2%까지(최소 1쪽)
EXCLUDE_MAX_PAGES = 3        # 그리고 3쪽까지만 해당 쪽을 빼고 색인한다

_PAGE_STATE_BY_STATUS = {
    "text": "NATIVE_TEXT",
    "ocr_applied": "OCR_TEXT",
    "blank": "VERIFIED_BLANK",
    "scanned": "SCAN_UNEXTRACTED",
    "ocr_low_quality": "OCR_LOW_QUALITY",
    "error": "ERROR",
    "unprocessed": "UNPROCESSED",
}


def _page_diag(status: str, **extra) -> dict:
    return {"status": status, "state": _PAGE_STATE_BY_STATUS.get(status, status.upper()), **extra}


def chunk_page_text(text: str, page_number: int, target_size: int = 1040, max_size: int = 1200, overlap: int = 160) -> list[dict]:
    """페이지 텍스트를 문맥·문장 경계를 보존하며 고품질 청크로 분할한다.

    1. PDF 줄바꿈으로 인해 단어나 수치 중간이 쪼개진 현상을 정돈.
    2. 단순 글자 수 슬라이싱 대신 문장 마침표·개행 경계에서 분할하여 키워드 분실 방지.
    """
    if not text or not text.strip():
        return []

    # 단어 중간의 부자연스러운 PDF 줄바꿈 결합
    normalized = re.sub(r'([가-힣a-zA-Z0-9,])\n([가-힣a-zA-Z0-9])', r'\1 \2', text)
    normalized = re.sub(r'[ \t]+', ' ', normalized).strip()
    if not normalized:
        return []

    if len(normalized) <= max_size:
        return [{"page": page_number, "start": 0, "text": normalized}]

    chunks = []
    start = 0
    total_len = len(normalized)

    while start < total_len:
        end = min(start + max_size, total_len)
        if end < total_len:
            # target_size 주변에서 자연스러운 문장 마침표 탐색
            search_start = max(start + target_size - 120, start + 200)
            for marker in ("\n\n", ".\n", ". ", "다. ", "함. ", "임. ", "\n", "; "):
                idx = normalized.rfind(marker, search_start, end)
                if idx != -1:
                    end = idx + len(marker)
                    break

        chunk_str = normalized[start:end].strip()
        if chunk_str:
            chunks.append({"page": page_number, "start": start, "text": chunk_str})

        if end >= total_len:
            break
        start = max(start + 1, end - overlap)

    return chunks


def excludable_pages(total):
    if not total or total < EXCLUDE_MIN_TOTAL:
        return 0
    return min(EXCLUDE_MAX_PAGES, max(1, int(total * EXCLUDE_MAX_SHARE)))


def scan_evidence(finding):
    """격리·제외 근거를 실행 JSON에 남긴다(무엇이 왜 걸렸는지 사람이 되짚을 수 있게)."""
    features = finding.confidence_features or {}
    observed = str(features.get("observed_text") or "")
    return {"type": str(getattr(finding.type, "value", finding.type)),
            "severity": str(getattr(finding.severity, "value", finding.severity)),
            "page": finding.page, "path": features.get("injection_path") or features.get("layer"),
            "intents": [t for t in (finding.tags or [])][:3], "excerpt": " ".join(observed.split())[:60],
            # TK-178: 문서 속성(메타데이터) 격리는 어느 필드였는지 남긴다(종전에는 발췌가 비어 근거를 알 수 없었다).
            **({"field": features.get("metadata_key") or features.get("field_name")}
               if (features.get("metadata_key") or features.get("field_name")) else {})}


def _ocr_pdf_page(pdfium_page, page_number: int) -> tuple[str, dict]:
    """Run bounded OCR on a single rendered PDF page and return (text, diagnostic)."""
    from packages.common.config import get_settings
    from packages.document_engine.ocr import get_ocr_adapter, is_noise, page_quality

    settings = get_settings()
    adapter = get_ocr_adapter()
    if not getattr(adapter, "available", False):
        return "", _page_diag("scanned", ocr_available=False)
    try:
        scale = 2.0
        with closing(pdfium_page.render(scale=scale)) as bitmap:
            image = bitmap.to_pil()
        lines = adapter.recognize_image(image, page=page_number, scale=scale)
    except Exception as exc:
        return "", _page_diag("error", error=type(exc).__name__)
    last_error = getattr(adapter, "last_error", None)
    if last_error:
        return "", _page_diag("error", error=str(last_error))
    raw_lines = [line for line in (lines or []) if (getattr(line, "text", "") or "").strip()]
    if not raw_lines:
        return "", _page_diag("scanned", ocr_attempted=True, ocr_empty=True)
    quality = page_quality(
        raw_lines,
        min_confidence=settings.ocr_quality_min_confidence,
        min_hangul_ratio=0.0,
    )
    kept = [
        line for line in raw_lines
        if float(getattr(line, "confidence", 0.0) or 0.0) >= settings.ocr_min_confidence
        and not is_noise(line.text)
    ]
    ocr_text = "\n".join(line.text.strip() for line in kept)
    if not ocr_text.strip() or quality.get("low_quality"):
        # 저품질·저신뢰도 OCR 결과는 빈 쪽이나 정상 완독으로 숨기지 않는다.
        usable_text = ocr_text if (ocr_text.strip() and kept) else ""
        return usable_text, _page_diag(
            "ocr_low_quality",
            ocr_attempted=True,
            lines=len(kept) if kept else len(raw_lines),
            ocr_quality=quality,
        )
    return ocr_text, _page_diag("ocr_applied", lines=len(kept), ocr_quality=quality)


def extract(path, filename, mime, *, continuation=None):
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    cont = continuation if isinstance(continuation, dict) else {}
    resumed = bool(cont and cont.get("next_page"))
    next_continuation = None
    page_diagnostics: dict[str, dict] = dict(cont.get("page_diagnostics") or {})
    prev_read_pages = int(cont.get("read_pages") or 0)
    prev_no_text_pages = list(cont.get("no_text_pages") or [])
    prev_fallback_pages = list(cont.get("fallback_pages") or [])
    prev_chars = int(cont.get("chars") or 0)

    if mime == "application/pdf" or path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")
            except Exception:
                decrypted = 0
            if not decrypted:
                raise ValueError("ENCRYPTED_REFERENCE")
            try:
                _ = len(reader.pages)
            except Exception:
                raise ValueError("ENCRYPTED_REFERENCE") from None
        doc = NormalizedDocument("reference", filename, mime, digest)
        doc.metadata = dict(reader.metadata or {})
        doc.raw_layers["metadata_text"] = str(doc.metadata)
        total, count = len(reader.pages), prev_chars
        start_page = max(1, int(cont.get("next_page") or 1))
        max_ocr_pages = max(0, int(os.getenv("LV_REFERENCE_OCR_MAX_PAGES", os.getenv("LV_OCR_MAX_PAGES", "5"))))
        ocr_used = 0
        native, fallback_pages = None, list(prev_fallback_pages)
        last_processed = start_page - 1
        try:
            import pypdfium2 as pdfium
            native = pdfium.PdfDocument(path)
        except Exception:
            pass  # Retain the existing parser if the native engine cannot open this PDF.
        try:
            for number in range(start_page, min(total, MAX_PAGES) + 1):
                text = None
                used_fallback = False
                page_error = None
                has_visual_objects = False
                object_check_ok = False
                if native is not None:
                    try:
                        with closing(native[number - 1]) as page:
                            with closing(page.get_textpage()) as textpage:
                                text = textpage.get_text_range()
                            if not (text or "").strip():
                                try:
                                    has_visual_objects = any(True for _ in page.get_objects())
                                    object_check_ok = True
                                except Exception as obj_exc:
                                    object_check_ok = False
                                    page_error = page_error or type(obj_exc).__name__
                    except Exception as exc:
                        text = None
                        page_error = type(exc).__name__
                if text is None or not text.strip():
                    used_fallback = True
                    if number not in fallback_pages:
                        fallback_pages.append(number)
                    try:
                        reader_page = reader.pages[number - 1]
                        text = reader_page.extract_text() or ""
                        if not text.strip() and not has_visual_objects:
                            try:
                                if getattr(reader_page, "images", None):
                                    has_visual_objects = True
                            except Exception as img_exc:
                                page_error = page_error or type(img_exc).__name__
                            if not has_visual_objects and not object_check_ok:
                                # pypdfium2 객체 열거를 못 한 경우 콘텐츠 스트림에 그리기·이미지 연산이 있으면 스캔/벡터로 취급한다.
                                try:
                                    contents = reader_page.get_contents()
                                    raw_ops = contents.get_data() if contents is not None else b""
                                    if raw_ops and re.search(rb"\b(?:Do|BI|re|l|c|S|s|f|F|B|b|sh)\b", raw_ops):
                                        has_visual_objects = True
                                except Exception as op_exc:
                                    page_error = page_error or type(op_exc).__name__
                    except Exception as exc:
                        if reader.is_encrypted and native is None and "Decrypt" in type(exc).__name__:
                            raise ValueError("ENCRYPTED_REFERENCE") from None
                        text = ""
                        page_error = page_error or type(exc).__name__

                if (text or "").strip():
                    page_diagnostics[str(number)] = _page_diag(
                        "text",
                        parser="pypdf" if used_fallback else "pypdfium2",
                    )
                elif has_visual_objects:
                    if max_ocr_pages > 0 and native is not None:
                        if ocr_used >= max_ocr_pages:
                            next_continuation = {
                                "next_page": number,
                                "chars": count,
                                "fallback_pages": fallback_pages,
                                "page_diagnostics": page_diagnostics,
                            }
                            break
                        ocr_used += 1
                        with closing(native[number - 1]) as page:
                            ocr_text, diag = _ocr_pdf_page(page, number)
                        text = ocr_text
                        page_diagnostics[str(number)] = diag
                    else:
                        page_diagnostics[str(number)] = _page_diag("scanned", ocr_available=max_ocr_pages > 0)
                elif page_error or not object_check_ok:
                    page_diagnostics[str(number)] = _page_diag(
                        "error",
                        error=page_error or "OBJECT_ENUMERATION_FAILED",
                        blank_verified=False,
                    )
                else:
                    page_diagnostics[str(number)] = _page_diag("blank", blank_verified=True)

                count += len(text)
                if count > MAX_CHARS:
                    break
                last_processed = number
                doc.pages.append(Page(number, blocks=[Block(f"p{number}", text, number)]))
        finally:
            if native is not None:
                native.close()
        doc.structure.update(text_parser="pypdfium2" if native is not None else "pypdf",
                             fallback_pages=fallback_pages)
    else:
        # Structured precedent tables use a bounded row reader.  This keeps a
        # large workbook out of the ordinary visible-text limit while retaining
        # sheet/row/case-head provenance for exact lookup.
        if path.suffix.lower() in (".xlsx", ".csv"):
            from .case_table import extract_case_table
            structured = extract_case_table(path, file_id="", revision="", continuation=continuation)
            if structured is not None:
                structured.setdefault("body_extraction_scope", "STRUCTURED_CASE_TABLE_ROWS")
                structured.setdefault("page_numbers_reliable", False)
                return structured
        doc = parse_document(str(path), document_id="reference", filename=filename,
                             mime_type=mime, sha256=digest)
        total = len(doc.pages)
        last_processed = total
        if doc.structure.get("parse_error") or doc.structure.get("unsupported_format"):
            raise ValueError("REFERENCE_PARSE_FAILED")
        if len(doc.visible_text) > MAX_CHARS or total > MAX_PAGES:
            raise ValueError("REFERENCE_TEXT_LIMIT")
    # TK-180: verified reference material is evidence, outside instruction classification.
    # Parsing, visibility, size and coverage constraints still apply.
    pages_hit, evidence = set(), []
    chunks, read_pages, no_text_pages = [], prev_read_pages, list(prev_no_text_pages)
    for page in doc.pages:
        if page.page_number in pages_hit:
            continue
        text = "\n".join(b.text for b in page.blocks if b.visible and b.source_layer == "visible_text")
        if not text.strip():
            if page.page_number not in no_text_pages:
                no_text_pages.append(page.page_number)
            continue
        read_pages += 1
        page_chunks = chunk_page_text(text, page.page_number)
        chunks.extend(page_chunks)
    if next_continuation is not None:
        next_continuation["read_pages"] = read_pages
        next_continuation["no_text_pages"] = no_text_pages
    coverage_missing = any(p.get("status") in ("UNVERIFIED", "OCR_LOW_QUALITY")
                           for p in doc.structure.get("page_coverage", []))
    unprocessed_pages = list(range(last_processed + 1, total + 1))
    blank_pages = sorted(int(p) for p, d in page_diagnostics.items() if d.get("status") == "blank")
    scanned_pages = sorted(int(p) for p, d in page_diagnostics.items() if d.get("status") == "scanned")
    ocr_pages = sorted(int(p) for p, d in page_diagnostics.items() if d.get("status") == "ocr_applied")
    ocr_low_quality_pages = sorted(int(p) for p, d in page_diagnostics.items() if d.get("status") == "ocr_low_quality")
    error_pages = sorted(int(p) for p, d in page_diagnostics.items() if d.get("status") == "error")

    if page_diagnostics:
        completed_statuses = {"text", "ocr_applied", "blank"}
        completed_pages = sum(
            1 for p in range(1, min(total, MAX_PAGES) + 1)
            if page_diagnostics.get(str(p), {}).get("status") in completed_statuses
        )
        incomplete_pages = sorted(
            p for p in range(1, total + 1)
            if page_diagnostics.get(str(p), {}).get("status") not in completed_statuses
        )
        coverage_complete = (
            not incomplete_pages
            and not next_continuation
            and not coverage_missing
            and not doc.parse_warnings
        )
        # Keep `partial` aligned with unreadable/no-text page disclosure while
        # `coverage_complete` distinguishes visually verified blank pages from unfinished reads.
        partial = (read_pages < total) or (not coverage_complete)
    else:
        completed_pages = read_pages
        incomplete_pages = unprocessed_pages
        partial = read_pages < total or bool(next_continuation) or coverage_missing or bool(doc.parse_warnings)
        coverage_complete = not partial

    page_state_counts = {}
    for p in range(1, total + 1):
        diag = page_diagnostics.get(str(p))
        state = (diag.get("state") if diag else ("NATIVE_TEXT" if p not in no_text_pages and p <= last_processed else "UNPROCESSED"))
        page_state_counts[state] = page_state_counts.get(state, 0) + 1

    if pages_hit:
        reason = "REFERENCE_INSTRUCTION_PAGES_EXCLUDED"
    elif not coverage_complete:
        reason = "REFERENCE_PARTIALLY_READ"
    elif partial and blank_pages:
        reason = "VERIFIED_BLANK_PAGES" if read_pages > 0 else "VERIFIED_BLANK_DOCUMENT"
    elif partial:
        reason = "REFERENCE_PARTIALLY_READ"
    else:
        reason = ""
    coverage_note = (
        "스캔·저품질 OCR·오류·미처리 쪽이 남아 있어 전문 완독으로 간주하지 않음"
        if not coverage_complete
        else ("시각적 객체가 없는 빈 쪽 확인을 포함해 전체 쪽 검사를 마침" if blank_pages else "")
    )
    return {"chunks": chunks, "sha256": digest, "partial": partial,
            "coverage_complete": coverage_complete,
            "excluded_pages": sorted(pages_hit), "scan_findings": evidence,
            "no_text_pages": no_text_pages,
            "page_diagnostics": page_diagnostics,
            "blank_pages": blank_pages,
            "scanned_pages": scanned_pages,
            "ocr_pages": ocr_pages,
            "ocr_low_quality_pages": ocr_low_quality_pages,
            "error_pages": error_pages,
            "incomplete_pages": incomplete_pages,
            "page_state_counts": page_state_counts,
            "continuation": next_continuation,
            "resumed": resumed,
            "text_parser": doc.structure.get("text_parser", doc.parser_name),
            "fallback_pages": doc.structure.get("fallback_pages", []),
            "unprocessed_pages": unprocessed_pages,
            "coverage_note": coverage_note,
            "page_numbers_reliable": doc.structure.get("page_numbers_reliable", path.suffix.lower() not in (".hwp", ".hwpx")),
            "body_extraction_scope": doc.structure.get("body_extraction_scope", "TEXT_EXTRACTION"),
            "pages": total,
            "read_pages": read_pages,
            "extracted_text_pages": read_pages,
            "completed_pages": completed_pages,
            "reason": reason}


def main():
    source, output, filename, mime = sys.argv[1:5]
    try:
        if sys.platform == "linux":
            import resource
            # Keep a compressed or malformed reference from exhausting the API/worker container.
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        continuation = json.loads(Path(sys.argv[5]).read_text(encoding="utf-8")) if len(sys.argv) > 5 else None
        result = extract(source, filename, mime, continuation=continuation)
    except ValueError as exc:
        # Preserve stable resource/security reason codes for the cache.  The
        # old broad catch turned an actionable limit or timeout into a generic
        # parse failure, making retries and operator diagnosis impossible.
        code = str(exc)
        allowed = {"REFERENCE_TEXT_LIMIT", "REFERENCE_PARSE_TIMEOUT", "REFERENCE_QUARANTINED",
                   "REFERENCE_PARSE_FAILED", "ENCRYPTED_REFERENCE", "REFERENCE_CASE_TABLE_PARTIAL"}
        result = {"chunks": [], "partial": True,
                  "reason": code if code in allowed else "REFERENCE_PARSE_FAILED"}
    except Exception:
        result = {"chunks": [], "partial": True, "reason": "REFERENCE_PARSE_FAILED"}
    Path(output).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
