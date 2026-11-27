"""Unit and integration tests for incremental Google Drive reference dataset management."""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
import uuid

import httpx
import pytest

from packages.rag_engine.drive import DriveClient, FOLDER, ReferenceError
from packages.rag_engine.library import ReferenceLibrary
from packages.rag_engine.preindex import preindex_drive_library
from packages.rag_engine.relevance import tokens


def _make_settings(tmp_path, folder_id: str = "folder_root_123456"):
    return SimpleNamespace(
        rag_drive_folder_id=folder_id,
        storage_root=str(tmp_path),
        allow_network=True,
        rag_sync_seconds=120,
        rag_max_files=50,
        rag_inventory_max_files=200,
        rag_download_mb=50,
        rag_metadata_first=False,
        rag_hybrid_semantic=False,
    )


def _item(
    file_id: str,
    name: str,
    *,
    parent: str = "folder_root_123456",
    modified: str = "2026-11-01T00:00:00Z",
    version: str = "1",
    data: bytes = b"",
    trashed: bool = False,
    can_download: bool = True,
) -> dict:
    return {
        "id": file_id,
        "name": name,
        "mimeType": "text/plain",
        "createdTime": "2026-10-01T00:00:00Z",
        "modifiedTime": modified,
        "version": version,
        "md5Checksum": hashlib.md5(data).hexdigest(),
        "size": str(len(data)),
        "parents": [parent],
        "trashed": trashed,
        "capabilities": {"canDownload": can_download},
    }


def _simple_extractor(texts_by_bytes: dict[bytes, str]):
    def _extract(data: bytes, filename: str, mime: str, **kwargs):
        text = texts_by_bytes.get(data, data.decode("utf-8", "replace"))
        return {
            "sha256": hashlib.sha256(data).hexdigest(),
            "pages": 1,
            "read_pages": 1,
            "searchable_pages": 1,
            "coverage_complete": True,
            "content_readable_complete": True,
            "chunks": [{"page": 1, "start": 0, "text": text}],
        }

    return _extract


class _MockChangesDrive:
    def __init__(self, *, root_id: str = "folder_root_123456", credential_mode: str = "service_account"):
        self.root_id = root_id
        self.credential_mode = credential_mode
        self.folders: dict[str, str] = {}
        self.calls: list[dict] = []
        self.call_totals = {"count": 0, "bytes": 0, "by_operation": {}, "by_status": {}}
        self.last_error_reason = ""
        self.root_trashed = False
        self.inventory_calls = 0
        self.changes_calls = 0
        self.download_calls = 0
        self.items: list[dict] = []
        self.contents: dict[str, bytes] = {}
        self.start_token = "tok_1"
        self.pending_changes: list[dict] = []
        self.next_token = "tok_2"
        self.changes_error: str | None = None

    def remaining(self) -> float:
        return 100.0

    def metadata(self, file_id: str) -> dict:
        if file_id == self.root_id:
            return {
                "id": self.root_id,
                "name": "root",
                "mimeType": FOLDER,
                "trashed": self.root_trashed,
            }
        for it in self.items:
            if it["id"] == file_id:
                return dict(it)
        raise ReferenceError("DRIVE_HTTP_404")

    def inventory(self, folder_id: str, max_files: int = 1000) -> list[dict]:
        self.inventory_calls += 1
        root = self.metadata(folder_id)
        if root.get("trashed"):
            raise ReferenceError("ROOT_FOLDER_UNAVAILABLE")
        self.folders = {folder_id: ""}
        return [dict(it, folder_path="", listed_parent=folder_id) for it in self.items]

    def get_start_page_token(self) -> str:
        return self.start_token

    def list_changes(self, page_token: str, *, max_changes: int = 500):
        self.changes_calls += 1
        if self.changes_error:
            raise ReferenceError(self.changes_error)
        return list(self.pending_changes), self.next_token, False

    def download(self, item: dict, *, max_bytes: int):
        self.download_calls += 1
        data = self.contents[item["id"]]
        return data, item["name"], item.get("mimeType", "text/plain")

    def close(self) -> None:
        return None


