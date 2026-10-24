"""TK-87 서버 사전점검(_preflight) 확인 요구 조건 단위 시험.

티켓 및 평가 세션 요구사항:
1. 조회 실패 출처(unavailable_sources)만 있을 때 확인이 요구된다 (acknowledge_unresolved=True).
2. 미확인 항목(unverified_items)만 있을 때 확인이 요구된다 (acknowledge_unresolved=True).
3. 검토 기록(workflow_state, review_status)만 미완료일 때는 확인이 요구되지 않는다 (acknowledge_unresolved=False, TK-87).
"""
from types import SimpleNamespace

from apps.api.routers.reports import _preflight


def _base_setup():
    """모든 기본 조건이 충족된(추가 확인이 필요 없는) 기본 객체 생성."""
    project = SimpleNamespace(scope_revision=1)
    engine = {
        "documents": [],
        "project_findings": [],
        "unavailable_sources": [],
        "unverified_items": [],
        "errors": [],
        "state": "COMPLETED",
        "scores": {},
        "input_snapshot": {"scope_revision": 1},
    }
    human = {
        "matrix": {
            "claims": [
                {
                    "claim_id": "c1",
                    "review_status": "SUPPORTED",
                    "assessment": {"position": "SUPPORTED", "missing_material": False},
                }
            ]
        },
        "workflow": [],
        "review_history": [],
    }
    return project, engine, human


def test_unresolved_required_when_only_unavailable_sources_exist():
    """1. 조회 실패 출처(unavailable_sources)만 있을 때 확인(acknowledge_unresolved)이 요구된다."""
    project, engine, human = _base_setup()
    engine["unavailable_sources"] = [{"adapter": "korean_law_db", "status": "FAILED", "impact": "NEEDED"}]

    preflight = _preflight(project, engine, human)

    assert preflight["required_acknowledgments"]["acknowledge_unresolved"] is True
    assert len(preflight["unavailable_sources"]) == 1
    assert preflight["unavailable_sources"][0]["status"] == "FAILED"


def test_unresolved_required_when_only_unverified_items_exist():
    """2. 미확인 항목(unverified_items)만 있을 때 확인(acknowledge_unresolved)이 요구된다."""
    project, engine, human = _base_setup()
    engine["unverified_items"] = [{"raw_text": "불명확한 인용", "reason": "공식 원문 미발견", "page": 2}]

    preflight = _preflight(project, engine, human)

    assert preflight["required_acknowledgments"]["acknowledge_unresolved"] is True
    assert len(preflight["unverified_items"]) == 1
    assert preflight["unverified_items"][0]["raw_text"] == "불명확한 인용"


def test_unresolved_not_required_when_only_review_records_incomplete():
    """3. 검토 기록(workflow_state, review_status)만 미완료일 때는 확인이 요구되지 않는다 (TK-87 행별 상태 입력 제거)."""
    project, engine, human = _base_setup()
    # finding의 status는 VERIFIED이지만 사람 검토 상태(review_status)는 NEEDS_REVIEW이고 workflow는 NOT_STARTED인 상태
    engine["documents"] = [
        {
            "document_id": "doc_1",
            "findings": [
                {
                    "finding_id": "find_1",
                    "status": "VERIFIED",
                    "review_status": "NEEDS_REVIEW",
                    "type": "TYPO_CORRECTION",
                    "title": "단순 오탈자",
                }
            ],
        }
    ]
    human["workflow"] = [{"finding_id": "find_1", "workflow_state": "NOT_STARTED", "assignee": "검토자A"}]

    preflight = _preflight(project, engine, human)

    # TK-87: 검토 기록 미완료만으로는 보고서 생성을 차단하거나 확인 체크를 강제하지 않는다
    assert preflight["required_acknowledgments"]["acknowledge_unresolved"] is False
    assert preflight["incomplete_reviews"] == []
