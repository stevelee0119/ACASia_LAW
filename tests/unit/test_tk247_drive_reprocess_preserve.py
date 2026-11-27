"""TK-247 unit tests: Preserve cached body on Drive reprocess timeout/failure, dedicated reprocess timeout, sync budget deferral, and primary-OCR restore of damaged entries."""
from __future__ import annotations

from dataclasses import replace as dc_replace
import json

from packages.common.config import get_settings
from packages.rag_engine.drive import ReferenceError, revision
from packages.rag_engine.extract import EXTRACTOR_VERSION
from packages.rag_engine.library import (
    OCR_REPROCESS_VERSION,
    ReferenceLibrary,
    resolve_reprocess_timeout_seconds,
)
from packages.rag_engine.relevance import tokens


def _make_drive(items: list[dict], downloaded: list[str], *, remaining_fn=lambda: 200.0):
    class _FakeDrive:
        credential_mode = "injected"
        folders = {}

        def remaining(self):
            return float(remaining_fn())

        def close(self):
            pass

        def inventory(self, folder, max_files=50):
            return list(items)

        def metadata(self, fid):
            return next(i for i in items if i["id"] == fid)

        def download(self, item, **_kw):
            downloaded.append(item["id"])
            return b"%PDF-1.4 synthetic reference bytes", item["name"], item["mimeType"]

    return lambda **_kw: _FakeDrive()


def _seed_healthy_low_quality_file(lib: ReferenceLibrary, item: dict, *, chunks_count: int = 400, searchable_pages: int = 407, total_pages: int = 411, low_pages: list[int] | None = None):
    low = low_pages if low_pages is not None else [2, 3, 4, 5]
    lib.directory.mkdir(parents=True, exist_ok=True)
    ver = revision(item) + ":" + EXTRACTOR_VERSION
    payload = {
        "pages": total_pages,
        "read_pages": searchable_pages,
        "completed_pages": searchable_pages,
        "searchable_pages": searchable_pages,
        "extracted_text_pages": searchable_pages,
        "chunk_count": chunks_count,
        "coverage_complete": True,
        "content_readable_complete": False,
        "ocr_low_quality_pages": list(low),
        "unread_pages_by_cause": {"OCR_LOW_QUALITY": list(low)},
        "confirmed_unreadable_pages": list(low),
        "confirmed_unreadable_causes": {"OCR_LOW_QUALITY": len(low)},
        "unreadable_confirmed": True,
        "unreadable_confirm_attempts": 2,
        "low_quality_reprocess_version": "tk231-rapidocr-preproc-v1",
    }
    def _chunk_text(i: int) -> str:
        if i == 0:
            return "계약 위반 손해배상 인과관계 검토 판시사항 본문"
        return f"절차 진행 보조 기록 일반 항목 {i}"

    with lib.connect() as db:
        db.execute("INSERT INTO files VALUES (?,?,?)", (item["id"], ver, json.dumps(payload)))
        db.executemany(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?)",
            [
                (
                    item["id"],
                    ver,
                    (idx % searchable_pages) + 1,
                    idx * 10,
                    _chunk_text(idx),
                    " ".join(tokens(_chunk_text(idx))),
                )
                for idx in range(chunks_count)
            ],
        )
        db.commit()