def test_pos1_unchanged_folder_skips_inventory_and_searches_prepared_dataset(tmp_path):
    """변경이 없는 폴더는 2회차부터 전체 목록 순회 없이 준비된 데이터셋으로 즉시 검색한다."""
    settings = _make_settings(tmp_path)
    doc_a = "대법원 2021다11111 판결은 불법행위 손해배상 책임을 판단한다. 민법 제750조 적용.".encode("utf-8")
    doc_b = "대법원 2022다22222 판결은 계약 해제의 효과를 다룬다. 민법 제543조 참고.".encode("utf-8")

    drive = _MockChangesDrive()
    drive.items = [
        _item("file_alpha_111111", "판례_알파.txt", data=doc_a),
        _item("file_beta_222222", "판례_베타.txt", data=doc_b),
    ]
    drive.contents = {"file_alpha_111111": doc_a, "file_beta_222222": doc_b}

    lib1 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    s1 = lib1.sync(collect_all=True)
    assert s1["status"] == "READY"
    assert drive.inventory_calls == 1
    assert drive.download_calls == 2
    assert s1["dataset"]["inventory_mode"] == "FULL_INVENTORY"

    # 2회차: 변경 없음 (pending_changes=[])
    lib2 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    s2 = lib2.sync(collect_all=True)
    assert s2["status"] == "READY"
    assert drive.inventory_calls == 1  # 전체 inventory 재호출 없음
    assert drive.changes_calls == 1
    assert drive.download_calls == 2  # 재다운로드 없음
    assert s2["dataset"]["inventory_mode"] == "CHANGES_UNCHANGED"
    assert s2["dataset"]["dataset_up_to_date"] is True
    assert s2["files_reused"] == 2

    hits = lib2.search_citation({"case_number": "2021다11111", "raw_text": "2021다11111"})
    assert len(hits) == 1
    assert hits[0]["file_id"] == "file_alpha_111111"

    law_hits = lib2.search_citation({"law_name": "민법", "article": "제750조", "raw_text": "민법 제750조"})
    assert len(law_hits) == 1
    assert law_hits[0]["file_id"] == "file_alpha_111111"


def test_pos2_incremental_changes_add_modify_delete_updates_dataset_only_for_diffs(tmp_path):
    """신규·수정·삭제 발생 시 해당 파일만 증분 반영하고 삭제 파일의 청크·식별자는 즉시 제거한다."""
    settings = _make_settings(tmp_path)
    doc_keep = "민법 제390조 채무불이행 손해배상 기준 문서.".encode("utf-8")
    doc_mod_v1 = "구버전 2020다33333 판례 요약.".encode("utf-8")
    doc_mod_v2 = "신버전 2024다44444 판례 요약.".encode("utf-8")
    doc_del = "삭제될 2019다55555 판례 문서.".encode("utf-8")
    doc_new = "신규 추가 2025다66666 판례 및 상법 제382조 해설.".encode("utf-8")

    drive = _MockChangesDrive()
    drive.items = [
        _item("file_keep_111111", "유지문서.txt", data=doc_keep),
        _item("file_mod_222222", "수정문서.txt", version="1", data=doc_mod_v1),
        _item("file_del_333333", "삭제문서.txt", data=doc_del),
    ]
    drive.contents = {
        "file_keep_111111": doc_keep,
        "file_mod_222222": doc_mod_v1,
        "file_del_333333": doc_del,
    }

    lib1 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    assert lib1.sync(collect_all=True)["status"] == "READY"
    assert drive.download_calls == 3

    # 2회차 변경: file_mod 수정, file_del 삭제(trashed), file_new 추가, file_keep 유지
    mod_item = _item("file_mod_222222", "수정문서.txt", modified="2026-11-02T00:00:00Z", version="2", data=doc_mod_v2)
    del_item = _item("file_del_333333", "삭제문서.txt", trashed=True, data=doc_del)
    new_item = _item("file_new_444444", "신규문서.txt", data=doc_new)
    drive.items = [drive.items[0], mod_item, new_item]
    drive.contents["file_mod_222222"] = doc_mod_v2
    drive.contents["file_new_444444"] = doc_new
    drive.pending_changes = [
        {"fileId": "file_mod_222222", "removed": False, "file": mod_item},
        {"fileId": "file_del_333333", "removed": False, "file": del_item},
        {"fileId": "file_new_444444", "removed": False, "file": new_item},
    ]

    lib2 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    s2 = lib2.sync(collect_all=True)
    assert s2["status"] == "READY"
    assert s2["dataset"]["inventory_mode"] == "CHANGES_DELTA_APPLIED"
    assert s2["dataset"]["added"] == 1
    assert s2["dataset"]["modified"] == 1
    assert s2["dataset"]["deleted"] == 1
    assert s2["dataset"]["unchanged"] == 1
    assert s2["dataset"]["dataset_up_to_date"] is False
    # file_mod, file_new만 다운로드 (총 3 + 2 = 5)
    assert drive.download_calls == 5
    assert drive.inventory_calls == 1

    assert lib2.search_citation({"case_number": "2019다55555", "raw_text": "2019다55555"}) == []
    assert lib2.search_citation({"case_number": "2020다33333", "raw_text": "2020다33333"}) == []
    assert len(lib2.search_citation({"case_number": "2024다44444", "raw_text": "2024다44444"})) == 1
    assert len(lib2.search_citation({"case_number": "2025다66666", "raw_text": "2025다66666"})) == 1
    assert len(lib2.search_citation({"law_name": "상법", "article": "제382조", "raw_text": "상법 제382조"})) == 1

    with lib2.connect() as db:
        del_ident_cnt = db.execute("SELECT COUNT(*) FROM chunk_identifiers WHERE file_id=?", ("file_del_333333",)).fetchone()[0]
        assert del_ident_cnt == 0


