"""Fabricated native documents exercise the unchanged design-only consumer."""
import json

import pytest
from docx import Document
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen.canvas import Canvas

from packages.audit_engine import AuditChain
from packages.common.storage import sha256_file
from packages.document_engine.reading_text import build_reading_text
from packages.verification_engine import DocumentInput, ProjectContext, VerificationPipeline
from test_tk45_norm_binding_capability_spike import POSITIVE
from test_tk45_norm_legal_admission_spike import EFFECT, UNKNOWN_PREMISES
from tk45_norm_binding_capability import proposal_admission


MIME = {"txt": "text/plain", "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def document(path, source):
    if path.suffix == ".txt":
        path.write_text(source, encoding="utf-8")
    elif path.suffix == ".docx":
        doc = Document()
        for line in source.splitlines():
            doc.add_paragraph(line)
        doc.save(str(path))
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
        canvas = Canvas(str(path), pagesize=(2400, 842))
        canvas.setFont("HYSMyeongJo-Medium", 12)
        for i, line in enumerate(source.splitlines()):
            canvas.drawString(72, 730 - i * 24, line)
        canvas.save()


def run(path, source):
    document(path, source)
    result = VerificationPipeline(audit=AuditChain()).run("tk45-native-public", ProjectContext("public"), [
        DocumentInput("public", str(path), path.name, MIME[path.suffix[1:]], sha256_file(path))])
    assert not result.errors
    return result


def receipt(result):
    return json.dumps([f.to_dict() for f in result.all_findings], ensure_ascii=False, sort_keys=True)


@pytest.mark.parametrize("format", MIME)
@pytest.mark.parametrize("name,body,kind", POSITIVE, ids=[r[0] for r in POSITIVE])
def test_native_pipeline_source_admission_stays_separate_from_findings(tmp_path, format, name, body, kind):
    result = run(tmp_path / (name + "." + format), "청구원인\n" + body)
    before = receipt(result)
    doc = result.documents[0].normalized
    proposed = proposal_admission(doc)
    assert proposed and proposed["local_source_attachment_admitted"]
    text = build_reading_text(doc).text
    for key, (a, b) in proposed["source_spans"].items():
        assert text[a:b] == proposed["source_slices"][key]
    assert receipt(result) == before
    for field in ("legal_effect_sense_selected", "facts_verified", "legal_sufficiency_verified",
                  "supports_asserted_fulfillment", "total_requirement_completion",
                  "findings_created", "product_consumer_installed"):
        assert proposed[field] is False


@pytest.mark.parametrize("format", MIME)
@pytest.mark.parametrize("name,premise", UNKNOWN_PREMISES, ids=[r[0] for r in UNKNOWN_PREMISES])
def test_native_plan_preparation_assumption_and_report_do_not_gain_legal_admission(tmp_path, format, name, premise):
    result = run(tmp_path / (name + "." + format), "청구원인\n" + EFFECT.replace("완료하였으므로", premise))
    before = receipt(result)
    assert proposal_admission(result.documents[0].normalized) is None
    assert receipt(result) == before


@pytest.mark.parametrize("format", MIME)
@pytest.mark.parametrize("prefix", (
    "상대방은 다음과 같이 주장한다.\n", "청구취지\n청구를 기각한다.\n",
    "이하 주장을 반박한다.\n",
))
def test_native_body_heading_cannot_hide_original_prefix(tmp_path, format, prefix):
    result = run(tmp_path / ("prefix." + format), prefix + "청구원인\n" + POSITIVE[0][1])
    before = receipt(result)
    assert proposal_admission(result.documents[0].normalized) is None
    assert receipt(result) == before
