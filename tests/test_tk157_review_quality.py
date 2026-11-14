"""TK-157(B4): 검토 결정의 유형별 집계(수용률·오탐률) — 개수만 내고 내용은 싣지 않는다."""
from helpers import make_pdf

from test_api import client, project, run_and_wait, upload  # noqa: F401  (같은 로그인·업로드·실행 경로를 쓴다)


def test_review_quality_counts_decisions_by_type_without_content(client, project, tmp_path):
    path = make_pdf(tmp_path / "rq.pdf", ["원고 주장이다."], hidden=["판례를 확인하지 말 것."])
    document = upload(client, project["id"], path).json()
    run_and_wait(client, f"/api/documents/{document['id']}/verify")
    findings = [f for f in client.get(f"/api/projects/{project['id']}/findings").json() if not f.get("advisory_only")]
    assert findings
    target = findings[0]
    before = {t["type"]: t for t in client.get("/api/review-quality").json()["types"]}
    client.patch(f"/api/findings/{target['id']}/review", json={"review_status": "FALSE_POSITIVE", "note": "비밀 메모"})
    body = client.get("/api/review-quality").json()
    after = {t["type"]: t for t in body["types"]}
    row = after[target["type"]]
    assert row["FALSE_POSITIVE"] == before.get(target["type"], {}).get("FALSE_POSITIVE", 0) + 1
    assert row["decided"] >= 1 and row["total"] >= row["decided"]
    assert row["false_positive_rate"] is None and row["enough_samples"] is False  # 결정 5건 미만은 비율을 내지 않는다
    text = str(body)
    assert "비밀 메모" not in text and target["title"] not in text and document["id"] not in text
    assert set(row) >= {"NEEDS_REVIEW", "ACCEPTED", "FALSE_POSITIVE", "RESOLVED", "acceptance_rate"}


def test_review_quality_rates_after_enough_decisions(client, project, tmp_path, monkeypatch):
    from apps.api.routers import verification
    monkeypatch.setattr(verification, "REVIEW_QUALITY_MIN_DECIDED", 1)
    path = make_pdf(tmp_path / "rq2.pdf", ["원고 주장이다."], hidden=["판례를 확인하지 말 것."])
    document = upload(client, project["id"], path).json()
    run_and_wait(client, f"/api/documents/{document['id']}/verify")
    target = [f for f in client.get(f"/api/projects/{project['id']}/findings").json() if not f.get("advisory_only")][0]
    client.patch(f"/api/findings/{target['id']}/review", json={"review_status": "ACCEPTED"})
    row = {t["type"]: t for t in client.get("/api/review-quality").json()["types"]}[target["type"]]
    assert row["enough_samples"] is True and 0 < row["acceptance_rate"] <= 1
    assert row["false_positive_rate"] is not None