def test_pos3_lazy_backfill_batched_inventory_and_preindex_inventory_stats(tmp_path):
    """기존 캐시 청크 지연 역색인, 다중 폴더 묶음 조회, preindex inventory 통계를 검증한다."""
    settings = _make_settings(tmp_path)
    doc = "대법원 2023다77777 판결 및 근로기준법 제23조 제1항 요건.".encode("utf-8")
    drive = _MockChangesDrive()
    drive.items = [_item("file_legacy_111111", "레거시.txt", data=doc)]
    drive.contents = {"file_legacy_111111": doc}

    lib1 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    assert lib1.sync(collect_all=True)["status"] == "READY"

    # 구버전 DB 상태 시뮬레이션: chunk_identifiers 비우고 identifier_index_version 제거
    with lib1.connect() as db:
        row = db.execute("SELECT revision, payload FROM files WHERE id=?", ("file_legacy_111111",)).fetchone()
        payload = json.loads(row[1])
        payload.pop("identifier_index_version", None)
        with db:
            db.execute("DELETE FROM chunk_identifiers")
            db.execute("UPDATE files SET payload=? WHERE id=?", (json.dumps(payload), "file_legacy_111111"))

    # 2회차 sync에서 재다운로드 없이 chunk_identifiers가 자동 복구되어야 한다
    lib2 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    assert lib2.sync(collect_all=True)["status"] == "READY"
    assert drive.download_calls == 1
    status = lib2.dataset_status()
    assert status["initialized"] is True
    assert status["identifiers_cached"] >= 2
    assert len(lib2.search_citation({"law_name": "근로기준법", "article": "제23조제1항", "raw_text": "근로기준법 제23조 제1항"})) == 1

    # preindex_drive_library가 summary["inventory"] 기반 통계도 정확히 집계하는지 확인
    report = preindex_drive_library(
        settings,
        max_rounds=2,
        client_factory=lambda **kw: drive,
        extractor=_simple_extractor({}),
    )
    assert report.converged is True
    assert report.files_complete == 1
    assert report.pages_total == 1
    assert report.pages_read == 1
    assert report.page_completion_rate == 1.0

    # DriveClient.batched_inventory 다중 폴더 묶음 질의 검증
    requests_seen: list[tuple[str, dict]] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.replace("/drive/v3/", "")
        params = dict(request.url.params)
        requests_seen.append((path, params))
        if path == "files/folder_root_123456":
            return httpx.Response(200, json={"id": "folder_root_123456", "name": "root", "mimeType": FOLDER, "trashed": False})
        if path == "files":
            return httpx.Response(200, json={
                "files": [
                    {"id": "sub_folder_111111", "name": "판례", "mimeType": FOLDER, "parents": ["folder_root_123456"]},
                    _item("file_in_sub_111111", "세부.txt", parent="sub_folder_111111", data=b"abc"),
                ]
            })
        return httpx.Response(404, json={})

    client = DriveClient(deadline=9999999999.0, transport=httpx.MockTransport(_handler), headers={"Authorization": "Bearer test"})
    try:
        items = client.batched_inventory(
            "folder_root_123456",
            {"folder_root_123456": "", "sub_folder_111111": "판례"},
        )
        assert len(items) == 1
        assert items[0]["folder_path"] == "판례"
        list_calls = [r for r in requests_seen if r[0] == "files"]
        assert len(list_calls) == 1
    finally:
        client.close()


