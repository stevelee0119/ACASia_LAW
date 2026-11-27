"""Incremental FTS5/BM25 cache; fresh Drive permissions gate every run's corpus."""
from __future__ import annotations

from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

from filelock import FileLock, Timeout

from packages.common.config import REPO_ROOT
from .drive import DriveClient, EXPORTS, FOLDER, ReferenceError, access_problem, revision, valid_id
from .extract import EXTRACTOR_VERSION

OCR_REPROCESS_VERSION = "tk245-fallback-env-v2"
IDENTIFIER_INDEX_VERSION = "v1"
DEFAULT_REFERENCE_REPROCESS_TIMEOUT_SECONDS = 120
_REPROCESS_RETRY_REASONS = (
    "reprocess_low_quality",
    "retryable_unread",
    "confirm_unreadable",
    "legacy_unread_reeval",
)
_BASE_ARTICLE_RE = re.compile(r"제[0-9]+조(?:의[0-9]+)?")
_NON_DIGIT_WS_RE = re.compile(
    r"(?<![0-9])[\u0009-\u000D\u001C-\u0020\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000\uFEFF]+"
    r"|[\u0009-\u000D\u001C-\u0020\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000\uFEFF]+(?![0-9])"
)
from . import relevance
from .relevance import tokens
from .case_table import lookup_records

SUPPORTED = {".pdf", ".docx", ".hwpx", ".hwp", ".xlsx", ".txt", ".md", ".csv"}

# 표준판례 표 후보 메타데이터 기준 (TK-74)
CASE_TABLE_EXTENSIONS = {".xlsx", ".csv"}
CASE_TABLE_MIMES = {
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
}
CASE_TABLE_MAX_BYTES = 96 * 1024 * 1024
# 이어 읽기(continuation) 중인 파일만 임시 보관하는 raw_cache 총량 상한:
# 단일 파일 상한(96 MiB) 기준 최대 2~3건 동시 이어 읽기를 수용하되 디스크 점유를 256 MiB 이하로 제한한다.
MAX_RAW_CACHE_BYTES = 256 * 1024 * 1024
_RETRYABLE_UNREAD_CAUSES = ("BUDGET_EXHAUSTED", "READ_TIMEOUT", "PARSE_FAILED")
_ALL_UNREAD_CAUSES = (
    "BUDGET_EXHAUSTED",
    "READ_TIMEOUT",
    "PARSE_FAILED",
    "OCR_UNAVAILABLE",
    "OCR_LOW_QUALITY",
    "CONTENT_NO_TEXT",
    "CONFIG_BLOCKED",
    "UNKNOWN",
)


def resolve_reprocess_timeout_seconds(environ: dict[str, str] | None = None) -> int:
    """Resolve dedicated timeout upper bound for Drive reprocess extractions (default 120s)."""
    env = os.environ if environ is None else environ
    raw = env.get("LV_REFERENCE_REPROCESS_TIMEOUT")
    if raw is None or not str(raw).strip():
        return DEFAULT_REFERENCE_REPROCESS_TIMEOUT_SECONDS
    try:
        val = int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return DEFAULT_REFERENCE_REPROCESS_TIMEOUT_SECONDS
    return max(1, min(600, val))


