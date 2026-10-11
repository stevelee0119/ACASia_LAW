"""Actual PDF availability is not proof of inspected source absence."""
import pytest
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfdoc import PDFDictionary,PDFString
from reportlab.pdfgen.canvas import Canvas
from packages.document_engine.reading_text import build_reading_text
from test_tk44_actualtext_provider import _parse
from test_tk44_named_actualtext_capture_budget_spike import trial
from tk44_named_capture_budget import CaptureBudget


def pages(path, modes):
    font='HYSMyeongJo-Medium';pdfmetrics.registerFont(UnicodeCIDFont(font))
    canvas=Canvas(str(path),pagesize=(595,842),pageCompression=1)
    for index,mode in enumerate(modes):
        canvas.setFont(font,12)
        if mode.endswith('selected'):canvas.addLiteral('/Span /Selected BDC')
        canvas.drawString(72,710,'공개된 새');canvas.drawString(72,692,'자료를 검토한다.')
        if mode.endswith('selected'):canvas.addLiteral('EMC')
        canvas.showPage();page=canvas._doc.Pages.pages[-1];page.check_format(canvas._doc)
        # A plain empty Python dict is omitted by ReportLab resources.format.
        # Preserve an actual /Properties << >> entry for this source contrast.
        if mode.startswith('empty'):page.Resources.Properties=PDFDictionary({})
        if mode.startswith('supported'):
            value=PDFDictionary({'ActualText':PDFString('공개된 새자료를 검토한다.'),'MCID':0})
            page.Resources.Properties={'Selected':canvas._doc.Reference(value,'Selected'+str(index))}
    canvas.save()


@pytest.mark.parametrize('mode,state,attempts,completed,unavailable,missing,complete',[
 ('absent-selected','UNAVAILABLE_UNINSPECTED',0,0,1,0,False),
 ('empty-selected','INSPECTED_INCOMPLETE',1,1,0,1,False),
 ('absent-unused','UNAVAILABLE_UNINSPECTED',0,0,1,0,False),
 ('empty-unused','INSPECTED_NO_SELECTED_PAGE_NAMED_SOURCE',1,1,0,0,True),
 ('supported-selected','INSPECTED_SUPPORTED',1,1,0,0,True),
])
def test_actual_page_inspection_lifecycle(tmp_path,monkeypatch,mode,state,attempts,completed,unavailable,missing,complete):
    path=tmp_path/'lifecycle.pdf';pages(path,[mode])
    baseline=_parse(path);doc,adapter=trial(path,monkeypatch);stats=adapter.capture.snapshot()
    assert stats['inspection_complete'] is complete
    assert stats['inspection_state']==state
    assert stats['inspection_attempted_pages']==attempts
    assert stats['inspection_completed_pages']==completed
    assert stats['inspection_unavailable_pages']==unavailable
    assert stats['selected_property_missing']==missing
    assert stats['named_selection_requests']==int(mode.endswith('selected') and attempts>0)
    if mode=='supported-selected':
        assert stats['decode_calls']==1
        assert any(page.attributes['actualtext_boundary_provider'].get('certified_edges',0)==1 for page in doc.pages)
    else:
        assert stats['decode_calls']==0
        assert build_reading_text(doc).text==build_reading_text(baseline).text


def test_other_page_success_cannot_replace_uninspected_page(tmp_path,monkeypatch):
    path=tmp_path/'mixed.pdf';pages(path,['absent-selected','supported-selected'])
    doc,adapter=trial(path,monkeypatch);stats=adapter.capture.snapshot()
    assert stats['inspection_state']=='INSPECTED_INCOMPLETE'
    assert not stats['inspection_complete']
    assert stats['inspection_attempted_pages']==stats['inspection_completed_pages']==1
    assert stats['inspection_unavailable_pages']==1
    assert stats['decode_calls']==1


def test_not_attempted_or_active_capture_never_claims_complete():
    capture=CaptureBudget()
    assert capture.snapshot()['inspection_state']=='NOT_ATTEMPTED'
    assert not capture.inspection_complete
    capture.begin_page()
    assert capture.snapshot()['inspection_state']=='IN_PROGRESS'
    assert not capture.inspection_complete


def test_failed_interpretation_stays_incomplete_after_later_success():
    capture=CaptureBudget();capture.begin_page();capture.end_page(False)
    capture.begin_page();capture.end_page(True)
    stats=capture.snapshot()
    assert not stats['inspection_complete'] and stats['inspection_state']=='INSPECTED_INCOMPLETE'
    assert stats['inspection_failed_pages']==1