def test_ctrl1_permission_revoked_and_trashed_root_fail_closed_with_snapshot(tmp_path):
    """스냅샷·캐시가 존재해도 루트 휴지통 또는 권한 회수 시 기존 데이터셋을 절대 반환하지 않는다 (Fail-Closed)."""
    settings = _make_settings(tmp_path)
    doc = "대법원 2021다99999 판결 본문.".encode("utf-8")
    drive = _MockChangesDrive()
    drive.items = [_item("file_secret_111111", "보안문서.txt", data=doc)]
    drive.contents = {"file_secret_111111": doc}

    lib1 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    assert lib1.sync(collect_all=True)["status"] == "READY"
    assert len(lib1.eligible) == 1

    # 1) 루트 폴더가 휴지통에 들어가면 Changes API 경로에서도 Fail-Closed
    drive.root_trashed = True
    lib2 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    s2 = lib2.sync(collect_all=True)
    assert s2["status"] == "UNAVAILABLE"
    assert lib2.eligible == {}
    assert lib2.search_citation({"case_number": "2021다99999", "raw_text": "2021다99999"}) == []

    # 2) 파일 다운로드 권한이 회수(canDownload=False)되면 Changes 델타로 즉시 색인·청크 제거
    drive.root_trashed = False
    revoked_item = _item("file_secret_111111", "보안문서.txt", can_download=False, data=doc)
    drive.pending_changes = [{"fileId": "file_secret_111111", "removed": False, "file": revoked_item}]
    lib3 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    s3 = lib3.sync(collect_all=True)
    assert s3["status"] == "PARTIAL"
    assert lib3.eligible == {}
    assert lib3.search_citation({"case_number": "2021다99999", "raw_text": "2021다99999"}) == []


def test_ctrl2_api_key_mode_and_changes_403_fallback_without_error(tmp_path):
    """API-key 모드 또는 /changes 403 응답 시 표준/묶음 목록 조회로 안전하게 폴백한다."""
    settings = _make_settings(tmp_path)
    doc = "민법 제105조 법률행위 해석 문서.".encode("utf-8")

    drive = _MockChangesDrive(credential_mode="api_key")
    drive.items = [_item("file_public_111111", "공개문서.txt", data=doc)]
    drive.contents = {"file_public_111111": doc}

    lib1 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    s1 = lib1.sync(collect_all=True)
    assert s1["status"] == "READY"
    assert drive.changes_calls == 0

    # credential_mode가 service_account여도 /changes가 403을 주면 inventory로 폴백해 성공해야 한다
    drive.credential_mode = "service_account"
    drive.changes_error = "DRIVE_HTTP_403"
    lib2 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    # 1차에 api_key여서 start_page_token이 없으므로 한 번 토큰 확보 후 다음 회차에 403 테스트
    assert lib2.sync(collect_all=True)["status"] == "READY"
    lib3 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    s3 = lib3.sync(collect_all=True)
    assert s3["status"] == "READY"
    assert drive.changes_calls >= 1
    assert s3["dataset"]["inventory_mode"] == "FULL_INVENTORY"


