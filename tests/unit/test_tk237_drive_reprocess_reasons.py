"""TK-237 unit tests: Drive unread cause recording, cause-set reprocess trigger, and 1-time legacy re-evaluation."""
from __future__ import annotations

from dataclasses import replace as dc_replace
import json

from packages.common.config import get_settings
from packages.rag_engine.drive import revision
from packages.rag_engine.extract import EXTRACTOR_VERSION
from packages.rag_engine.library import ReferenceLibrary


def _make_drive(items: list[dict], downloaded: list[str]):
    class _FakeDrive:
        credential_mode = "injected"
        folders = {}

        def remaining(self):
            return 100.0

        def close(self):
            pass

        def inventory(self, folder, max_files=50):
            return list(items)

        def metadata(self, fid):
            return next(i for i in items if i["id"] == fid)

        def download(self, item, **_kw):
            downloaded.append(item["id"])
            return b"%PDF-1.4 dummy", item["name"], item["mimeType"]

    return lambda **_kw: _FakeDrive()


def test_tk237_pos1_low_quality_cause_only_triggers_selective_reprocess(tmp_path, monkeypatch):
    """양성 1: unread_pages_by_cause['OCR_LOW_QUALITY']만 있어도 선택 재처리가 발동하고 다른 정상 파일은 캐시 재사용된다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk237_1", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "clean_doc", "name": "normal.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
        {"id": "low_doc", "name": "scanned.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []

    def _extractor(content, name, mime, **_kw):
        return {
            "chunks": [
                {"page": 1, "start": 0, "text": "1쪽 본문"},
                {"page": 2, "start": 0, "text": "2쪽 복구 본문"},
            ],
            "chunk_count": 2,
            "pages": 2,
            "read_pages": 2,
            "completed_pages": 2,
            "searchable_pages": 2,
            "extracted_text_pages": 2,
            "ocr_low_quality_pages": [],
            "coverage_complete": True,
            "content_readable_complete": True,
        }

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        v0 = revision(items[0]) + ":" + EXTRACTOR_VERSION
        v1 = revision(items[1]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "clean_doc", v0,
            json.dumps({"pages": 2, "read_pages": 2, "completed_pages": 2, "chunk_count": 1, "searchable_pages": 2, "extracted_text_pages": 2, "coverage_complete": True, "content_readable_complete": True}),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("clean_doc", v0, 1, 0, "정상 판례 본문", "정상 판례 본문"))
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "low_doc", v1,
            json.dumps({
                "pages": 2,
                "read_pages": 1,
                "completed_pages": 1,
                "chunk_count": 1,
                "searchable_pages": 1,
                "extracted_text_pages": 1,
                "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2]},
                "coverage_complete": True,
                "content_readable_complete": False,
            }),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("low_doc", v1, 1, 0, "1쪽 본문", "1쪽 본문"))
        db.commit()

    summary = lib.sync(collect_all=True)
    assert downloaded == ["low_doc"]
    by_id = {e["file_id"]: e for e in summary["inventory"]}
    assert by_id["clean_doc"].get("reused") is True
    assert by_id["low_doc"].get("reused") is not True
    gl = summary["coverage_ledger"]["global_library"]
    assert gl["searchable_pages_delta"] == 1
    assert gl["recovered_pages"] >= 0


def test_tk237_pos2_parse_failed_cause_reconciled_and_retried(tmp_path):
    """양성 2: extractor가 사유를 안 채워도 pages - completed_pages 차이를 PARSE_FAILED로 분해 기록하고 재시도한다."""
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk237_2", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "err_doc", "name": "partial.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []
    calls = 0

    def _extractor(content, name, mime, **_kw):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "chunks": [{"page": 1, "start": 0, "text": "1쪽 본문"}],
                "pages": 4,
                "read_pages": 2,
                "completed_pages": 2,
                "partial": True,
                "coverage_complete": False,
                "content_readable_complete": False,
                "reason": "REFERENCE_PARTIALLY_READ",
            }
        return {
            "chunks": [{"page": p, "start": 0, "text": f"{p}쪽 본문"} for p in range(1, 5)],
            "pages": 4,
            "read_pages": 4,
            "completed_pages": 4,
            "partial": False,
            "coverage_complete": True,
            "content_readable_complete": True,
        }

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_extractor)
    s1 = lib.sync(collect_all=True)
    inv1 = s1["inventory"][0]
    by_cause1 = inv1["unread_pages_by_cause"]
    assert sum(len(v) for v in by_cause1.values()) == 4 - 2

    s2 = lib.sync(collect_all=True)
    assert calls == 2
    assert s2["inventory"][0]["completed_pages"] == 4
    assert s2["coverage_ledger"]["global_library"]["searchable_pages_delta"] == 3


def test_tk237_pos3_legacy_cache_reevaluated_once_then_reused(tmp_path):
    """양성 3: 사유 필드가 없고 카운터만 어긋난 레거시 캐시는 1회만 재평가해 사유를 채우고 이후 재사용한다."""
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk237_3", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "legacy_doc", "name": "legacy.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []
    calls = 0

    def _extractor(content, name, mime, **_kw):
        nonlocal calls
        calls += 1
        return {
            "chunks": [{"page": 1, "start": 0, "text": "1쪽 본문"}],
            "pages": 5,
            "read_pages": 3,
            "completed_pages": 3,
            "partial": True,
            "coverage_complete": True,
            "content_readable_complete": False,
            "unread_pages_by_cause": {"OCR_UNAVAILABLE": [4, 5]},
            "config_blocked_pages": [4, 5],
        }

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        v = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "legacy_doc", v,
            json.dumps({
                "pages": 5,
                "read_pages": 3,
                "extracted_text_pages": 3,
                "completed_pages": 3,
                "chunk_count": 1,
                "coverage_complete": True,
                "content_readable_complete": False,
            }),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("legacy_doc", v, 1, 0, "1쪽 본문", "1쪽 본문"))
        db.commit()

    s1 = lib.sync(collect_all=True)
    assert calls == 1
    assert s1["inventory"][0].get("reused") is not True
    assert s1["inventory"][0]["unread_pages_by_cause"]["OCR_UNAVAILABLE"] == [4, 5]
    assert s1["coverage_ledger"]["global_library"]["reprocessed_pages"] == 2

    s2 = lib.sync(collect_all=True)
    assert calls == 1
    assert s2["inventory"][0].get("reused") is True


def test_tk237_ctrl1_completed_doc_not_reprocessed(tmp_path):
    """대조 1: 완독 자료는 재처리하지 않고 캐시를 재사용한다."""
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk237_c1", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "ok_doc", "name": "ok.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []
    calls = 0

    def _extractor(*_a, **_kw):
        nonlocal calls
        calls += 1
        return {"chunks": [], "pages": 3, "read_pages": 3, "completed_pages": 3}

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        v = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "ok_doc", v,
            json.dumps({"pages": 3, "read_pages": 3, "completed_pages": 3, "chunk_count": 1, "coverage_complete": True, "content_readable_complete": True}),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("ok_doc", v, 1, 0, "정상", "정상"))
        db.commit()

    s = lib.sync(collect_all=True)
    assert calls == 0
    assert downloaded == []
    assert s["inventory"][0].get("reused") is True


def test_tk237_ctrl2_verified_blank_pages_not_retried(tmp_path):
    """대조 2: 확인된 빈 쪽(CONTENT_NO_TEXT)만 있는 자료는 재시도하지 않는다."""
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk237_c2", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "blank_doc", "name": "blank.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []
    calls = 0

    def _extractor(*_a, **_kw):
        nonlocal calls
        calls += 1
        return {"chunks": []}

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        v = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "blank_doc", v,
            json.dumps({
                "pages": 2,
                "read_pages": 1,
                "completed_pages": 2,
                "blank_pages": [2],
                "unread_pages_by_cause": {"CONTENT_NO_TEXT": [2]},
                "chunk_count": 1,
                "coverage_complete": True,
                "content_readable_complete": False,
                "reason": "VERIFIED_BLANK_PAGES",
            }),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("blank_doc", v, 1, 0, "본문", "본문"))
        db.commit()

    s = lib.sync(collect_all=True)
    assert calls == 0
    assert downloaded == []
    assert s["inventory"][0].get("reused") is True


def test_tk237_ctrl3_config_blocked_pages_not_retried(tmp_path):
    """대조 3: 설정 차단(OCR_UNAVAILABLE/config_blocked_pages) 쪽은 재시도하지 않는다."""
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk237_c3", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "blocked_doc", "name": "blocked.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []
    calls = 0

    def _extractor(*_a, **_kw):
        nonlocal calls
        calls += 1
        return {"chunks": []}

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        v = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "blocked_doc", v,
            json.dumps({
                "pages": 2,
                "read_pages": 1,
                "completed_pages": 1,
                "unread_pages_by_cause": {"OCR_UNAVAILABLE": [2]},
                "config_blocked_pages": [2],
                "chunk_count": 1,
                "coverage_complete": False,
                "content_readable_complete": False,
            }),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("blocked_doc", v, 1, 0, "본문", "본문"))
        db.commit()

    s = lib.sync(collect_all=True)
    assert calls == 0
    assert downloaded == []
    assert s["inventory"][0].get("reused") is True
