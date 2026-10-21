"""TK-78 공식 DB 조회 결과의 실행 단위 집계(source_lookup_summary) 검증 시험.

실제 진입점(VerificationPipeline.run)에서:
1. 가짜 전송(transport)으로 성공 1·시간 초과 1·찾지 못함 1·캐시 적중 1을 구성하여
   run_manifest['source_lookup_summary']의 출처별 및 전체 건수가 정확히 맞는지 검증한다 (>= 1만 보는 시험 불가).
2. 네트워크 비활성화(LV_ALLOW_NETWORK=0) 시 집계가 0/빈 상태로 안전하게 반환되고 오류가 나지 않는지 검증한다.
3. 집계 데이터 내에 질의어, URL, 인용 원문, API 키(OC) 등 민감 문자열이 전혀 들어가지 않는지 검증한다.
"""
from dataclasses import replace
import json
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest

from packages.common.config import get_settings
from packages.common.enums import AdapterStatus, VerificationProfile
from packages.common.storage import sha256_file
from packages.report_engine.exporters import to_payload
from packages.source_adapters import transport
from packages.source_adapters.law_go_kr import LawGoKrAdapter
from packages.source_adapters.local_mirror import LocalLegalMirror
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)


def install_mock(monkeypatch, handler):
    """httpx.AsyncClient를 가짜 MockTransport 핸들러로 치환합니다."""
    original = httpx.AsyncClient
    monkeypatch.setattr(
        transport.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )


def test_tk78_pipeline_run_source_lookup_summary_exact_counts(tmp_path, monkeypatch):
    """실제 진입점(VerificationPipeline.run)에서 성공 1·시간 초과 1·찾지 못함 1·캐시 적중 1의 건수 정확 대조 검증."""
    # 문서 내용:
    # 1. 2020다12345 (성공)
    # 2. 2021다99999 (찾지 못함)
    # 3. 2022다88888 (시간 초과)
    # 4. 2020다12345 (동일 판례 재인용 -> 캐시 적중)
    doc1_content = (
        "원고는 대법원 2020다12345 판결에 근거하여 피고의 손해배상 책임을 주장합니다. "
        "또한 피고는 대법원 2021다99999 판결의 취지에 비추어 소송이 부적법하다고 항변합니다. "
        "이에 대하여 원고는 대법원 2022다88888 판결을 들어 재항변합니다."
    )
    doc2_content = "원고는 앞서 인용한 대법원 2020다12345 판결의 법리를 거듭 확인합니다."

    doc1_path = tmp_path / "brief_tk78_1.txt"
    doc1_path.write_text(doc1_content, encoding="utf-8")
    doc2_path = tmp_path / "brief_tk78_2.txt"
    doc2_path.write_text(doc2_content, encoding="utf-8")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        # 1. 시간 초과 케이스: 2022다88888
        if "2022" in url_str:
            raise httpx.ReadTimeout("Mocked read timeout for TK-78", request=request)
        # 2. 성공 케이스: 2020다12345
        if "2020" in url_str:
            payload = {
                "PrecSearch": {
                    "totalCnt": 1,
                    "prec": [
                        {
                            "판례일련번호": "12345",
                            "사건번호": "2020다12345",
                            "사건명": "손해배상(기)",
                            "선고일자": "2020.10.15",
                            "법원명": "대법원",
                            "판결유형": "판결",
                            "선고": "선고",
                            "판시사항": "손해배상 성립 요건",
                            "판결요지": "불법행위로 인한 손해배상 책임 인정",
                        }
                    ],
                }
            }
            return httpx.Response(200, json=payload, request=request)
        # 3. 찾지 못함 케이스: 2021다99999
        if "2021" in url_str:
            payload = {
                "PrecSearch": {
                    "totalCnt": 0,
                    "prec": [],
                }
            }
            return httpx.Response(200, json=payload, request=request)
        # 기본 빈 응답
        return httpx.Response(200, json={"PrecSearch": {"totalCnt": 0, "prec": []}}, request=request)

    install_mock(monkeypatch, mock_handler)

    pipeline = VerificationPipeline()
    pipeline.settings = replace(
        get_settings(),
        allow_network=True,
        source_lookup_attempts=1,
        source_lookup_budget_seconds=30.0,
        law_go_kr_oc="mock_user_oc_123",
        rag_drive_folder_id="",
    )
    # 로컬 미러 대신 원격 Mock 조회를 타도록 no-mirror 설정
    pipeline.registry.law.mirror = LocalLegalMirror(root=str(tmp_path / "no-mirror"))
    pipeline.registry.law.settings = pipeline.settings

    context = ProjectContext("project-tk78", profile=VerificationProfile.QUICK)
    doc_inputs = [
        DocumentInput("doc_tk78_1", str(doc1_path), doc1_path.name, sha256=sha256_file(doc1_path), mime_type="text/plain"),
        DocumentInput("doc_tk78_2", str(doc2_path), doc2_path.name, sha256=sha256_file(doc2_path), mime_type="text/plain"),
    ]

    result = pipeline.run("run-tk78-exact", context, doc_inputs)

    # 1. run_manifest에 source_lookup_summary가 존재하는지 확인
    assert "source_lookup_summary" in result.run_manifest
    summary = result.run_manifest["source_lookup_summary"]
    # 2. 정확한 건수 대조 (>= 1만 보는 시험 불인정)
    # 4건의 인용에 따른 정확한 요청 및 시도 수:
    # - 2020다12345 (성공 1건): 목록 및 본문 조회 2건 성공 (attempts 2, READY 2)
    # - 2021다99999 (찾지 못함 1건): nb 조회 및 검색 조회 2건 완료 (attempts 2, READY 2)
    # - 2022다88888 (시간 초과 1건): 1차 조회 및 지연 재시도 2건 타임아웃 (attempts 2, TIMEOUT 2, retryable 2)
    # - 2020다12345 (캐시 적중 1건): doc2에서 2건 모두 캐시 적중 (attempts 0, cache_hits 2, READY 2)
    assert summary["requests"] == 8
    assert summary["total_requests"] == 8
    assert summary["http_attempts"] == 6
    assert summary["total_http_attempts"] == 6
    assert summary["cache_hits"] == 2
    assert summary["total_cache_hits"] == 2
    assert summary["retryable_failures"] == 2
    assert summary["total_retryable_failures"] == 2

    # 상태(AdapterStatus)별 건수: READY 6건, TIMEOUT 2건
    assert summary["by_status"] == {"READY": 6, "TIMEOUT": 2}

    # 소요 시간 및 recovery 소진 문서 수 (2022다88888 타임아웃으로 recovery 1회 사용)
    assert summary["spent_seconds"] >= 0.0
    assert summary["recovery_used_documents"] == 1

    # 3. 출처(adapter)별 집계 검증: law_go_kr
    assert "law_go_kr" in summary["adapters"]
    adapter = summary["adapters"]["law_go_kr"]
    assert adapter["requests"] == 8
    assert adapter["http_attempts"] == 6
    assert adapter["cache_hits"] == 2
    assert adapter["by_status"] == {"READY": 6, "TIMEOUT": 2}
    assert adapter["retryable_failures"] == 2

    # 4. 보고서 내보내기(to_payload)에 그대로 실리는지 검증 (요구 3항)
    payload = to_payload(result)
    assert "run_manifest" in payload
    assert "source_lookup_summary" in payload["run_manifest"]
    assert payload["run_manifest"]["source_lookup_summary"] == summary


