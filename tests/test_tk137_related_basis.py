# -*- coding: utf-8 -*-
"""TK-137 제한형 관련 근거 탐색(깊이 1 위임 및 명시 참조) 단위 및 통합 테스트."""

from unittest.mock import MagicMock, patch
import pytest

from packages.source_adapters.base import AdapterStatus
from packages.source_adapters.law_go_kr import LawGoKrAdapter
from packages.common.enums import CitationType
from packages.common.schemas import Citation
from packages.legal_engine.related_authorities import (
    review_related_authorities,
    report_lines,
    _parse_thd_cmp,
    _extract_references,
    _discover_tk137_authorities,
)


class MockDoc:
    """테스트용 문서 모의 객체."""
    def __init__(self, filename="test_doc.hwpx", engine_data=None):
        self.filename = filename
        self.document_id = "doc_test"
        self.engine_data = engine_data or {}


def _create_mock_verifier(adapter):
    """테스트용 verifier 모의 객체 생성."""
    verifier = MagicMock()
    verifier.registry = MagicMock()
    verifier.registry.law = adapter
    verifier.verify_citations.return_value = MagicMock(source_records=[], data={"verdicts": []})
    return verifier


def test_law_go_kr_adapter_get_thd_cmp_guards():
    """LawGoKrAdapter의 get_thd_cmp 네트워크 가드 및 크기 상한(2.5MB) 테스트."""
    settings = MagicMock()
    settings.allow_network = False
    settings.law_go_kr_oc = "test_oc"
    adapter = LawGoKrAdapter(enabled=True)
    adapter.settings = settings

    # 1. allow_network = False 시 None 반환
    assert adapter.get_thd_cmp(12345) is None

    # 2. OC 미설정(status != READY) 시 None 반환
    settings.allow_network = True
    settings.law_go_kr_oc = ""
    assert adapter.get_thd_cmp(12345) is None

    # 3. 2.5MB 초과 페이로드 시 _limit_exceeded 반환
    settings.law_go_kr_oc = "test_oc"
    large_payload = b"x" * (int(2.5 * 1024 * 1024) + 10)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = large_payload
    with patch.object(adapter, "_http_get", return_value=mock_resp):
        res = adapter.get_thd_cmp(12345)
        assert res is not None
        assert res.get("_limit_exceeded") is True

    # 4. 정상 JSON 응답 반환
    mock_resp.content = b'{"LspttnThdCmpLawXService": {"status": "ok"}}'
    mock_resp.json.return_value = {"LspttnThdCmpLawXService": {"status": "ok"}}
    with patch.object(adapter, "_http_get", return_value=mock_resp):
        res = adapter.get_thd_cmp(12345)
        assert res == {"LspttnThdCmpLawXService": {"status": "ok"}}


def test_positive_1_single_delegation():
    """양성 1: 단일 위임 조문 (법률 제11조 -> 시행령 제3조) 정상 수집 검증."""
    adapter = MagicMock()
    adapter.name = "law_go_kr"
    adapter.settings.allow_network = True
    adapter.status.return_value = AdapterStatus.READY

    # resolve_statute 모의: MST 1001 반환
    adapter.resolve_statute.return_value = MagicMock(
        records=[{"version_id": "1001", "law_name": "근로기준법"}]
    )

    # 3단 비교 모의 응답 (단일 시행령 조문 dict)
    adapter.get_thd_cmp.return_value = {
        "LspttnThdCmpLawXService": {
            "기본정보": {
                "법령명_한글": "근로기준법",
                "시행령명_한글": "근로기준법 시행령",
                "삼단비교존재여부": "Y",
            },
            "위임조문삼단비교": {
                "법률조문": {
                    "조번호": "11",
                    "조가지번호": "0",
                    "조문제목": "근로조건의 명시",
                    "조문내용": "사용자는 근로계약을 체결할 때에 근로자에게 다음 각 호의 사항을 명시하여야 한다.",
                    "시행령조문": {
                        "조번호": "3",
                        "조가지번호": "0",
                        "조문제목": "명시하여야 할 근로조건",
                        "조문내용": "법 제11조에 따라 명시하여야 할 사항은 다음과 같다.",
                    },
                }
            },
        }
    }

    verifier = _create_mock_verifier(adapter)
    cit = Citation.create(
        CitationType.STATUTE,
        "근로기준법 제11조",
        law_name="근로기준법",
        article="11",
    )
    doc = MockDoc()

    res, _ = review_related_authorities(doc, [cit], verifier)
    assert res is not None
    assert res["delegation_status"] == "COMPLETED"
    assert len(res["delegations"]) == 1
    d = res["delegations"][0]
    assert d["source_law"] == "근로기준법"
    assert d["source_article"] == "11"
    assert d["target_law"] == "근로기준법 시행령"
    assert d["target_article"] == "3"
    assert d["target_title"] == "명시하여야 할 근로조건"
    assert res["explicit_references"] == []


