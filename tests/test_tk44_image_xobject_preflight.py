"""Fabricated image pages and metadata-only Form admission controls."""
from types import SimpleNamespace

import pytest
from pdfminer.pdftypes import PDFObjRef, PDFStream
from pdfminer.psparser import LIT

from packages.document_engine import actualtext_boundaries as provider
from packages.document_engine.named_actualtext_capture import NamedActualTextCapture
from test_tk44_actualtext_provider import _parse
from test_tk44_selected_form_inspection import INSTRUCTIONS, form_pdf


def image_pdf(path, pages=1, color="white"):
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas
    canvas = Canvas(str(path), pageCompression=1)
    image = ImageReader(Image.new("RGB", (8, 8), color))
    for page in range(pages):
        canvas.setFont("Helvetica", 10)
        for line in range(30):
            canvas.drawString(50, 780 - line * 20,
                              f"Synthetic public reading line {line} on page {page}. Section {chr(65 + page)}.")
        canvas.drawImage(image, 400, 100, width=20, height=20)
        canvas.showPage()
    canvas.save()


@pytest.mark.parametrize("color", ("white", "blue", "green"))
def test_image_only_page_skips_provider_interpreter(tmp_path, monkeypatch, color):
    path = tmp_path / "image.pdf"
    image_pdf(path, color=color)
    def unexpected(*args):
        pytest.fail("image-only page entered the ActualText interpreter")
    monkeypatch.setattr(provider._Interpreter, "process_page", unexpected)
    doc = _parse(path)
    assert len(doc.pages) == 1
    assert any("Synthetic public reading line 29" in block.text for block in doc.blocks)
    assert doc.pages[0].attributes["actualtext_boundary_provider"]["inspection_unavailable"]
    assert doc.structure["named_actualtext_inspection"]["decode_calls"] == 0


@pytest.mark.parametrize("text", INSTRUCTIONS)
def test_form_still_admits_provider_and_security_source(tmp_path, monkeypatch, text):
    from packages.adversarial_engine.scanner import scan_document
    path = tmp_path / "form.pdf"
    form_pdf(path, text, indirect=True)
    calls = []
    original = provider._Interpreter.process_page
    def tracked(self, page):
        calls.append(page)
        return original(self, page)
    monkeypatch.setattr(provider._Interpreter, "process_page", tracked)
    doc = _parse(path)
    assert len(calls) == 1
    assert text in doc.structure["actual_text_strings"]
    assert any("ACTUAL_TEXT" in f.tags and "INSTRUCTION_OVERRIDE" in f.tags
               for f in scan_document(doc).findings)
    assert not doc.structure["named_actualtext_inspection"]["inspection_complete"]
    assert not doc.pages[0].attributes["actualtext_boundary_provider"]["certified_edges"]


def page_with(xobjects):
    return SimpleNamespace(page_number=1,
                           page_obj=SimpleNamespace(resources={"XObject": xobjects}))


@pytest.mark.parametrize("subtype,expected", (("Image", False), ("Form", True), ("PS", False)))
@pytest.mark.parametrize("indirect", (False, True))
def test_preflight_reads_only_stream_subtype(monkeypatch, subtype, expected, indirect):
    stream = PDFStream({"Subtype": LIT(subtype), "Resources": object()}, b"not decoded")
    def unexpected(*args):
        pytest.fail("preflight decoded an uninvoked XObject")
    monkeypatch.setattr(PDFStream, "get_data", unexpected)
    class ReferenceDocument:
        def getobj(self, objid):
            return stream
    value = PDFObjRef(ReferenceDocument(), 1, 0) if indirect else stream
    capture = NamedActualTextCapture()
    assert provider._named_available(page_with({"Source": value}), capture) is expected
    assert capture.contexts == 1 and capture.decode_calls == 0
    assert capture.reference_fetches == int(indirect)


def test_direct_xobject_admission_uses_shared_context_budget():
    capture = NamedActualTextCapture()
    images = {str(i): PDFStream({"Subtype": LIT("Image")}, b"")
              for i in range(capture.MAX_CONTEXTS)}
    images["BeyondBudget"] = PDFStream({"Subtype": LIT("Form")}, b"")
    assert not provider._named_available(page_with(images), capture)
    assert capture.exceeded and capture.contexts == capture.MAX_CONTEXTS
    assert not capture.inspection_complete and capture.decode_calls == 0


def test_dictionary_with_form_label_is_not_a_form_stream():
    capture = NamedActualTextCapture()
    assert not provider._named_available(page_with({"Malformed": {"Subtype": LIT("Form")}}), capture)


def test_indirect_subtype_uses_shared_reference_budget():
    class ReferenceDocument:
        def getobj(self, objid):
            return LIT("Form")
    stream = PDFStream({"Subtype": PDFObjRef(ReferenceDocument(), 1, 0)}, b"")
    capture = NamedActualTextCapture()
    assert provider._named_available(page_with({"Source": stream}), capture)
    assert capture.reference_fetches == 1
    exhausted = NamedActualTextCapture()
    exhausted.reference_visits = exhausted.MAX_REFERENCES
    assert not provider._named_available(page_with({"Source": stream}), exhausted)
    assert exhausted.exceeded and not exhausted.inspection_complete