def test_tk247_pos1_reprocess_timeout_preserves_chunks_ready_and_zero_recovered_pages(tmp_path, monkeypatch):
    """양성 1: 재처리 시간 초과 시 기존 400조각·407쪽 본문과 READY 상태를 보존하고 허위 복구(recovered_pages)를 0으로 둔다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    assert resolve_reprocess_timeout_seconds({}) == 120

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk247_p1", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "ref_400", "name": "bundle_a.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 500},
    ]
    downloaded: list[str] = []
    observed_timeouts: list[int] = []
    remaining_val = [200.0]

    def _timeout_extractor(*_a, **kw):
        observed_timeouts.append(int(kw["timeout"]))
        raise ReferenceError("REFERENCE_PARSE_TIMEOUT")

    lib = ReferenceLibrary(
        settings,
        client_factory=_make_drive(items, downloaded, remaining_fn=lambda: remaining_val[0]),
        extractor=_timeout_extractor,
    )
    _seed_healthy_low_quality_file(lib, items[0], chunks_count=400, searchable_pages=407, total_pages=411, low_pages=[2, 3, 4, 5])

    # 1차 실행(남은 예산 200초 -> 한도 min(120, 140) = 120초): 시간 초과 실패하더라도 기존 본문 보존
    s1 = lib.sync(collect_all=True)
    assert observed_timeouts == [120]
    assert s1["status"] == "READY"
    assert s1["files_indexed"] == 1
    assert s1["issues"] == []
    assert s1["reprocess_failed"] == 1
    assert s1["ocr_reprocess"]["reprocess_failed"] == 1
    assert s1["ocr_reprocess"]["recovered_pages"] == 0
    assert s1["coverage_ledger"]["global_library"]["recovered_pages"] == 0
    assert s1["coverage_ledger"]["global_library"]["searchable_pages"] == 407
    inv1 = s1["inventory"][0]
    assert inv1["status"] == "INDEXED"
    assert inv1["reprocess_failures"] == 1
    assert inv1["last_reprocess_error"] == "REFERENCE_PARSE_TIMEOUT"
    assert inv1["recovered_pages"] == 0
    with lib.connect() as db:
        assert db.execute("SELECT count(*) FROM chunks WHERE file_id='ref_400'").fetchone()[0] == 400
        saved1 = json.loads(db.execute("SELECT payload FROM files WHERE id='ref_400'").fetchone()[0])
        assert saved1["low_quality_reprocess_version"] != OCR_REPROCESS_VERSION
    assert len(lib.search("계약 위반 손해배상")) >= 1

    # 2차 실행(남은 예산 100초 -> 한도 min(120, 40) = 40초): 한 번 더 시도 후 2회 실패 도달 -> 판 기록
    remaining_val[0] = 100.0
    s2 = lib.sync(collect_all=True)
    assert observed_timeouts == [120, 40]
    assert s2["status"] == "READY"
    assert s2["files_indexed"] == 1
    assert s2["ocr_reprocess"]["recovered_pages"] == 0
    assert s2["inventory"][0]["reprocess_failures"] == 2

    # 3차 실행: 2회 실패 후 재시도 정지(추출 0회, 캐시 재사용)
    s3 = lib.sync(collect_all=True)
    assert observed_timeouts == [120, 40]
    assert s3["diagnostics"]["extractions"]["count"] == 0
    assert s3["files_reused"] == 1
    assert s3["status"] == "READY"
    assert s3["files_indexed"] == 1


def test_tk247_pos2_damaged_file_restored_with_primary_ocr_then_protected_on_fallback_timeout(tmp_path, monkeypatch):
    """양성 2: 이미 손상된 빈 기록(previous_searchable_pages>0)은 1회차에 폴백을 끈 1차 OCR로 복원하고, 이후 폴백 재처리 실패 시에도 보존한다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk247_p2", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "damaged_doc", "name": "damaged.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 500},
    ]
    downloaded: list[str] = []
    fb_flags: list[bool] = []

    def _extractor(*_a, **kw):
        fb_cfg = kw.get("ocr_fallback_config") or {}
        fb_on = bool(fb_cfg.get("enabled"))
        fb_flags.append(fb_on)
        if fb_on:
            raise ReferenceError("REFERENCE_PARSE_TIMEOUT")
        return {
            "chunks": [
                {"page": (idx % 407) + 1, "start": idx * 10, "text": f"복원된 본문 {idx}"}
                for idx in range(400)
            ],
            "pages": 411,
            "read_pages": 407,
            "completed_pages": 407,
            "searchable_pages": 407,
            "extracted_text_pages": 407,
            "coverage_complete": True,
            "content_readable_complete": False,
            "ocr_low_quality_pages": [2, 3, 4, 5],
            "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2, 3, 4, 5]},
            "confirmed_unreadable_pages": [2, 3, 4, 5],
            "confirmed_unreadable_causes": {"OCR_LOW_QUALITY": 4},
            "child_ocr_config": {
                "fallback_engine": "none",
                "fallback_mode": "off",
                "fallback_enabled": False,
                "adapter_type": "TesseractOCRAdapter",
                "fallback_adapter": None,
            },
        }

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    ver = revision(items[0]) + ":" + EXTRACTOR_VERSION
    # 0.30.1 배포 직후 손상 상태 재현: chunk_count=0, reason=REFERENCE_PARSE_TIMEOUT, previous_searchable_pages=407, 판=v2
    with lib.connect() as db:
        db.execute(
            "INSERT INTO files VALUES (?,?,?)",
            (
                "damaged_doc",
                ver,
                json.dumps({
                    "partial": True,
                    "reason": "REFERENCE_PARSE_TIMEOUT",
                    "chunk_count": 0,
                    "searchable_pages": 0,
                    "previous_searchable_pages": 407,
                    "searchable_pages_delta": -407,
                    "low_quality_reprocess_version": OCR_REPROCESS_VERSION,
                }),
            ),
        )
        db.commit()

    # 1회차: 폴백 끄고 복원 -> 조각 400·407쪽, READY, 판 기록 제거
    s1 = lib.sync(collect_all=True)
    assert fb_flags == [False]
    assert s1["status"] == "READY"
    assert s1["files_indexed"] == 1
    assert s1["restored_files"] == 1
    assert s1["ocr_reprocess"]["restored_files"] == 1
    assert s1["ocr_reprocess"]["recovered_pages"] == 0
    assert s1["coverage_ledger"]["global_library"]["searchable_pages"] == 407
    with lib.connect() as db:
        assert db.execute("SELECT count(*) FROM chunks WHERE file_id='damaged_doc'").fetchone()[0] == 400
        restored_payload = json.loads(db.execute("SELECT payload FROM files WHERE id='damaged_doc'").fetchone()[0])
        assert "low_quality_reprocess_version" not in restored_payload

    # 2회차: 폴백 켜고 재처리 시도 -> 시간 초과 -> 400조각 보존, READY 유지
    s2 = lib.sync(collect_all=True)
    assert fb_flags == [False, True]
    assert s2["status"] == "READY"
    assert s2["files_indexed"] == 1
    assert s2["reprocess_failed"] == 1
    assert s2["ocr_reprocess"]["recovered_pages"] == 0
    with lib.connect() as db:
        assert db.execute("SELECT count(*) FROM chunks WHERE file_id='damaged_doc'").fetchone()[0] == 400

    # 3회차: 폴백 재처리 2번째 실패 -> 400조각 보존 + 정지 판 기록
    s3 = lib.sync(collect_all=True)
    assert fb_flags == [False, True, True]
    assert s3["status"] == "READY"
    assert s3["inventory"][0]["reprocess_failures"] == 2

    # 4회차: 더 이상 추출 시도 없음, 내내 400조각 유지
    s4 = lib.sync(collect_all=True)
    assert fb_flags == [False, True, True]
    assert s4["diagnostics"]["extractions"]["count"] == 0
    assert s4["status"] == "READY"
    with lib.connect() as db:
        assert db.execute("SELECT count(*) FROM chunks WHERE file_id='damaged_doc'").fetchone()[0] == 400