def test_positive_2_multiple_delegations_and_merge():
    """양성 2: 동일 조번호 행 병합(N5) 및 복수 위임(시행령+시행규칙) 수집 검증."""
    adapter = MagicMock()
    adapter.name = "law_go_kr"
    adapter.settings.allow_network = True
    adapter.status.return_value = AdapterStatus.READY

    adapter.resolve_statute.return_value = MagicMock(
        records=[{"version_id": "1002", "law_name": "근로기준법"}]
    )

    # 동일 법률조문 11조가 분할되어 오는 경우 (N5 실측 사실 반영)
    adapter.get_thd_cmp.return_value = {
        "LspttnThdCmpLawXService": {
            "기본정보": {
                "법령명_한글": "근로기준법",
                "시행령명_한글": "근로기준법 시행령",
                "시행규칙명_한글": "근로기준법 시행규칙",
                "삼단비교존재여부": "Y",
            },
            "위임조문삼단비교": {
                "법률조문": [
                    {
                        "조번호": "11",
                        "조가지번호": "0",
                        "조문제목": "근로조건의 명시",
                        "조문내용": "내용1",
                        "시행령조문": [
                            {"조번호": "3", "조가지번호": "0", "조문제목": "영1", "조문내용": ""},
                            {"조번호": "4", "조가지번호": "0", "조문제목": "영2", "조문내용": ""},
                        ],
                    },
                    {
                        "조번호": "11",
                        "조가지번호": "0",
                        "조문제목": "근로조건의 명시",
                        "조문내용": "내용1",
                        "시행규칙조문": [
                            {"조번호": "2", "조가지번호": "0", "조문제목": "규칙1", "조문내용": ""},
                        ],
                    },
                ]
            },
        }
    }

    verifier = _create_mock_verifier(adapter)
    cit = Citation.create(
        CitationType.STATUTE,
        "근로기준법 제11조",
        law_name="근로기준법",
        article="11",
    )
    doc = MockDoc()

    res, _ = review_related_authorities(doc, [cit], verifier)
    assert res is not None
    # 3건(영 제3조, 영 제4조, 규칙 제2조) 모두 수집
    assert len(res["delegations"]) == 3
    targets = [(d["target_law"], d["target_article"]) for d in res["delegations"]]
    assert ("근로기준법 시행령", "3") in targets
    assert ("근로기준법 시행령", "4") in targets
    assert ("근로기준법 시행규칙", "2") in targets


