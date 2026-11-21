"""Unit tests for deterministic source cassette recording and replay (P0 PR-03)."""
from __future__ import annotations

import json
import pytest
import httpx

from packages.common.enums import AdapterStatus
from packages.source_adapters.cassette import (
    CassetteError,
    CassettePIIError,
    compute_cassette_key,
    load_cassette_response,
    record_cassette_entry,
    sanitize_params,
)
from packages.source_adapters.law_go_kr import LawGoKrAdapter
from packages.source_adapters.transport import SourceRequestStopped, source_get, source_lookup_session


def test_cassette_redacts_credentials_and_blocks_pii(tmp_path):
    key1 = compute_cassette_key(
        "law_go_kr",
        "https://www.law.go.kr/DRF/lawSearch.do",
        params={"OC": "secret_id_1", "target": "prec", "nb": "2020다12345"},
    )
    key2 = compute_cassette_key(
        "law_go_kr",
        "https://www.law.go.kr/DRF/lawSearch.do",
        params={"OC": "secret_id_2", "target": "prec", "nb": "2020다12345"},
    )
    assert key1 == key2
    assert "OC" not in sanitize_params({"OC": "secret", "nb": "2020다12345"})

    pii_resp = httpx.Response(200, content="당사자 900101-1234567 확인".encode("utf-8"))
    with pytest.raises(CassettePIIError):
        record_cassette_entry(
            "law_go_kr",
            "https://www.law.go.kr/DRF/lawSearch.do",
            params={"nb": "2020다12345"},
            headers={},
            response=pii_resp,
            cassette_dir=tmp_path,
        )


def test_cassette_record_and_offline_replay_via_transport(tmp_path, monkeypatch):
    url = "https://www.law.go.kr/DRF/lawSearch.do"
    params = {"OC": "dev_oc", "target": "prec", "nb": "2021다99999"}
    sample_xml = b'{"PrecSearch": {"totalCnt": "1"}}'

    record_cassette_entry(
        "law_go_kr",
        url,
        params=params,
        headers=None,
        response=httpx.Response(200, headers={"content-type": "application/json"}, content=sample_xml),
        cassette_dir=tmp_path,
    )

    monkeypatch.setenv("LV_ALLOW_NETWORK", "0")
    monkeypatch.setenv("LV_SOURCE_REPLAY_MODE", "REPLAY")
    monkeypatch.setenv("LV_SOURCE_CASSETTE_DIR", str(tmp_path))

    adapter = LawGoKrAdapter()
    assert adapter.status() == AdapterStatus.READY

    with source_lookup_session(30):
        replayed = source_get("law_go_kr", url, params={"OC": "other_oc", "target": "prec", "nb": "2021다99999"})
    assert replayed.status_code == 200
    assert replayed.content == sample_xml

    with source_lookup_session(30):
        with pytest.raises(SourceRequestStopped) as exc_info:
            source_get("law_go_kr", url, params={"target": "prec", "nb": "9999다00000"})
    assert exc_info.value.status == AdapterStatus.DISABLED
    assert "REPLAY_MISS" in str(exc_info.value)


def test_cassette_detects_tampered_hash_and_expiration(tmp_path):
    url = "https://www.law.go.kr/DRF/lawService.do"
    params = {"target": "prec", "ID": "12345"}
    path = record_cassette_entry(
        "law_go_kr",
        url,
        params=params,
        headers=None,
        response=httpx.Response(200, content=b"<prec>ok</prec>"),
        cassette_dir=tmp_path,
    )

    req_key = compute_cassette_key("law_go_kr", url, params=params)
    expected_path = tmp_path / f"law_go_kr_{req_key[:24]}.json"
    assert path.resolve() == expected_path.resolve()

    data = json.loads(expected_path.read_text(encoding="utf-8"))
    data["recorded_at"] = "2020-01-01T00:00:00+00:00"
    expected_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CassetteError, match="REPLAY_EXPIRED"):
        load_cassette_response("law_go_kr", url, params=params, cassette_dir=tmp_path, max_age_days=7.0)

    data["recorded_at"] = "2099-01-01T00:00:00+00:00"
    data["content_sha256"] = "0" * 64
    expected_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CassetteError, match="REPLAY_HASH_MISMATCH"):
        load_cassette_response("law_go_kr", url, params=params, cassette_dir=tmp_path)


@pytest.mark.parametrize("adapter_id", ["law_go_kr", "scourt-precedent", "moleg_01"])
def test_cassette_allows_valid_adapter_identifiers(tmp_path, adapter_id):
    inside = tmp_path / "inside"
    url = "https://www.law.go.kr/DRF/lawSearch.do"
    params = {"target": "prec", "nb": "2022다10001"}
    written = record_cassette_entry(
        adapter_id,
        url,
        params=params,
        headers=None,
        response=httpx.Response(200, content=b'{"ok": true}'),
        cassette_dir=inside,
    )
    assert written.parent == inside.resolve()
    loaded = load_cassette_response(adapter_id, url, params=params, cassette_dir=inside)
    assert loaded.status_code == 200
    assert loaded.content == b'{"ok": true}'


