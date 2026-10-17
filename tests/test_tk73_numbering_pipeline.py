"""Approved TK73 behavior through actual file parsing and full offline pipeline."""
import pytest

from packages.common.config import reset_settings
from packages.verification_engine.pipeline import DocumentInput, ProjectContext, VerificationPipeline


@pytest.mark.parametrize("title", ("운송대장", "검수기록", "입고목록"))
def test_pipeline_removes_repeated_mention_and_keeps_original_A(tmp_path, monkeypatch, title):
    path = tmp_path / "public.txt"
    path.write_text("\n\n".join([
        f"갑 제1호증: {title}, 차례를 설명하고 묶음번호 7을 인용한다.",
        f"갑 제1호증 {title}: 같은 자료의 내용을 설명한다.",
        f"갑 제2호증: {title}, REF-AA 뒤 설명을 붙인다.",
        f"갑 제2호증 {title}: REF-BB 뒤 내용을 기록한다.",
    ]), encoding="utf-8")
    with monkeypatch.context() as patch:
        patch.setenv("LV_ALLOW_NETWORK", "0")
        patch.setenv("LV_DATA_DIR", str(tmp_path / "data"))
        reset_settings()
        try:
            result = VerificationPipeline().run("tk73-public-run", ProjectContext("tk73-public-project"),
                [DocumentInput("public-document", str(path), path.name)])
        finally:
            reset_settings()
    assert not result.errors
    assert len(result.documents) == 1
    findings = [finding for finding in result.documents[0].findings
                if finding.confidence_features.get("rule_id") == "EVI.EVIDENCE_NUMBER_DUPLICATE"]
    assert len(findings) == 1
    finding = findings[0]
    assert str(finding.evidence_grade) == "A" and str(finding.status) == "CONTRADICTED"
    assert finding.confidence_features["exhibit"] == "갑 제2호증"
    assert finding.confidence_features["names"] == [
        f"{title}, REF-AA 뒤 설명을 붙인다.", f"{title}: REF-BB 뒤 내용을 기록한다."]
    assert len(finding.evidence) == 1
    assert "REF-AA" in finding.evidence[0].excerpt and "REF-BB" in finding.evidence[0].excerpt
