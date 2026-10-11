"""Design-only page Properties resolution; production remains unchanged."""
import pytest
from pdfminer.pdftypes import PDFObjRef
from pdfminer.psparser import PSLiteral, literal_name
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfdoc import PDFDictionary, PDFString, PDFName
from reportlab.pdfgen.canvas import Canvas

from packages.document_engine import actualtext_boundaries as provider
from test_tk44_actualtext_provider import _parse


def bounded_resolve(value, limit=8):
    seen = set()
    for _ in range(limit):
        if not isinstance(value, PDFObjRef):
            return value
        identity = (id(value.doc), value.objid)
        if identity in seen:
            return None
        seen.add(identity)
        try:
            value = value.resolve()
        except Exception:
            return None
    return None


class ResourceInterpreter(provider._Interpreter):
    """Only exact current-page named property dictionaries, never Form proof."""
    def do_BDC(self, tag, props):
        if isinstance(props, PSLiteral):
            resources = bounded_resolve(self.resources)
            properties = bounded_resolve(resources.get('Properties')) if isinstance(resources, dict) else None
            selected = bounded_resolve(properties.get(literal_name(props))) if isinstance(properties, dict) else None
            if isinstance(selected, dict):
                props = selected
        return super().do_BDC(tag, props)


def source(path, left, right, separator, width, mode='named', indirect=True,
           font='HYSMyeongJo-Medium', size=12, unrelated=0):
    pdfmetrics.registerFont(UnicodeCIDFont(font))
    canvas = Canvas(str(path), pagesize=(width, 842), pageCompression=1)
    canvas.setFont(font, size)
    # Activate existing provider's byte preflight only. This comment is not a
    # replacement source; only the actual resource dictionary can prove text.
    canvas.addLiteral('% /ActualText page resource capability preflight')
    if mode == 'alpha': canvas.setFillAlpha(0)
    if mode == 'rotation': canvas.rotate(5)
    if mode == 'unknown_outer': canvas.addLiteral('/Div /Absent BDC')
    if mode == 'ocg_outer': canvas.addLiteral('/OC /Boundary BDC')
    if mode == 'form': canvas.beginForm('Body'); canvas.setFont(font, 12)
    canvas.addLiteral(('/Div ' if mode == 'nonspan' else '/Span ') + '/Boundary BDC')
    canvas.drawString(72, 710, left, mode=3 if mode == 'invisible' else None)
    canvas.drawString(72, 692, right, mode=3 if mode == 'invisible' else None)
    if mode != 'unclosed': canvas.addLiteral('EMC')
    if mode == 'form': canvas.endForm(); canvas.doForm('Body')
    if mode in {'unknown_outer', 'ocg_outer'}: canvas.addLiteral('EMC')
    if mode == 'future_shading':
        canvas.linearGradient(0, 0, width, 842, [(1, 1, 1), (1, 1, 1)], extend=True)
    for index in range(unrelated):
        canvas.drawString(72, 550 - index * 30, '별도 문단을 확인한다.')
    canvas.showPage()
    page = canvas._doc.Pages.pages[-1]
    page.check_format(canvas._doc)
    logical = left + separator + right
    if mode == 'disagree': logical += '별개'
    if mode == 'zero_width': logical = left + '\u200b' + right
    value = PDFDictionary({'ActualText': PDFString(logical), 'MCID': 0})
    if mode == 'wrong_type': value = PDFString(logical)
    if mode == 'bad_utf16': value = PDFDictionary({'ActualText': PDFString(b'\xfe\xff\xd8\x00')})
    if mode == 'ocg_property': value = PDFDictionary({'ActualText': PDFString(logical), 'OC': PDFName('Other')})
    if indirect: value = canvas._doc.Reference(value, 'PublicBoundaryProperty')
    page.Resources.Properties = {} if mode == 'missing' else {'Boundary': value}
    canvas.save()


def observations(doc):
    return [o for b in doc.blocks for o in b.attributes.get('boundary_observations', [])]


@pytest.mark.parametrize('left,right', [('공개된 새', '자료를 검토한다.'), ('내용은 전문', '가가 확인하였다.'), ('검토한 가', '능성을 설명한다.')])
@pytest.mark.parametrize('width', [420, 595, 720])
@pytest.mark.parametrize('separator,state', [('', 'JOIN_CONFIRMED'), (' ', 'SPACE_CONFIRMED')])
@pytest.mark.parametrize('indirect', [False, True])
def test_named_page_property_owns_source_not_name_or_layout(tmp_path, monkeypatch, left, right, width, separator, state, indirect):
    path = tmp_path / 'named.pdf'
    source(path, left, right, separator, width, indirect=indirect)
    baseline = _parse(path)
    assert observations(baseline)[0]['boundary_signal'] == 'UNKNOWN'
    with monkeypatch.context() as patch:
        patch.setattr(provider, '_Interpreter', ResourceInterpreter)
        proposed = _parse(path)
    observation = observations(proposed)[0]
    assert observation['boundary_signal'] == state
    assert observation['logical_source_evidence']['logical_boundary_span'] == [len(left), len(left) + len(separator)]
    assert proposed.blocks[0].text == left + separator + right


@pytest.mark.parametrize('mode', ['missing', 'wrong_type', 'bad_utf16', 'unknown_outer', 'ocg_outer', 'ocg_property', 'nonspan', 'invisible', 'alpha', 'rotation', 'form', 'unclosed', 'disagree', 'zero_width', 'future_shading'])
def test_resource_lookup_does_not_relax_existing_source_visibility_scope(tmp_path, monkeypatch, mode):
    path = tmp_path / 'opposite.pdf'
    source(path, '공개된 새', '자료를 검토한다.', '', 595, mode=mode)
    baseline = _parse(path)
    with monkeypatch.context() as patch:
        patch.setattr(provider, '_Interpreter', ResourceInterpreter)
        proposed = _parse(path)
    assert all(o['boundary_signal'] == 'UNKNOWN' for o in observations(proposed))
    assert [b.text for b in proposed.blocks] == [b.text for b in baseline.blocks]
    assert proposed.raw_layers == baseline.raw_layers


def test_resolution_budget_does_not_treat_unproved_value_as_dictionary():
    assert bounded_resolve(None) is None
    assert bounded_resolve('not a dictionary') == 'not a dictionary'
    class CyclicDocument:
        def getobj(self, objid): return PDFObjRef(self, objid, None)
    assert bounded_resolve(PDFObjRef(CyclicDocument(), 1, None)) is None


@pytest.mark.parametrize('font,size,unrelated', [('HYSMyeongJo-Medium', 10, 0), ('HYSMyeongJo-Medium', 14, 2), ('HYGothic-Medium', 10, 2), ('HYGothic-Medium', 14, 0)])
def test_resource_proof_does_not_take_font_or_other_paragraph_as_separator_evidence(tmp_path, monkeypatch, font, size, unrelated):
    path = tmp_path / 'layout.pdf'
    source(path, '검토한 가', '능성을 설명한다.', '', 595, font=font, size=size, unrelated=unrelated)
    with monkeypatch.context() as patch:
        patch.setattr(provider, '_Interpreter', ResourceInterpreter)
        proposed = _parse(path)
    observation = observations(proposed)[0]
    assert observation['boundary_signal'] == 'JOIN_CONFIRMED'
    assert observation['logical_source_evidence']['logical_boundary_span'] == [5, 5]