@pytest.mark.parametrize(
    "bad_adapter",
    ["../escape", "../../etc/passwd", "a/b", "a\\b", "", "bad adapter!"],
)
def test_cassette_blocks_path_traversal_and_invalid_adapters(tmp_path, bad_adapter):
    inside = tmp_path / "inside"
    inside.mkdir()
    url = "https://www.law.go.kr/DRF/lawSearch.do"
    params = {"target": "prec", "nb": "2022다10001"}

    with pytest.raises(CassetteError):
        record_cassette_entry(
            bad_adapter,
            url,
            params=params,
            headers=None,
            response=httpx.Response(200, content=b"escaped"),
            cassette_dir=inside,
        )
    with pytest.raises(CassetteError):
        load_cassette_response(bad_adapter, url, params=params, cassette_dir=inside)
    assert list(tmp_path.iterdir()) == [inside]


def test_cassette_blocks_symlink_escape_and_traversal_env_dir(tmp_path, monkeypatch):
    inside = tmp_path / "inside"
    inside.mkdir()
    outside_secret = tmp_path / "outside_secret.json"
    outside_secret.write_text('{"secret": true}', encoding="utf-8")

    url = "https://www.law.go.kr/DRF/lawSearch.do"
    params = {"target": "prec", "nb": "2022다10002"}
    req_key = compute_cassette_key("law_go_kr", url, params=params)
    symlink_path = inside / f"law_go_kr_{req_key[:24]}.json"
    symlink_path.symlink_to(outside_secret)

    with pytest.raises(CassetteError):
        load_cassette_response("law_go_kr", url, params=params, cassette_dir=inside)
    with pytest.raises(CassetteError):
        record_cassette_entry(
            "law_go_kr",
            url,
            params=params,
            headers=None,
            response=httpx.Response(200, content=b"overwrite"),
            cassette_dir=inside,
        )
    assert outside_secret.read_text(encoding="utf-8") == '{"secret": true}'

    monkeypatch.setenv("LV_SOURCE_CASSETTE_DIR", str(inside / ".." / "outside"))
    with pytest.raises(CassetteError):
        load_cassette_response("law_go_kr", url, params=params)


def test_cassette_toctou_symlink_swap_blocks_record_replay_and_root_escape(tmp_path, monkeypatch):
    import packages.source_adapters.cassette as cassette_mod

    inside = tmp_path / "inside"
    inside.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text('{"secret": "untouched"}', encoding="utf-8")

    url = "https://www.law.go.kr/DRF/lawSearch.do"
    params = {"target": "prec", "nb": "2022다10003"}
    req_key = compute_cassette_key("law_go_kr", url, params=params)
    target_link = inside / f"law_go_kr_{req_key[:24]}.json"

    # 1) RECORD TOCTOU: plant symlink right after _safe_cassette_file passes
    orig_safe = cassette_mod._safe_cassette_file

    def _swap_after_check(root_dir, adapter, rkey):
        res = orig_safe(root_dir, adapter, rkey)
        if not target_link.exists() and not target_link.is_symlink():
            target_link.symlink_to(outside)
        return res

    monkeypatch.setattr(cassette_mod, "_safe_cassette_file", _swap_after_check)
    with pytest.raises(CassetteError):
        record_cassette_entry(
            "law_go_kr",
            url,
            params=params,
            headers=None,
            response=httpx.Response(200, content=b'{"hijack": true}'),
            cassette_dir=inside,
        )
    assert outside.read_text(encoding="utf-8") == '{"secret": "untouched"}'

    # 2) REPLAY TOCTOU: O_NOFOLLOW blocks symlink planted right after _safe_cassette_file
    with pytest.raises(CassetteError):
        load_cassette_response("law_go_kr", url, params=params, cassette_dir=inside)
    monkeypatch.undo()
    target_link.unlink()

    # 3) Root swap TOCTOU: swap root dir to a symlink after _resolve_cassette_root
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()
    swappable = tmp_path / "swappable"
    swappable.mkdir()
    orig_resolve = cassette_mod._resolve_cassette_root

    def _swap_root(cdir):
        resolved = orig_resolve(cdir)
        swappable.rmdir()
        swappable.symlink_to(outside_dir)
        return resolved

    monkeypatch.setattr(cassette_mod, "_resolve_cassette_root", _swap_root)
    with pytest.raises(CassetteError):
        record_cassette_entry(
            "law_go_kr",
            url,
            params=params,
            headers=None,
            response=httpx.Response(200, content=b'{"root_escape": true}'),
            cassette_dir=swappable,
        )
    assert list(outside_dir.iterdir()) == []

    # 4) Reject cassette root outside allowed roots (/etc, /var, root symlink to /etc)
    monkeypatch.undo()
    monkeypatch.setenv("LV_SOURCE_CASSETTE_DIR", "/etc")
    with pytest.raises(CassetteError):
        load_cassette_response("law_go_kr", url, params=params)
    etc_link = tmp_path / "etc_link"
    etc_link.symlink_to("/etc")
    monkeypatch.setenv("LV_SOURCE_CASSETTE_DIR", str(etc_link))
    with pytest.raises(CassetteError):
        load_cassette_response("law_go_kr", url, params=params)