def resolve_inline_reprocess_enabled(environ: dict[str, str] | None = None) -> bool:
    """일반 검증 경로에서의 자동 저품질 OCR 재처리 허용 여부(기본 활성)."""
    env = os.environ if environ is None else environ
    raw = str(env.get("LV_RAG_INLINE_REPROCESS") or "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _extract_chunk_identifier_rows(file_id: str, version: str, chunk_rows: list[tuple]) -> list[tuple]:
    """청크 본문에서 사건번호·기본 조문 식별자를 추출해 색인 행으로 변환한다."""
    from .reference_binding import CASE_RE, authority_text

    out: list[tuple] = []
    for chunk_rowid, page, start, raw_text in chunk_rows:
        text_str = str(raw_text or "")
        if not text_str:
            continue
        norm = authority_text(text_str)
        spaced_digits = re.sub(r"[「」『』]", "", _NON_DIGIT_WS_RE.sub("", text_str))
        seen_keys: set[tuple[str, str]] = set()
        for m in CASE_RE.finditer(norm):
            seen_keys.add(("case", m.group(1)))
        for m in CASE_RE.finditer(spaced_digits):
            seen_keys.add(("case", m.group(1)))
        for m in _BASE_ARTICLE_RE.finditer(norm):
            seen_keys.add(("article", m.group(0)))
        for kind, key in seen_keys:
            out.append((kind, key, int(chunk_rowid), file_id, version, int(page), int(start)))
    return out


def _citation_lookup_key(ident: tuple | None) -> tuple[str, str] | None:
    """reference_binding.identifier() 결과를 chunk_identifiers 조회 키로 변환한다."""
    if not ident:
        return None
    if ident[0] == "case":
        return ("case", str(ident[1]))
    if ident[0] == "law":
        m = _BASE_ARTICLE_RE.match(str(ident[2] or ""))
        if m:
            return ("article", m.group(0))
    return None


def _prior_has_body(p: dict | None) -> bool:
    """Return True when cached payload holds extracted body chunks or searchable pages."""
    if not isinstance(p, dict):
        return False
    return int(p.get("chunk_count") or 0) > 0 or int(p.get("searchable_pages") or 0) > 0


def _accepts_kwarg(fn, name: str) -> bool:
    """Check whether callable accepts keyword argument `name` or `**kwargs`."""
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD or param.name == name:
            return True
    return False


def _low_quality_page_set(p: dict | None) -> set[int]:
    """Return union of ocr_low_quality_pages and unread_pages_by_cause['OCR_LOW_QUALITY'] page numbers."""
    if not isinstance(p, dict):
        return set()
    by_cause = p.get("unread_pages_by_cause")
    cause_pages = (by_cause.get("OCR_LOW_QUALITY") or []) if isinstance(by_cause, dict) else []
    raw_pages = p.get("ocr_low_quality_pages") or []
    return {int(pg) for pg in (*raw_pages, *cause_pages) if pg is not None}


def _has_any_unread_reason_fields(p: dict) -> bool:
    by_cause = p.get("unread_pages_by_cause") or {}
    if isinstance(by_cause, dict) and any(bool(v) for v in by_cause.values()):
        return True
    for key in (
        "unread_pages",
        "ocr_low_quality_pages",
        "confirmed_unreadable_pages",
        "config_blocked_pages",
        "no_text_pages",
        "error_pages",
        "scanned_pages",
        "unprocessed_pages",
    ):
        if p.get(key):
            return True
    return False


def _is_legacy_unread_without_reasons(p: dict) -> bool:
    if p.get("legacy_unread_reevaluated"):
        return False
    pages = int(p.get("pages") or 0)
    completed = p.get("completed_pages") if p.get("completed_pages") is not None else p.get("read_pages")
    if pages <= 0 or completed is None or int(completed) >= pages:
        return False
    return not _has_any_unread_reason_fields(p)


def _reconcile_unread_causes(parsed: dict) -> None:
    """Ensure unread causes account for the exact pages - completed_pages gap without fabricating pages."""
    pages = int(parsed.get("pages") or 0)
    if pages <= 0:
        return
    if parsed.get("completed_pages") is None and parsed.get("read_pages") is not None:
        parsed["completed_pages"] = int(parsed.get("read_pages") or 0)
    completed = int(parsed.get("completed_pages") or 0)
    gap = max(0, pages - completed)
    raw_by_cause = parsed.get("unread_pages_by_cause")
    by_cause: dict[str, list[int]] = {k: list((raw_by_cause or {}).get(k) or []) for k in _ALL_UNREAD_CAUSES}
    if isinstance(raw_by_cause, dict):
        for k, v in raw_by_cause.items():
            if k not in by_cause and isinstance(v, list):
                by_cause[k] = list(v)

    accounted_pages: set[int] = set()
    for plist in by_cause.values():
        for pg in plist:
            accounted_pages.add(int(pg))

    unknown_count = 0
    if gap > len(accounted_pages):
        needed = gap - len(accounted_pages)
        for pg in (parsed.get("config_blocked_pages") or []):
            if needed <= 0:
                break
            pg_int = int(pg)
            if pg_int not in accounted_pages:
                by_cause["CONFIG_BLOCKED"].append(pg_int)
                accounted_pages.add(pg_int)
                needed -= 1
        for pg in (parsed.get("blank_pages") or []):
            if needed <= 0:
                break
            pg_int = int(pg)
            if pg_int not in accounted_pages:
                by_cause["CONTENT_NO_TEXT"].append(pg_int)
                accounted_pages.add(pg_int)
                needed -= 1
        for pg in (parsed.get("ocr_low_quality_pages") or []):
            if needed <= 0:
                break
            pg_int = int(pg)
            if pg_int not in accounted_pages:
                by_cause["OCR_LOW_QUALITY"].append(pg_int)
                accounted_pages.add(pg_int)
                needed -= 1
        for pg in (parsed.get("error_pages") or []):
            if needed <= 0:
                break
            pg_int = int(pg)
            if pg_int not in accounted_pages:
                by_cause["PARSE_FAILED"].append(pg_int)
                accounted_pages.add(pg_int)
                needed -= 1
        for pg in (parsed.get("unprocessed_pages") or []):
            if needed <= 0:
                break
            pg_int = int(pg)
            if pg_int not in accounted_pages:
                cause = "BUDGET_EXHAUSTED" if parsed.get("continuation") else "PARSE_FAILED"
                by_cause[cause].append(pg_int)
                accounted_pages.add(pg_int)
                needed -= 1
        for pg in (parsed.get("no_text_pages") or []):
            if needed <= 0:
                break
            pg_int = int(pg)
            if pg_int not in accounted_pages:
                by_cause["CONTENT_NO_TEXT"].append(pg_int)
                accounted_pages.add(pg_int)
                needed -= 1

        if needed > 0:
            reason_upper = str(parsed.get("reason") or "").upper()
            if "TIMEOUT" in reason_upper:
                fallback_cause: Optional[str] = "READ_TIMEOUT"
            elif "BUDGET" in reason_upper or parsed.get("continuation"):
                fallback_cause = "BUDGET_EXHAUSTED"
            elif "OCR_LOW" in reason_upper:
                fallback_cause = "OCR_LOW_QUALITY"
            elif "OCR" in reason_upper:
                fallback_cause = "OCR_UNAVAILABLE"
            elif "BLANK" in reason_upper or "NO_TEXT" in reason_upper:
                fallback_cause = "CONTENT_NO_TEXT"
            elif "PARSE_FAILED" in reason_upper or "PARSE_ERROR" in reason_upper:
                fallback_cause = "PARSE_FAILED"
            else:
                fallback_cause = None

            if fallback_cause is not None:
                candidate_pages = [p for p in range(1, pages + 1) if p not in accounted_pages][:needed]
                for pg_int in candidate_pages:
                    by_cause[fallback_cause].append(pg_int)
                    accounted_pages.add(pg_int)
                    needed -= 1
            if needed > 0:
                # Legacy or unattributed gap: record UNKNOWN count without fabricating page numbers
                unknown_count = needed

    for k in list(by_cause.keys()):
        by_cause[k] = sorted({int(x) for x in by_cause[k]})
    parsed["unread_pages_by_cause"] = by_cause
    cause_counts = {k: len(v) for k, v in by_cause.items() if v}
    if unknown_count > 0:
        cause_counts["UNKNOWN"] = unknown_count
    parsed["unread_cause_counts"] = cause_counts
    if gap > 0 and not parsed.get("unread_pages") and accounted_pages:
        parsed["unread_pages"] = sorted(accounted_pages)



def is_case_table_candidate(item: dict) -> bool:
    """파일명이나 서면 본문과의 낱말 일치 여부와 무관하게 메타데이터로 판례 표 후보를 식별한다 (TK-74 한국어 주석)."""
    size = int(item.get("size") or 0)
    if size > CASE_TABLE_MAX_BYTES:
        return False
    name = str(item.get("name") or "")
    if name.endswith((".xlsx", ".csv", ".XLSX", ".CSV")):
        return True
    mime = str(item.get("mimeType") or "").lower()
    if mime in CASE_TABLE_MIMES:
        return True
    ext = relevance.extension(name).lower()
    return ext in CASE_TABLE_EXTENSIONS


EXTRACT_ENV_ALLOWLIST = frozenset({
    "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "PYTHONUTF8",
    "APPDATA", "USERPROFILE", "HOME",
    "LV_CASE_TABLE_MAX_EXCLUDED_ROWS",
    "LV_REFERENCE_OCR_MAX_PAGES",
    "LV_OCR_FALLBACK_ENGINE",
    "LV_OCR_FALLBACK_MODE",
    "LV_OCR_LANG",
    "LV_OCR_PSM",
    "LV_OCR_DPI",
    "LV_OCR_MIN_CONFIDENCE",
    "LV_OCR_QUALITY_MIN_CONFIDENCE",
    "LV_OCR_MIN_HANGUL_RATIO",
    "LV_OCR_TIMEOUT_SECONDS",
    "TESSDATA_PREFIX",
})


def build_isolated_extract_env(
    temporary_dir: Path | str,
    *,
    source_env: dict[str, str] | None = None,
    ocr_fallback_config: dict | None = None,
) -> dict[str, str]:
    """Build sanitized subprocess environment for isolated_extract using strict allowlist + shared OCR fallback config."""
    from packages.document_engine.ocr import resolve_ocr_fallback_config

    raw_env = os.environ if source_env is None else source_env
    env = {k: str(v) for k, v in raw_env.items() if k.upper() in EXTRACT_ENV_ALLOWLIST and v is not None}
    fb_cfg = ocr_fallback_config if isinstance(ocr_fallback_config, dict) else resolve_ocr_fallback_config(raw_env)
    env["LV_OCR_FALLBACK_ENGINE"] = str(fb_cfg.get("engine") or "none")
    env["LV_OCR_FALLBACK_MODE"] = str(fb_cfg.get("mode") or "off")
    env.update(
        LV_ALLOW_NETWORK="0",
        LV_OCR_MAX_PAGES="5",
        LV_INDEPENDENT_OCR="off",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        LV_DATA_DIR=str(Path(temporary_dir) / "data"),
        LV_STORAGE_ROOT=str(Path(temporary_dir) / "storage"),
    )
    return env


def isolated_extract(data, filename, mime, *, directory, timeout, continuation=None, ocr_fallback_config: dict | None = None):
    from apps.api.security import scan_upload

    # MIME and signature take precedence over cosmetic names such as "x.pdf copy".
    if data.lstrip().startswith(b"%PDF"):
        filename, mime = "reference.pdf", "application/pdf"
    else:
        filename = "reference" + relevance.extension(filename)
    if Path(filename).suffix not in SUPPORTED or scan_upload(filename, data):
        raise ReferenceError("UNSUPPORTED_OR_UNSAFE_REFERENCE")
    with tempfile.TemporaryDirectory(prefix="extract-", dir=directory) as temporary:
        path, output = Path(temporary) / filename, Path(temporary) / "result.json"
        path.write_bytes(data)
        arguments = [sys.executable, "-m", "packages.rag_engine.extract", str(path), str(output), filename, mime]
        if continuation:
            checkpoint = Path(temporary) / "continuation.json"
            checkpoint.write_text(json.dumps(continuation, ensure_ascii=False), encoding="utf-8")
            arguments.append(str(checkpoint))
        env = build_isolated_extract_env(temporary, ocr_fallback_config=ocr_fallback_config)
        try:
            subprocess.run(arguments, cwd=REPO_ROOT, env=env, timeout=timeout,
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            raise ReferenceError("REFERENCE_PARSE_TIMEOUT") from None
        except subprocess.CalledProcessError:
            raise ReferenceError("REFERENCE_PARSE_FAILED") from None
        if not output.exists():
            raise ReferenceError("REFERENCE_TEXT_LIMIT")
        # Structured tables carry row provenance alongside text.  Their bound
        # is explicit and independent from the ordinary 16 MB extraction cap;
        # a malformed/unbounded workbook still fails closed.
        payload_size = output.stat().st_size
        if payload_size > 64_000_000:
            raise ReferenceError("REFERENCE_TEXT_LIMIT")
        payload = json.loads(output.read_text(encoding="utf-8"))
        if payload_size > 16_000_000 and not payload.get("structured_case_table"):
            raise ReferenceError("REFERENCE_TEXT_LIMIT")
        return payload


def stale_quarantine(parsed):
    return parsed.get("reason") == "REFERENCE_QUARANTINED" and "scan_findings" not in parsed


class ReferenceLibrary:
    def __init__(self, settings, *, check=lambda: None, notify=lambda done, total: None,
                 client_factory=DriveClient, extractor=isolated_extract):
        self.settings, self.check = settings, check
        self.notify = notify
        self.client_factory, self.extractor = client_factory, extractor
        self._default_collect_all: bool | None = None
        self._case_rows_cache: list[dict] | None = None
        self._case_number_index: dict[str, list[dict]] = {}
        self.folder = settings.rag_drive_folder_id
        folder_key = hashlib.sha256(self.folder.encode()).hexdigest()
        self.directory = Path(settings.storage_root) / "reference-cache" / folder_key
        self.db_path = self.directory / "index.sqlite3"
        self.eligible = {}
        self.summary = {"status": "DISABLED", "folder_id": self.folder, "checked_at": None,
                        "snapshot_hash": None, "files_seen": 0, "files_indexed": 0,
                        "files_reused": 0, "issues": [], "sources": [], "duplicates": [], "similar_names": [],
                        "diagnostics": {}, "inventory": [],
                        "retrieval": "SQLite FTS5; Korean character bigrams; corpus-IDF relevance gate "
                                     "with folder/file-name bonus; structured case rows use exact lookup and claim-level holding-first search",
                        "authority": "USER_REFERENCE_NOT_OFFICIAL", "extractor": EXTRACTOR_VERSION}

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=2)
        page_size = db.execute("PRAGMA page_size").fetchone()[0]
        db.execute(f"PRAGMA max_page_count={512 * 1024 * 1024 // page_size}")
        db.execute("CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, revision TEXT, payload TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS dataset_state (key TEXT PRIMARY KEY, value TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS chunk_embeddings ("
                   "file_id TEXT, revision TEXT, page INTEGER, start INTEGER, model TEXT, vector_json TEXT, "
                   "PRIMARY KEY (file_id, revision, page, start, model))")
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5("
                   "file_id UNINDEXED, revision UNINDEXED, page UNINDEXED, start UNINDEXED, text UNINDEXED, terms)")
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunk_terms USING fts5vocab(chunks, 'row')")
        db.execute("""CREATE TABLE IF NOT EXISTS chunk_identifiers (
            ident_kind TEXT NOT NULL,
            ident_key TEXT NOT NULL,
            chunk_rowid INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            revision TEXT NOT NULL,
            page INTEGER NOT NULL,
            start INTEGER NOT NULL
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_chunk_identifiers_lookup "
                   "ON chunk_identifiers (ident_kind, ident_key, file_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_chunk_identifiers_file "
                   "ON chunk_identifiers (file_id)")
        db.execute("""CREATE TABLE IF NOT EXISTS case_rows (
            record_id TEXT PRIMARY KEY, file_id TEXT NOT NULL, revision TEXT NOT NULL,
            sheet TEXT, row_number INTEGER, source_cell_range TEXT,
            original_number TEXT, title TEXT, case_info TEXT, court TEXT,
            decision_date TEXT, case_numbers TEXT, target_case_numbers TEXT, referenced_case_numbers TEXT,
            issue TEXT, facts TEXT,
            reason TEXT, holding TEXT, hyperlinks TEXT, quality_warnings TEXT,
            case_head TEXT, indexed_text TEXT, raw_cells TEXT
        )""")
        columns = {row[1] for row in db.execute("PRAGMA table_info(case_rows)")}
        for missing in ("target_case_numbers", "referenced_case_numbers", "raw_cells"):
            if missing not in columns:
                db.execute(f"ALTER TABLE case_rows ADD COLUMN {missing} TEXT")
        try:
            yield db
        finally:
            db.close()

    def _load_dataset_snapshot(self, db) -> dict | None:
        row = db.execute("SELECT value FROM dataset_state WHERE key='inventory_snapshot'").fetchone()
        if not row or not row[0]:
            return None
        try:
            snap = json.loads(row[0])
        except (TypeError, ValueError):
            return None
        if not isinstance(snap, dict) or snap.get("folder_id") != self.folder:
            return None
        return snap

    def _save_dataset_snapshot(
        self,
        db,
        *,
        items: list[dict],
        folders: dict[str, str],
        start_page_token: str | None,
        snapshot_hash: str | None,
        inventory_mode: str,
    ) -> None:
        payload = {
            "folder_id": self.folder,
            "items": items,
            "folders": folders,
            "start_page_token": start_page_token or "",
            "snapshot_hash": snapshot_hash or "",
            "inventory_mode": inventory_mode,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with db:
            db.execute(
                "INSERT OR REPLACE INTO dataset_state (key, value) VALUES (?, ?)",
                ("inventory_snapshot", json.dumps(payload, ensure_ascii=False)),
            )

    @staticmethod
    def _compute_dataset_diff(prev_items: list[dict], cur_items: list[dict]) -> dict:
        prev_map = {it["id"]: it for it in (prev_items or []) if isinstance(it, dict) and it.get("id")}
        cur_map = {it["id"]: it for it in (cur_items or []) if isinstance(it, dict) and it.get("id")}
        added = sorted(fid for fid in cur_map if fid not in prev_map)
        deleted = sorted(fid for fid in prev_map if fid not in cur_map)
        modified: list[str] = []
        unchanged = 0
        for fid, cur in cur_map.items():
            prev = prev_map.get(fid)
            if prev is None:
                continue
            same_rev = (
                prev.get("modifiedTime") == cur.get("modifiedTime")
                and prev.get("version") == cur.get("version")
                and prev.get("md5Checksum") == cur.get("md5Checksum")
                and prev.get("name") == cur.get("name")
                and prev.get("trashed") == cur.get("trashed")
                and prev.get("capabilities") == cur.get("capabilities")
                and prev.get("folder_path") == cur.get("folder_path")
            )
            if same_rev:
                unchanged += 1
            else:
                modified.append(fid)
        return {
            "added": len(added),
            "modified": len(modified),
            "deleted": len(deleted),
            "unchanged": unchanged,
            "dataset_up_to_date": (len(added) == 0 and len(modified) == 0 and len(deleted) == 0),
        }

    def _resolve_inventory(self, client, db) -> tuple[list[dict], dict[str, str], str, str | None, dict]:
        """Drive 변경 감지(Changes API) 또는 묶음 폴더 조회로 최신 파일 목록을 확보한다.

        권한 회수·휴지통·목록 실패 시에는 Fail-Closed 원칙에 따라 예외를 발생시킨다.
        """
        snapshot = self._load_dataset_snapshot(db)
        prev_items = list((snapshot or {}).get("items") or [])
        prev_folders = dict((snapshot or {}).get("folders") or {})
        prev_token = str((snapshot or {}).get("start_page_token") or "").strip()
        credential_mode = getattr(client, "credential_mode", "injected")

        # 1) Changes API 기반 증분 동기화 (OAuth / 서비스 계정 / 테스트 더블)
        if (
            snapshot is not None
            and prev_token
            and credential_mode != "api_key"
            and hasattr(client, "list_changes")
        ):
            root = client.metadata(self.folder)
            if root.get("mimeType") != FOLDER or root.get("trashed"):
                raise ReferenceError("ROOT_FOLDER_UNAVAILABLE")
            try:
                changes, new_token, overflowed = client.list_changes(prev_token)
                if not overflowed:
                    if not changes:
                        if hasattr(client, "folders"):
                            client.folders = dict(prev_folders)
                        diff = self._compute_dataset_diff(prev_items, prev_items)
                        return prev_items, prev_folders, "CHANGES_UNCHANGED", (new_token or prev_token), diff

                    folder_ids = set(prev_folders.keys())
                    by_id = {it["id"]: dict(it) for it in prev_items if isinstance(it, dict) and it.get("id")}
                    needs_full_scan = False
                    for ch in changes:
                        fid = str(ch.get("fileId") or (ch.get("file") or {}).get("id") or "")
                        if not fid:
                            continue
                        f_obj = ch.get("file")
                        if fid in folder_ids or (isinstance(f_obj, dict) and f_obj.get("mimeType") == FOLDER):
                            needs_full_scan = True
                            break
                        removed = bool(ch.get("removed"))
                        if removed or not isinstance(f_obj, dict) or f_obj.get("trashed"):
                            by_id.pop(fid, None)
                            continue
                        parents = f_obj.get("parents") or []
                        matched_parent = next((p for p in parents if p in folder_ids), None)
                        if matched_parent is None:
                            if fid in by_id and not parents:
                                matched_parent = by_id[fid].get("listed_parent")
                            elif fid in by_id and parents:
                                by_id.pop(fid, None)
                                continue
                            else:
                                # 외부 폴더 파일의 변경은 무시한다.
                                continue
                        updated = dict(f_obj)
                        updated["folder_path"] = prev_folders.get(matched_parent, "")
                        updated["listed_parent"] = matched_parent
                        by_id[fid] = updated
                    if not needs_full_scan:
                        cur_items = list(by_id.values())
                        if len(cur_items) <= self.settings.rag_inventory_max_files:
                            if hasattr(client, "folders"):
                                client.folders = dict(prev_folders)
                            diff = self._compute_dataset_diff(prev_items, cur_items)
                            return cur_items, prev_folders, "CHANGES_DELTA_APPLIED", (new_token or prev_token), diff
            except ReferenceError as exc:
                if str(exc) not in ("DRIVE_HTTP_400", "DRIVE_HTTP_401", "DRIVE_HTTP_403", "DRIVE_HTTP_404", "INVALID_CHANGE_TOKEN"):
                    raise

        # 2) 다중 폴더 묶음 조회(API Key 포함 모든 모드) 또는 표준 순회
        if len(prev_folders) > 1 and hasattr(client, "batched_inventory"):
            items = client.batched_inventory(
                self.folder,
                prev_folders,
                max_files=self.settings.rag_inventory_max_files,
            )
            inventory_mode = "BATCHED_INVENTORY"
        else:
            items = client.inventory(self.folder, max_files=self.settings.rag_inventory_max_files)
            inventory_mode = "FULL_INVENTORY"
        folders = dict(getattr(client, "folders", {}) or {})
        next_token: str | None = None
        if credential_mode != "api_key" and hasattr(client, "get_start_page_token"):
            try:
                next_token = client.get_start_page_token()
            except ReferenceError as exc:
                if str(exc) == "SYNC_BUDGET_EXHAUSTED":
                    raise
                next_token = None
        diff = (
            self._compute_dataset_diff(prev_items, items)
            if snapshot is not None
            else {"added": len(items), "modified": 0, "deleted": 0, "unchanged": 0, "dataset_up_to_date": False}
        )
        return items, folders, inventory_mode, next_token, diff

    def dataset_status(self) -> dict:
        """현재 로컬 참조자료 데이터셋(index.sqlite3)의 최신화·색인 상태를 반환한다."""
        configured = bool(self.folder)
        base = {
            "configured": configured,
            "initialized": False,
            "updated_at": None,
            "snapshot_hash": None,
            "inventory_mode": None,
            "has_change_token": False,
            "files_cached": 0,
            "files_indexed": 0,
            "chunks_cached": 0,
            "case_rows_cached": 0,
            "identifiers_cached": 0,
            "searchable_pages": 0,
            "pending_continuations": 0,
            "pending_low_quality_reprocess": 0,
            "failed_updates": 0,
            "inline_reprocess_enabled": resolve_inline_reprocess_enabled(),
        }
        if not configured or not self.db_path.is_file():
            return base
        with self.connect() as db:
            snap = self._load_dataset_snapshot(db)
            files_rows = db.execute("SELECT payload FROM files").fetchall()
            chunks_cached = int((db.execute("SELECT COUNT(*) FROM chunks").fetchone() or [0])[0])
            case_rows_cached = int((db.execute("SELECT COUNT(*) FROM case_rows").fetchone() or [0])[0])
            identifiers_cached = int((db.execute("SELECT COUNT(*) FROM chunk_identifiers").fetchone() or [0])[0])
        searchable_pages = 0
        pending_continuations = 0
        pending_low_quality = 0
        failed_updates = 0
        files_indexed = 0
        for (raw_payload,) in files_rows:
            try:
                p = json.loads(raw_payload or "{}")
            except (TypeError, ValueError):
                continue
            if int(p.get("chunk_count") or 0) > 0 or p.get("structured_case_table"):
                files_indexed += 1
            searchable_pages += int(p.get("searchable_pages") or 0)
            if p.get("continuation"):
                pending_continuations += 1
            if _low_quality_page_set(p) and p.get("low_quality_reprocess_version") != OCR_REPROCESS_VERSION:
                pending_low_quality += 1
            if p.get("modified_update_failed"):
                failed_updates += 1
        base.update({
            "initialized": bool(snap is not None or len(files_rows) > 0),
            "updated_at": (snap or {}).get("updated_at"),
            "snapshot_hash": (snap or {}).get("snapshot_hash"),
            "inventory_mode": (snap or {}).get("inventory_mode"),
            "has_change_token": bool((snap or {}).get("start_page_token")),
            "files_cached": len(files_rows),
            "files_indexed": files_indexed,
            "chunks_cached": chunks_cached,
            "case_rows_cached": case_rows_cached,
            "identifiers_cached": identifiers_cached,
            "searchable_pages": searchable_pages,
            "pending_continuations": pending_continuations,
            "pending_low_quality_reprocess": pending_low_quality,
            "failed_updates": failed_updates,
        })
        return base

    def sync(self, query="", *, collect_all: bool | None = None, reprocess_low_quality: Optional[bool] = None):
        from packages.document_engine.ocr import resolve_ocr_fallback_config

        started = time.monotonic()
        self.eligible = {}
        self._case_rows_cache = None
        self._case_number_index = {}
        self._run_ocr_fallback_config = resolve_ocr_fallback_config()
        inline_reprocess = resolve_inline_reprocess_enabled()
        self._run_auto_reprocess = bool(
            reprocess_low_quality
            if reprocess_low_quality is not None
            else (self._run_ocr_fallback_config["enabled"] and inline_reprocess)
        )
        self.summary.update(checked_at=None, snapshot_hash=None, files_seen=0, files_indexed=0,
                            files_reused=0, issues=[], sources=[], duplicates=[], similar_names=[], inventory=[])
        self.summary.pop("coverage_ledger", None)
        self.summary.pop("ocr_reprocess", None)
        self.summary.pop("ocr_fallback_attempted_pages", None)
        self.summary.pop("ocr_fallback_adopted_pages", None)
        self.summary.pop("reprocess_failed", None)
        self.summary.pop("reprocess_deferred", None)
        self.summary.pop("restored_files", None)
        self.summary.pop("restore_failed", None)
        self.summary.pop("dataset", None)
        # 분석 문서마다 따로 받은 질의(목록)나 하나로 합친 질의(문자열) 모두 받는다.
        raw_queries = [q for q in (query if isinstance(query, (list, tuple)) else [query]) if q]
        eff_collect_all = self._default_collect_all if collect_all is None else collect_all
        decoupled = bool(eff_collect_all) if eff_collect_all is not None else (not bool(self.settings.rag_metadata_first))
        self.sync_query = "\n".join(raw_queries) if (raw_queries and (not decoupled or eff_collect_all)) else ""
        queries = raw_queries if (raw_queries and not decoupled) else []
        budget = max(1, min(600, self.settings.rag_sync_seconds))
        reprocess_timeout_cap = resolve_reprocess_timeout_seconds()
        collection_mode = "DECOUPLED_FULL_CORPUS" if decoupled else ("METADATA_GATE" if queries else "FULL_CORPUS")
        selection_strategy = "METADATA_GATE" if queries else ("FULL_CORPUS_INDEX" if raw_queries else "CACHE_SIZE_ORDER")
        diagnostics = self.summary["diagnostics"] = {
            "started_at": datetime.now(timezone.utc).isoformat(), "folder_id": self.folder,
            "network_allowed": bool(self.settings.allow_network), "budget_seconds": budget,
            "reprocess_timeout_seconds": reprocess_timeout_cap,
            "max_files": self.settings.rag_max_files, "inventory_max_files": self.settings.rag_inventory_max_files,
            "selection_strategy": selection_strategy,
            "collection_mode": collection_mode,
            "download_budget_mb": self.settings.rag_download_mb,
            "credential_mode": None, "stages": [], "downloads": {"count": 0, "bytes": 0},
            "extractions": {"count": 0, "ms": 0}, "duplicates_skipped": 0, "deferred": 0,
            "reprocess_failed": 0, "reprocess_deferred": 0, "restored_files": 0, "restore_failed": 0}
        if not self.folder:
            return self.summary
        self.summary["status"] = "UNAVAILABLE"
        if not self.settings.allow_network:
            self.summary["issues"] = [{"reason": "NETWORK_DISABLED"}]
            return self._finish(started, None)
        deadline = time.monotonic() + budget
        client = self.client_factory(deadline=deadline, check=self.check)
        diagnostics["credential_mode"] = getattr(client, "credential_mode", "injected")
        try:
            valid_id(self.folder)
            self.directory.mkdir(parents=True, exist_ok=True)
            with FileLock(str(self.db_path) + ".lock", timeout=min(3, client.remaining())):
                mark = time.monotonic()
                with self.connect() as db:
                    items, folders, inventory_mode, next_change_token, dataset_diff = self._resolve_inventory(client, db)
                self._stage("inventory", mark, files=len(items), mode=inventory_mode)
                diagnostics["inventory_mode"] = inventory_mode
                diagnostics["dataset_diff"] = dataset_diff
                self.summary["checked_at"] = datetime.now(timezone.utc).isoformat()
                self.summary["files_seen"] = len(items)
                # inventory 항목에 mimeType을 보존하여 확장자가 없는 Google Sheets 등 표 후보 식별이 누락되지 않도록 한다 (TK-74)
                self.summary["inventory"] = [{"file_id": item["id"], "name": item.get("name", ""),
                    "mimeType": item.get("mimeType", ""),
                    "folder_path": item.get("folder_path", ""), "size": int(item.get("size") or 0),
                    "metadata": relevance.metadata_priority(item, self.sync_query),
                    "status": "SELECTED_PENDING", "reason": "NOT_PROCESSED", "background_queued": False}
                    for item in items]
                diagnostics["folders_seen"] = len(folders)
                diagnostics["folder_paths"] = sorted(p for p in folders.values() if p)[:200]
                extensions = {}
                for item in items:
                    mime = item.get("mimeType", "")
                    key = mime if mime.startswith("application/vnd.google-apps") else (
                        relevance.extension(item.get("name")) or "(none)")
                    extensions[key] = extensions.get(key, 0) + 1
                diagnostics["files_by_type"] = extensions
                duplicates, similar, skip = relevance.duplicate_groups(items)
                self.summary["duplicates"], self.summary["similar_names"] = duplicates, similar
                # collect_all=False/레거시 METADATA_GATE 모드에서만 열기 전 선정을 쓰고, 분리 수집 모드에서는 전량 수집한다.
                gate = None
                if queries:
                    try:
                        gate = self._metadata_gate(client, items, queries, folders)
                    except ReferenceError:
                        raise
                    except Exception as exc:  # 선정 단계의 결함이 Drive 검토 전체를 멈추게 하지 않는다
                        diagnostics["metadata_gate"] = {"error": type(exc).__name__, "fallback": "ALL_FILES_BY_PRIORITY"}
                if gate:
                    for entry in self.summary["inventory"]:
                        entry["gate"] = gate[entry["file_id"]]
                mark = time.monotonic()
                with self.connect() as db:
                    self._sync_files(client, db, items, skip, gate, reprocess_low_quality=reprocess_low_quality)
                    snap_hash = hashlib.sha256(json.dumps(
                        sorted((k, v["revision"], v["sha256"]) for k, v in self.eligible.items())).encode()).hexdigest()
                    self._save_dataset_snapshot(
                        db,
                        items=items,
                        folders=folders,
                        start_page_token=next_change_token,
                        snapshot_hash=snap_hash,
                        inventory_mode=inventory_mode,
                    )
                self._stage("files", mark, indexed=len(self.eligible))
                self.summary["sources"] = list(self.eligible.values())
                self.summary["files_indexed"] = len(self.eligible)
                self.summary["snapshot_hash"] = snap_hash
                self.summary["dataset"] = {
                    "inventory_mode": inventory_mode,
                    **dataset_diff,
                    "has_change_token": bool(next_change_token),
                }
                self.summary["status"] = "PARTIAL" if self.summary["issues"] else "READY"
        except Exception as exc:
            # No offline fallback: previous cached references are ineligible on listing/auth failure.
            self.eligible = {}
            self.summary["issues"].append({"reason": str(exc) if isinstance(exc, ReferenceError)
                                            else "CACHE_BUSY" if isinstance(exc, Timeout) else "SYNC_FAILED"})
        finally:
            client.close()
        return self._finish(started, client)

    def _stage(self, name, mark, **values):
        self.summary["diagnostics"]["stages"].append(
            {"stage": name, "ms": round((time.monotonic() - mark) * 1000), **values})

    def _finish(self, started, client):
        from packages.document_engine.ocr import resolve_ocr_fallback_config

        diagnostics = self.summary["diagnostics"]
        status_info = self.case_table_status()
        diagnostics["case_table_candidates"] = status_info["candidates"]
        self.summary["case_table_status"] = status_info["status"]
        if status_info["status"] != "NO_CASE_TABLE":
            diagnostics["case_table_status"] = status_info["status"]
        diagnostics["finished_at"] = datetime.now(timezone.utc).isoformat()
        diagnostics["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        diagnostics["outcome"] = self.summary["status"]
        counts = {}
        pages_total = 0
        extracted_text_pages = 0
        completed_pages = 0
        searchable_pages = 0
        searchable_pages_delta = 0
        ocr_fallback_attempted_pages = 0
        ocr_fallback_adopted_pages = 0
        low_quality_pages_before = 0
        low_quality_pages_after = 0
        reprocessed_pages = 0
        recovered_pages = 0
        reprocessed_files = 0
        reprocess_failed_files = 0
        reprocess_deferred_files = 0
        restored_files = 0
        restore_failed_files = 0
        fresh_child_ocr_configs: list[dict] = []
        cached_child_ocr_configs: list[dict] = []
        page_states: dict[str, int] = {}
        files_complete = 0
        files_partial = 0
        files_failed = 0
        files_not_selected = 0
        unread_cause_pages: dict[str, int] = {
            "BUDGET_EXHAUSTED": 0,
            "READ_TIMEOUT": 0,
            "PARSE_FAILED": 0,
            "OCR_UNAVAILABLE": 0,
            "OCR_LOW_QUALITY": 0,
            "CONTENT_NO_TEXT": 0,
            "CONFIG_BLOCKED": 0,
            "UNKNOWN": 0,
        }
        unread_cause_files: dict[str, int] = {
            "BUDGET_EXHAUSTED": 0,
            "READ_TIMEOUT": 0,
            "PARSE_FAILED": 0,
            "OCR_UNAVAILABLE": 0,
            "OCR_LOW_QUALITY": 0,
            "CONTENT_NO_TEXT": 0,
            "CONFIG_BLOCKED": 0,
            "UNKNOWN": 0,
        }
        confirmed_unreadable_files = 0
        confirmed_unreadable_pages = 0
        confirmed_unreadable_by_cause: dict[str, int] = {}
        for item in self.summary["inventory"]:
            if item["reason"] == "NOT_PROCESSED":
                item["reason"] = "SYNC_INTERRUPTED"
            st = item.get("status") or ""
            if st == "INDEXED":
                files_complete += 1
            elif st == "INDEXED_PARTIAL":
                files_partial += 1
            elif st == "NOT_SELECTED_METADATA":
                files_not_selected += 1
            elif st in ("PARSE_FAILED", "UNAVAILABLE", "UNSUPPORTED_TYPE", "QUARANTINED"):
                files_failed += 1
            pages_total += int(item.get("pages") or 0)
            extracted_text_pages += int(
                item.get("extracted_text_pages")
                if item.get("extracted_text_pages") is not None
                else (item.get("read_pages") or 0)
            )
            completed_pages += int(
                item.get("completed_pages")
                if item.get("completed_pages") is not None
                else (item.get("read_pages") or 0)
            )
            searchable_pages += int(
                item.get("searchable_pages")
                if item.get("searchable_pages") is not None
                else (
                    item.get("extracted_text_pages")
                    if item.get("extracted_text_pages") is not None
                    else (item.get("read_pages") or 0)
                )
            )
            if item.get("searchable_pages_delta") is not None:
                searchable_pages_delta += int(item.get("searchable_pages_delta") or 0)
            if item.get("reprocessed_in_run"):
                reprocessed_files += 1
            if item.get("reprocess_failed"):
                reprocess_failed_files += 1
            if item.get("reprocess_deferred"):
                reprocess_deferred_files += 1
            if item.get("restored_in_run"):
                restored_files += 1
            if item.get("restore_failed"):
                restore_failed_files += 1
            child_cfg = item.get("child_ocr_config")
            if isinstance(child_cfg, dict):
                if item.get("reused") or item.get("reprocess_failed"):
                    cached_child_ocr_configs.append(child_cfg)
                else:
                    fresh_child_ocr_configs.append(child_cfg)
            if item.get("low_quality_pages_before") is not None:
                low_quality_pages_before += int(item.get("low_quality_pages_before") or 0)
                low_quality_pages_after += int(item.get("low_quality_pages_after") or 0)
                reprocessed_pages += int(item.get("reprocessed_pages") or 0)
                if not item.get("reprocess_failed"):
                    recovered_pages += int(item.get("recovered_pages") or 0)
            fb_sum = item.get("ocr_fallback_summary")
            if isinstance(fb_sum, dict):
                ocr_fallback_attempted_pages += len(fb_sum.get("attempted_pages") or [])
                ocr_fallback_adopted_pages += len(fb_sum.get("adopted_pages") or [])
            for k, v in (item.get("page_state_counts") or {}).items():
                page_states[k] = page_states.get(k, 0) + int(v or 0)
            by_cause = item.get("unread_pages_by_cause") or {}
            cause_counts = item.get("unread_cause_counts") or {}
            if by_cause or cause_counts:
                seen_causes: set[str] = set()
                for cause_key, plist in by_cause.items():
                    if plist:
                        unread_cause_pages[cause_key] = unread_cause_pages.get(cause_key, 0) + len(plist)
                        unread_cause_files[cause_key] = unread_cause_files.get(cause_key, 0) + 1
                        seen_causes.add(cause_key)
                for cause_key, cnt in cause_counts.items():
                    if cnt and cause_key not in seen_causes:
                        unread_cause_pages[cause_key] = unread_cause_pages.get(cause_key, 0) + int(cnt)
                        unread_cause_files[cause_key] = unread_cause_files.get(cause_key, 0) + 1
            elif item.get("unread_cause"):
                c = item["unread_cause"]
                unread_cause_files[c] = unread_cause_files.get(c, 0) + 1
            item_unreadable = item.get("confirmed_unreadable_pages") or []
            if item_unreadable and item.get("unreadable_confirmed"):
                confirmed_unreadable_files += 1
                confirmed_unreadable_pages += len(item_unreadable)
                for ck, cv in (item.get("confirmed_unreadable_causes") or {}).items():
                    if cv:
                        confirmed_unreadable_by_cause[ck] = confirmed_unreadable_by_cause.get(ck, 0) + int(cv)
        self.summary["unreadable_summary"] = {
            "files": confirmed_unreadable_files,
            "pages": confirmed_unreadable_pages,
            "by_cause": confirmed_unreadable_by_cause,
        }
        if self.summary["status"] == "READY":
            self.summary["read_completeness"] = (
                "READY_WITH_UNREADABLE" if confirmed_unreadable_pages > 0 else "FULL"
            )
        else:
            self.summary["read_completeness"] = self.summary["status"]

        parent_fb_cfg = getattr(self, "_run_ocr_fallback_config", None) or resolve_ocr_fallback_config()
        auto_reprocess_on = bool(getattr(self, "_run_auto_reprocess", parent_fb_cfg["enabled"]))
        reprocess_timeout_cap = int(diagnostics.get("reprocess_timeout_seconds") or resolve_reprocess_timeout_seconds())
        diagnostics["reprocess_failed"] = reprocess_failed_files
        diagnostics["reprocess_deferred"] = reprocess_deferred_files
        diagnostics["restored_files"] = restored_files
        diagnostics["restore_failed"] = restore_failed_files
        observed_child_cfg = (
            fresh_child_ocr_configs[-1]
            if fresh_child_ocr_configs
            else (cached_child_ocr_configs[-1] if cached_child_ocr_configs else None)
        )
        zero_fallback_attempt_reason: str | None = None
        if auto_reprocess_on and ocr_fallback_attempted_pages == 0:
            extractions_run = int((diagnostics.get("extractions") or {}).get("count") or 0)
            if extractions_run == 0:
                zero_fallback_attempt_reason = (
                    "REPROCESS_DEFERRED_SYNC_BUDGET"
                    if reprocess_deferred_files > 0
                    else "NO_FILES_EXTRACTED_ALL_REUSED"
                )
            elif reprocess_failed_files > 0 and not fresh_child_ocr_configs:
                zero_fallback_attempt_reason = "REPROCESS_EXTRACTION_FAILED_OR_TIMEOUT"
            elif restored_files > 0 and fresh_child_ocr_configs and all(not c.get("fallback_enabled") for c in fresh_child_ocr_configs):
                zero_fallback_attempt_reason = "RESTORE_PRIMARY_OCR_ONLY_FALLBACK_NEXT_RUN"
            elif any(not c.get("fallback_enabled") for c in fresh_child_ocr_configs):
                zero_fallback_attempt_reason = "CHILD_FALLBACK_CONFIG_DISABLED"
            elif any(c.get("fallback_enabled") and not c.get("fallback_adapter") for c in fresh_child_ocr_configs):
                zero_fallback_attempt_reason = "CHILD_FALLBACK_ADAPTER_UNAVAILABLE"
            elif any(
                "PRIMARY_QUALITY_SUFFICIENT" in ((it.get("ocr_fallback_summary") or {}).get("reason_counts") or {})
                for it in self.summary["inventory"]
                if not it.get("reused")
            ):
                zero_fallback_attempt_reason = "PRIMARY_OCR_QUALITY_SUFFICIENT"
            elif any(it.get("config_blocked_pages") for it in self.summary["inventory"] if not it.get("reused")):
                zero_fallback_attempt_reason = "OCR_CONFIG_BLOCKED"
            elif not fresh_child_ocr_configs:
                zero_fallback_attempt_reason = "NO_CHILD_OCR_TELEMETRY"
            else:
                zero_fallback_attempt_reason = "NO_LOW_QUALITY_SCANNED_PAGES_IN_EXTRACTED_FILES"

        self.summary["ocr_fallback_attempted_pages"] = ocr_fallback_attempted_pages
        self.summary["ocr_fallback_adopted_pages"] = ocr_fallback_adopted_pages
        self.summary["reprocess_failed"] = reprocess_failed_files
        self.summary["reprocess_deferred"] = reprocess_deferred_files
        self.summary["restored_files"] = restored_files
        self.summary["restore_failed"] = restore_failed_files
        self.summary["ocr_reprocess"] = {
            "reprocess_version": OCR_REPROCESS_VERSION,
            "auto_reprocess_enabled": auto_reprocess_on,
            "reprocess_timeout_seconds": reprocess_timeout_cap,
            "parent_ocr_config": {
                "fallback_engine": parent_fb_cfg["engine"],
                "fallback_mode": parent_fb_cfg["mode"],
                "fallback_enabled": bool(parent_fb_cfg["enabled"]),
            },
            "child_ocr_config": observed_child_cfg,
            "reprocessed_files": reprocessed_files,
            "reprocessed_pages": reprocessed_pages,
            "reprocess_failed": reprocess_failed_files,
            "reprocess_deferred": reprocess_deferred_files,
            "restored_files": restored_files,
            "restore_failed": restore_failed_files,
            "low_quality_pages_before": low_quality_pages_before,
            "low_quality_pages_after": low_quality_pages_after,
            "recovered_pages": recovered_pages,
            "ocr_fallback_attempted_pages": ocr_fallback_attempted_pages,
            "ocr_fallback_adopted_pages": ocr_fallback_adopted_pages,
            "zero_fallback_attempt_reason": zero_fallback_attempt_reason,
        }
        self.summary["coverage_ledger"] = {
            "collection_mode": diagnostics.get("collection_mode"),
            "global_library": {
                "files_seen": self.summary.get("files_seen", 0),
                "files_indexed": self.summary.get("files_indexed", 0),
                "files_reused": self.summary.get("files_reused", 0),
                "files_complete": files_complete,
                "files_partial": files_partial,
                "files_failed_or_unavailable": files_failed,
                "files_not_selected_metadata": files_not_selected,
                "pages_total": pages_total,
                "extracted_text_pages": extracted_text_pages,
                "searchable_pages": searchable_pages,
                "searchable_pages_delta": searchable_pages_delta,
                "ocr_fallback_attempted_pages": ocr_fallback_attempted_pages,
                "ocr_fallback_adopted_pages": ocr_fallback_adopted_pages,
                "low_quality_pages_before": low_quality_pages_before,
                "low_quality_pages_after": low_quality_pages_after,
                "reprocessed_files": reprocessed_files,
                "reprocessed_pages": reprocessed_pages,
                "reprocess_failed": reprocess_failed_files,
                "reprocess_deferred": reprocess_deferred_files,
                "restored_files": restored_files,
                "restore_failed": restore_failed_files,
                "recovered_pages": recovered_pages,
                "child_ocr_config": observed_child_cfg,
                "zero_fallback_attempt_reason": zero_fallback_attempt_reason,
                "completed_pages": completed_pages,
                "page_states": page_states,
                "unread_cause_pages": unread_cause_pages,
                "unread_cause_files": unread_cause_files,
                "confirmed_unreadable_files": confirmed_unreadable_files,
                "confirmed_unreadable_pages": confirmed_unreadable_pages,
                "confirmed_unreadable_by_cause": confirmed_unreadable_by_cause,
            },
        }
        diagnostics["unread_cause_counts"] = {
            "pages": unread_cause_pages,
            "files": unread_cause_files,
        }
        for issue in self.summary["issues"]:
            counts[issue.get("reason", "")] = counts.get(issue.get("reason", ""), 0) + 1
        diagnostics["issue_counts"] = counts
        if client is not None:
            diagnostics["http"] = {"totals": getattr(client, "call_totals", {}),
                                   "calls": list(getattr(client, "calls", []))}
        return self.summary

    def _metadata_gate(self, client, items, queries, folders):
        """열어 볼 후보: 폴더·파일명 점수 + Drive 서버 본문 검색(파일을 내려받지 않음)."""
        info = {"thresholds": relevance.gate_thresholds(), "fulltext": []}
        hits = {}
        search = getattr(client, "search_fulltext", None)
        folder_ids = list(folders) or [self.folder]
        mark = time.monotonic()
        for query in queries if search else []:
            words = relevance.salient_words(query)
            if not words:
                continue
            try:
                found = search(folder_ids, words)
            except ReferenceError as exc:
                # 본문 검색을 쓸 수 없으면 이름 점수만으로 고른다(열기 전 선정의 보조 수단일 뿐이다).
                entry = {"terms": words, "error": str(exc)}
                if getattr(client, "last_error_reason", ""):
                    entry["reason"] = client.last_error_reason
                info["fulltext"].append(entry)
                if str(exc) in ("DRIVE_HTTP_401", "DRIVE_HTTP_403", "DRIVE_HTTP_429", "DRIVE_FULLTEXT_FORBIDDEN",
                                "SYNC_BUDGET_EXHAUSTED"):
                    # 같은 거절을 문서마다 반복하지 않는다(0.9.8 실제 실행: 403 5회).
                    info["fulltext_available"] = False
                    break
                continue
            info["fulltext"].append({"terms": words, "files": len(found)})
            for file_id in found:
                hits.setdefault(file_id, []).append(" ".join(words))
        gate = relevance.metadata_gate(items, queries, hits)
        self._gate_weights = relevance.gate_weights(items)
        info["selected"] = sum(1 for g in gate.values() if g["selected"])
        info["not_selected"] = len(gate) - info["selected"]
        info["ms"] = round((time.monotonic() - mark) * 1000)
        self.summary["diagnostics"]["metadata_gate"] = info
        return gate

    def _sync_files(self, client, db, items, skip, gate=None, *, reprocess_low_quality: Optional[bool] = None):
        cache_dir = self.directory / "raw_cache"

        def _delete_raw_cache(target_id: str) -> None:
            try:
                (cache_dir / f"{target_id}.bin").unlink(missing_ok=True)
            except OSError:
                pass

        def _enforce_raw_cache_limit(protect_path: Path | None = None) -> None:
            if not cache_dir.is_dir():
                return
            entries: list[tuple[float, str, int, Path]] = []
            total_bytes = 0
            for p in cache_dir.glob("*.bin"):
                try:
                    st = p.stat()
                except OSError:
                    continue
                total_bytes += st.st_size
                entries.append((st.st_mtime, p.name, st.st_size, p))
            limit_bytes = max(0, int(getattr(self, "max_raw_cache_bytes", MAX_RAW_CACHE_BYTES)))
            if total_bytes <= limit_bytes:
                return
            for _, _, sz, p in sorted(entries, key=lambda x: (x[0], x[1])):
                if total_bytes <= limit_bytes:
                    break
                if protect_path is not None and p == protect_path:
                    continue
                try:
                    p.unlink(missing_ok=True)
                    total_bytes -= sz
                except OSError:
                    pass

        def _purge_file(target_id: str) -> None:
            db.execute("DELETE FROM chunks WHERE file_id=?", (target_id,))
            db.execute("DELETE FROM chunk_identifiers WHERE file_id=?", (target_id,))
            db.execute("DELETE FROM case_rows WHERE file_id=?", (target_id,))
            db.execute("DELETE FROM files WHERE id=?", (target_id,))
            db.commit()
            _delete_raw_cache(target_id)

        diagnostics = self.summary["diagnostics"]
        seen = {item["id"] for item in items}
        # Delete only after a complete listing, never infer deletion from a failed page.
        for (file_id,) in db.execute("SELECT id FROM files").fetchall():
            if file_id not in seen:
                db.execute("DELETE FROM chunks WHERE file_id=?", (file_id,))
                db.execute("DELETE FROM chunk_identifiers WHERE file_id=?", (file_id,))
                db.execute("DELETE FROM case_rows WHERE file_id=?", (file_id,))
                db.execute("DELETE FROM files WHERE id=?", (file_id,))
                _delete_raw_cache(file_id)
        db.commit()
        downloaded = 0
        new_files = 0
        # Identical copies come last and are skipped when their kept original is usable.
        # Cached files next, so bounded runs stay useful while new material warms up.
        cached = {row[0] for row in db.execute("SELECT id FROM files")}
        audit = {item["file_id"]: item for item in self.summary["inventory"]}
        items_by_id = {item["id"]: item for item in items}
        chosen = (lambda file_id: True) if gate is None else (lambda file_id: gate[file_id]["selected"])
        # inventory 및 원본 items 항목의 메타데이터를 모두 확인하여 표 후보를 누락 없이 식별한다 (TK-74)
        is_candidate = lambda file_id: (
            is_case_table_candidate(audit.get(file_id, {}))
            or is_case_table_candidate(items_by_id.get(file_id, {}))
        )
        ordered = sorted(items, key=lambda i: (
            not (chosen(i["id"]) or is_candidate(i["id"])),
            not is_candidate(i["id"]),
            gate[i["id"]].get("rank", 0) if gate else 0,
            -audit[i["id"]]["metadata"]["score"],
            -(gate[i["id"]]["score"] if gate else 0), i["id"] in skip, i["id"] not in cached,
            int(i.get("size") or 0), i["id"]))
        for index, item in enumerate(ordered):
            self.notify(index, len(ordered))
            file_id = item["id"]
            entry = audit[file_id]
            if not chosen(file_id) and not is_candidate(file_id) and file_id not in cached:
                # 후보가 아니고 색인된 적도 없는 일반 파일은 권한 확인·내려받기 없이 넘어간다.
                entry.update(status="NOT_SELECTED_METADATA", reason=gate[file_id]["reason"] if gate else "NOT_SELECTED")
                continue
            try:
                client.remaining()
                if skip.get(file_id) in self.eligible:
                    diagnostics["duplicates_skipped"] += 1
                    _purge_file(file_id)
                    entry.update(status="DUPLICATE_REUSED", reason="IDENTICAL_CONTENT", duplicate_of=skip[file_id])
                    continue
                # The listing was read moments ago in this run; it already carries parents, trash state,
                # download permission and revision, so an unchanged cached file needs no second request.
                problem = access_problem(item)
                if problem:
                    _purge_file(file_id)
                    raise ReferenceError(problem)
                folder_path = item.get("folder_path", "")
                version = revision(item) + ":" + EXTRACTOR_VERSION
                prior_any_row = db.execute("SELECT revision, payload FROM files WHERE id=?", (file_id,)).fetchone()
                prior_any_rev = prior_any_row[0] if prior_any_row else None
                prior_any = json.loads(prior_any_row[1]) if prior_any_row else None
                row = db.execute("SELECT payload FROM files WHERE id=? AND revision=?", (file_id, version)).fetchone()
                if (
                    row is None
                    and prior_any is not None
                    and prior_any_rev
                    and item.get("md5Checksum")
                    and prior_any.get("drive_md5") == item.get("md5Checksum")
                    and prior_any.get("extractor_version") == EXTRACTOR_VERSION
                    and _prior_has_body(prior_any)
                    and not prior_any.get("continuation")
                    and not stale_quarantine(prior_any)
                ):
                    # 이름·폴더 위치만 변경되고 본문 md5가 동일하면 기존 청크·임베딩·식별자를 새 revision으로 승계한다.
                    with db:
                        db.execute("UPDATE files SET revision=? WHERE id=? AND revision=?", (version, file_id, prior_any_rev))
                        db.execute("UPDATE chunks SET revision=? WHERE file_id=? AND revision=?", (version, file_id, prior_any_rev))
                        db.execute("UPDATE chunk_identifiers SET revision=? WHERE file_id=? AND revision=?", (version, file_id, prior_any_rev))
                        db.execute("UPDATE chunk_embeddings SET revision=? WHERE file_id=? AND revision=?", (version, file_id, prior_any_rev))
                        db.execute("UPDATE case_rows SET revision=? WHERE file_id=? AND revision=?", (version, file_id, prior_any_rev))
                    prior_any_rev = version
                    entry["metadata_only_renamed_or_moved"] = True
                    row = db.execute("SELECT payload FROM files WHERE id=? AND revision=?", (file_id, version)).fetchone()
                if row and stale_quarantine(json.loads(row[0])):
                    row = None                    # 예전 규칙(파일 전체 격리, 근거 미기록)의 결과는 다시 읽는다
                def _has_retryable_unread(p: dict) -> bool:
                    if int(p.get("retry_attempts") or 0) >= 2:
                        return False
                    if p.get("retryable_unread_pages"):
                        return True
                    by_cause = p.get("unread_pages_by_cause") or {}
                    config_blocked = set(p.get("config_blocked_pages") or [])
                    confirmed = set(p.get("confirmed_unreadable_pages") or [])
                    for cause_key in _RETRYABLE_UNREAD_CAUSES:
                        pages_for_cause = [pg for pg in (by_cause.get(cause_key) or []) if pg not in config_blocked and pg not in confirmed]
                        if pages_for_cause:
                            return True
                    return False

                def _needs_unreadable_confirmation(p: dict) -> bool:
                    return bool(
                        p.get("confirmed_unreadable_pages")
                        and not p.get("unreadable_confirmed")
                        and int(p.get("unreadable_confirm_attempts") or 0) < 2
                    )

                from packages.document_engine.ocr import resolve_ocr_fallback_config

                ocr_fb_cfg = getattr(self, "_run_ocr_fallback_config", None) or resolve_ocr_fallback_config()
                auto_reprocess = bool(
                    reprocess_low_quality
                    if reprocess_low_quality is not None
                    else (ocr_fb_cfg["enabled"] and resolve_inline_reprocess_enabled())
                )
                reprocess_cap = resolve_reprocess_timeout_seconds()

                def _needs_damaged_extract_restore(p: dict) -> bool:
                    if p.get("continuation"):
                        return False
                    if int(p.get("resume_failures") or 0) >= 2:
                        return False
                    if p.get("reason") not in ("REFERENCE_PARSE_TIMEOUT", "REFERENCE_PARSE_FAILED"):
                        return False
                    if int(p.get("chunk_count") or 0) != 0:
                        return False
                    attempts = int(p.get("restore_attempts") or 0)
                    if attempts >= 2:
                        return False
                    return int(p.get("previous_searchable_pages") or 0) > 0 or attempts > 0

                def _needs_low_quality_ocr_reprocess(p: dict) -> bool:
                    low_pages = _low_quality_page_set(p)
                    if not low_pages:
                        return False
                    if reprocess_low_quality is True:
                        return True
                    return auto_reprocess and p.get("low_quality_reprocess_version") != OCR_REPROCESS_VERSION

                prior_same_rev_row = row
                prior = json.loads(row[0]) if row else None
                continuation = prior.get("continuation") if prior else None
                retry_reason = None
                if continuation:
                    row = None  # Only a progressing structured table or bounded OCR is retried at the same revision.
                    retry_reason = "continuation"
                elif prior and _needs_damaged_extract_restore(prior):
                    row = None
                    retry_reason = "restore_failed_extract"
                elif prior and _needs_low_quality_ocr_reprocess(prior):
                    row = None
                    retry_reason = "reprocess_low_quality"
                elif prior and _has_retryable_unread(prior):
                    row = None
                    retry_reason = "retryable_unread"
                elif prior and _needs_unreadable_confirmation(prior):
                    row = None
                    retry_reason = "confirm_unreadable"
                elif prior and _is_legacy_unread_without_reasons(prior):
                    row = None
                    retry_reason = "legacy_unread_reeval"

                if (
                    row is None
                    and prior_same_rev_row is not None
                    and retry_reason in _REPROCESS_RETRY_REASONS
                    and min(float(reprocess_cap), float(client.remaining()) - 60.0) < 30.0
                ):
                    # 예산 부족(한도 30초 미만 / 남은 예산 90초 미만)이면 기존 결과를 쓰고 다음 실행으로 미룬다 (TK-247)
                    row = prior_same_rev_row
                    retry_reason = None
                    entry["reprocess_deferred"] = True

                if row:
                    parsed = json.loads(row[0])
                    _reconcile_unread_causes(parsed)
                    if parsed.get("identifier_index_version") != IDENTIFIER_INDEX_VERSION:
                        existing_chunks = db.execute(
                            "SELECT rowid, page, start, text FROM chunks WHERE file_id=? AND revision=?",
                            (file_id, version),
                        ).fetchall()
                        ident_rows = _extract_chunk_identifier_rows(file_id, version, existing_chunks)
                        parsed["identifier_index_version"] = IDENTIFIER_INDEX_VERSION
                        with db:
                            db.execute("DELETE FROM chunk_identifiers WHERE file_id=?", (file_id,))
                            if ident_rows:
                                db.executemany(
                                    "INSERT INTO chunk_identifiers VALUES (?,?,?,?,?,?,?)",
                                    ident_rows,
                                )
                            db.execute(
                                "UPDATE files SET payload=? WHERE id=? AND revision=?",
                                (json.dumps(parsed), file_id, version),
                            )
                    self.summary["files_reused"] += 1
                    entry["reused"] = True
                elif not chosen(file_id) and not is_candidate(file_id):
                    # 이름·경로·본문 검색 어느 쪽으로도 관련 후보가 아니고 표 후보도 아니면 열지 않는다.
                    entry.update(status="NOT_SELECTED_METADATA", reason=gate[file_id]["reason"] if gate else "NOT_SELECTED")
                    continue
                else:
                    if new_files >= self.settings.rag_max_files:
                        raise ReferenceError("INDEX_FILE_BUDGET_EXHAUSTED")
                    new_files += 1
                    if client.remaining() < 30:
                        raise ReferenceError("SYNC_BUDGET_EXHAUSTED")
                    fresh = client.metadata(file_id)
                    problem = access_problem(item, fresh)
                    if problem:
                        _purge_file(file_id)
                        self._access_detail(item, fresh, problem)
                        raise ReferenceError(problem)
                    item = {**fresh, "folder_path": folder_path, "listed_parent": item.get("listed_parent")}
                    version = revision(item) + ":" + EXTRACTOR_VERSION
                    if prior and (
                        continuation
                        or retry_reason in (*_REPROCESS_RETRY_REASONS, "restore_failed_extract")
                    ):
                        stored = db.execute("SELECT revision FROM files WHERE id=?", (file_id,)).fetchone()
                        if not stored or stored[0] != version:
                            prior, continuation = None, None
                            retry_reason = None
                    mime = item.get("mimeType", "")
                    if (mime not in EXPORTS and mime != "application/pdf"
                            and relevance.extension(item.get("name")) not in SUPPORTED):
                        raise ReferenceError("UNSUPPORTED_REFERENCE_FORMAT")
                    cache_path = cache_dir / f"{file_id}.bin"
                    reused_local_bytes = False
                    if (
                        prior
                        and (continuation or retry_reason in ("retryable_unread", "confirm_unreadable", "legacy_unread_reeval"))
                        and prior.get("sha256")
                        and cache_path.is_file()
                    ):
                        cached_bytes = cache_path.read_bytes()
                        if hashlib.sha256(cached_bytes).hexdigest() == prior.get("sha256"):
                            data = cached_bytes
                            filename = prior.get("cached_filename") or item.get("name") or "reference"
                            mime = prior.get("cached_mime") or mime
                            reused_local_bytes = True
                    if not reused_local_bytes:
                        limit = min(96 * 1024 * 1024, self.settings.rag_download_mb * 1024 * 1024 - downloaded)
                        if limit <= 0 or int(item.get("size") or 0) > limit:
                            raise ReferenceError("DOWNLOAD_BUDGET_EXHAUSTED")
                        data, filename, mime = client.download(item, max_bytes=limit)
                        downloaded += len(data)
                        diagnostics["downloads"]["count"] += 1
                        diagnostics["downloads"]["bytes"] += len(data)
                        after = client.metadata(file_id)
                        after_problem = access_problem(item, after)
                        if after_problem:
                            _purge_file(file_id)
                            self._access_detail(item, after, after_problem)
                            raise ReferenceError(after_problem)
                        if revision(after) != revision(item):
                            raise ReferenceError("REFERENCE_CHANGED_DURING_DOWNLOAD")
                        if item.get("md5Checksum") and hashlib.md5(data).hexdigest() != item["md5Checksum"]:
                            raise ReferenceError("REFERENCE_CHECKSUM_MISMATCH")
                    if (
                        prior is not None
                        and retry_reason in _REPROCESS_RETRY_REASONS
                        and min(float(reprocess_cap), float(client.remaining()) - 60.0) < 30.0
                    ):
                        # 내려받기 뒤 남은 예산이 90초 미만으로 줄었으면 추출하지 않고 기존 결과를 유지한다 (TK-247)
                        parsed = copy.deepcopy(prior)
                        _reconcile_unread_causes(parsed)
                        self.summary["files_reused"] += 1
                        entry["reused"] = True
                        entry["reprocess_deferred"] = True
                    else:
                        if client.remaining() < 30:
                            raise ReferenceError("SYNC_BUDGET_EXHAUSTED")
                        if retry_reason in _REPROCESS_RETRY_REASONS:
                            extract_timeout = int(min(float(reprocess_cap), float(client.remaining()) - 60.0))
                        elif retry_reason == "restore_failed_extract":
                            extract_timeout = max(30, int(min(60.0, float(client.remaining()) - 30.0)))
                        else:
                            extract_timeout = 30
                        effective_ocr_fb_cfg = (
                            {"engine": "none", "mode": "off", "enabled": False}
                            if retry_reason == "restore_failed_extract"
                            else ocr_fb_cfg
                        )
                        extract_fail_reason: str | None = None
                        mark = time.monotonic()
                        try:
                            kwargs = {"directory": self.directory, "timeout": extract_timeout}
                            if continuation:
                                kwargs["continuation"] = continuation
                            if self.extractor is isolated_extract or _accepts_kwarg(self.extractor, "ocr_fallback_config"):
                                kwargs["ocr_fallback_config"] = effective_ocr_fb_cfg
                            parsed = self.extractor(data, filename, mime, **kwargs)
                            if (continuation and not parsed.get("resumed")
                                    and parsed.get("reason") in ("REFERENCE_PARSE_TIMEOUT", "REFERENCE_PARSE_FAILED")):
                                raise ReferenceError(parsed["reason"])
                            if (
                                not continuation
                                and not parsed.get("chunks")
                                and not parsed.get("case_records")
                                and parsed.get("reason") in ("REFERENCE_PARSE_TIMEOUT", "REFERENCE_PARSE_FAILED")
                            ):
                                extract_fail_reason = str(parsed["reason"])
                        except ReferenceError as exc:
                            if str(exc) not in ("REFERENCE_PARSE_TIMEOUT", "REFERENCE_PARSE_FAILED"):
                                raise
                            if continuation:
                                # Retain committed rows/cursor, but do not retry a stuck row forever.
                                failed_batch = dict(prior)
                                failed_batch["resume_failures"] = int(prior.get("resume_failures", 0)) + 1
                                if failed_batch["resume_failures"] >= 2:
                                    failed_batch["continuation"] = None
                                    failed_batch.update(partial=True, reason=str(exc))
                                    _delete_raw_cache(file_id)
                                with db:
                                    db.execute("UPDATE files SET payload=? WHERE id=? AND revision=?",
                                               (json.dumps(failed_batch), file_id, version))
                                raise
                            extract_fail_reason = str(exc)
                            parsed = {"chunks": [], "partial": True, "reason": extract_fail_reason}
                        finally:
                            diagnostics["extractions"]["count"] += 1
                            diagnostics["extractions"]["ms"] += round((time.monotonic() - mark) * 1000)

                        if (
                            extract_fail_reason is not None
                            and retry_reason in _REPROCESS_RETRY_REASONS
                            and _prior_has_body(prior)
                        ):
                            # TK-247 ①: 재처리 실패 시 기존 조각·기록을 보존하고 이번 실행에서도 기존 본문으로 색인한다.
                            preserved = copy.deepcopy(prior)
                            prev_fail_ver = preserved.get("reprocess_failures_version")
                            base_failures = (
                                0
                                if (prev_fail_ver is not None and prev_fail_ver != OCR_REPROCESS_VERSION)
                                else int(preserved.get("reprocess_failures") or 0)
                            )
                            failures = base_failures + 1
                            preserved["reprocess_failures"] = failures
                            preserved["reprocess_failures_version"] = OCR_REPROCESS_VERSION
                            preserved["last_reprocess_error"] = extract_fail_reason
                            preserved["recovered_pages"] = 0
                            preserved["searchable_pages_delta"] = 0
                            if retry_reason == "reprocess_low_quality":
                                prev_low_cnt = len(_low_quality_page_set(preserved))
                                preserved["low_quality_pages_before"] = prev_low_cnt
                                preserved["low_quality_pages_after"] = prev_low_cnt
                                preserved["reprocessed_pages"] = 0
                                if failures >= 2:
                                    preserved["low_quality_reprocess_version"] = OCR_REPROCESS_VERSION
                                    if preserved.get("confirmed_unreadable_pages"):
                                        preserved["unreadable_confirm_attempts"] = max(
                                            2, int(preserved.get("unreadable_confirm_attempts") or 0) + 1
                                        )
                                        preserved["unreadable_confirmed"] = True
                            elif retry_reason == "retryable_unread":
                                if failures >= 2:
                                    preserved["retry_attempts"] = max(2, int(preserved.get("retry_attempts") or 0) + 1)
                                else:
                                    preserved["retry_attempts"] = max(1, int(preserved.get("retry_attempts") or 0))
                            elif retry_reason == "confirm_unreadable":
                                if failures >= 2:
                                    preserved["unreadable_confirm_attempts"] = max(
                                        2, int(preserved.get("unreadable_confirm_attempts") or 0) + 1
                                    )
                                    preserved["unreadable_confirmed"] = True
                                else:
                                    preserved["unreadable_confirm_attempts"] = max(
                                        1, int(preserved.get("unreadable_confirm_attempts") or 0)
                                    )
                            elif retry_reason == "legacy_unread_reeval":
                                if failures >= 2:
                                    preserved["legacy_unread_reevaluated"] = True
                            if not preserved.get("continuation"):
                                _delete_raw_cache(file_id)
                            with db:
                                db.execute(
                                    "UPDATE files SET payload=? WHERE id=? AND revision=?",
                                    (json.dumps(preserved), file_id, version),
                                )
                            parsed = copy.deepcopy(preserved)
                            _reconcile_unread_causes(parsed)
                            entry["reprocess_failed"] = True
                            entry["reprocess_failures"] = failures
                            entry["last_reprocess_error"] = extract_fail_reason
                        elif (
                            extract_fail_reason is not None
                            and prior is None
                            and prior_any is not None
                            and prior_any_rev
                            and _prior_has_body(prior_any)
                        ):
                            # 수정본 추출이 실패하면 기존 정상 색인·청크·식별자를 덮어쓰지 않고 유지한다.
                            preserved = copy.deepcopy(prior_any)
                            preserved["last_update_error"] = extract_fail_reason
                            preserved["modified_update_failed"] = True
                            with db:
                                db.execute(
                                    "UPDATE files SET payload=? WHERE id=? AND revision=?",
                                    (json.dumps(preserved), file_id, prior_any_rev),
                                )
                            parsed = copy.deepcopy(preserved)
                            _reconcile_unread_causes(parsed)
                            version = prior_any_rev
                            entry["modified_update_failed"] = True
                            entry["fallback_to_prior_version"] = True
                            entry["prior_indexed_at"] = prior_any.get("indexed_at")
                            entry["last_update_error"] = extract_fail_reason
                        else:
                            if retry_reason == "reprocess_low_quality" and extract_fail_reason is None:
                                entry["reprocessed_in_run"] = True
                            if retry_reason in _REPROCESS_RETRY_REASONS and extract_fail_reason is None:
                                parsed["reprocess_failures"] = 0
                                parsed.pop("last_reprocess_error", None)
                                parsed.pop("reprocess_failures_version", None)
                            chunks = parsed.pop("chunks", [])
                            case_records = parsed.pop("case_records", [])
                            is_case_table = bool(parsed.get("structured_case_table"))
                            # 판례표가 아닌 일반 스프레드시트라 하더라도 추후 문서 선별 시 캐시 재사용을 위해
                            # chunks 및 parsed 메타데이터는 DB에 온전히 보존하여 저장한다 (TK-74 회귀 방지 보완).
                            append_batch = bool(prior and parsed.get("resumed") and prior.get("sha256") == parsed.get("sha256")
                                                and parsed.get("reason") != "REFERENCE_QUARANTINED")
                            parsed["chunk_count"] = len(chunks) + (prior.get("chunk_count", 0) if append_batch else 0)
                            parsed["cached_filename"] = filename
                            parsed["cached_mime"] = mime
                            parsed["drive_md5"] = item.get("md5Checksum") or ""
                            parsed["extractor_version"] = EXTRACTOR_VERSION
                            parsed["indexed_at"] = datetime.now(timezone.utc).isoformat()
                            parsed.pop("modified_update_failed", None)
                            parsed.pop("last_update_error", None)
                            _reconcile_unread_causes(parsed)
                            if retry_reason == "legacy_unread_reeval" or (prior and prior.get("legacy_unread_reevaluated")):
                                parsed["legacy_unread_reevaluated"] = True
                            if retry_reason == "retryable_unread" and prior:
                                prior_best = int(
                                    prior.get("best_read_pages")
                                    if prior.get("best_read_pages") is not None
                                    else (prior.get("read_pages") or 0)
                                )
                                cur_read = int(parsed.get("read_pages") or 0)
                                if cur_read > prior_best:
                                    parsed["best_read_pages"] = cur_read
                                    parsed["retry_attempts"] = 0
                                else:
                                    parsed["best_read_pages"] = prior_best
                                    parsed["retry_attempts"] = int(prior.get("retry_attempts") or 0) + 1
                            elif parsed.get("read_pages") is not None:
                                prior_best = int(
                                    (prior or {}).get("best_read_pages")
                                    if (prior or {}).get("best_read_pages") is not None
                                    else ((prior or {}).get("read_pages") or 0)
                                )
                                parsed["best_read_pages"] = max(prior_best, int(parsed.get("read_pages") or 0))
                            cur_searchable = parsed.get("searchable_pages")
                            if cur_searchable is None:
                                cur_searchable = len({int(c["page"]) for c in chunks if isinstance(c, dict) and c.get("page") is not None})
                                parsed["searchable_pages"] = cur_searchable
                            prior_for_searchable = prior or prior_any
                            if prior_for_searchable:
                                prev_searchable = prior_for_searchable.get("searchable_pages")
                                if prev_searchable is None:
                                    prev_searchable = (
                                        prior_for_searchable.get("extracted_text_pages")
                                        if prior_for_searchable.get("extracted_text_pages") is not None
                                        else prior_for_searchable.get("read_pages")
                                    )
                                if (
                                    retry_reason == "restore_failed_extract"
                                    and extract_fail_reason is not None
                                    and int(prev_searchable or 0) == 0
                                    and int(prior_for_searchable.get("previous_searchable_pages") or 0) > 0
                                ):
                                    # 손상 파일 복원 실패 시 원래의 previous_searchable_pages 표식을 덮어쓰지 않는다.
                                    prev_searchable = int(prior_for_searchable["previous_searchable_pages"])
                                if prev_searchable is not None:
                                    parsed["previous_searchable_pages"] = int(prev_searchable)
                                    parsed["searchable_pages_delta"] = int(cur_searchable) - int(prev_searchable)
                            cur_low_set = _low_quality_page_set(parsed)
                            if (
                                extract_fail_reason is None
                                and retry_reason in ("reprocess_low_quality", "legacy_unread_reeval")
                                and prior_for_searchable
                            ):
                                prev_low_set = _low_quality_page_set(prior_for_searchable)
                                prev_low_pages = len(prev_low_set)
                                cur_low_pages = len(cur_low_set)
                                if prev_low_pages == 0 and retry_reason == "legacy_unread_reeval":
                                    prev_pages = int(prior_for_searchable.get("pages") or 0)
                                    prev_comp = prior_for_searchable.get("completed_pages")
                                    if prev_comp is None:
                                        prev_comp = prior_for_searchable.get("read_pages") or 0
                                    prev_gap = max(0, prev_pages - int(prev_comp))
                                    parsed["low_quality_pages_before"] = prev_low_pages
                                    parsed["low_quality_pages_after"] = cur_low_pages
                                    parsed["reprocessed_pages"] = prev_gap
                                    parsed["recovered_pages"] = max(0, int(parsed.get("searchable_pages_delta") or 0))
                                else:
                                    parsed["low_quality_pages_before"] = prev_low_pages
                                    parsed["low_quality_pages_after"] = cur_low_pages
                                    parsed["reprocessed_pages"] = prev_low_pages
                                    parsed["recovered_pages"] = max(0, prev_low_pages - cur_low_pages)
                            if retry_reason == "restore_failed_extract":
                                if extract_fail_reason is not None:
                                    restore_attempts = int((prior or {}).get("restore_attempts") or 0) + 1
                                    parsed["restore_attempts"] = restore_attempts
                                    parsed["last_restore_error"] = extract_fail_reason
                                    parsed["recovered_pages"] = 0
                                    entry["restore_failed"] = True
                                    entry["restore_attempts"] = restore_attempts
                                else:
                                    # TK-247 ④: 1차 OCR로 손상 복원에 성공하면 판 기록을 비워 다음 실행에서 폴백 재처리를 보존 규칙 아래 시도하게 한다.
                                    parsed.pop("low_quality_reprocess_version", None)
                                    parsed.pop("restore_attempts", None)
                                    parsed.pop("last_restore_error", None)
                                    parsed["reprocess_failures"] = 0
                                    parsed.pop("last_reprocess_error", None)
                                    parsed.pop("reprocess_failures_version", None)
                                    parsed["restored_from_failed_extract"] = True
                                    entry["restored_in_run"] = True
                            elif extract_fail_reason is None and (
                                (auto_reprocess and effective_ocr_fb_cfg.get("enabled") and cur_low_set)
                                or retry_reason == "reprocess_low_quality"
                            ):
                                parsed["low_quality_reprocess_version"] = OCR_REPROCESS_VERSION
                            if parsed.get("confirmed_unreadable_pages"):
                                base_attempts = int((prior or {}).get("unreadable_confirm_attempts") or 0)
                                if retry_reason in ("reprocess_low_quality", "restore_failed_extract") and prior:
                                    base_attempts = max(1, base_attempts)
                                attempts = base_attempts + 1
                                parsed["unreadable_confirm_attempts"] = attempts
                                if (
                                    retry_reason in ("confirm_unreadable", "reprocess_low_quality")
                                    and prior
                                    and sorted(parsed.get("confirmed_unreadable_pages") or []) == sorted(prior.get("confirmed_unreadable_pages") or [])
                                ) or attempts >= 2:
                                    parsed["unreadable_confirmed"] = True
                                elif parsed.get("unreadable_confirmed") is not True:
                                    parsed["unreadable_confirmed"] = False
                            if parsed.get("continuation"):
                                limit_bytes = max(0, int(getattr(self, "max_raw_cache_bytes", MAX_RAW_CACHE_BYTES)))
                                if len(data) <= limit_bytes:
                                    cache_dir.mkdir(parents=True, exist_ok=True)
                                    try:
                                        os.chmod(cache_dir, 0o700)
                                    except OSError:
                                        pass
                                    cache_path.write_bytes(data)
                                    try:
                                        os.chmod(cache_path, 0o600)
                                    except OSError:
                                        pass
                                    _enforce_raw_cache_limit(protect_path=cache_path)
                            else:
                                _delete_raw_cache(file_id)
                            # Cache terminal parse outcomes, too; a large unreadable file must not starve later files.
                            parsed["identifier_index_version"] = IDENTIFIER_INDEX_VERSION
                            with db:
                                if not append_batch:
                                    db.execute("DELETE FROM chunks WHERE file_id=?", (file_id,))
                                    db.execute("DELETE FROM chunk_identifiers WHERE file_id=?", (file_id,))
                                    db.execute("DELETE FROM case_rows WHERE file_id=?", (file_id,))
                                db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?)", (file_id, version, json.dumps(parsed)))
                                inserted_ident_rows: list[tuple] = []
                                for c in chunks:
                                    cur = db.execute(
                                        "INSERT INTO chunks VALUES (?,?,?,?,?,?)",
                                        (file_id, version, c["page"], c["start"], c["text"], " ".join(tokens(c["text"]))),
                                    )
                                    inserted_ident_rows.append((cur.lastrowid, c["page"], c["start"], c["text"]))
                                if inserted_ident_rows:
                                    ident_rows = _extract_chunk_identifier_rows(file_id, version, inserted_ident_rows)
                                    if ident_rows:
                                        db.executemany(
                                            "INSERT INTO chunk_identifiers VALUES (?,?,?,?,?,?,?)",
                                            ident_rows,
                                        )
                                if case_records:
                                    db.executemany("""INSERT OR REPLACE INTO case_rows
                                        (record_id,file_id,revision,sheet,row_number,source_cell_range,
                                         original_number,title,case_info,court,decision_date,case_numbers,
                                         target_case_numbers,referenced_case_numbers,issue,facts,reason,holding,
                                         hyperlinks,quality_warnings,case_head,indexed_text,raw_cells) VALUES
                                        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", [
                                        (r.get("record_id"), file_id, version, r.get("sheet"), r.get("row"),
                                         r.get("source_cell_range"), r.get("original_number"), r.get("title"),
                                         r.get("case_info"), r.get("court"), r.get("decision_date"),
                                         json.dumps(r.get("case_numbers", []), ensure_ascii=False),
                                         json.dumps(r.get("target_case_numbers", r.get("case_numbers", [])), ensure_ascii=False),
                                         json.dumps(r.get("referenced_case_numbers", []), ensure_ascii=False), r.get("issue"),
                                         r.get("facts"), r.get("reason"), r.get("holding"),
                                         json.dumps(r.get("hyperlinks", []), ensure_ascii=False),
                                         json.dumps(r.get("quality_warnings", []), ensure_ascii=False),
                                         r.get("case_head"), r.get("indexed_text"),
                                         json.dumps(r.get("raw_cells", {}), ensure_ascii=False)) for r in case_records])
                is_case_table = bool(parsed.get("structured_case_table"))
                raw_reason = parsed.get("reason") or ""
                has_continuation = bool(parsed.get("continuation"))
                if "coverage_complete" in parsed and "content_readable_complete" in parsed:
                    unconfirmed_unreadable = bool(
                        parsed.get("confirmed_unreadable_pages") and not parsed.get("unreadable_confirmed")
                    )
                    exec_coverage_complete = (
                        bool(parsed.get("coverage_complete"))
                        and not has_continuation
                        and not unconfirmed_unreadable
                    )
                    content_readable_complete = bool(parsed.get("content_readable_complete"))
                    is_partial = not exec_coverage_complete
                    blank_only_complete = bool(
                        exec_coverage_complete
                        and not content_readable_complete
                        and parsed.get("blank_pages")
                        and raw_reason in ("", "VERIFIED_BLANK_PAGES", "VERIFIED_BLANK_DOCUMENT")
                    )
                    content_only_incomplete = bool(exec_coverage_complete and not content_readable_complete)
                else:
                    has_unfinished_pages = bool(
                        parsed.get("incomplete_pages")
                        or parsed.get("scanned_pages")
                        or parsed.get("ocr_low_quality_pages")
                        or parsed.get("error_pages")
                        or parsed.get("unprocessed_pages")
                    )
                    blank_only_complete = bool(
                        parsed.get("coverage_complete")
                        and not has_unfinished_pages
                        and not has_continuation
                        and parsed.get("blank_pages")
                        and raw_reason in ("", "VERIFIED_BLANK_PAGES", "VERIFIED_BLANK_DOCUMENT")
                    )
                    is_partial = (
                        has_unfinished_pages
                        or has_continuation
                        or (bool(parsed.get("partial")) and not blank_only_complete)
                    )
                    content_only_incomplete = False
                chunk_count = int(parsed.get("chunk_count", 0))

                # 파싱 중 오류·시간초과·격리 또는 미완료(이어 읽기 대기) 여부 판정 (TK-74 한국어 주석)
                # 실제 sync 과정에서 추출기가 타임아웃, 파싱 실패, 격리 등을 반환한 경우를 포착한다.
                is_failed_or_incomplete = (
                    is_partial
                    or has_continuation
                    or any(k in raw_reason.upper() for k in ("TIMEOUT", "FAILED", "QUARANTINE", "UNAVAILABLE", "UNSUPPORTED"))
                )

                if is_case_table:
                    # 1. 판례표로 성공적으로 확인된 경우
                    entry["structured_case_table"] = True
                    entry["case_table_stats"] = parsed.get("stats", {})
                    entry["continuation"] = has_continuation
                    status = "INDEXED_PARTIAL" if is_partial else "INDEXED"
                    entry.update(
                        status=status,
                        reason=raw_reason or "TEXT_INDEXED",
                        pages=parsed.get("pages"),
                        read_pages=parsed.get("read_pages"),
                    )
                    if is_partial:
                        self.summary["issues"].append({
                            "file_id": file_id,
                            "name": item.get("name"),
                            "reason": raw_reason or "REFERENCE_PARTIALLY_READ",
                            "read_pages": parsed.get("read_pages"),
                            "pages": parsed.get("pages"),
                        })
                elif is_candidate(file_id) and not chosen(file_id):
                    # 2. 표 후보이나 서면 본문 선별에서 제외된 파일 (TK-74 보완)
                    if is_failed_or_incomplete:
                        # 읽기 실패, 시간초과, 보안 격리, 또는 미완료(0행 이어 읽기 등)인 경우:
                        # 정상 음성(NOT_A_CASE_TABLE)으로 덮어쓰지 않고 실제 실패/진행 사유와 상태를 보존한다.
                        if "QUARANTINE" in raw_reason.upper():
                            cand_status = "QUARANTINED"
                        elif has_continuation:
                            cand_status = "INDEXED_PARTIAL"
                            entry["continuation"] = True
                        elif any(k in raw_reason.upper() for k in ("TIMEOUT", "FAILED")):
                            cand_status = "PARSE_FAILED"
                        elif chunk_count > 0 and is_partial:
                            cand_status = "INDEXED_PARTIAL"
                        else:
                            cand_status = "PARSE_FAILED"

                        entry.update(
                            status=cand_status,
                            reason=raw_reason or "REFERENCE_PARSE_FAILED",
                            pages=parsed.get("pages"),
                            read_pages=parsed.get("read_pages"),
                        )
                        self.summary["issues"].append({
                            "file_id": file_id,
                            "name": item.get("name"),
                            "reason": raw_reason or "REFERENCE_PARSE_FAILED",
                            "read_pages": parsed.get("read_pages"),
                            "pages": parsed.get("pages"),
                        })
                    else:
                        # 정상적으로 완전히 읽었으나 판례표 요건을 충족하지 못한 경우: 정상 음성 판별
                        entry.update(status="NOT_A_CASE_TABLE", reason="NOT_A_CASE_TABLE")
                else:
                    # 3. 일반 문서(실행 문제 없이 자료 성질 쪽만 남은 경우는 INDEXED + CONTENT_UNREADABLE_PAGES로 분리)
                    verified_blank_doc = bool(blank_only_complete and not chunk_count)
                    if is_partial or (not chunk_count and not verified_blank_doc and not content_only_incomplete):
                        issue_obj = {
                            "file_id": file_id,
                            "name": item.get("name"),
                            "reason": raw_reason or "REFERENCE_EMPTY",
                            "read_pages": parsed.get("read_pages"),
                            "pages": parsed.get("pages"),
                        }
                        if parsed.get("unread_pages_by_cause"):
                            issue_obj["unread_pages_by_cause"] = parsed["unread_pages_by_cause"]
                        self.summary["issues"].append(issue_obj)
                    cand_status = (
                        ("INDEXED_PARTIAL" if is_partial else "INDEXED")
                        if (chunk_count or verified_blank_doc or content_only_incomplete)
                        else "PARSE_FAILED"
                    )
                    entry.update(
                        status=cand_status,
                        reason=raw_reason or ("VERIFIED_BLANK_DOCUMENT" if verified_blank_doc else "TEXT_INDEXED"),
                        pages=parsed.get("pages"),
                        read_pages=parsed.get("read_pages"),
                    )

                for bool_key in ("coverage_complete", "content_readable_complete", "unreadable_confirmed"):
                    if bool_key in parsed:
                        entry[bool_key] = bool(parsed[bool_key])
                for key in ("excluded_pages", "scan_findings", "no_text_pages", "unprocessed_pages", "coverage_note",
                            "page_diagnostics", "ocr_pages", "ocr_low_quality_pages", "ocr_fallback_summary", "child_ocr_config",
                            "blank_pages", "scanned_pages",
                            "error_pages", "incomplete_pages", "page_state_counts", "text_parser", "fallback_pages",
                            "unread_pages", "unread_pages_by_cause", "unread_cause_counts", "execution_incomplete_pages", "content_unreadable_pages",
                            "retryable_unread_pages", "config_blocked_pages", "confirmed_unreadable_pages",
                            "confirmed_unreadable_causes", "native_open_error", "read_completeness",
                            "last_reprocess_error", "last_restore_error",
                            "stats", "read_ranges", "excluded_rows", "table_version"):
                    if parsed.get(key):
                        entry[key] = parsed[key]
                for count_key in ("extracted_text_pages", "completed_pages", "best_read_pages",
                                  "searchable_pages", "previous_searchable_pages", "searchable_pages_delta",
                                  "low_quality_pages_before", "low_quality_pages_after",
                                  "reprocessed_pages", "recovered_pages",
                                  "reprocess_failures", "restore_attempts"):
                    if count_key in parsed and parsed[count_key] is not None:
                        entry[count_key] = parsed[count_key]
                if parsed.get("structured_case_table"):
                    entry["structured_case_table"] = True
                    entry["case_table_stats"] = parsed.get("stats", {})
                entry["page_numbers_reliable"] = parsed.get("page_numbers_reliable", True)
                # 미선별 스프레드시트 후보만 일반 검색에서 격리한다. 권한·리비전 검사를 통과한
                # 일반 문서 캐시는 현재 이름 선별과 무관하게 기존 본문 검색 대상으로 유지한다.
                if is_case_table or (chunk_count > 0 and (not is_candidate(file_id) or chosen(file_id))):
                    self.eligible[file_id] = {"file_id": file_id, "title": item.get("name", ""),
                        "folder_path": folder_path,
                        "format": relevance.source_format(item.get("name", ""), item.get("mimeType", "")),
                        "mime_type": item.get("mimeType", ""),
                        "base_name": relevance.base_name(item.get("name", "")).lower(),
                        "metadata_score": entry["metadata"]["score"],
                        "url": "https://drive.google.com/file/d/" + file_id + "/view",
                        "revision": version, "modified_time": item.get("modifiedTime"),
                        "sha256": parsed.get("sha256", ""), "partial": bool(is_partial),
                        "pages": parsed.get("pages"), "read_pages": parsed.get("read_pages"),
                        "extracted_text_pages": parsed.get("extracted_text_pages", parsed.get("read_pages")),
                        "completed_pages": parsed.get("completed_pages", parsed.get("read_pages")),
                        "page_numbers_reliable": parsed.get("page_numbers_reliable", True),
                        "body_extraction_scope": parsed.get("body_extraction_scope"),
                        "chunk_count": chunk_count,
                        "structured_case_table": is_case_table,
                        "case_table_stats": parsed.get("stats", {}),
                        "case_table_only": bool(is_case_table and not chosen(file_id)),
                        "identifier_indexed": parsed.get("identifier_index_version") == IDENTIFIER_INDEX_VERSION}
            except ReferenceError as exc:
                code = str(exc)
                reason_detail = code
                if code == "DRIVE_NETWORK_ERROR" and getattr(client, "last_error_reason", ""):
                    reason_detail = f"DRIVE_NETWORK_ERROR ({client.last_error_reason})"
                unread_cause = (
                    "BUDGET_EXHAUSTED" if "BUDGET" in code
                    else "READ_TIMEOUT" if "TIMEOUT" in code
                    else "PARSE_FAILED"
                )
                entry.update(
                    status="UNSUPPORTED_TYPE" if code == "UNSUPPORTED_REFERENCE_FORMAT" else
                    "SELECTED_PENDING" if "BUDGET" in code else "UNAVAILABLE",
                    reason=reason_detail,
                    unread_cause=unread_cause,
                )
                if str(exc) in ("DRIVE_HTTP_401", "DRIVE_HTTP_429"):
                    raise
                self.summary["issues"].append({"file_id": file_id, "name": item.get("name"), "reason": reason_detail, "unread_cause": unread_cause})
                if str(exc) == "SYNC_BUDGET_EXHAUSTED":
                    # 미룬 파일 수는 열기로 한 후보 중 남은 것만 센다(선정되지 않은 파일은 미룬 것이 아니다).
                    diagnostics["deferred"] = sum(1 for later in ordered[index:] if chosen(later["id"]))
                    self.summary["issues"].append({"reason": "FILES_DEFERRED", "count": diagnostics["deferred"]})
                    for later in ordered[index + 1:]:
                        if chosen(later["id"]):
                            audit[later["id"]].update(status="SELECTED_PENDING", reason="SYNC_BUDGET_EXHAUSTED", unread_cause="BUDGET_EXHAUSTED")
                        else:
                            audit[later["id"]].update(status="NOT_SELECTED_METADATA", reason=gate[later["id"]]["reason"])
                    break
            except Exception:
                entry.update(status="PARSE_FAILED", reason="REFERENCE_PROCESSING_FAILED", unread_cause="PARSE_FAILED")
                self.summary["issues"].append({"file_id": file_id, "reason": "REFERENCE_PROCESSING_FAILED", "unread_cause": "PARSE_FAILED"})

    def _access_detail(self, listed, fresh, problem):
        """Record the fields behind an access decision (IDs and flags only) for the run JSON."""
        details = self.summary["diagnostics"].setdefault("access_checks", [])
        if len(details) < 10:
            details.append({"file_id": listed.get("id"), "reason": problem,
                            "listed_parent": listed.get("listed_parent"),
                            "listed_parents": listed.get("parents"), "fresh_parents": fresh.get("parents"),
                            "fresh_trashed": fresh.get("trashed"),
                            "fresh_can_download": (fresh.get("capabilities") or {}).get("canDownload")})

    def select(
        self,
        text,
        limit=12,
        *,
        target_date=None,
        case_type=None,
        embedding_adapter=None,
        reranker_adapter=None,
        exclude_inapplicable=True,
    ):
        """Choose relevant files (text match plus folder/file-name bonus), then their best excerpts.

        Returns the decision log; `sources` is empty when nothing is relevant, and then the Drive
        library is not used for the document."""
        log = {"decision": "NOT_USED", "reason": "", "thresholds": relevance.thresholds(),
               "corpus_chunks": 0, "query_terms": [], "candidates": [], "files_selected": 0, "sources": []}
        # 관련 있어 보이는데 읽지 못한 파일이 있으면 '관련 자료 없음'으로 단정하지 않는다. 일부 쪽만 못 읽은
        # 파일(INDEXED_PARTIAL)은 이미 색인돼 대조에 들어갔으므로 미검토로 세지 않는다.
        pending = [item for item in self.summary.get("inventory", [])
                   if item["status"] not in ("INDEXED", "INDEXED_PARTIAL", "DUPLICATE_REUSED", "NOT_SELECTED_METADATA")
                   and (relevance.metadata_priority(item, text)["score"] > 0
                        or relevance.name_gate_passes(getattr(self, "_gate_weights", {}).get(item["file_id"], {}), text))]
        log["coverage"] = "INCOMPLETE_COVERAGE" if pending else "CHECKED_INDEXED_CORPUS"
        log["unreviewed_candidates"] = pending
        prose_eligible = {k: v for k, v in self.eligible.items() if not v.get("case_table_only")}
        if not prose_eligible:
            if pending:
                log["decision"] = "INCOMPLETE_COVERAGE"
            log["reason"] = "NO_ELIGIBLE_REFERENCE"
            return log
        mark = time.monotonic()
        total = sum(v.get("chunk_count") or 0 for v in prose_eligible.values())
        log["corpus_chunks"] = total
        scan_text = str(text or "")[:150000]
        counts = set(relevance.query_tokens(scan_text))
        names = relevance.name_weights(prose_eligible)
        priority_ids = sorted(k for k, v in prose_eligible.items() if relevance.priority_reference(v, scan_text))
        log["priority_references"] = [{"file_id": k, "title": prose_eligible[k].get("title"),
                                      "searched": False, "search_reason": "NOT_EXECUTED" if i < 12 else "SEARCH_LIMIT"}
                                     for i, k in enumerate(priority_ids)]
        interrupted_phases: list[str] = []
        retried_queries = 0
        partial_results = False
        rows: list[tuple] = []
        frequency: dict[str, int] = {}
        profiles: list = []
        profile: dict = {}
        present: list[str] = []

        def _is_interrupted(exc: Exception) -> bool:
            return "interrupted" in str(exc).lower()

        with self.connect() as db:
            deadline = time.monotonic() + 5
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
            terms = sorted(counts)
            try:
                for offset in range(0, len(terms), 500):
                    batch = terms[offset:offset + 500]
                    frequency.update(db.execute("SELECT term, doc FROM chunk_terms WHERE term IN ("
                                                + ",".join("?" for _ in batch) + ")", batch).fetchall())
            except Exception as exc:
                if not _is_interrupted(exc):
                    raise
                interrupted_phases.append("term_frequency")
                partial_results = True
                retried_queries += 1
                deadline = time.monotonic() + 2
                try:
                    for offset in range(0, min(len(terms), 250), 250):
                        batch = terms[offset:offset + 250]
                        frequency.update(db.execute("SELECT term, doc FROM chunk_terms WHERE term IN ("
                                                    + ",".join("?" for _ in batch) + ")", batch).fetchall())
                except Exception as retry_exc:
                    if not _is_interrupted(retry_exc):
                        raise
                    interrupted_phases.append("term_frequency_retry")

            profiles = relevance.query_profiles(scan_text, frequency, total)
            profile = profiles[0]
            # Round-robin window terms keeps one issue from consuming the query budget.
            present = list(dict.fromkeys(t for rank in range(relevance.QUERY_TERMS)
                for p in profiles for t in list(p)[rank:rank + 1] if t in frequency))[:240]
            log["query_windows"] = len(profiles) - 1
            log["topic_window_chars"] = relevance.TOPIC_WINDOW
            log["topic_step_chars"] = relevance.TOPIC_STEP
            log["query_terms"] = [{"term": t, "weight": round(profile[t], 3), "chunks": frequency.get(t, 0)}
                                  for t in list(profile)[:20] if t in frequency]
            if not present:
                if pending or interrupted_phases:
                    log["decision"] = "INCOMPLETE_COVERAGE"
                if interrupted_phases:
                    log["coverage"] = "INCOMPLETE_COVERAGE"
                    log["search_interrupted"] = True
                    log["reason"] = "SQLITE_QUERY_INTERRUPTED"
                else:
                    log["reason"] = "NO_SHARED_KEY_TERMS"
                for item in log["priority_references"]:
                    item["search_reason"] = "SQLITE_QUERY_INTERRUPTED" if interrupted_phases else "NO_SHARED_KEY_TERMS"
                log["ms"] = round((time.monotonic() - mark) * 1000)
                log["search_diagnostics"] = {
                    "query_kind": "document_select",
                    "ms": log["ms"],
                    "candidate_chunks": 0,
                    "interrupted": bool(interrupted_phases),
                    "interrupted_phases": interrupted_phases,
                    "retried_queries": retried_queries,
                    "partial_results": partial_results,
                    "incomplete_reason": "SQLITE_QUERY_INTERRUPTED" if interrupted_phases else None,
                }
                return log

            db.execute("CREATE TEMP TABLE eligible (id TEXT PRIMARY KEY, revision TEXT)")
            db.executemany("INSERT INTO eligible VALUES (?,?)", [(k, v["revision"]) for k, v in prose_eligible.items()])
            try:
                rows = db.execute("SELECT file_id, page, start, text, terms FROM chunks "
                    "JOIN eligible e ON e.id=chunks.file_id AND e.revision=chunks.revision "
                    "WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT ?",
                    (" OR ".join('"' + term + '"' for term in present), relevance.CANDIDATE_CHUNKS)).fetchall()
            except Exception as exc:
                if not _is_interrupted(exc):
                    raise
                interrupted_phases.append("main_fts")
                partial_results = True
                reduced_present = present[:40]
                if reduced_present:
                    retried_queries += 1
                    deadline = time.monotonic() + 2
                    try:
                        rows = db.execute("SELECT file_id, page, start, text, terms FROM chunks "
                            "JOIN eligible e ON e.id=chunks.file_id AND e.revision=chunks.revision "
                            "WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT ?",
                            (" OR ".join('"' + term + '"' for term in reduced_present), min(100, relevance.CANDIDATE_CHUNKS))).fetchall()
                    except Exception as retry_exc:
                        if not _is_interrupted(retry_exc):
                            raise
                        interrupted_phases.append("main_fts_retry")

            # 뒷부분 소수 쟁점이 전체 상위 300청크 밖으로 밀리지 않도록 구간별 보조 조회를 병행한다.
            if len(profiles) > 1:
                step_win = max(1, (len(profiles) - 1) // 16)
                for p_win in profiles[1::step_win][:16]:
                    if time.monotonic() >= deadline:
                        interrupted_phases.append("window_fts_budget")
                        partial_results = True
                        break
                    win_terms = [t for t in p_win if t in frequency][:24]
                    if not win_terms:
                        continue
                    try:
                        rows.extend(db.execute("SELECT file_id, page, start, text, terms FROM chunks "
                            "JOIN eligible e ON e.id=chunks.file_id AND e.revision=chunks.revision "
                            "WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT 25",
                            (" OR ".join('"' + term + '"' for term in win_terms),)).fetchall())
                    except Exception as exc:
                        if not _is_interrupted(exc):
                            raise
                        interrupted_phases.append("window_fts")
                        partial_results = True
                        break

            # A large, relevant casebook must not disappear behind the global top-chunk limit.
            for index, file_id in enumerate(priority_ids[:12]):
                if time.monotonic() >= deadline:
                    interrupted_phases.append("priority_fts_budget")
                    partial_results = True
                    for rem in log["priority_references"][index:12]:
                        rem["search_reason"] = "SEARCH_INTERRUPTED"
                    break
                try:
                    rows.extend(db.execute("SELECT file_id, page, start, text, terms FROM chunks "
                        "WHERE chunks MATCH ? AND file_id=? AND revision=? ORDER BY bm25(chunks) LIMIT 40",
                        (" OR ".join('"' + term + '"' for term in present[:80]), file_id,
                         prose_eligible[file_id]["revision"])).fetchall())
                    log["priority_references"][index].update(searched=True, search_reason="SEARCH_COMPLETED")
                except Exception as exc:
                    if not _is_interrupted(exc):
                        raise
                    interrupted_phases.append("priority_fts")
                    partial_results = True
                    for rem in log["priority_references"][index:12]:
                        rem["search_reason"] = "SEARCH_INTERRUPTED"
                    break

        if interrupted_phases:
            log["coverage"] = "INCOMPLETE_COVERAGE"
            log["decision"] = "INCOMPLETE_COVERAGE"
            log["search_interrupted"] = True
        log["search_diagnostics"] = {
            "query_kind": "document_select",
            "ms": round((time.monotonic() - mark) * 1000),
            "candidate_chunks": len(rows),
            "interrupted": bool(interrupted_phases),
            "interrupted_phases": interrupted_phases,
            "retried_queries": retried_queries,
            "partial_results": partial_results,
            "incomplete_reason": "SQLITE_QUERY_INTERRUPTED" if interrupted_phases else None,
        }
        # A short query cannot share more terms than it has.
        required = min(relevance.MIN_MATCHED_TERMS, len(profile))
        log["required_shared_terms"] = required
        files = {}
        for file_id, page, start, excerpt, terms in dict.fromkeys(rows):
            chunk_terms = set(terms.split())
            scores = [(*relevance.coverage(p, chunk_terms), index) for index, p in enumerate(profiles)]
            score, matched, window = max(scores, key=lambda s: (len(s[1]) >= required, s[0], len(s[1])))
            entry = files.setdefault(file_id, {"chunks": []})
            entry["chunks"].append((score, len(matched), int(page), int(start), excerpt, window))
        hybrid_enabled = bool(getattr(self.settings, "rag_hybrid_semantic", True))
        doc_stems = set(relevance.content_stems(scan_text, limit=80)) if hybrid_enabled else set()
        candidates = []
        for file_id, entry in files.items():
            source = self.eligible[file_id]
            name_score, name_hits = relevance.name_coverage(names.get(file_id, {}), counts)
            best = max(entry["chunks"], key=lambda c: (c[1] >= required and c[0] >= relevance.MIN_CHUNK_COVERAGE, c[0], c[1]))
            metadata_bonus = min(0.05, (source.get("metadata_score") or 0) / 1000)
            file_score = best[0] + relevance.META_WEIGHT * name_score + metadata_bonus
            sem_score = (relevance.local_semantic_score(scan_text[:6000], best[4], query_stems=doc_stems)
                         if hybrid_enabled else 0.0)
            reasons = []
            if best[1] < required:
                reasons.append("TOO_FEW_SHARED_TERMS")
            if best[0] < relevance.MIN_CHUNK_COVERAGE:
                reasons.append("LOW_TEXT_COVERAGE")
            # 파일명이 무관한 문서(name_score==0)라도 본문 적용 비율이 기준 이상이고 어간·의미 근접도가 높으면 탈락시키지 않는다.
            body_strong = best[0] >= relevance.MIN_CHUNK_COVERAGE and best[1] >= required and (
                best[0] >= 0.20 or sem_score >= 0.22
            )
            if file_score < relevance.MIN_FILE_SCORE and not body_strong:
                reasons.append("LOW_FILE_SCORE")
            candidates.append({"file_id": file_id, "title": source.get("title"), "folder_path": source.get("folder_path"),
                               "format": source.get("format") or relevance.source_format(
                                   source.get("title", ""), source.get("mime_type", "")),
                               "mime_type": source.get("mime_type", ""),
                               "page": int(best[2]), "start": int(best[3]),
                               "pages_matched": sorted({int(c[2]) for c in entry["chunks"]})[:20],
                               "text_coverage": round(best[0], 3), "shared_terms": best[1],
                               "name_coverage": round(name_score, 3), "name_terms": name_hits[:8],
                               "metadata_bonus": round(metadata_bonus, 3),
                               "semantic_score": round(sem_score, 3),
                               "matched_query_window": best[5],
                               "file_score": round(file_score, 3), "selected": not reasons, "rejected_because": reasons,
                               "_name": name_score, "_chunks": entry["chunks"]})
        candidates.sort(key=lambda c: (-c["file_score"], c["file_id"]))
        chosen = [c for c in candidates if c["selected"]]
        chunk_outcomes: dict[int, dict[str, Any]] = {}
        for candidate in candidates:
            fid_cand = candidate["file_id"]
            cand_chunks = sorted(
                candidate["_chunks"],
                key=lambda c: (
                    not (c[0] >= relevance.MIN_CHUNK_COVERAGE and c[1] >= required),
                    -c[0],
                    c[2],
                    c[3],
                ),
            )
            q_rank = 0
            for c in cand_chunks:
                is_qual = c[0] >= relevance.MIN_CHUNK_COVERAGE and c[1] >= required
                if is_qual:
                    q_rank += 1
                chunk_outcomes[id(c)] = {
                    "file_id": fid_cand,
                    "rank_in_file": q_rank if is_qual else None,
                    "page": int(c[2]),
                    "length": len(c[4]),
                    "text_coverage": round(c[0], 3),
                    "shared_terms": int(c[1]),
                    "qualified": is_qual,
                    "delivered": False,
                    "source_id": None,
                    "drop_reason": (
                        "BELOW_THRESHOLD"
                        if not is_qual
                        else ("FILE_NOT_QUALIFIED" if not candidate["selected"] else None)
                    ),
                }

        excerpts = []
        for candidate in chosen:
            qual_sorted = sorted(
                (c for c in candidate["_chunks"]
                 if c[0] >= relevance.MIN_CHUNK_COVERAGE and c[1] >= required),
                key=lambda c: (-c[0], c[2], c[3]),
            )
            usable = qual_sorted[:relevance.PER_FILE_EXCERPTS]
            for c in qual_sorted[relevance.PER_FILE_EXCERPTS:]:
                chunk_outcomes[id(c)]["drop_reason"] = "EXCEEDED_PER_FILE_EXCERPTS"
            excerpts.extend((c[0] + relevance.META_WEIGHT * candidate["_name"] + candidate["metadata_bonus"],
                             candidate["file_id"], c) for c in usable)
        excerpts.sort(key=lambda e: (-e[0], e[1], e[2][2], e[2][3]))
        reserved, reserved_ids = [], set()
        for excerpt in excerpts:
            if excerpt[1] in priority_ids[:12] and excerpt[1] not in reserved_ids:
                reserved.append(excerpt)
                reserved_ids.add(excerpt[1])
        excerpts = reserved + [e for e in excerpts if e not in reserved]
        result, seen_exact = [], set()
        seen_fp: dict[str, str] = {}
        per_file_picked: dict[str, int] = {}
        per_base_picked: dict[str, int] = {}
        leftover_unique, leftover_dup = [], []
        dup_suppressed = 0

        def _append_excerpt(score_val, fid_val, chunk_tuple, *, duplicate_of: str = ""):
            coverage_val, shared_val, page_val, start_val, text_val, window_val = chunk_tuple
            src_meta = self.eligible[fid_val]
            fp_val = relevance.content_fingerprint(text_val)
            sid = "R" + str(len(result) + 1)
            item_dict = {
                **src_meta,
                "format": src_meta.get("format") or relevance.source_format(
                    src_meta.get("title", ""), src_meta.get("mime_type", "")),
                "source_id": sid,
                "page": page_val,
                "start": start_val,
                "text": text_val,
                "relevance": round(score_val, 3),
                "text_coverage": round(coverage_val, 3),
                "shared_terms": shared_val,
                "matched_query_window": window_val,
                "content_fingerprint": fp_val,
            }
            if duplicate_of:
                item_dict["duplicate_content"] = True
                item_dict["duplicate_of_source_id"] = duplicate_of
            result.append(item_dict)
            outcome = chunk_outcomes.get(id(chunk_tuple))
            if outcome is not None:
                outcome["delivered"] = True
                outcome["source_id"] = sid
                outcome["drop_reason"] = None
            return sid, fp_val

        # 1차 패스: 서로 다른 내용(content_fingerprint)·파일명 묶음·파일에 각 1슬롯씩 먼저 배정해 중복 청크 독점 차단
        pass1_visited = 0
        for score, file_id, chunk in excerpts:
            pass1_visited += 1
            excerpt = chunk[4]
            digest = hashlib.sha256(excerpt.encode()).hexdigest()
            if digest in seen_exact:
                dup_suppressed += 1
                chunk_outcomes[id(chunk)]["drop_reason"] = "DUPLICATE_FINGERPRINT_SUPPRESSED"
                continue
            seen_exact.add(digest)
            fp = relevance.content_fingerprint(excerpt)
            src_meta = self.eligible[file_id]
            base_key = (src_meta.get("base_name")
                        or relevance.base_name(src_meta.get("title", "")).lower()
                        or file_id)
            if fp and fp in seen_fp:
                dup_suppressed += 1
                chunk_outcomes[id(chunk)]["drop_reason"] = "DUPLICATE_FINGERPRINT_SUPPRESSED"
                leftover_dup.append((score, file_id, chunk, fp))
                continue
            if per_file_picked.get(file_id, 0) >= 1 or per_base_picked.get(base_key, 0) >= 1:
                leftover_unique.append((score, file_id, chunk, fp))
                continue
            sid, fp_val = _append_excerpt(score, file_id, chunk)
            if fp_val:
                seen_fp.setdefault(fp_val, sid)
            per_file_picked[file_id] = per_file_picked.get(file_id, 0) + 1
            per_base_picked[base_key] = per_base_picked.get(base_key, 0) + 1
            if limit is not None and len(result) >= limit:
                break
        for _score, _fid, rem_chunk in excerpts[pass1_visited:]:
            if chunk_outcomes[id(rem_chunk)]["drop_reason"] is None:
                chunk_outcomes[id(rem_chunk)]["drop_reason"] = "GLOBAL_LIMIT_REACHED"

        # 2차 패스: 고유 내용 추가 청크 채우기
        if limit is None or len(result) < limit:
            pass2_visited = 0
            for score, file_id, chunk, fp in leftover_unique:
                pass2_visited += 1
                if fp and fp in seen_fp:
                    dup_suppressed += 1
                    chunk_outcomes[id(chunk)]["drop_reason"] = "DUPLICATE_FINGERPRINT_SUPPRESSED"
                    leftover_dup.append((score, file_id, chunk, fp))
                    continue
                sid, fp_val = _append_excerpt(score, file_id, chunk)
                if fp_val:
                    seen_fp.setdefault(fp_val, sid)
                if limit is not None and len(result) >= limit:
                    break
            for _score, _fid, rem_chunk, _fp in leftover_unique[pass2_visited:]:
                if chunk_outcomes[id(rem_chunk)]["drop_reason"] is None:
                    chunk_outcomes[id(rem_chunk)]["drop_reason"] = "GLOBAL_LIMIT_REACHED"
        else:
            for _score, _fid, rem_chunk, _fp in leftover_unique:
                if chunk_outcomes[id(rem_chunk)]["drop_reason"] is None:
                    chunk_outcomes[id(rem_chunk)]["drop_reason"] = "GLOBAL_LIMIT_REACHED"

        # 3차 패스: 슬롯이 아직 남았을 때만 타 형식 중복 청크를 보조 기록으로 포함(출처 표기 포함)
        if limit is None or len(result) < limit:
            for score, file_id, chunk, fp in leftover_dup:
                _append_excerpt(score, file_id, chunk, duplicate_of=seen_fp.get(fp, ""))
                if limit is not None and len(result) >= limit:
                    break

        selected_ids = {s["file_id"] for s in result}
        drop_reason_counts: dict[str, int] = {}
        file_obs_list = []
        delivered_obs_by_sid: dict[str, dict[str, Any]] = {}
        file_index_by_id = {c["file_id"]: idx for idx, c in enumerate(candidates)}
        for idx, candidate in enumerate(candidates):
            cand_chunks = sorted(
                candidate["_chunks"],
                key=lambda c: (
                    not (c[0] >= relevance.MIN_CHUNK_COVERAGE and c[1] >= required),
                    -c[0],
                    c[2],
                    c[3],
                ),
            )
            lengths = sorted(len(c[4]) for c in cand_chunks)
            n_len = len(lengths)
            if n_len == 0:
                dist = {"min": 0, "median": 0, "max": 0}
            elif n_len % 2 == 1:
                dist = {"min": lengths[0], "median": lengths[n_len // 2], "max": lengths[-1]}
            else:
                med = (lengths[n_len // 2 - 1] + lengths[n_len // 2]) / 2
                dist = {"min": lengths[0], "median": int(med) if med.is_integer() else med, "max": lengths[-1]}
            chunk_entries = []
            qual_count = 0
            below_count = 0
            for c in cand_chunks:
                o = chunk_outcomes[id(c)]
                if o["qualified"]:
                    qual_count += 1
                else:
                    below_count += 1
                if o["drop_reason"]:
                    drop_reason_counts[o["drop_reason"]] = drop_reason_counts.get(o["drop_reason"], 0) + 1
                entry_public = {
                    "rank_in_file": o["rank_in_file"],
                    "page": o["page"],
                    "length": o["length"],
                    "text_coverage": o["text_coverage"],
                    "shared_terms": o["shared_terms"],
                    "qualified": o["qualified"],
                    "delivered": o["delivered"],
                    "source_id": o["source_id"],
                    "drop_reason": o["drop_reason"],
                }
                chunk_entries.append(entry_public)
                if o["delivered"] and o["source_id"]:
                    delivered_obs_by_sid[o["source_id"]] = {
                        "source_id": o["source_id"],
                        "file_index": idx,
                        "rank_in_file": o["rank_in_file"],
                        "page": o["page"],
                        "length": o["length"],
                        "text_coverage": o["text_coverage"],
                        "shared_terms": o["shared_terms"],
                    }
            file_obs_list.append({
                "file_index": idx,
                "qualified": bool(candidate["selected"]),
                "selected": candidate["file_id"] in selected_ids,
                "candidate_chunks_total": len(cand_chunks),
                "qualified_chunks_count": qual_count,
                "below_threshold_chunks_count": below_count,
                "chunk_length_distribution": dist,
                "chunks": chunk_entries,
            })

        delivered_excerpts_obs = []
        for s in result:
            sid = s["source_id"]
            d_obs = dict(delivered_obs_by_sid.get(sid, {"source_id": sid}))
            f_idx = d_obs.get("file_index", file_index_by_id.get(s["file_id"]))
            d_len = d_obs.get("length", len(s.get("text") or ""))
            longer_dropped = []
            if f_idx is not None and 0 <= f_idx < len(file_obs_list):
                longer_dropped = [
                    {
                        "rank_in_file": ce["rank_in_file"],
                        "page": ce["page"],
                        "length": ce["length"],
                        "text_coverage": ce["text_coverage"],
                        "shared_terms": ce["shared_terms"],
                        "drop_reason": ce["drop_reason"],
                    }
                    for ce in file_obs_list[f_idx]["chunks"]
                    if not ce["delivered"] and ce["length"] > d_len
                ]
            d_obs["duplicate_content"] = bool(s.get("duplicate_content"))
            d_obs["longer_dropped_chunks_in_file"] = longer_dropped
            delivered_excerpts_obs.append(d_obs)

        for candidate in candidates:
            candidate.pop("_name"), candidate.pop("_chunks")
        log["candidates"] = candidates
        log["candidates_total"] = len(candidates)
        log["files_qualified"] = len(chosen)
        log["duplicate_chunks_suppressed"] = dup_suppressed
        log["files_selected"] = len(selected_ids)
        for candidate in candidates:
            candidate["qualified"] = candidate["selected"]
            candidate["selected"] = candidate["file_id"] in selected_ids
            if candidate["qualified"] and not candidate["selected"]:
                candidate["rejected_because"] = ["EXCERPT_BUDGET_OR_DUPLICATE"]
        for item in log["priority_references"]:
            item["selected"] = item["file_id"] in selected_ids
        log["excerpt_selection_observability"] = {
            "candidate_files_total": len(candidates),
            "selected_files_count": len(selected_ids),
            "delivered_excerpts_count": len(result),
            "per_file_excerpts_cap": relevance.PER_FILE_EXCERPTS,
            "global_limit": limit,
            "drop_reason_counts": drop_reason_counts,
            "delivered_excerpts": delivered_excerpts_obs,
            "files": file_obs_list,
        }
        from packages.rag_engine.applicability_filter import annotate_applicability
        from packages.rag_engine.hybrid_retriever import build_rag_adapters_from_env, retrieve_hybrid_chunks

        env_diag: dict[str, Any] = {}
        if embedding_adapter is None and reranker_adapter is None:
            embedding_adapter, reranker_adapter, env_diag = build_rag_adapters_from_env(
                allow_network=bool(getattr(self.settings, "allow_network", False))
            )

        retrieval_mode = "LEXICAL_ONLY"
        retrieval_warnings: list[str] = []
        retrieval_telemetry: dict[str, Any] = {
            "effective_mode": "LEXICAL_ONLY",
            "embedding_requests": 0,
            "embedding_successes": 0,
            "embedding_failures": 0,
            "reranker_requests": 0,
            "reranker_successes": 0,
            "reranker_failures": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "fallback_reasons": list(
                env_diag.get("fallback_reasons")
                or ([env_diag["fallback_reason"]] if env_diag.get("fallback_reason") else [])
            ),
        }
        if result and (embedding_adapter is not None or reranker_adapter is not None):
            hybrid_input = [
                {**s, "chunk_id": s.get("source_id") or f"R{idx + 1}"}
                for idx, s in enumerate(result)
            ]
            emb_model_key = str(getattr(embedding_adapter, "model", "") or getattr(embedding_adapter, "name", "default"))
            cached_vectors: dict[str, list[float]] = {}
            chunk_meta_by_cid: dict[str, tuple[str, str, int, int]] = {}
            if embedding_adapter is not None and getattr(embedding_adapter, "available", False):
                for ch in hybrid_input:
                    fid = str(ch.get("file_id") or "")
                    rev = str((self.eligible.get(fid) or {}).get("revision") or "")
                    pg = int(ch.get("page") or 0)
                    st = int(ch.get("start") or 0)
                    cid = str(ch.get("chunk_id") or "")
                    if fid and rev and cid:
                        chunk_meta_by_cid[cid] = (fid, rev, pg, st)
                if chunk_meta_by_cid:
                    try:
                        with self.connect() as db:
                            for cid, (fid, rev, pg, st) in chunk_meta_by_cid.items():
                                row_vec = db.execute(
                                    "SELECT vector_json FROM chunk_embeddings "
                                    "WHERE file_id=? AND revision=? AND page=? AND start=? AND model=?",
                                    (fid, rev, pg, st, emb_model_key),
                                ).fetchone()
                                if row_vec and row_vec[0]:
                                    cached_vectors[cid] = json.loads(row_vec[0])
                    except Exception:
                        cached_vectors = {}
            hybrid_out = retrieve_hybrid_chunks(
                scan_text[:6000],
                hybrid_input,
                embedding_adapter=embedding_adapter,
                reranker_adapter=reranker_adapter,
                chunk_vectors=cached_vectors,
                target_date=target_date,
                case_type=case_type,
                exclude_inapplicable=False,
                top_k=len(hybrid_input),
            )
            computed_vecs = hybrid_out.get("computed_chunk_vectors") or {}
            if computed_vecs and chunk_meta_by_cid:
                try:
                    with self.connect() as db:
                        db.executemany(
                            "INSERT OR REPLACE INTO chunk_embeddings (file_id, revision, page, start, model, vector_json) "
                            "VALUES (?,?,?,?,?,?)",
                            [
                                (*chunk_meta_by_cid[cid], emb_model_key, json.dumps(vec))
                                for cid, vec in computed_vecs.items()
                                if cid in chunk_meta_by_cid and vec
                            ],
                        )
                        db.commit()
                except Exception:
                    pass
            retrieval_mode = hybrid_out["retrieval_mode"]
            retrieval_warnings = hybrid_out["retrieval_warnings"]
            retrieval_telemetry = hybrid_out.get("retrieval_telemetry") or retrieval_telemetry
            result = hybrid_out["chunks"]
        else:
            result = annotate_applicability(
                result,
                target_date=target_date,
                case_type=case_type,
                exclude_inapplicable=False,
            )

        inapplicable = [s for s in result if not s.get("eligible_for_support", True)]
        applicability_warnings = [
            {
                "source_id": s.get("source_id"),
                "file_id": s.get("file_id"),
                "title": s.get("title"),
                "warnings": s.get("applicability_warnings") or [],
                "reasons": s.get("applicability_reasons") or [],
            }
            for s in inapplicable
        ]
        if exclude_inapplicable and inapplicable:
            result = [s for s in result if s.get("eligible_for_support", True)]

        log["retrieval_mode"] = retrieval_mode
        log["retrieval_warnings"] = retrieval_warnings
        log["retrieval_telemetry"] = retrieval_telemetry
        log["applicability_warnings"] = applicability_warnings
        log["inapplicable_sources"] = inapplicable
        log["sources"] = result
        log["decision"] = "USED" if result else "INCOMPLETE_COVERAGE" if (pending or interrupted_phases) else "NOT_USED"
        if result:
            log["reason"] = "RELEVANT_REFERENCE_FOUND"
        elif inapplicable:
            log["reason"] = "NO_APPLICABLE_REFERENCE"
        else:
            log["reason"] = "NO_CANDIDATE_CHUNK" if not candidates else "BELOW_RELEVANCE_THRESHOLD"
        log["ms"] = round((time.monotonic() - mark) * 1000)
        return log

    def search(self, text, limit=12):
        return self.select(text, limit)["sources"]

    def search_citation(self, citation, limit=12):
        """Local exact-identifier search independent of whole-document top 12.

        Only the current eligible revision is read. Editorial case tables retain
        their separate metadata path and cannot supply SUPPORTS here.
        """
        import re as _re

        from .reference_binding import anchor_of, citation_excerpt, identifier

        ident = identifier(citation)
        if not ident:
            return []
        eligible = {file_id: meta for file_id, meta in self.eligible.items()
                    if not (meta.get("structured_case_table") or meta.get("case_table_only"))}
        if not eligible:
            return []
        # 사전 추출된 식별자 색인(chunk_identifiers)이 모든 대상 파일에 준비되어 있으면 B-Tree 인덱스로 즉시 조회한다.
        # (미색인 캐시가 섞여 있을 때만 기존 instr(text, digits) 전체 스캔으로 폴백한다.)
        lookup = _citation_lookup_key(ident)
        all_indexed = all(bool(meta.get("identifier_indexed")) for meta in eligible.values())
        found = []
        with self.connect() as db:
            if lookup and all_indexed:
                rows = db.execute(
                    "SELECT c.file_id, c.revision, c.page, c.start, c.text "
                    "FROM chunk_identifiers idx "
                    "JOIN chunks c ON c.rowid = idx.chunk_rowid "
                    "WHERE idx.ident_kind = ? AND idx.ident_key = ?",
                    lookup,
                ).fetchall()
            else:
                digits = max(_re.findall(r"[0-9]+", anchor_of(ident)), key=len, default="")
                rows = db.execute("SELECT file_id, revision, page, start, text FROM chunks WHERE instr(text, ?) > 0",
                                  (digits,)).fetchall()
        for file_id, revision, page, start, text in sorted(rows, key=lambda r: (r[0], int(r[2]), int(r[3]))):
            meta = eligible.get(file_id)
            if not meta or revision != meta["revision"]:
                continue
            excerpt = citation_excerpt(citation, text)
            if not excerpt:
                continue
            found.append({
                **meta,
                "file_id": file_id,
                "format": meta.get("format") or relevance.source_format(
                    meta.get("title", ""), meta.get("mime_type", "")),
                "page": int(page),
                "start": int(start) + text.index(excerpt),
                "text": excerpt,
                "content_fingerprint": relevance.content_fingerprint(excerpt),
            })
            if len(found) >= limit:
                return found
        return found

    def search_claim(self, claim_text: str, *, citations=None, limit: int = 5) -> list[dict]:
        """주장 단위 다중 경로 검색(식별자·어간/FTS5·로컬 하이브리드 유사도 + 다양성·인접 문맥 결합).

        항상 현재 실행의 self.eligible (file_id, revision)으로만 제한되어 삭제·철회·격리 문서는 제외한다.
        """
        query = str(claim_text or "").strip()
        if not query and not citations:
            return []
        prose_eligible = {
            fid: meta for fid, meta in self.eligible.items()
            if not (meta.get("structured_case_table") or meta.get("case_table_only"))
        }
        if not prose_eligible:
            return []

        hybrid_enabled = bool(getattr(self.settings, "rag_hybrid_semantic", True))
        identifiers = relevance.extract_identifiers(query, citations=citations)
        stems = relevance.content_stems(query, limit=24)
        stems_set = set(stems)
        q_tokens = list(dict.fromkeys(relevance.tokens(relevance.query_text(query))))[:48]
        q_token_set = set(q_tokens)

        candidates: dict[tuple[str, int, int], dict] = {}

        def _register(fid: str, page: int, start: int, text: str, path_name: str, *,
                      exact: bool = False, fts_rank: int | None = None, c_terms: set[str] | None = None):
            meta = prose_eligible.get(fid)
            if not meta:
                return
            key = (fid, int(page), int(start))
            entry = candidates.get(key)
            if entry is None:
                entry = {
                    "file_id": fid, "page": int(page), "start": int(start), "text": text,
                    "paths": set(), "exact": False, "fts_rank": None, "c_terms": c_terms,
                }
                candidates[key] = entry
            entry["paths"].add(path_name)
            if exact:
                entry["exact"] = True
            if fts_rank is not None and (entry["fts_rank"] is None or fts_rank < entry["fts_rank"]):
                entry["fts_rank"] = fts_rank

        # 경로 1: 사건번호 및 법령명+조문 정확 식별자 조회
        cit_list = list(citations or [])
        for num in identifiers.get("case_numbers", []):
            cit_list.append({"case_number": num, "raw_text": num})
        for lname, art in identifiers.get("law_articles", []):
            cit_list.append({"law_name": lname, "article": art, "raw_text": f"{lname} {art}"})
        seen_cits = set()
        for cit in cit_list:
            from .reference_binding import identifier as _ident
            ident = _ident(cit)
            if not ident or ident in seen_cits:
                continue
            seen_cits.add(ident)
            for hit in self.search_citation(cit, limit=limit):
                _register(hit["file_id"], hit["page"], hit["start"], hit["text"],
                          "EXACT_IDENTIFIER", exact=True)

        # 경로 2: 한국어 어간 + 2-gram FTS5 검색 (+ 필요 시 로컬 하이브리드 폴백)
        claim_mark = time.monotonic()
        claim_interrupted_phases: list[str] = []
        claim_retried = 0
        claim_partial = False

        def _is_claim_interrupted(exc: Exception) -> bool:
            return "interrupted" in str(exc).lower()

        with self.connect() as db:
            deadline = time.monotonic() + 3
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
            db.execute("CREATE TEMP TABLE IF NOT EXISTS claim_eligible (id TEXT PRIMARY KEY, revision TEXT)")
            db.execute("DELETE FROM claim_eligible")
            db.executemany("INSERT INTO claim_eligible VALUES (?,?)",
                           [(k, v["revision"]) for k, v in prose_eligible.items()])

            if q_tokens:
                fts_rows: list[tuple] = []
                try:
                    fts_rows = db.execute(
                        "SELECT c.file_id, c.page, c.start, c.text, c.terms FROM chunks c "
                        "JOIN claim_eligible e ON e.id=c.file_id AND e.revision=c.revision "
                        "WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT 60",
                        (" OR ".join('"' + t + '"' for t in q_tokens),),
                    ).fetchall()
                except Exception as exc:
                    if not _is_claim_interrupted(exc):
                        raise
                    claim_interrupted_phases.append("claim_fts")
                    claim_partial = True
                    reduced_tokens = q_tokens[:16]
                    if reduced_tokens:
                        claim_retried += 1
                        deadline = time.monotonic() + 1.5
                        try:
                            fts_rows = db.execute(
                                "SELECT c.file_id, c.page, c.start, c.text, c.terms FROM chunks c "
                                "JOIN claim_eligible e ON e.id=c.file_id AND e.revision=c.revision "
                                "WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT 20",
                                (" OR ".join('"' + t + '"' for t in reduced_tokens),),
                            ).fetchall()
                        except Exception as retry_exc:
                            if not _is_claim_interrupted(retry_exc):
                                raise
                            claim_interrupted_phases.append("claim_fts_retry")
                for rank_idx, (fid, page, start, ctext, cterms) in enumerate(fts_rows):
                    _register(fid, int(page), int(start), ctext, "LEXICAL_STEM_FTS",
                              fts_rank=rank_idx, c_terms=set(cterms.split()))

            stem_probes = [s for s in stems if len(s) >= 2][:10]
            if stem_probes and time.monotonic() < deadline:
                where_clause = " OR ".join("instr(c.text, ?) > 0" for _ in stem_probes)
                stem_rows: list[tuple] = []
                try:
                    stem_rows = db.execute(
                        f"SELECT c.file_id, c.page, c.start, c.text, c.terms FROM chunks c "
                        f"JOIN claim_eligible e ON e.id=c.file_id AND e.revision=c.revision "
                        f"WHERE ({where_clause}) LIMIT 80",
                        stem_probes,
                    ).fetchall()
                except Exception as exc:
                    if not _is_claim_interrupted(exc):
                        raise
                    claim_interrupted_phases.append("claim_stem_scan")
                    claim_partial = True
                    if not candidates and stem_probes[:3]:
                        claim_retried += 1
                        deadline = time.monotonic() + 1.5
                        small_where = " OR ".join("instr(c.text, ?) > 0" for _ in stem_probes[:3])
                        try:
                            stem_rows = db.execute(
                                f"SELECT c.file_id, c.page, c.start, c.text, c.terms FROM chunks c "
                                f"JOIN claim_eligible e ON e.id=c.file_id AND e.revision=c.revision "
                                f"WHERE ({small_where}) LIMIT 20",
                                stem_probes[:3],
                            ).fetchall()
                        except Exception as retry_exc:
                            if not _is_claim_interrupted(retry_exc):
                                raise
                            claim_interrupted_phases.append("claim_stem_scan_retry")
                for fid, page, start, ctext, cterms in stem_rows:
                    _register(fid, int(page), int(start), ctext, "LEXICAL_STEM_FTS",
                              c_terms=set(cterms.split()))
            elif stem_probes and time.monotonic() >= deadline:
                claim_interrupted_phases.append("claim_stem_scan_budget")
                claim_partial = True

            # 경로 3 보충: 표현이 크게 달라 어휘 겹침 후보가 적을 때 현재 유효 청크 일부를 의미 유사도로 직접 탐색
            if hybrid_enabled and len(candidates) < 12 and (stems or q_tokens) and time.monotonic() < deadline:
                try:
                    scan_rows = db.execute(
                        "SELECT c.file_id, c.page, c.start, c.text, c.terms FROM chunks c "
                        "JOIN claim_eligible e ON e.id=c.file_id AND e.revision=c.revision LIMIT 120"
                    ).fetchall()
                    for fid, page, start, ctext, cterms in scan_rows:
                        key = (fid, int(page), int(start))
                        if key in candidates:
                            continue
                        c_stems = set(relevance.content_stems(ctext, limit=80))
                        sem = relevance.local_semantic_score(query, ctext, query_stems=stems_set, candidate_stems=c_stems)
                        if sem >= 0.24:
                            _register(fid, int(page), int(start), ctext, "HYBRID_SEMANTIC",
                                      c_terms=set(cterms.split()))
                except Exception as exc:
                    if not _is_claim_interrupted(exc):
                        raise
                    claim_interrupted_phases.append("claim_hybrid_scan")
                    claim_partial = True

        self._last_claim_search_diag = {
            "query_kind": "claim_search",
            "ms": round((time.monotonic() - claim_mark) * 1000),
            "candidate_count": len(candidates),
            "interrupted": bool(claim_interrupted_phases),
            "interrupted_phases": claim_interrupted_phases,
            "retried_queries": claim_retried,
            "partial_results": claim_partial,
            "incomplete_reason": "SQLITE_QUERY_INTERRUPTED" if claim_interrupted_phases else None,
        }
        if not candidates:
            return []

        scored = []
        law_names = identifiers.get("law_names", [])
        for cand in candidates.values():
            ctext = cand["text"]
            meta = prose_eligible[cand["file_id"]]
            c_stems = set(relevance.content_stems(ctext, limit=80))
            stem_hits = [s for s in stems if s in ctext or s in c_stems]
            bigram_hits = len(q_token_set & (cand["c_terms"] or set(relevance.tokens(ctext))))
            sem = (relevance.local_semantic_score(query, ctext, query_stems=stems_set, candidate_stems=c_stems)
                   if hybrid_enabled else 0.0)
            law_hit = any(ln in ctext for ln in law_names)
            qualified = (
                cand["exact"]
                or (len(stems) >= 2 and len(stem_hits) >= 2)
                or (len(stems) == 1 and len(stem_hits) == 1)
                or (law_hit and len(stem_hits) >= 1)
                or (hybrid_enabled and sem >= 0.24 and (len(stem_hits) >= 1 or bigram_hits >= 3))
            )
            if not qualified:
                continue
            if hybrid_enabled and sem >= 0.20:
                cand["paths"].add("HYBRID_SEMANTIC")
            stem_ratio = len(stem_hits) / max(1, len(stems)) if stems else 0.0
            rrf = (1.0 / (20 + cand["fts_rank"])) if cand["fts_rank"] is not None else 0.0
            meta_bonus = min(0.05, (meta.get("metadata_score") or 0) / 1000)
            score = (
                (2.0 if cand["exact"] else 0.0)
                + 0.45 * stem_ratio
                + 0.08 * min(5, len(stem_hits))
                + 0.45 * sem
                + 0.35 * rrf
                + meta_bonus
            )
            cand["score"] = round(score, 4)
            cand["semantic_score"] = sem
            cand["stem_hits"] = len(stem_hits)
            scored.append(cand)

        scored.sort(key=lambda c: (-c["score"], c["file_id"], c["page"], c["start"]))

        # 동일 내용(다형식)·동일 파일명 묶음·동일 파일의 후보 독점 방지 (1: 다양성, 2: 고유 추가 청크, 3: 잔여 중복)
        picked = []
        seen_keys: set[tuple[str, int, int]] = set()
        seen_fp: dict[str, tuple[str, int, int]] = {}
        per_file: dict[str, int] = {}
        per_base: dict[str, int] = {}
        leftover_unique = []
        leftover_dup = []

        def _cand_key(c):
            return (c["file_id"], c["page"], c["start"])

        for cand in scored:
            fid = cand["file_id"]
            meta = prose_eligible[fid]
            base_key = (meta.get("base_name")
                        or relevance.base_name(meta.get("title", "")).lower()
                        or fid)
            fp = relevance.content_fingerprint(cand["text"])
            cand["_fp"] = fp
            cand["_base_key"] = base_key
            if fp and fp in seen_fp:
                cand["_duplicate_of_file_id"] = seen_fp[fp][0]
                leftover_dup.append(cand)
                continue
            if per_file.get(fid, 0) >= 1 or per_base.get(base_key, 0) >= 1:
                leftover_unique.append(cand)
                continue
            cand["_duplicate_of_file_id"] = ""
            picked.append(cand)
            seen_keys.add(_cand_key(cand))
            if fp:
                seen_fp.setdefault(fp, _cand_key(cand))
            per_file[fid] = per_file.get(fid, 0) + 1
            per_base[base_key] = per_base.get(base_key, 0) + 1
            if len(picked) >= limit:
                break

        if len(picked) < limit:
            defer_unique = []
            for cand in leftover_unique:
                fp = cand["_fp"]
                fid = cand["file_id"]
                if fp and fp in seen_fp:
                    cand["_duplicate_of_file_id"] = seen_fp[fp][0]
                    leftover_dup.append(cand)
                    continue
                if per_file.get(fid, 0) < 2:
                    cand["_duplicate_of_file_id"] = ""
                    picked.append(cand)
                    seen_keys.add(_cand_key(cand))
                    if fp:
                        seen_fp.setdefault(fp, _cand_key(cand))
                    per_file[fid] = per_file.get(fid, 0) + 1
                    if len(picked) >= limit:
                        break
                else:
                    defer_unique.append(cand)
            if len(picked) < limit:
                for cand in defer_unique:
                    fp = cand["_fp"]
                    if fp and fp in seen_fp:
                        cand["_duplicate_of_file_id"] = seen_fp[fp][0]
                        leftover_dup.append(cand)
                        continue
                    cand["_duplicate_of_file_id"] = ""
                    picked.append(cand)
                    seen_keys.add(_cand_key(cand))
                    if fp:
                        seen_fp.setdefault(fp, _cand_key(cand))
                    if len(picked) >= limit:
                        break

        if len(picked) < limit:
            for cand in leftover_dup:
                if _cand_key(cand) in seen_keys:
                    continue
                picked.append(cand)
                seen_keys.add(_cand_key(cand))
                if len(picked) >= limit:
                    break

        # 인접 같은 (파일, 쪽) 청크 문맥 결합(문단 경계 절단 완화, review.py에서 800자 내로 발췌)
        results = []
        with self.connect() as db:
            for cand in picked[:limit]:
                fid = cand["file_id"]
                meta = prose_eligible[fid]
                text_out = cand["text"]
                if not cand["exact"]:
                    rev = meta["revision"]
                    nxt = db.execute(
                        "SELECT start, text FROM chunks WHERE file_id=? AND revision=? AND page=? AND start>? "
                        "ORDER BY start ASC LIMIT 1",
                        (fid, rev, cand["page"], cand["start"]),
                    ).fetchone()
                    if nxt and len(text_out) + len(nxt[1]) <= 2200:
                        text_out = text_out.rstrip() + "\n" + nxt[1].lstrip()
                fp_out = relevance.content_fingerprint(text_out) or cand.get("_fp", "")
                item = {
                    **meta,
                    "file_id": fid,
                    "format": meta.get("format") or relevance.source_format(
                        meta.get("title", ""), meta.get("mime_type", "")),
                    "mime_type": meta.get("mime_type", ""),
                    "source_id": "",
                    "page": cand["page"],
                    "start": cand["start"],
                    "text": text_out,
                    "relevance": cand["score"],
                    "semantic_score": cand["semantic_score"],
                    "retrieval_paths": sorted(cand["paths"]),
                    "claim_search_matched": True,
                    "content_fingerprint": fp_out,
                }
                if cand.get("_duplicate_of_file_id"):
                    item["duplicate_content"] = True
                    item["duplicate_of_file_id"] = cand["_duplicate_of_file_id"]
                results.append(item)
        return results

    def has_case_tables(self) -> bool:
        return any(v.get("structured_case_table") for v in self.eligible.values())

    def case_table_status(self) -> dict[str, Any]:
        """표 후보별 색인 상태 및 종합 판례표 상태를 반환한다 (TK-74 보완)."""
        inventory = self.summary.get("inventory", [])
        candidates = [item for item in inventory if is_case_table_candidate(item)]
        if not candidates:
            if self._case_rows():
                return {"status": "INDEXED", "candidates": [], "indexed_rows": len(self._case_rows())}
            return {"status": "NO_CASE_TABLE", "candidates": [], "indexed_rows": 0}

        cand_diagnostics = []
        has_indexed = False
        has_partial = False
        has_indexing = False
        has_quarantine = False
        has_failed = False
        total_indexed_rows = 0

        for c in candidates:
            fid = c.get("file_id")
            status = str(c.get("status") or "")
            reason = str(c.get("reason") or "")
            stats = c.get("case_table_stats") or {}
            indexed = stats.get("indexed", 0)
            total_indexed_rows += indexed
            continuation = bool(c.get("continuation"))

            diag = {
                "file_id": fid,
                "name": c.get("name"),
                "status": status,
                "indexed_rows": indexed,
                "continuation": continuation,
                "reason": reason,
                "stats": stats,
            }
            cand_diagnostics.append(diag)

            if status == "INDEXED":
                if continuation:
                    has_partial = True
                    has_indexing = True
                else:
                    has_indexed = True
            elif status == "INDEXED_PARTIAL":
                has_partial = True
                if continuation:
                    has_indexing = True
            elif status == "SELECTED_PENDING" or "BUDGET" in reason or "INDEXING" in status:
                has_indexing = True
            elif status == "QUARANTINED" or "QUARANTINE" in reason:
                has_quarantine = True
            elif status == "NOT_A_CASE_TABLE" or reason == "NOT_A_CASE_TABLE":
                pass
            elif status in ("PARSE_FAILED", "UNAVAILABLE", "UNSUPPORTED_TYPE") or any(
                err in reason.upper() for err in ("TIMEOUT", "PARSE_FAILED", "PARSE_TIMEOUT", "EXTRACT_TIMEOUT", "EXTRACT_FAILED", "DOWNLOAD_FAILED", "UNAVAILABLE", "UNSUPPORTED")
            ):
                has_failed = True
            elif status == "NOT_SELECTED_METADATA":
                # 아직 검토되지 않은 후보
                has_indexing = True

        if total_indexed_rows == 0 and self._case_rows():
            total_indexed_rows = len(self._case_rows())
            if any(v.get("structured_case_table") for v in self.eligible.values()):
                has_indexed = True

        # 종합 상태 판정:
        # 1. 색인된 표가 있는 경우:
        #    - 격리, 실패/타임아웃, 예산 대기/진행 중, 부분 색인 중 하나라도 있으면 PARTIAL (완료 표+격리/실패 후보 구분)
        #    - 그렇지 않고 온전히 완료되었으면 INDEXED
        if (has_indexed or has_partial or total_indexed_rows > 0):
            if has_partial or has_indexing or has_quarantine or has_failed:
                overall = "PARTIAL"
            else:
                overall = "INDEXED"
        # 2. 색인된 표가 없는 경우:
        #    - 모든 후보가 판례표가 아님으로 확인되었으면 NO_CASE_TABLE
        #    - 격리 후보가 있으면 QUARANTINED
        #    - 진행 중/예산 대기 후보가 있으면 INDEXING
        #    - 읽기 실패/타임아웃 후보가 있으면 PARTIAL (완전 부재로 단정하지 않고 미검토 범위 구분)
        elif all(d["status"] == "NOT_A_CASE_TABLE" or d.get("reason") == "NOT_A_CASE_TABLE" for d in cand_diagnostics):
            overall = "NO_CASE_TABLE"
        elif has_quarantine and not has_indexing and not has_failed:
            overall = "QUARANTINED"
        elif has_indexing and not has_failed and not has_quarantine:
            overall = "INDEXING"
        else:
            # 실패/타임아웃이 있거나 여러 미완료 상태가 혼합된 경우 -> PARTIAL
            overall = "PARTIAL"

        return {
            "status": overall,
            "candidates": cand_diagnostics,
            "indexed_rows": total_indexed_rows,
        }

    def _case_rows(self) -> list[dict]:
        if self._case_rows_cache is not None:
            return self._case_rows_cache
        if not self.db_path.exists():
            return []
        try:
            with self.connect() as db:
                rows = db.execute("""SELECT record_id,file_id,revision,sheet,row_number,
                    source_cell_range,original_number,title,case_info,court,decision_date,
                    case_numbers,target_case_numbers,referenced_case_numbers,issue,facts,reason,holding,hyperlinks,quality_warnings,
                    case_head,indexed_text,raw_cells FROM case_rows""").fetchall()
        except sqlite3.Error:
            self._case_rows_cache = []
            self._case_number_index = {}
            return self._case_rows_cache
        fields = ("record_id", "file_id", "revision", "sheet", "row", "source_cell_range",
                  "original_number", "title", "case_info", "court", "decision_date",
                  "case_numbers", "target_case_numbers", "referenced_case_numbers", "issue", "facts", "reason", "holding", "hyperlinks",
                  "quality_warnings", "case_head", "indexed_text", "raw_cells")
        result = []
        for row in rows:
            item = dict(zip(fields, row))
            if item["file_id"] not in self.eligible:
                continue
            for key in ("case_numbers", "target_case_numbers", "referenced_case_numbers", "hyperlinks", "quality_warnings", "raw_cells"):
                try:
                    item[key] = json.loads(item[key] or "[]")
                except (TypeError, ValueError):
                    item[key] = []
            result.append(item)
        self._case_rows_cache = result
        self._case_number_index = {}
        for item in result:
            for number in item.get("target_case_numbers") or item.get("case_numbers") or []:
                key = str(number or "").replace(" ", "")
                if key:
                    self._case_number_index.setdefault(key, []).append(item)
        return result

    def match_case(self, citation) -> dict:
        """Exact lookup in the structured corpus; never changes official findings."""
        case_number = getattr(citation, "canonical_case_number", None) or getattr(citation, "case_number", None)
        court = getattr(citation, "court", None) or getattr(citation, "court_name", None)
        decision_date = getattr(citation, "decision_date", None) or getattr(citation, "date", None)
        if isinstance(citation, dict):
            case_number = case_number or citation.get("canonical_case_number") or citation.get("case_number")
            court = court or citation.get("court") or citation.get("court_name")
            decision_date = decision_date or citation.get("decision_date") or citation.get("date")
        self._case_rows()  # Populate the per-document exact-number index once.
        normalized = str(case_number or "").replace(" ", "")
        rows = self._case_number_index.get(normalized, []) if normalized else self._case_rows()
        return lookup_records(rows, normalized, court=court,
                              decision_date=str(decision_date or "") or None)

    def search_case_table(self, text: str, *, citations=None, limit: int = 5) -> list[dict]:
        """Claim-level search over every eligible case-table row.

        Holding/reason are ordered before the issue text so the existing
        request envelope receives the most probative editorial material first.
        """
        rows = self._case_rows()
        if not rows:
            return []
        exact_ids = set()
        for citation in citations or []:
            match = self.match_case(citation)
            if match.get("record_id"):
                exact_ids.add(match["record_id"])
            exact_ids.update(match.get("record_ids") or [])
        query = str(text or "")
        from .relevance import salient_words
        words = salient_words(query, limit=12)
        if not words:
            import re
            words = list(dict.fromkeys(re.findall(r"[가-힣]{2,}", query)))[:12]
        ranked = []
        for row in rows:
            hay = " ".join([row.get("title", ""), row.get("issue", ""), row.get("reason", ""),
                            row.get("holding", ""), row.get("facts", "")])
            score = (1000 if row.get("record_id") in exact_ids else 0) + sum(hay.count(w) for w in words)
            exact = row.get("record_id") in exact_ids
            if exact or score >= 2:
                ranked.append((score, row, exact))
        ranked.sort(key=lambda pair: (-pair[0], pair[1].get("file_id", ""), pair[1].get("row", 0)))
        result = []
        exact_ranked = [item for item in ranked if item[2]]
        related_ranked = [item for item in ranked if not item[2]][:max(0, limit - len(exact_ranked))]
        for _score, row, exact in (exact_ranked + related_ranked)[:limit]:
            source = self.eligible.get(row["file_id"], {})
            # One source item remains within the established 800-character
            # claim envelope; the review layer applies masking before use.
            holding = row.get("holding") or ""
            support = " | ".join(filter(None, [row.get("case_head"), holding, row.get("reason"), row.get("issue")]))
            result.append({
                **source,
                "format": source.get("format") or relevance.source_format(
                    source.get("title", ""), source.get("mime_type", "")),
                "mime_type": source.get("mime_type", ""),
                "source_id": "",
                "text": support[:800],
                "page": row.get("row", 1),
                "relevance": _score,
                "structured_case_table": exact,
                "case_table_candidate": True,
                "case_record_id": row.get("record_id"),
                "case_head": row.get("case_head"),
                "sheet": row.get("sheet"),
                "row": row.get("row"),
                "source_cell_range": row.get("source_cell_range"),
                "case_numbers": row.get("case_numbers", []),
                "court": row.get("court"),
                "decision_date": row.get("decision_date"),
                "holding": holding,
                "content_fingerprint": relevance.content_fingerprint(support[:800]),
            })
        return result
