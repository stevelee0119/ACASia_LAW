"""TK-82 Drive 참고자료 내려받기 네트워크 오류 구분 및 1회 재시도 검증 시험.

1. 오류 원인 구분:
   - 연결 실패(ConnectError/ConnectTimeout)
   - 읽기 시간 초과(ReadTimeout)
   - 전송 중 끊김(일부 바이트 수신 후 RemoteProtocolError/ReadError)
   - 받은 바이트 수를 함께 남김
2. 동기화 예산 잔여 시 최대 1회만 재시도:
   - 1차 실패 후 재시도 성공 시 정상 데이터 반환 및 호출 기록에 retried=True 남음
   - 2차 모두 실패 시 DRIVE_NETWORK_ERROR 및 세부 reason 남음
   - HTTP 403, 파일 크기 초과, 동기화 예산 소진은 재시도하지 않음
"""
from dataclasses import replace
import time
from typing import Iterator

import httpx
import pytest

from packages.rag_engine.drive import DriveClient, ReferenceError
from packages.rag_engine.library import ReferenceLibrary


def test_tk82_retry_success_after_first_connect_failure(monkeypatch):
    """1차 연결 실패 후 2차 재시도에 성공하면 정상 반환 및 호출 기록에 재시도가 남는지 검증."""
    calls_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls_made.append(request)
        if len(calls_made) == 1:
            raise httpx.ConnectError("Mocked connect failure", request=request)
        return httpx.Response(200, content=b"SUCCESSFUL_RETRY_DATA", request=request)

    client = DriveClient(
        deadline=time.monotonic() + 30.0,
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer mock-token"},
    )

    data = client.read("files/test_file_id")
    assert data == b"SUCCESSFUL_RETRY_DATA"
    assert len(calls_made) == 2

    # 호출 기록 검증
    assert len(client.calls) == 2
    first_call = client.calls[0]
    second_call = client.calls[1]

    assert first_call["error"] == "DRIVE_NETWORK_ERROR"
    assert "CONNECT_FAILED" in first_call.get("reason", "")
    assert "0 bytes" in first_call.get("reason", "")
    assert first_call.get("retried") is not True

    assert second_call["status"] == 200
    assert second_call.get("retried") is True
    assert second_call["bytes"] == len(b"SUCCESSFUL_RETRY_DATA")


def test_tk82_both_attempts_fail_read_timeout(monkeypatch):
    """2회 모두 읽기 타임아웃으로 실패 시 DRIVE_NETWORK_ERROR 및 세부 reason이 남는지 검증."""
    calls_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls_made.append(request)
        raise httpx.ReadTimeout("Mocked read timeout", request=request)

    client = DriveClient(
        deadline=time.monotonic() + 30.0,
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer mock-token"},
    )

    with pytest.raises(ReferenceError, match="DRIVE_NETWORK_ERROR"):
        client.read("files/test_timeout_id")

    assert len(calls_made) == 2
    assert len(client.calls) == 2

    assert "READ_TIMEOUT" in client.last_error_reason
    assert "0 bytes" in client.last_error_reason

    second_call = client.calls[1]
    assert second_call["error"] == "DRIVE_NETWORK_ERROR"
    assert second_call.get("retried") is True
    assert "READ_TIMEOUT" in second_call.get("reason", "")


