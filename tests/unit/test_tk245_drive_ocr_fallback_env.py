"""TK-245 unit tests: Drive low-quality reprocess fallback env propagation, shared config source, v2 1-time reprocess, union recovery counting, and manifest observability."""
from __future__ import annotations

from dataclasses import replace as dc_replace
import json
import subprocess
import sys

from packages.common.config import REPO_ROOT, get_settings
from packages.document_engine.ocr import resolve_ocr_fallback_config
from packages.rag_engine.drive import revision
from packages.rag_engine.extract import EXTRACTOR_VERSION
from packages.rag_engine.library import (
    EXTRACT_ENV_ALLOWLIST,
    OCR_REPROCESS_VERSION,
    ReferenceLibrary,
    build_isolated_extract_env,
    isolated_extract,
)


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
            return b"normal reference text body", item["name"], item["mimeType"]

    return lambda **_kw: _FakeDrive()


def test_tk245_pos1_fallback_enabled_propagates_to_child_and_builds_composite_adapter(tmp_path, monkeypatch):
    """양성 1: 부모가 폴백 재처리를 켜면 자식 추출 프로세스에 폴백 변수가 전달되어 CompositeOCRAdapter(RapidOCRAdapter)를 구성하고 비밀 변수는 차단된다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")
    monkeypatch.setenv("LV_ALLOW_NETWORK", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-must-not-leak")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-must-not-leak")
    monkeypatch.setenv("LV_LAW_GO_KR_OC", "oc-secret-must-not-leak")
    monkeypatch.setenv("LV_PSEUDONYM_SECRET", "pseudo-secret-must-not-leak")
    monkeypatch.setenv("LV_DATABASE_URL", "postgresql://secret:pw@host/db")

    parent_cfg = resolve_ocr_fallback_config()
    assert parent_cfg == {"engine": "rapidocr", "mode": "auto", "enabled": True}

    captured_envs: list[dict[str, str]] = []
    real_run = subprocess.run

    def _spy_run(args, *a, **kw):
        if "env" in kw and isinstance(kw["env"], dict):
            captured_envs.append(dict(kw["env"]))
        return real_run(args, *a, **kw)

    monkeypatch.setattr("packages.rag_engine.library.subprocess.run", _spy_run)
    payload = isolated_extract(
        "징계 절차 기준 참고 문서 본문입니다.".encode("utf-8"),
        "ref.txt",
        "text/plain",
        directory=tmp_path,
        timeout=30,
        ocr_fallback_config=parent_cfg,
    )
    assert len(captured_envs) == 1
    child_env = captured_envs[0]

    # 1) 폴백 설정 전달 및 격리 불변식 검증
    assert child_env["LV_OCR_FALLBACK_ENGINE"] == "rapidocr"
    assert child_env["LV_OCR_FALLBACK_MODE"] == "auto"
    assert child_env["LV_ALLOW_NETWORK"] == "0"
    assert child_env["LV_OCR_MAX_PAGES"] == "5"
    assert child_env["LV_INDEPENDENT_OCR"] == "off"
    assert child_env["OPENBLAS_NUM_THREADS"] == "1"
    assert child_env["OMP_NUM_THREADS"] == "1"
    assert child_env["MKL_NUM_THREADS"] == "1"

    # 2) 허용 목록 밖 비밀 변수 차단 검증
    for secret_key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LV_LAW_GO_KR_OC", "LV_PSEUDONYM_SECRET", "LV_DATABASE_URL"):
        assert secret_key not in child_env
        assert secret_key not in EXTRACT_ENV_ALLOWLIST

    # 3) 자식 환경으로 실제 별도 파이썬 프로세스에서 get_ocr_adapter() 호출 시 CompositeOCRAdapter + rapidocr 구성 확인
    probe = real_run(
        [
            sys.executable,
            "-c",
            (
                "import json; from packages.document_engine.ocr import get_ocr_adapter, resolve_ocr_fallback_config; "
                "a = get_ocr_adapter(); "
                "print(json.dumps({'cfg': resolve_ocr_fallback_config(), 'cls': type(a).__name__, "
                "'fb': getattr(getattr(a, 'fallback', None), 'name', None), 'mode': getattr(a, 'mode', None)}))"
            ),
        ],
        cwd=REPO_ROOT,
        env=child_env,
        check=True,
        capture_output=True,
        text=True,
    )
    info = json.loads(probe.stdout.strip().splitlines()[-1])
    assert info["cfg"] == parent_cfg
    assert info["cls"] == "CompositeOCRAdapter"
    assert info["fb"] == "rapidocr"
    assert info["mode"] == "auto"
    assert payload["child_ocr_config"]["fallback_engine"] == "rapidocr"
    assert payload["child_ocr_config"]["fallback_mode"] == "auto"
    assert payload["child_ocr_config"]["fallback_enabled"] is True


def test_tk245_pos2_v1_cached_file_reprocessed_once_then_reused_as_v2(tmp_path, monkeypatch):
    """양성 2: v1(tk231-rapidocr-preproc-v1) 기록 파일은 판 올림(v2) 뒤 정확히 1회 재처리되고, 복구 미달 쪽을 완독으로 둔갑시키지 않으며 다음 실행에서는 재처리하지 않는다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")
    assert OCR_REPROCESS_VERSION == "tk245-fallback-env-v2"

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk245_p2", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "v1_doc", "name": "scan_ref.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []
    calls = 0

    def _extractor(*_a, **_kw):
        nonlocal calls
        calls += 1
        return {
            "chunks": [{"page": 1, "start": 0, "text": "1쪽 정상 본문"}],
            "pages": 2,
            "read_pages": 1,
            "completed_pages": 1,
            "searchable_pages": 1,
            "extracted_text_pages": 1,
            "partial": False,
            "coverage_complete": True,
            "content_readable_complete": False,
            "ocr_low_quality_pages": [2],
            "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2]},
            "confirmed_unreadable_pages": [2],
            "confirmed_unreadable_causes": {"OCR_LOW_QUALITY": 1},
            "ocr_fallback_summary": {"attempted_pages": [2], "adopted_pages": [], "reason_counts": {"FALLBACK_NOT_IMPROVED": 1}},
            "child_ocr_config": {
                "fallback_engine": "rapidocr",
                "fallback_mode": "auto",
                "fallback_enabled": True,
                "adapter_type": "CompositeOCRAdapter",
                "fallback_adapter": "rapidocr",
            },
        }

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        ver = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "v1_doc", ver,
            json.dumps({
                "pages": 2,
                "read_pages": 1,
                "completed_pages": 1,
                "searchable_pages": 1,
                "extracted_text_pages": 1,
                "chunk_count": 1,
                "coverage_complete": True,
                "content_readable_complete": False,
                "ocr_low_quality_pages": [2],
                "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2]},
                "confirmed_unreadable_pages": [2],
                "low_quality_reprocess_version": "tk231-rapidocr-preproc-v1",
            }),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("v1_doc", ver, 1, 0, "1쪽 정상 본문", "1쪽 정상 본문"))
        db.commit()

    # 1차 sync: v1 -> v2 판 올림으로 1회 재처리
    s1 = lib.sync(collect_all=True)
    assert calls == 1
    assert downloaded == ["v1_doc"]
    assert s1["ocr_fallback_attempted_pages"] == 1
    assert s1["ocr_reprocess"]["reprocessed_files"] == 1
    assert s1["ocr_reprocess"]["reprocessed_pages"] == 1
    assert s1["ocr_reprocess"]["recovered_pages"] == 0
    assert s1["ocr_reprocess"]["child_ocr_config"]["adapter_type"] == "CompositeOCRAdapter"
    assert s1["ocr_reprocess"]["zero_fallback_attempt_reason"] is None
    # 복구 미달 쪽이 완독으로 둔갑하지 않음
    inv1 = s1["inventory"][0]
    assert inv1["content_readable_complete"] is False
    assert inv1["unread_pages_by_cause"]["OCR_LOW_QUALITY"] == [2]

    # 2차 sync: 이제 v2로 기록되어 재처리하지 않고 캐시 재사용
    s2 = lib.sync(collect_all=True)
    assert calls == 1
    assert s2["inventory"][0].get("reused") is True