def test_positive_3_explicit_references_5_steps():
    """양성 3: 본문 명시 참조 5단계 판별 (앞말 법령명, 같은 법, 같은 법 시행령, 인용 법령 기본값, 같은 조 배제)."""
    # 5단계 정규식 판별 단위 테스트
    source_law = "근로기준법"
    source_art = "11"
    content = (
        "제1항에 따른 계약은 「민법」 제750조에 따라 손해배상을 청구할 수 있으며, "
        "같은 법 제10조에 규정된 바를 따르고, "
        "필요한 절차는 같은 법 시행령 제3조에 따라 정한다. "
        "또한 제12조에 의하여 처벌받을 수 있으나, "
        "같은 조 제2항에 따라 면제된다."
    )
    law_articles = {
        (12, 0): {"title": "벌칙", "content": "벌칙 조항 내용"}
    }

    refs = _extract_references(source_law, source_art, content, law_articles)

    ref_tuples = [(r["target_law"], r["target_article"]) for r in refs]
    # 1. 앞말 법령명: 민법 제750조
    assert ("민법", "750") in ref_tuples
    # 2. 같은 법: 근로기준법 제10조
    assert ("근로기준법", "10") in ref_tuples
    # 3. 같은 법 시행령: 근로기준법 시행령 제3조
    assert ("근로기준법 시행령", "3") in ref_tuples
    # 4. 수식어 없는 단독 조번호: 인용 법령(근로기준법) 제12조
    assert ("근로기준법", "12") in ref_tuples
    # 5. 같은 조 제2항은 제외됨
    assert not any(r["target_article"] == "2" for r in refs)

    # 동일 법령 기수신 조문(제12조)의 제목 및 본문 발췌 확인
    ref_12 = next(r for r in refs if r["target_article"] == "12")
    assert ref_12["target_title"] == "벌칙"
    assert ref_12["target_excerpt"] == "벌칙 조항 내용"


def test_contrast_1_thd_cmp_not_supported():
    """대조 1: 3단 비교 미지원 법령 (삼단비교존재여부 == 'N')."""
    adapter = MagicMock()
    adapter.name = "law_go_kr"
    adapter.settings.allow_network = True
    adapter.status.return_value = AdapterStatus.READY

    adapter.resolve_statute.return_value = MagicMock(
        records=[{"version_id": "1003", "law_name": "일반법"}]
    )
    adapter.get_thd_cmp.return_value = {
        "LspttnThdCmpLawXService": {
            "기본정보": {
                "법령명_한글": "일반법",
                "삼단비교존재여부": "N",
            }
        }
    }

    verifier = _create_mock_verifier(adapter)
    cit = Citation.create(CitationType.STATUTE, "일반법 제5조", law_name="일반법", article="5")
    doc = MockDoc()

    res, _ = review_related_authorities(doc, [cit], verifier)
    assert res is None  # 국가계약법도 없고 delegations/explicit_refs도 없으므로 None


def test_contrast_2_no_delegation_in_article():
    """대조 2: 위임 조문이 없는 법률 조문."""
    adapter = MagicMock()
    adapter.name = "law_go_kr"
    adapter.settings.allow_network = True
    adapter.status.return_value = AdapterStatus.READY

    adapter.resolve_statute.return_value = MagicMock(
        records=[{"version_id": "1004", "law_name": "근로기준법"}]
    )
    adapter.get_thd_cmp.return_value = {
        "LspttnThdCmpLawXService": {
            "기본정보": {
                "법령명_한글": "근로기준법",
                "시행령명_한글": "근로기준법 시행령",
                "삼단비교존재여부": "Y",
            },
            "위임조문삼단비교": {
                "법률조문": {
                    "조번호": "10",
                    "조가지번호": "0",
                    "조문제목": "적용범위",
                    "조문내용": "이 법은 모든 사업 또는 사업장에 적용한다.",
                    # 시행령조문, 시행규칙조문 없음
                }
            },
        }
    }

    verifier = _create_mock_verifier(adapter)
    cit = Citation.create(CitationType.STATUTE, "근로기준법 제10조", law_name="근로기준법", article="10")
    doc = MockDoc()

    res, _ = review_related_authorities(doc, [cit], verifier)
    # 위임 및 참조가 없으므로 None 반환 (N3 충족)
    assert res is None