def test_tk82_stream_interrupted_with_partial_bytes(monkeypatch):
    """일부 바이트 수신 후 전송이 끊겼을 때 받은 바이트 수가 사유에 남고 재시도에 성공하는지 검증."""
    calls_made = []

    class BrokenStream(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            yield b"PARTIAL_HEADER_65536_BYTES_" + b"x" * (65536 - 27)  # 65536 바이트 수신
            raise httpx.RemoteProtocolError("Connection broken during streaming")

    def handler(request: httpx.Request) -> httpx.Response:
        calls_made.append(request)
        if len(calls_made) == 1:
            return httpx.Response(200, stream=BrokenStream(), request=request)
        return httpx.Response(200, content=b"FULL_RECOVERED_CONTENT", request=request)

    client = DriveClient(
        deadline=time.monotonic() + 30.0,
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer mock-token"},
    )

    data = client.read("files/test_stream_id")
    assert data == b"FULL_RECOVERED_CONTENT"
    assert len(calls_made) == 2

    first_call = client.calls[0]
    assert first_call["error"] == "DRIVE_NETWORK_ERROR"
    assert "STREAM_INTERRUPTED" in first_call.get("reason", "")
    assert "65536 bytes" in first_call.get("reason", "")

    second_call = client.calls[1]
    assert second_call["status"] == 200
    assert second_call.get("retried") is True


def test_tk82_http_403_not_retried(monkeypatch):
    """HTTP 403 오류는 재시도하지 않고 즉시 1회만에 실패하는지 검증."""
    calls_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls_made.append(request)
        return httpx.Response(403, json={"error": {"errors": [{"reason": "insufficientPermissions"}]}}, request=request)

    client = DriveClient(
        deadline=time.monotonic() + 30.0,
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer mock-token"},
    )

    with pytest.raises(ReferenceError, match="DRIVE_HTTP_403"):
        client.read("files/test_403_id")

    # 재시도 없이 정확히 1회만 호출됨
    assert len(calls_made) == 1
    assert len(client.calls) == 1
    assert client.calls[0]["status"] == 403
    assert client.calls[0].get("retried") is not True
    assert client.calls[0].get("reason") == "insufficientPermissions"


def test_tk82_file_size_limit_not_retried(monkeypatch):
    """파일 크기 한도(FILE_SIZE_LIMIT) 초과 시 재시도하지 않는지 검증."""
    calls_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls_made.append(request)
        return httpx.Response(200, content=b"A" * 5000, request=request)

    client = DriveClient(
        deadline=time.monotonic() + 30.0,
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer mock-token"},
    )

    with pytest.raises(ReferenceError, match="FILE_SIZE_LIMIT"):
        client.read("files/test_large_id", max_bytes=1000)

    # 재시도 없이 정확히 1회만 호출됨
    assert len(calls_made) == 1
    assert len(client.calls) == 1
    assert client.calls[0]["error"] == "FILE_SIZE_LIMIT"
    assert client.calls[0].get("retried") is not True


def test_tk82_sync_budget_exhausted_not_retried(monkeypatch):
    """동기화 예산이 소진된 경우 재시도 루프에 진입하지 않고 예외가 발생하는지 검증."""
    client = DriveClient(
        deadline=time.monotonic() - 1.0,  # 이미 마감시한 초과
        transport=httpx.MockTransport(lambda req: httpx.Response(200)),
        headers={"Authorization": "Bearer mock-token"},
    )

    with pytest.raises(ReferenceError, match="SYNC_BUDGET_EXHAUSTED"):
        client.read("files/test_expired_id")

    assert len(client.calls) == 1
    assert client.calls[0]["error"] == "SYNC_BUDGET_EXHAUSTED"
    assert client.calls[0].get("retried") is not True


def test_tk82_library_sync_records_reason_detail(tmp_path, monkeypatch):
    """ReferenceLibrary 동기화 시 DRIVE_NETWORK_ERROR의 세부 사유가 inventory/issues에 남는지 검증."""
    mock_file_id = "test_network_error_file_id"
    mock_file_name = "test_broken_manual.pdf"

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        # 1. 루트 폴더 메타데이터
        if "files/root_folder_id" in url_str:
            return httpx.Response(200, json={"id": "root_folder_id", "name": "root", "mimeType": "application/vnd.google-apps.folder"}, request=request)
        # 2. 파일 목록 조회
        if "files?" in url_str and "q=" in url_str:
            return httpx.Response(200, json={
                "files": [{
                    "id": mock_file_id,
                    "name": mock_file_name,
                    "mimeType": "application/pdf",
                    "modifiedTime": "2026-10-19T00:00:00Z",
                    "version": "1",
                    "size": "5000",
                    "capabilities": {"canDownload": True},
                }]
            }, request=request)
        # 3. 개별 파일 메타데이터 조회 (alt=media 없음)
        if f"files/{mock_file_id}?" in url_str and "alt=media" not in url_str:
            return httpx.Response(200, json={
                "id": mock_file_id,
                "name": mock_file_name,
                "mimeType": "application/pdf",
                "modifiedTime": "2026-10-19T00:00:00Z",
                "version": "1",
                "size": "5000",
                "capabilities": {"canDownload": True},
            }, request=request)
        # 4. 파일 다운로드 요청 시 ConnectError 발생
        if "alt=media" in url_str:
            raise httpx.ConnectError("Network link broken during download", request=request)
        raise httpx.ConnectError("Unexpected request", request=request)

    from packages.common.config import get_settings
    settings = get_settings()
    settings = replace(
        settings,
        rag_drive_folder_id="root_folder_id",
        allow_network=True,
    )

    class CustomDriveClient(DriveClient):
        def __init__(self, **kwargs):
            super().__init__(
                deadline=kwargs.get("deadline", time.monotonic() + 30.0),
                check=kwargs.get("check", lambda: None),
                transport=httpx.MockTransport(handler),
                headers={"Authorization": "Bearer mock-token"},
            )

    library = ReferenceLibrary(settings, client_factory=CustomDriveClient)
    summary = library.sync()
    # 인벤토리 처리 기록 검증
    inv_item = next((item for item in summary.get("inventory", []) if item.get("file_id") == mock_file_id), None)
    assert inv_item is not None
    assert inv_item["status"] == "UNAVAILABLE"
    # 세부 사유와 수신 바이트(0 bytes)가 reason에 포함됨
    assert "DRIVE_NETWORK_ERROR" in inv_item["reason"]
    assert "CONNECT_FAILED" in inv_item["reason"]
    assert "0 bytes" in inv_item["reason"]

    # 이슈 기록 검증
    issue_item = next((iss for iss in summary.get("issues", []) if iss.get("file_id") == mock_file_id), None)
    assert issue_item is not None
    assert "DRIVE_NETWORK_ERROR" in issue_item["reason"]
    assert "CONNECT_FAILED" in issue_item["reason"]


def test_tk82_non_retryable_network_error_not_retried():
    """연결실패·읽기타임아웃·전송중단 외의 네트워크 오류(예: UnsupportedProtocol, DecodingError)는 재시도하지 않고 1회만에 종료되는지 검증 (TK-82)."""
    calls_made = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls_made.append(request)
        raise httpx.UnsupportedProtocol("Unsupported protocol scheme: custom://")

    client = DriveClient(
        deadline=time.monotonic() + 30.0,
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer mock-token"},
    )

    with pytest.raises(ReferenceError, match="DRIVE_NETWORK_ERROR"):
        client.read("files/test_unsupported_id")

    # 재시도 없이 정확히 1회만 호출됨
    assert len(calls_made) == 1
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["error"] == "DRIVE_NETWORK_ERROR"
    assert call.get("retried") is not True
    assert "UnsupportedProtocol" in call.get("reason", "")
    assert "UnsupportedProtocol" in client.last_error_reason