def test_tk78_network_disabled_zero_or_empty(tmp_path):
    """네트워크 비활성화(LV_ALLOW_NETWORK=0) 상태에서 집계가 0 또는 빈 상태로 안전하게 반환되는지 검증."""
    doc_path = tmp_path / "brief_no_net.txt"
    doc_path.write_text("원고는 대법원 2020다12345 판결을 인용합니다.", encoding="utf-8")

    pipeline = VerificationPipeline()
    pipeline.settings = replace(
        get_settings(),
        allow_network=False,
        rag_drive_folder_id="",
    )
    context = ProjectContext("project-tk78-nonet", profile=VerificationProfile.QUICK)
    doc_input = DocumentInput(
        "doc_nonet",
        str(doc_path),
        doc_path.name,
        sha256=sha256_file(doc_path),
        mime_type="text/plain",
    )

    result = pipeline.run("run-tk78-nonet", context, [doc_input])

    assert "source_lookup_summary" in result.run_manifest
    summary = result.run_manifest["source_lookup_summary"]

    assert summary["requests"] == 0
    assert summary["http_attempts"] == 0
    assert summary["cache_hits"] == 0
    assert summary["retryable_failures"] == 0
    assert summary["by_status"] == {}
    assert summary["adapters"] == {}
    assert summary["spent_seconds"] == 0.0
    assert summary["recovery_used_documents"] == 0


def test_tk78_no_query_url_or_keys_in_summary(tmp_path, monkeypatch):
    """집계 요약 데이터 내에 질의어, URL, 인용문, 키(OC) 문자열이 절대 들어가지 않는지 검증 (요구 2항)."""
    doc_path = tmp_path / "brief_secret.txt"
    doc_path.write_text("원고는 대법원 2020다12345 판결을 인용합니다.", encoding="utf-8")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "PrecSearch": {
                "totalCnt": 1,
                "prec": [
                    {
                        "판례일련번호": "12345",
                        "사건번호": "2020다12345",
                        "사건명": "손해배상(기)",
                        "선고일자": "2020.10.15",
                        "법원명": "대법원",
                        "판결유형": "판결",
                        "선고": "선고",
                    }
                ],
            }
        }
        return httpx.Response(200, json=payload, request=request)

    install_mock(monkeypatch, mock_handler)

    test_secret_oc = "very_secret_oc_key_9999"
    pipeline = VerificationPipeline()
    pipeline.settings = replace(
        get_settings(),
        allow_network=True,
        source_lookup_attempts=1,
        law_go_kr_oc=test_secret_oc,
        rag_drive_folder_id="",
    )
    pipeline.registry.law.mirror = LocalLegalMirror(root=str(tmp_path / "no-mirror"))
    pipeline.registry.law.settings = pipeline.settings

    context = ProjectContext("project-tk78-sec", profile=VerificationProfile.QUICK)
    doc_input = DocumentInput(
        "doc_sec",
        str(doc_path),
        doc_path.name,
        sha256=sha256_file(doc_path),
        mime_type="text/plain",
    )

    result = pipeline.run("run-tk78-sec", context, [doc_input])
    summary = result.run_manifest["source_lookup_summary"]

    # 직렬화된 문자열 내에 민감 정보가 포함되지 않음을 단언
    dumped = json.dumps(summary, ensure_ascii=False)
    assert "2020다12345" not in dumped
    assert "law.go.kr" not in dumped
    assert "lawSearch.do" not in dumped
    assert "https://" not in dumped
    assert test_secret_oc not in dumped
    assert "손해배상" not in dumped
    assert "대법원" not in dumped