def test_contrast_3_single_fetch_and_cache_per_law():
    """대조 3: 법령 단위 1회 단일 조회 및 다수 조문 캐시 공유 검증."""
    adapter = MagicMock()
    adapter.name = "law_go_kr"
    adapter.settings.allow_network = True
    adapter.status.return_value = AdapterStatus.READY

    adapter.resolve_statute.return_value = MagicMock(
        records=[{"version_id": "1005", "law_name": "근로기준법"}]
    )
    adapter.get_thd_cmp.return_value = {
        "LspttnThdCmpLawXService": {
            "기본정보": {
                "법령명_한글": "근로기준법",
                "시행령명_한글": "근로기준법 시행령",
                "삼단비교존재여부": "Y",
            },
            "위임조문삼단비교": {
                "법률조문": [
                    {
                        "조번호": "10",
                        "조가지번호": "0",
                        "조문내용": "내용",
                        "시행령조문": {"조번호": "2", "조가지번호": "0", "조문내용": ""},
                    },
                    {
                        "조번호": "11",
                        "조가지번호": "0",
                        "조문내용": "내용",
                        "시행령조문": {"조번호": "3", "조가지번호": "0", "조문내용": ""},
                    },
                ]
            },
        }
    }

    verifier = _create_mock_verifier(adapter)
    cit1 = Citation.create(CitationType.STATUTE, "근로기준법 제10조", law_name="근로기준법", article="10")
    cit2 = Citation.create(CitationType.STATUTE, "근로기준법 제11조", law_name="근로기준법", article="11")
    doc = MockDoc()

    res, _ = review_related_authorities(doc, [cit1, cit2], verifier)
    assert res is not None
    # 동일 법령에 대해 resolve_statute 및 get_thd_cmp는 각각 1회만 호출되어야 함
    assert adapter.resolve_statute.call_count == 1
    assert adapter.get_thd_cmp.call_count == 1
    assert len(res["delegations"]) == 2


def test_contrast_4_limit_exceeded_payload():
    """대조 4: 2.5MB 상한 초과 페이로드 수신 시 limit_reached 처리 검증."""
    adapter = MagicMock()
    adapter.name = "law_go_kr"
    adapter.settings.allow_network = True
    adapter.status.return_value = AdapterStatus.READY

    adapter.resolve_statute.return_value = MagicMock(
        records=[{"version_id": "1006", "law_name": "방대한법"}]
    )
    # 어댑터가 크기 초과로 감지한 경우
    adapter.get_thd_cmp.return_value = {"_limit_exceeded": True}

    verifier = _create_mock_verifier(adapter)
    cit = Citation.create(CitationType.STATUTE, "방대한법 제1조", law_name="방대한법", article="1")
    doc = MockDoc()

    res, _ = review_related_authorities(doc, [cit], verifier)
    assert res is None  # 결과가 없으므로 None


def test_contrast_5_network_disabled_and_unavailable():
    """대조 5: allow_network False 또는 어댑터 비가용 시 호출 생략 검증 (N3)."""
    # 1. allow_network = False
    adapter = MagicMock()
    adapter.name = "law_go_kr"
    adapter.settings.allow_network = False
    adapter.status.return_value = AdapterStatus.READY

    verifier = _create_mock_verifier(adapter)
    cit = Citation.create(CitationType.STATUTE, "근로기준법 제10조", law_name="근로기준법", article="10")
    doc = MockDoc()

    res, _ = review_related_authorities(doc, [cit], verifier)
    assert res is None
    adapter.get_thd_cmp.assert_not_called()

    # 2. 어댑터 상태가 READY가 아님
    adapter.settings.allow_network = True
    adapter.status.return_value = AdapterStatus.ERROR
    res, _ = review_related_authorities(doc, [cit], verifier)
    assert res is None
    adapter.get_thd_cmp.assert_not_called()

    # 3. verifier에 law 어댑터가 없음
    verifier_none = MagicMock(registry=MagicMock(law=None))
    res, _ = review_related_authorities(doc, [cit], verifier_none)
    assert res is None