def test_tk245_pos3_empty_ocr_attempted_pages_in_cause_union_counted_in_recovery(tmp_path, monkeypatch):
    """양성 3: ocr_low_quality_pages에 없고 unread_pages_by_cause['OCR_LOW_QUALITY']에만 있던(시도했으나 빈 OCR) 쪽도 합집합 전후 복구 집계에 포함된다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk245_p3", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "union_doc", "name": "mixed_low.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
    ]
    downloaded: list[str] = []

    def _extractor(*_a, **_kw):
        # 3쪽(이전 빈 OCR 쪽)은 복구되고 2쪽만 저품질로 남음
        return {
            "chunks": [
                {"page": 1, "start": 0, "text": "1쪽 본문"},
                {"page": 3, "start": 0, "text": "3쪽 폴백 복구 본문"},
            ],
            "pages": 3,
            "read_pages": 2,
            "completed_pages": 2,
            "searchable_pages": 2,
            "extracted_text_pages": 2,
            "coverage_complete": True,
            "content_readable_complete": False,
            "ocr_pages": [3],
            "ocr_low_quality_pages": [2],
            "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2]},
            "confirmed_unreadable_pages": [2],
            "ocr_fallback_summary": {"attempted_pages": [2, 3], "adopted_pages": [3], "reason_counts": {"FALLBACK_IMPROVED_QUALITY": 1, "FALLBACK_NOT_IMPROVED": 1}},
            "child_ocr_config": {"fallback_engine": "rapidocr", "fallback_mode": "auto", "fallback_enabled": True, "adapter_type": "CompositeOCRAdapter", "fallback_adapter": "rapidocr"},
        }

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_extractor)
    lib.directory.mkdir(parents=True, exist_ok=True)
    with lib.connect() as db:
        ver = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "union_doc", ver,
            json.dumps({
                "pages": 3,
                "read_pages": 1,
                "completed_pages": 1,
                "searchable_pages": 1,
                "extracted_text_pages": 1,
                "chunk_count": 1,
                "coverage_complete": True,
                "content_readable_complete": False,
                # 2쪽은 저품질 텍스트, 3쪽은 OCR 시도 후 빈 결과라 ocr_low_quality_pages에는 없고 unread_pages_by_cause에만 있음
                "ocr_low_quality_pages": [2],
                "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2, 3]},
                "confirmed_unreadable_pages": [2, 3],
                "unreadable_confirmed": True,
                "low_quality_reprocess_version": "tk231-rapidocr-preproc-v1",
            }),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("union_doc", ver, 1, 0, "1쪽 본문", "1쪽 본문"))
        db.commit()

    summary = lib.sync(collect_all=True)
    rep = summary["ocr_reprocess"]
    assert rep["low_quality_pages_before"] == 2  # {2} ∪ {2, 3} = {2, 3} -> 2쪽
    assert rep["low_quality_pages_after"] == 1   # {2} -> 1쪽
    assert rep["reprocessed_pages"] == 2
    assert rep["recovered_pages"] == 1
    assert rep["ocr_fallback_attempted_pages"] == 2
    assert rep["ocr_fallback_adopted_pages"] == 1


def test_tk245_ctrl1_fallback_disabled_does_not_reprocess_low_quality_file(tmp_path, monkeypatch):
    """대조 1: 폴백이 꺼져 있으면(LV_OCR_FALLBACK_ENGINE=none / mode=off) 저품질 쪽이 있는 캐시 파일도 재처리하지 않는다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "none")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "off")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk245_c1", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "off_doc", "name": "low.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
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
        ver = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "off_doc", ver,
            json.dumps({
                "pages": 2,
                "read_pages": 1,
                "completed_pages": 1,
                "chunk_count": 1,
                "coverage_complete": True,
                "content_readable_complete": False,
                "ocr_low_quality_pages": [2],
                "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2]},
                "low_quality_reprocess_version": "tk231-rapidocr-preproc-v1",
            }),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("off_doc", ver, 1, 0, "본문", "본문"))
        db.commit()

    s = lib.sync(collect_all=True)
    assert calls == 0
    assert downloaded == []
    assert s["inventory"][0].get("reused") is True
    assert s["ocr_reprocess"]["auto_reprocess_enabled"] is False