def test_ctrl3_identifier_index_never_leaks_wrong_law_or_inline_reprocess_flag(tmp_path, monkeypatch):
    """조문 번호가 같아도 법령명이 다르면 결속하지 않으며, LV_RAG_INLINE_REPROCESS=false면 인라인 재처리를 보류한다."""
    settings = _make_settings(tmp_path)
    doc = "형법 제23조 정당방위에 관한 설명이다.".encode("utf-8")
    drive = _MockChangesDrive()
    drive.items = [_item("file_law_111111", "형법자료.txt", data=doc)]
    drive.contents = {"file_law_111111": doc}

    lib = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    assert lib.sync(collect_all=True)["status"] == "READY"

    # article 키('제23조')는 chunk_identifiers에 존재하지만 법령명이 근로기준법이므로 결과는 0건이어야 한다.
    assert lib.search_citation({"law_name": "근로기준법", "article": "제23조", "raw_text": "근로기준법 제23조"}) == []
    assert len(lib.search_citation({"law_name": "형법", "article": "제23조", "raw_text": "형법 제23조"})) == 1

    # LV_RAG_INLINE_REPROCESS=false 제어 확인
    monkeypatch.setenv("LV_RAG_INLINE_REPROCESS", "false")
    monkeypatch.setenv("LV_OCR_FALLBACK_ENGINE", "rapidocr")
    monkeypatch.setenv("LV_OCR_FALLBACK_MODE", "on_low_quality")
    lib_inline = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    s_inline = lib_inline.sync(collect_all=True)
    assert s_inline["ocr_reprocess"]["auto_reprocess_enabled"] is False