def test_n5_truncation_prioritizes_delegations():
    """N5: 인용당 최대 3건 절삭 검증 (위임 우선 배분 후 남은 자리에 명시 참조)."""
    adapter = MagicMock()
    adapter.name = "law_go_kr"
    adapter.settings.allow_network = True
    adapter.status.return_value = AdapterStatus.READY

    adapter.resolve_statute.return_value = MagicMock(
        records=[{"version_id": "1007", "law_name": "테스트법"}]
    )
    # 위임 2건 + 본문 명시 참조 3건
    adapter.get_thd_cmp.return_value = {
        "LspttnThdCmpLawXService": {
            "기본정보": {
                "법령명_한글": "테스트법",
                "시행령명_한글": "테스트법 시행령",
                "삼단비교존재여부": "Y",
            },
            "위임조문삼단비교": {
                "법률조문": {
                    "조번호": "10",
                    "조가지번호": "0",
                    "조문내용": "제11조에 따르고 제12조에 따르고 제13조에 따른다.",
                    "시행령조문": [
                        {"조번호": "1", "조가지번호": "0", "조문내용": ""},
                        {"조번호": "2", "조가지번호": "0", "조문내용": ""},
                    ],
                }
            },
        }
    }

    verifier = _create_mock_verifier(adapter)
    cit = Citation.create(CitationType.STATUTE, "테스트법 제10조", law_name="테스트법", article="10")
    doc = MockDoc()

    res, _ = review_related_authorities(doc, [cit], verifier)
    assert res is not None
    # 위임 2건 우선 배분
    assert len(res["delegations"]) == 2
    # 남은 1자리에 명시 참조 1건만 배분되어 총 3건
    assert len(res["explicit_references"]) == 1


def test_n1_time_budget_guard():
    """N1: 누적 시간 15초 초과 시 추가 외부 호출 중단 및 LIMIT_EXCEEDED 처리 검증."""
    adapter = MagicMock()
    adapter.name = "law_go_kr"
    adapter.settings.allow_network = True
    adapter.status.return_value = AdapterStatus.READY

    adapter.resolve_statute.return_value = MagicMock(
        records=[{"version_id": "1008", "law_name": "시간법"}]
    )

    verifier = _create_mock_verifier(adapter)
    cit1 = Citation.create(CitationType.STATUTE, "시간법 제1조", law_name="시간법", article="1")
    cit2 = Citation.create(CitationType.STATUTE, "시간법2 제1조", law_name="시간법2", article="1")

    # time.monotonic 모의: 첫 번째 호출 이후 16초 경과
    with patch("time.monotonic", side_effect=[0.0, 16.0, 16.0, 16.0]):
        dels, refs, status = _discover_tk137_authorities([cit1, cit2], verifier)
        assert status == "LIMIT_EXCEEDED"


def test_n6_report_lines_and_quick_mode():
    """N6: report_lines 포맷 검증 및 quick 모드 시 동작 검증."""
    # 1. report_lines 출력 확인
    doc = MockDoc(filename="갑제1호증.hwpx", engine_data={
        "related_authorities": {
            "origin": "DISCOVERED_AUTHORITY",
            "status": "SOURCE_REVIEW_ONLY",
            "note": "관련 법령 및 위임·명시 참조 조문 검토",
            "candidates": [],
            "verdicts": [],
            "delegations": [
                {
                    "source_law": "근로기준법",
                    "source_article": "11",
                    "target_law": "근로기준법 시행령",
                    "target_article": "3",
                    "target_title": "명시사항",
                }
            ],
            "explicit_references": [
                {
                    "source_law": "근로기준법",
                    "source_article": "11",
                    "target_law": "민법",
                    "target_article": "750",
                    "target_title": "",
                }
            ],
        }
    })

    lines = report_lines([doc])
    assert any("[위임] 근로기준법 제11조 → 근로기준법 시행령 제3조(명시사항) / 검토 자료" in l for l in lines)
    assert any("[참조] 근로기준법 제11조 → 민법 제750조 / 검토 자료" in l for l in lines)

    # 2. quick 모드 검증
    cit = Citation.create(CitationType.STATUTE, "근로기준법 제11조", law_name="근로기준법", article="11")
    res_quick, _ = review_related_authorities(doc, [cit], None, quick=True)
    # 국가계약법 쟁점이 없는 일반 조문은 quick 모드 시 즉시 None 반환
    assert res_quick is None
