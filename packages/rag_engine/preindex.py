"""Batch Drive RAG pre-indexing runner and page-completion reporter (P0 PR-02).

Repeatedly invokes `ReferenceLibrary.sync(collect_all=True)` until all eligible Drive
reference files reach `coverage_complete` (or `max_rounds` is reached), eliminating
5-page per-run `PARTIAL` / `BUDGET_EXHAUSTED` bottlenecks during user-facing verification.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
import os
from typing import Any, Callable, Dict, Iterator, List, Optional

from packages.rag_engine.library import ReferenceLibrary


@contextmanager
def _temp_env(overrides: Dict[str, Optional[str]]) -> Iterator[None]:
    previous = {k: os.environ.get(k) for k in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, old in previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


@dataclass
class PreindexReport:
    status: str
    folder_id: str
    rounds_executed: int
    converged: bool
    files_total: int = 0
    files_complete: int = 0
    files_partial: int = 0
    files_failed: int = 0
    pages_total: int = 0
    pages_read: int = 0
    page_completion_rate: Optional[float] = None
    remaining_continuations: int = 0
    coverage_ledger: Dict[str, Any] = field(default_factory=dict)
    issues: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _has_pending_work(summary: Dict[str, Any]) -> tuple[int, int]:
    """Return (remaining_continuations, partial_count) from a ReferenceLibrary summary."""
    continuations = 0
    partials = 0
    for item in (summary.get("files") or summary.get("inventory") or []):
        if not isinstance(item, dict):
            continue
        if item.get("continuation"):
            continuations += 1
        if item.get("status") == "INDEXED_PARTIAL":
            partials += 1
    return continuations, partials


def _compute_page_stats(summary: Dict[str, Any]) -> tuple[int, int, int, int, int, bool]:
    files_complete = 0
    files_partial = 0
    files_failed = 0
    pages_total = 0
    pages_read = 0
    has_unknown_pages = False
    for item in (summary.get("files") or summary.get("inventory") or []):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        if status in ("NOT_SELECTED_METADATA", "DUPLICATE_REUSED"):
            continue
        if status == "INDEXED":
            files_complete += 1
        elif status == "INDEXED_PARTIAL":
            files_partial += 1
        elif status in ("PARSE_FAILED", "QUARANTINED", "ERROR"):
            files_failed += 1
        p_tot = item.get("pages")
        p_read = item.get("read_pages")
        if isinstance(p_tot, int) and p_tot > 0:
            pages_total += p_tot
            if isinstance(p_read, int) and p_read >= 0:
                pages_read += min(p_read, p_tot)
            elif status == "INDEXED":
                pages_read += p_tot
        else:
            has_unknown_pages = True
    return files_complete, files_partial, files_failed, pages_total, pages_read, has_unknown_pages


def preindex_drive_library(
    settings: Any,
    *,
    max_rounds: int = 10,
    ocr_pages_per_batch: Optional[int] = None,
    reprocess_low_quality: Optional[bool] = None,
    library_factory: Callable[..., ReferenceLibrary] = ReferenceLibrary,
    **library_kwargs: Any,
) -> PreindexReport:
    """Run Drive reference indexing until all continuations converge or `max_rounds` is hit."""
    if not getattr(settings, "rag_drive_folder_id", ""):
        return PreindexReport(
            status="DISABLED",
            folder_id="",
            rounds_executed=0,
            converged=True,
        )

    bounded_rounds = max(1, int(max_rounds))
    env_overrides: Dict[str, Optional[str]] = {}
    if ocr_pages_per_batch is not None:
        env_overrides["LV_REFERENCE_OCR_MAX_PAGES"] = str(max(1, int(ocr_pages_per_batch)))

    last_summary: Dict[str, Any] = {}
    rounds = 0
    converged = False

    with _temp_env(env_overrides):
        for round_idx in range(1, bounded_rounds + 1):
            rounds = round_idx
            lib = library_factory(settings, **library_kwargs)
            if reprocess_low_quality is not None:
                last_summary = lib.sync(collect_all=True, reprocess_low_quality=reprocess_low_quality)
            else:
                last_summary = lib.sync(collect_all=True)
            continuations, partials = _has_pending_work(last_summary)
            if continuations == 0 and partials == 0:
                converged = True
                break
            if continuations == 0 and round_idx >= 2:
                # No active continuation cursor remains; further identical rounds will not advance.
                break

    files_complete, files_partial, files_failed, pages_total, pages_read, has_unknown_pages = _compute_page_stats(last_summary)
    continuations, _ = _has_pending_work(last_summary)
    files_total = files_complete + files_partial + files_failed
    converged = converged and files_partial == 0 and files_failed == 0 and continuations == 0
    if files_failed > 0 and files_complete == 0 and pages_total == 0:
        completion_rate: Optional[float] = 0.0
    elif has_unknown_pages:
        # At least one file (e.g., failed or unmeasured) has unknown page count; never report 100%.
        completion_rate = None
    elif pages_total > 0:
        completion_rate = round(pages_read / pages_total, 4)
    else:
        completion_rate = None

    return PreindexReport(
        status=str(last_summary.get("status") or "UNKNOWN"),
        folder_id=str(getattr(settings, "rag_drive_folder_id", "")),
        rounds_executed=rounds,
        converged=converged,
        files_total=files_total,
        files_complete=files_complete,
        files_partial=files_partial,
        files_failed=files_failed,
        pages_total=pages_total,
        pages_read=pages_read,
        page_completion_rate=completion_rate,
        remaining_continuations=continuations,
        coverage_ledger=dict(last_summary.get("coverage_ledger") or {}),
        issues=list(last_summary.get("issues") or []),
    )
