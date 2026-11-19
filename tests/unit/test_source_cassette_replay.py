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

    data = json.loads(path.read_text(encoding="utf-8"))
    data["recorded_at"] = "2020-01-01T00:00:00+00:00"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CassetteError, match="REPLAY_EXPIRED"):
        load_cassette_response("law_go_kr", url, params=params, cassette_dir=tmp_path, max_age_days=7.0)

    data["recorded_at"] = "2099-01-01T00:00:00+00:00"
    data["content_sha256"] = "0" * 64
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CassetteError, match="REPLAY_HASH_MISMATCH"):
        load_cassette_response("law_go_kr", url, params=params, cassette_dir=tmp_path)
