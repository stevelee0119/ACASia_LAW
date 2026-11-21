"""Deterministic HTTP snapshot cassette recorder and replayer for official source adapters (P0 PR-03).

Modes (`LV_SOURCE_REPLAY_MODE`):
- `LIVE` (default): normal network execution.
- `RECORD`: performs live requests (when network is allowed), redacts credential parameters/headers,
  checks for high-risk PII leakage, and writes deterministic JSON snapshots to `LV_SOURCE_CASSETTE_DIR`.
- `REPLAY`: serves responses strictly from `LV_SOURCE_CASSETTE_DIR` with zero network I/O
  (compatible with `LV_ALLOW_NETWORK=0`). Fails closed (`AdapterStatus.DISABLED`) on cache miss,
  hash mismatch, or snapshot expiration (`LV_SOURCE_CASSETTE_MAX_AGE_DAYS`).
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, Mapping, Optional

import httpx

from packages.common.enums import AdapterStatus

CASSETTE_SCHEMA_VERSION = 1

REDACTED_PARAM_KEYS = frozenset({
    "oc",
    "key",
    "apikey",
    "api_key",
    "access_token",
    "token",
    "secret",
    "password",
})

REDACTED_HEADER_KEYS = frozenset({
    "authorization",
    "x-api-key",
    "proxy-authorization",
    "cookie",
    "set-cookie",
})

# High-risk PII patterns (RRN / Foreigner Reg No) that must never be stored in a shared test cassette.
_HIGH_RISK_PII_RE = re.compile(r"\b\d{6}-[1-8]\d{6}\b")
_SAFE_ADAPTER_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SAFE_HEX_RE = re.compile(r"^[0-9a-f]{24}$")


class CassetteError(RuntimeError):
    """Base error for cassette recording/replay violations."""


class CassettePIIError(CassetteError):
    """Raised when high-risk PII is detected in a query or payload during cassette recording."""


def _validate_adapter_id(adapter: str) -> str:
    clean = str(adapter or "").strip()
    if not _SAFE_ADAPTER_RE.fullmatch(clean):
        raise CassetteError(f"유효하지 않은 카세트 어댑터 식별자입니다: {adapter!r}")
    return clean


def _resolve_cassette_root(cassette_dir: Optional[Path]) -> Path:
    raw_dir = cassette_dir if cassette_dir is not None else get_cassette_dir()
    if raw_dir is None:
        raise CassetteError("LV_SOURCE_CASSETTE_DIR가 설정되지 않았습니다")
    raw_str = str(raw_dir)
    if "\x00" in raw_str or ".." in Path(raw_str).parts:
        raise CassetteError("허용되지 않는 카세트 루트 경로입니다")
    if Path(raw_str).is_symlink():
        raise CassetteError("심볼릭 링크 카세트 루트 경로는 허용되지 않습니다")
    return Path(os.path.realpath(os.path.normpath(raw_str)))


def _safe_cassette_file(root_dir: Path, adapter: str, req_key: str) -> Path:
    safe_adapter = _validate_adapter_id(adapter)
    key_prefix = str(req_key or "")[:24].lower()
    if not _SAFE_HEX_RE.fullmatch(key_prefix):
        raise CassetteError("유효하지 않은 카세트 요청 키입니다")
    base_str = os.path.realpath(str(root_dir))
    candidate_str = os.path.join(base_str, f"{safe_adapter}_{key_prefix}.json")
    if os.path.islink(candidate_str):
        raise CassetteError("심볼릭 링크 카세트 파일은 허용되지 않습니다")
    resolved_str = os.path.realpath(candidate_str)
    if os.path.commonpath([base_str, resolved_str]) != base_str or not resolved_str.startswith(base_str + os.sep):
        raise CassetteError("카세트 파일 경로가 허용된 디렉터리 경계를 벗어났습니다")
    return Path(resolved_str)


def get_replay_mode() -> str:
    mode = (os.getenv("LV_SOURCE_REPLAY_MODE") or "LIVE").strip().upper()
    return mode if mode in {"LIVE", "RECORD", "REPLAY"} else "LIVE"


def get_cassette_dir() -> Optional[Path]:
    raw = (os.getenv("LV_SOURCE_CASSETTE_DIR") or "").strip()
    if not raw:
        return None
    if "\x00" in raw or ".." in Path(raw).parts:
        raise CassetteError("유효하지 않은 LV_SOURCE_CASSETTE_DIR 경로입니다")
    if Path(raw).is_symlink():
        raise CassetteError("심볼릭 링크 LV_SOURCE_CASSETTE_DIR 경로는 허용되지 않습니다")
    return Path(os.path.realpath(os.path.normpath(raw)))


def get_max_age_days() -> Optional[float]:
    raw = (os.getenv("LV_SOURCE_CASSETTE_MAX_AGE_DAYS") or "").strip()
    if not raw:
        return None
    try:
        val = float(raw)
        return val if val > 0 else None
    except ValueError:
        return None


def replay_mode_active() -> bool:
    """True when deterministic offline replay mode is enabled with a configured cassette directory."""
    return get_replay_mode() == "REPLAY" and get_cassette_dir() is not None


def record_mode_active() -> bool:
    """True when cassette recording mode is enabled with a configured cassette directory."""
    return get_replay_mode() == "RECORD" and get_cassette_dir() is not None


def sanitize_params(params: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not params:
        return {}
    cleaned: Dict[str, Any] = {}
    for k, v in sorted(params.items(), key=lambda item: str(item[0])):
        key_str = str(k)
        if key_str.lower() in REDACTED_PARAM_KEYS:
            continue
        cleaned[key_str] = v
    return cleaned


def sanitize_headers(headers: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    if not headers:
        return {}
    cleaned: Dict[str, str] = {}
    for k, v in sorted(headers.items(), key=lambda item: str(item[0]).lower()):
        key_str = str(k)
        if key_str.lower() in REDACTED_HEADER_KEYS:
            continue
        cleaned[key_str] = str(v)
    return cleaned


def compute_cassette_key(
    adapter: str,
    url: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    headers: Optional[Mapping[str, Any]] = None,
) -> str:
    """Compute a credential-independent deterministic SHA-256 request key."""
    canonical = {
        "adapter": str(adapter or "").strip(),
        "url": str(url or "").strip(),
        "params": sanitize_params(params),
        "headers": sanitize_headers(headers),
    }
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _check_no_pii(text: str) -> None:
    if _HIGH_RISK_PII_RE.search(text or ""):
        raise CassettePIIError("카세트 스냅샷에 주민등록번호 형식의 민감 개인정보가 포함되어 저장을 거부합니다")


def record_cassette_entry(
    adapter: str,
    url: str,
    *,
    params: Optional[Mapping[str, Any]],
    headers: Optional[Mapping[str, Any]],
    response: httpx.Response,
    cassette_dir: Optional[Path] = None,
) -> Path:
    """Persist a sanitized HTTP response into the cassette directory."""
    safe_adapter = _validate_adapter_id(adapter)
    target_dir = _resolve_cassette_root(cassette_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    clean_params = sanitize_params(params)
    clean_headers = sanitize_headers(headers)
    _check_no_pii(json.dumps(clean_params, ensure_ascii=False, default=str))

    raw_bytes = bytes(response.content or b"")
    text_preview = raw_bytes.decode("utf-8", errors="ignore")
    _check_no_pii(text_preview)

    req_key = compute_cassette_key(safe_adapter, url, params=params, headers=headers)
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    resp_headers = {
        k: v
        for k, v in response.headers.items()
        if k.lower() not in ({"content-encoding", "content-length", "transfer-encoding"} | REDACTED_HEADER_KEYS)
    }

    entry = {
        "schema_version": CASSETTE_SCHEMA_VERSION,
        "request_key": req_key,
        "adapter": safe_adapter,
        "url": url,
        "params": clean_params,
        "request_headers": clean_headers,
        "status_code": int(response.status_code),
        "response_headers": resp_headers,
        "content_sha256": content_hash,
        "body_b64": base64.b64encode(raw_bytes).decode("ascii"),
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    file_path = _safe_cassette_file(target_dir, safe_adapter, req_key)
    file_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return file_path


def load_cassette_response(
    adapter: str,
    url: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    headers: Optional[Mapping[str, Any]] = None,
    cassette_dir: Optional[Path] = None,
    max_age_days: Optional[float] = None,
) -> httpx.Response:
    """Load and verify a recorded HTTP response from the cassette directory.

    Raises `CassetteError` on missing file, integrity hash mismatch, or expired snapshot.
    """
    safe_adapter = _validate_adapter_id(adapter)
    target_dir = _resolve_cassette_root(cassette_dir)

    req_key = compute_cassette_key(safe_adapter, url, params=params, headers=headers)
    file_path = _safe_cassette_file(target_dir, safe_adapter, req_key)
    if not file_path.is_file():
        raise CassetteError(f"REPLAY_MISS: 카세트 스냅샷을 찾을 수 없습니다 ({safe_adapter}, key={req_key[:12]})")

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CassetteError(f"REPLAY_CORRUPT: 카세트 JSON 파싱 실패 ({file_path.name})") from exc

    if data.get("request_key") != req_key:
        raise CassetteError(f"REPLAY_KEY_MISMATCH: 요청 서명이 일치하지 않습니다 ({file_path.name})")

    try:
        raw_bytes = base64.b64decode(str(data.get("body_b64") or ""))
    except Exception as exc:
        raise CassetteError(f"REPLAY_CORRUPT: 본문 base64 디코딩 실패 ({file_path.name})") from exc

    actual_hash = hashlib.sha256(raw_bytes).hexdigest()
    if actual_hash != data.get("content_sha256"):
        raise CassetteError(f"REPLAY_HASH_MISMATCH: 카세트 본문 해시 불일치 ({file_path.name})")

    effective_max_age = max_age_days if max_age_days is not None else get_max_age_days()
    if effective_max_age is not None:
        recorded_raw = str(data.get("recorded_at") or "").strip()
        if not recorded_raw:
            raise CassetteError(f"REPLAY_EXPIRED: 카세트 기록 시각(recorded_at)이 없습니다 ({file_path.name})")
        try:
            recorded_dt = datetime.fromisoformat(recorded_raw.replace("Z", "+00:00"))
            if recorded_dt.tzinfo is None:
                recorded_dt = recorded_dt.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise CassetteError(f"REPLAY_EXPIRED: 카세트 기록 시각 형식 오류 ({recorded_raw})") from exc
        age_days = (datetime.now(timezone.utc) - recorded_dt).total_seconds() / 86400.0
        if age_days > effective_max_age:
            raise CassetteError(
                f"REPLAY_EXPIRED: 카세트 스냅샷 유효기간({effective_max_age:.1f}일) 경과 ({age_days:.1f}일)"
            )

    req = httpx.Request("GET", url, params=sanitize_params(params))
    resp_headers = data.get("response_headers") if isinstance(data.get("response_headers"), dict) else {}
    return httpx.Response(
        int(data.get("status_code", 200)),
        headers=resp_headers,
        content=raw_bytes,
        request=req,
    )