def test_tk247_pos3_low_sync_budget_defers_reprocess_and_keeps_corpus_indexed(tmp_path, monkeypatch):
    """양성 3: 남은 동기화 예산이 90초 미만(한도 30초 미만, 예: 60초)이면 추출 없이 기존 결과를 쓰고 재처리를 다음 실행으로 미룬다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk247_p3", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "low_cached", "name": "scan_a.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 200},
        {"id": "tail_cached", "name": "tail_b.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 300},
    ]
    downloaded: list[str] = []
    calls = 0
    remaining_val = [60.0]

    def _extractor(*_a, **_kw):
        nonlocal calls
        calls += 1
        return {
            "chunks": [{"page": 1, "start": 0, "text": "재처리 완료 본문"}, {"page": 2, "start": 0, "text": "2쪽 복구"}],
            "pages": 2,
            "read_pages": 2,
            "completed_pages": 2,
            "searchable_pages": 2,
            "extracted_text_pages": 2,
            "ocr_low_quality_pages": [],
            "coverage_complete": True,
            "content_readable_complete": True,
        }

    lib = ReferenceLibrary(
        settings,
        client_factory=_make_drive(items, downloaded, remaining_fn=lambda: remaining_val[0]),
        extractor=_extractor,
    )
    _seed_healthy_low_quality_file(lib, items[0], chunks_count=10, searchable_pages=1, total_pages=2, low_pages=[2])
    with lib.connect() as db:
        ver_tail = revision(items[1]) + ":" + EXTRACTOR_VERSION
        db.execute(
            "INSERT INTO files VALUES (?,?,?)",
            ("tail_cached", ver_tail, json.dumps({"pages": 3, "read_pages": 3, "completed_pages": 3, "searchable_pages": 3, "chunk_count": 1, "coverage_complete": True, "content_readable_complete": True})),
        )
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("tail_cached", ver_tail, 1, 0, "뒤 캐시 문서 본문", "뒤 캐시 문서 본문"))
        db.commit()

    # 1차 실행(남은 예산 60초 < 90초): 추출 0회, 미룸 기록, 뒤 캐시 파일까지 모두 READY 색인 유지
    s1 = lib.sync(collect_all=True)
    assert calls == 0
    assert downloaded == []
    assert s1["status"] == "READY"
    assert s1["files_indexed"] == 2
    assert s1["files_reused"] == 2
    assert s1["reprocess_deferred"] == 1
    assert s1["ocr_reprocess"]["reprocess_deferred"] == 1
    assert s1["ocr_reprocess"]["zero_fallback_attempt_reason"] == "REPROCESS_DEFERRED_SYNC_BUDGET"
    by_id1 = {e["file_id"]: e for e in s1["inventory"]}
    assert by_id1["low_cached"]["reprocess_deferred"] is True

    # 2차 실행(남은 예산 180초 >= 90초): 미뤄졌던 파일이 정상 재처리됨
    remaining_val[0] = 180.0
    s2 = lib.sync(collect_all=True)
    assert calls == 1
    assert downloaded == ["low_cached"]
    assert s2["reprocess_deferred"] == 0
    assert s2["ocr_reprocess"]["recovered_pages"] == 1


def test_tk247_ctrl1_initial_extract_timeout_is_terminal_and_not_retried(tmp_path, monkeypatch):
    """대조 1: 처음 추출부터 시간 초과가 난 파일(previous_searchable_pages 없음)은 복원 재시도 대상이 아니며 기존처럼 단말 실패로 캐시된다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk247_c1", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "first_timeout", "name": "huge_broken.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 400},
    ]
    downloaded: list[str] = []
    calls = 0
    timeouts: list[int] = []

    def _always_timeout(*_a, **kw):
        nonlocal calls
        calls += 1
        timeouts.append(int(kw["timeout"]))
        raise ReferenceError("REFERENCE_PARSE_TIMEOUT")

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_always_timeout)

    s1 = lib.sync(collect_all=True)
    assert calls == 1
    assert timeouts == [30]  # 첫 추출은 기존대로 30초 한도
    assert s1["status"] == "PARTIAL"
    assert s1["issues"][0]["reason"] == "REFERENCE_PARSE_TIMEOUT"
    assert s1["restored_files"] == 0

    # 2차·3차 실행: 복원 대상이 아니므로 재추출하지 않음
    s2 = lib.sync(collect_all=True)
    s3 = lib.sync(collect_all=True)
    assert calls == 1
    assert s2["status"] == "PARTIAL"
    assert s3["status"] == "PARTIAL"