def test_api_reference_dataset_endpoints(tmp_path, monkeypatch):
    """GET/POST /api/settings/reference-dataset 엔드포인트가 상태 조회 및 관리자 동기화를 수행한다."""
    from fastapi.testclient import TestClient

    from apps.api import db as db_module
    from apps.api.auth import ROLE_ADMIN, ROLE_MEMBER, hash_password, issue_session
    from apps.api.db import Organization, User, get_session_factory
    from apps.api.main import create_app
    from apps.api.routers import settings_router

    monkeypatch.setenv("LV_AUTH_MODE", "multi-user")
    test_settings = _make_settings(tmp_path / "storage", folder_id="folder_api_123456")
    monkeypatch.setattr(settings_router, "get_settings", lambda: test_settings)

    db_module.reset_engine()
    app = create_app()
    session = get_session_factory()()
    try:
        org = session.query(Organization).first() or Organization(name="테스트기관")
        if org.id is None:
            session.add(org)
            session.flush()
        admin = User(
            email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
            display_name="관리자",
            role=ROLE_ADMIN,
            approval_status="APPROVED",
            organization_id=org.id,
            password_hash=hash_password("pw-12345678"),
        )
        member = User(
            email=f"user-{uuid.uuid4().hex[:8]}@example.com",
            display_name="일반사용자",
            role=ROLE_MEMBER,
            approval_status="APPROVED",
            organization_id=org.id,
            password_hash=hash_password("pw-12345678"),
        )
        session.add_all([admin, member])
        session.commit()
        admin_tok = issue_session(session, admin)
        member_tok = issue_session(session, member)
    finally:
        session.close()

    client = TestClient(app, base_url="https://testserver")
    # 일반 사용자는 settings 조회·동기화 모두 불가 (403)
    res_member_get = client.get("/api/settings/reference-dataset", headers={"Authorization": f"Bearer {member_tok}"})
    assert res_member_get.status_code == 403
    res_forbidden = client.post("/api/admin/reference-dataset/sync", headers={"Authorization": f"Bearer {member_tok}"})
    assert res_forbidden.status_code == 403

    res_get = client.get("/api/settings/reference-dataset", headers={"Authorization": f"Bearer {admin_tok}"})
    assert res_get.status_code == 200
    assert res_get.json()["configured"] is True

    monkeypatch.setattr(
        settings_router,
        "preindex_drive_library",
        lambda settings, **kw: SimpleNamespace(
            to_dict=lambda: {"status": "READY", "converged": True, "rounds_executed": 1, "files_complete": 2}
        ),
    )
    res_sync = client.post(
        "/api/admin/reference-dataset/sync",
        json={"max_rounds": 2, "reprocess_low_quality": True},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert res_sync.status_code == 200
    body = res_sync.json()
    assert body["report"]["status"] == "READY"
    assert body["report"]["converged"] is True
    assert "dataset" in body


def test_pos4_rename_with_same_md5_reuses_chunks_without_redownload(tmp_path):
    """파일 이름·폴더 위치만 바뀌고 md5Checksum이 같으면 재다운로드·재추출 없이 기존 색인을 승계한다."""
    settings = _make_settings(tmp_path)
    doc = "대법원 2023다88888 판결 본문.".encode("utf-8")
    drive = _MockChangesDrive()
    drive.items = [_item("file_rename_111111", "초기이름.txt", data=doc)]
    drive.contents = {"file_rename_111111": doc}

    lib1 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    assert lib1.sync(collect_all=True)["status"] == "READY"
    assert drive.download_calls == 1

    renamed_item = _item("file_rename_111111", "변경된이름.txt", modified="2026-11-03T00:00:00Z", version="2", data=doc)
    drive.items = [renamed_item]
    drive.pending_changes = [{"fileId": "file_rename_111111", "removed": False, "file": renamed_item}]

    lib2 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    s2 = lib2.sync(collect_all=True)
    assert s2["status"] == "READY"
    assert drive.download_calls == 1  # 재다운로드 0회
    assert s2["inventory"][0].get("metadata_only_renamed_or_moved") is True
    hits = lib2.search_citation({"case_number": "2023다88888", "raw_text": "2023다88888"})
    assert len(hits) == 1
    assert hits[0]["title"] == "변경된이름.txt"


def test_ctrl4_modified_extract_failure_preserves_prior_verified_index(tmp_path):
    """수정본 추출이 실패해도 기존 정상 색인을 덮어쓰지 않고 유지하며 실패 상태를 표시한다."""
    settings = _make_settings(tmp_path)
    doc_v1 = "대법원 2022다99999 기존 정상 판결 본문.".encode("utf-8")
    doc_v2 = "손상된 수정본 바이트".encode("utf-8")
    drive = _MockChangesDrive()
    drive.items = [_item("file_update_111111", "갱신대상.txt", version="1", data=doc_v1)]
    drive.contents = {"file_update_111111": doc_v1}

    lib1 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_simple_extractor({}))
    assert lib1.sync(collect_all=True)["status"] == "READY"

    mod_v2 = _item("file_update_111111", "갱신대상.txt", modified="2026-11-04T00:00:00Z", version="2", data=doc_v2)
    drive.items = [mod_v2]
    drive.contents["file_update_111111"] = doc_v2
    drive.pending_changes = [{"fileId": "file_update_111111", "removed": False, "file": mod_v2}]

    def _failing_extractor(data: bytes, filename: str, mime: str, **kwargs):
        raise ReferenceError("REFERENCE_PARSE_TIMEOUT")

    lib2 = ReferenceLibrary(settings, client_factory=lambda **kw: drive, extractor=_failing_extractor)
    s2 = lib2.sync(collect_all=True)
    assert s2["inventory"][0].get("modified_update_failed") is True
    assert s2["inventory"][0].get("fallback_to_prior_version") is True
    assert s2["inventory"][0].get("last_update_error") == "REFERENCE_PARSE_TIMEOUT"
    assert lib2.dataset_status()["failed_updates"] == 1

    # 기존 정상 색인이 그대로 유지되어 검색 가능해야 한다
    hits = lib2.search_citation({"case_number": "2022다99999", "raw_text": "2022다99999"})
    assert len(hits) == 1