def test_tk245_ctrl2_v2_cached_file_not_reprocessed(tmp_path, monkeypatch):
    """대조 2: 이미 현행 판(v2)으로 기록된 저품질 파일은 폴백이 켜져 있어도 다시 재처리하지 않고 시도 0 사유를 기록한다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk245_c2", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "v2_doc", "name": "low_v2.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
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
        ver = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "v2_doc", ver,
            json.dumps({
                "pages": 2,
                "read_pages": 1,
                "completed_pages": 1,
                "chunk_count": 1,
                "coverage_complete": True,
                "content_readable_complete": False,
                "ocr_low_quality_pages": [2],
                "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2]},
                "confirmed_unreadable_pages": [2],
                "unreadable_confirmed": True,
                "low_quality_reprocess_version": OCR_REPROCESS_VERSION,
            }),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("v2_doc", ver, 1, 0, "본문", "본문"))
        db.commit()

    s = lib.sync(collect_all=True)
    assert calls == 0
    assert downloaded == []
    assert s["inventory"][0].get("reused") is True
    assert s["ocr_reprocess"]["zero_fallback_attempt_reason"] == "NO_FILES_EXTRACTED_ALL_REUSED"


def test_tk245_ctrl3_completed_file_not_reprocessed(tmp_path, monkeypatch):
    """대조 3: 폴백이 켜져 있어도 저품질 쪽이 없는 완독 파일은 재처리하지 않는다."""
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")

    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk245_c3", storage_root=tmp_path, allow_network=True)
    items = [
        {"id": "ok_doc", "name": "complete.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100},
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
        ver = revision(items[0]) + ":" + EXTRACTOR_VERSION
        db.execute("INSERT INTO files VALUES (?,?,?)", (
            "ok_doc", ver,
            json.dumps({
                "pages": 4,
                "read_pages": 4,
                "completed_pages": 4,
                "chunk_count": 2,
                "coverage_complete": True,
                "content_readable_complete": True,
            }),
        ))
        db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)", ("ok_doc", ver, 1, 0, "완독 본문", "완독 본문"))
        db.commit()

    s = lib.sync(collect_all=True)
    assert calls == 0
    assert downloaded == []
    assert s["inventory"][0].get("reused") is True


def test_tk245_shared_config_source_and_zero_attempt_reason_recorded(tmp_path, monkeypatch):
    """보강 검증: 부모 판단과 자식 환경 빌더가 같은 resolve_ocr_fallback_config() 출처를 쓰고, 폴백 켬인데 시도 0이면 구체 사유를 기록한다."""
    for raw_env in (
        {"LV_OCR_FALLBACK_ENGINE": "rapidocr", "LV_OCR_FALLBACK_MODE": "auto"},
        {"LV_OCR_FALLBACK_ENGINE": "rapidocr"},
        {"LV_OCR_FALLBACK_ENGINE": "rapidocr", "LV_OCR_FALLBACK_MODE": "off"},
        {"LV_OCR_FALLBACK_ENGINE": "none", "LV_OCR_FALLBACK_MODE": "auto"},
        {},
    ):
        parent_cfg = resolve_ocr_fallback_config(raw_env)
        child_env = build_isolated_extract_env(tmp_path, source_env=raw_env)
        child_cfg = resolve_ocr_fallback_config(child_env)
        assert child_cfg == parent_cfg

    # 폴백 켬 상태에서 자식 어댑터 미가용으로 시도 0건이 된 경우 사유 기록 확인
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "auto")
    settings = dc_replace(get_settings(), rag_drive_folder_id="folder_tk245_zero", storage_root=tmp_path, allow_network=True)
    items = [{"id": "z_doc", "name": "z.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-11-22T00:00:00Z", "version": "1", "size": 100}]
    downloaded: list[str] = []

    def _unavail_extractor(*_a, **_kw):
        return {
            "chunks": [{"page": 1, "start": 0, "text": "1쪽 본문"}],
            "pages": 2,
            "read_pages": 1,
            "completed_pages": 1,
            "coverage_complete": True,
            "content_readable_complete": False,
            "ocr_low_quality_pages": [2],
            "unread_pages_by_cause": {"OCR_LOW_QUALITY": [2]},
            "child_ocr_config": {
                "fallback_engine": "rapidocr",
                "fallback_mode": "auto",
                "fallback_enabled": True,
                "adapter_type": "TesseractOCRAdapter",
                "fallback_adapter": None,
            },
        }

    lib = ReferenceLibrary(settings, client_factory=_make_drive(items, downloaded), extractor=_unavail_extractor)
    s = lib.sync(collect_all=True)
    assert s["ocr_fallback_attempted_pages"] == 0
    assert s["ocr_reprocess"]["zero_fallback_attempt_reason"] == "CHILD_FALLBACK_ADAPTER_UNAVAILABLE"
