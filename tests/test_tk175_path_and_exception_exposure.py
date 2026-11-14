"""TK-175: main의 기존 CodeQL 경고(제품 코드 11건) — 경로 주입(storage·project_purge)과 예외 문구 노출(진단 응답).

경로 검사는 CodeQL이 인정하는 꼴(정규화한 경로 값 자체에 구분자 붙인 접두 검사 하나)로 바꾸고, 동작은 그대로 둔다.
값은 모두 합성이다.
"""
from __future__ import annotations

import os

import pytest

from packages.common.storage import (EncryptedObjectStorage, LocalObjectStorage, _project_dirs,
                                     resolve_within)


@pytest.mark.parametrize("parts", [("a.pdf",), ("prj_1", "a.pdf"), ("prj_1/sub/a.pdf",)])
def test_paths_inside_the_root_are_returned_resolved(tmp_path, parts):
    root = tmp_path / "store"
    root.mkdir()
    got = resolve_within(root, *parts)
    assert got == os.path.realpath(os.path.join(root, *parts)) and got.startswith(os.path.join(os.path.realpath(root), ""))


@pytest.mark.parametrize("key", ["../outside.pdf", "../store2/a.pdf", "/etc/passwd", "a/../../x", ""])
def test_paths_escaping_the_root_or_naming_a_sibling_are_rejected(tmp_path, key):
    (tmp_path / "store").mkdir()
    (tmp_path / "store2").mkdir()
    with pytest.raises(ValueError):
        resolve_within(tmp_path / "store", key)


def test_symlink_pointing_outside_is_rejected(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    (tmp_path / "secret").mkdir()
    os.symlink(tmp_path / "secret", root / "link")
    with pytest.raises(ValueError):
        resolve_within(root, "link/x.pdf")


def test_local_storage_round_trip_and_traversal_refusal(tmp_path):
    storage = LocalObjectStorage(root=tmp_path / "store")
    key = storage.put_original("prj_1/a.pdf", b"case")
    assert storage.get(key) == b"case" and storage.exists(key) and storage.path(key).is_file()
    for bad in ("../x", "originals/../../store2/x"):
        with pytest.raises(ValueError):
            storage.get(bad)


def test_project_dirs_are_exactly_one_level_under_each_area(tmp_path):
    root = tmp_path / "store"
    LocalObjectStorage(root=root)
    dirs = list(_project_dirs(root, "prj_1"))
    real = os.path.realpath(root)
    assert [str(d) for d in dirs] == [os.path.join(real, "originals", "prj_1"), os.path.join(real, "derivatives", "prj_1")]
    for bad in ("../x", "a/b", "prj\n", ""):
        with pytest.raises(ValueError):
            list(_project_dirs(root, bad))


def test_encrypted_cache_rejects_a_sibling_of_the_cache_root(tmp_path, monkeypatch):
    from packages.pii_engine.key_provider import default_key_provider

    monkeypatch.setenv("LV_VAULT_KEY_PROVIDER", "env")
    monkeypatch.setenv("LV_PSEUDONYM_SECRET", "tk175-synthetic-secret")
    storage = EncryptedObjectStorage(LocalObjectStorage(root=tmp_path / "store"), key_provider=default_key_provider(),
                                     cache_root=tmp_path / "cache")
    key = storage.put_original("prj_1/a.pdf", b"case")
    assert storage.path(key).read_bytes() == b"case"
    (tmp_path / "cache2").mkdir()
    with pytest.raises(ValueError):
        storage.path("../cache2/x")


def test_purge_removes_the_vault_file_of_a_valid_project(tmp_path, monkeypatch):
    import apps.api.project_purge as purge

    monkeypatch.setattr(purge, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(purge, "get_storage", lambda: LocalObjectStorage(root=tmp_path / "store"))
    (tmp_path / "pii_vault").mkdir()
    vault = tmp_path / "pii_vault" / "prj_1.vault"
    vault.write_bytes(b"v")
    other = tmp_path / "pii_vault" / "prj_2.vault"
    other.write_bytes(b"v")
    result = purge.purge_files("prj_1")
    assert not vault.exists() and other.exists() and result["file_errors"] == []


def test_worker_state_error_carries_only_the_exception_type(monkeypatch):
    import apps.api.services as services
    from apps.api.capabilities import _worker_state

    def broken():
        raise RuntimeError("synthetic-internal-detail /srv/secret")

    monkeypatch.setattr(services, "get_runner", broken)
    state = _worker_state()
    assert state["error"] == "RuntimeError" and "secret" not in str(state)


def test_startup_encryption_error_does_not_echo_the_exception_text(tmp_path, monkeypatch):
    import apps.api.db as db
    import apps.api.main as main_module
    from packages.common.storage import StorageKeyConfigurationError, reset_storage, storage_encryption_error

    def broken():
        try:
            raise ValueError("synthetic-key-material-AAAA")
        except ValueError as exc:
            raise StorageKeyConfigurationError(f"키 공급자를 만들 수 없습니다. (ValueError: {exc})") from exc

    monkeypatch.setenv("LV_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LV_DATABASE_URL", f"sqlite:///{tmp_path}/boot.db")
    monkeypatch.setattr(main_module, "verify_storage_encryption_config", broken)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    reset_storage()
    try:
        main_module.create_app()
        message = storage_encryption_error()
        assert message and "AAAA" not in message and "ValueError" in message and "서버 로그" in message
    finally:
        db._engine = db._SessionLocal = None
        reset_storage()