def test_tk247_ctrl2_successful_reprocess_replaces_chunks_and_counts_recovery(tmp_path, monkeypatch):
    """대조 2: 재처리가 성공하면 기존대로 조각을 새 본문으로 교체하고 복구 쪽수(recovered_pages)를 정확히 집계한다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk247_c2", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "recover_ok", "name": "recover.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 200},
    ]
    downloaded: list[str] = []
    calls = 0

    def _success_extractor(*_a, **_kw):
        nonlocal calls
        calls += 1
        return {
            "chunks": [
                {"page": 1, "start": 0, "text": "교체된 신규 본문 1쪽"},
                {"page": 2, "start": 0, "text": "폴백으로 복구된 신규 본문 2쪽"},
            ],
            "pages": 3,
            "read_pages": 2,
            "completed_pages": 2,
            "searchable_pages": 2,
            "extracted_text_pages": 2,
            "coverage_complete": True,
            "content_readable_complete": False,
            "ocr_low_quality_pages": [3],
            "unread_pages_by_cause": {"OCR_LOW_QUALITY": [3]},
            "confirmed_unreadable_pages": [3],
            "confirmed_unreadable_causes": {"OCR_LOW_QUALITY": 1},
            "ocr_fallback_summary": {"attempted_pages": [2, 3], "adopted_pages": [2], "reason_counts": {"FALLBACK_IMPROVED_QUALITY": 1}},
            "child_ocr_config": {"fallback_engine": "rapidocr", "fallback_mode": "auto", "fallback_enabled": True, "adapter_type": "CompositeOCRAdapter", "fallback_adapter": "rapidocr"},
        }

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_success_extractor)
    _seed_healthy_low_quality_file(lib, items[0], chunks_count=1, searchable_pages=1, total_pages=3, low_pages=[2, 3])

    s1 = lib.sync(collect_all=True)
    assert calls == 1
    assert s1["status"] == "READY"
    assert s1["reprocess_failed"] == 0
    assert s1["ocr_reprocess"]["reprocessed_files"] == 1
    assert s1["ocr_reprocess"]["low_quality_pages_before"] == 2
    assert s1["ocr_reprocess"]["low_quality_pages_after"] == 1
    assert s1["ocr_reprocess"]["recovered_pages"] == 1
    assert len(lib.search("폴백으로 복구된 신규 본문")) == 1
    assert lib.search("계약 위반 손해배상") == []

    # 다음 실행에서는 캐시 재사용
    s2 = lib.sync(collect_all=True)
    assert calls == 1
    assert s2["files_reused"] == 1


def test_tk247_ctrl3_stops_retrying_after_two_failures_both_reprocess_and_restore(tmp_path, monkeypatch):
    """대조 3: 재처리 실패와 손상 파일 복원 실패 모두 최대 2회까지만 시도한 뒤 멈추고 무한 재시도하지 않는다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk247_c3", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "reproc_fail2", "name": "reproc.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 200},
        {"id": "damaged_fail2", "name": "damaged_perm.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 200},
    ]
    downloaded: list[str] = []
    calls_by_name: dict[str, int] = {}

    def _always_fail(_data, name, _mime, **_kw):
        calls_by_name[name] = calls_by_name.get(name, 0) + 1
        raise ReferenceError("REFERENCE_PARSE_FAILED")

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_always_fail)
    _seed_healthy_low_quality_file(lib, items[0], chunks_count=5, searchable_pages=5, total_pages=6, low_pages=[6])
    with lib.connect() as db:
        ver_dmg = revision(items[1]) + ":" + EXTRACTOR_VERSION
        db.execute(
            "INSERT INTO files VALUES (?,?,?)",
            (
                "damaged_fail2",
                ver_dmg,
                json.dumps({
                    "partial": True,
                    "reason": "REFERENCE_PARSE_TIMEOUT",
                    "chunk_count": 0,
                    "searchable_pages": 0,
                    "previous_searchable_pages": 248,
                    "low_quality_reprocess_version": OCR_REPROCESS_VERSION,
                }),
            ),
        )
        db.commit()

    # 1차 실행: 둘 다 1회씩 시도 후 실패 (정상본은 보존, 손상본은 PARSE_FAILED 유지해 H-REF가 계속 탐지)
    s1 = lib.sync(collect_all=True)
    assert calls_by_name == {"reproc.pdf": 1, "damaged_perm.pdf": 1}
    assert s1["reprocess_failed"] == 1
    assert s1["restore_failed"] == 1
    assert s1["status"] == "PARTIAL"  # damaged_fail2가 여전히 PARSE_FAILED이므로 H-REF 경고 유지
    assert any(iss.get("file_id") == "damaged_fail2" for iss in s1["issues"])

    # 2차 실행: 둘 다 2회째 시도 후 실패
    s2 = lib.sync(collect_all=True)
    assert calls_by_name == {"reproc.pdf": 2, "damaged_perm.pdf": 2}
    by_id2 = {e["file_id"]: e for e in s2["inventory"]}
    assert by_id2["reproc_fail2"]["reprocess_failures"] == 2
    assert by_id2["damaged_fail2"]["restore_attempts"] == 2
    assert by_id2["damaged_fail2"]["previous_searchable_pages"] == 248

    # 3차 실행: 둘 다 2회 도달했으므로 추가 추출 0회
    s3 = lib.sync(collect_all=True)
    assert calls_by_name == {"reproc.pdf": 2, "damaged_perm.pdf": 2}
    assert s3["diagnostics"]["extractions"]["count"] == 0
    assert s3["files_reused"] == 2
    with lib.connect() as db:
        assert db.execute("SELECT count(*) FROM chunks WHERE file_id='reproc_fail2'").fetchone()[0] == 5
