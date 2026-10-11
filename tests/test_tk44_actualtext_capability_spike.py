"""Public capability spike only; no production parser/provider is changed.

Run with pytest. Generated PDFs contain only synthetic Korean text. The custom
device demonstrates whether the existing pdfminer pipeline can bind an inline
ActualText property to original page glyphs, without equating MCIDs with identity.
"""
from collections import defaultdict
import json

import pdfplumber
import pytest
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.psparser import literal_name
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen.canvas import Canvas

from packages.document_engine import parse_document
from packages.document_engine.pdf_parser import PdfParser


def _pdf(path, *, width=595, font='HYSMyeongJo-Medium', size=12,
         logical='자료는 새문서로 정리된다.', mode='inline', direct_space=False,
         unrelated=0):
    pdfmetrics.registerFont(UnicodeCIDFont(font))
    canvas = Canvas(str(path), pagesize=(width, 842), pageCompression=1)
    canvas.setFont(font, size)
    prop = '<< /MCID 0 /ActualText <FEFF' + logical.encode('utf-16-be').hex() + '> >>'
    if mode == 'named':
        canvas.addLiteral('/Span /NamedProperty BDC')
    elif mode != 'untagged':
        canvas.addLiteral('/Span ' + prop + ' BDC')
    canvas.drawString(72, 700, '자료는 새' + (' ' if direct_space else ''))
    if mode == 'nested':
        canvas.addLiteral('/Span ' + prop + ' BDC')
    canvas.drawString(72, 700 - size * 1.5, '문서로 정리된다.')
    if mode == 'nested':
        canvas.addLiteral('EMC')
    if mode != 'untagged':
        canvas.addLiteral('EMC')
    for i in range(unrelated):
        canvas.drawString(72, 550 - i * 24, '별도 문단을 살펴본다.')
    canvas.save()


class _MarkedDevice(PDFPageAggregator):
    """Library hook spike, with invocation identity and a proper nested stack."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stack, self.spans, self.glyphs = [], [], []
        self.unsupported = []

    def begin_tag(self, tag, props=None):
        context = None
        if isinstance(props, dict) and 'ActualText' in props:
            raw = props['ActualText']
            text = None
            # Strict decoding; replacement/error ignoring cannot establish proof.
            if isinstance(raw, bytes) and raw.startswith(b'\xfe\xff'):
                try:
                    text = raw[2:].decode('utf-16-be')
                except UnicodeDecodeError:
                    pass
            context = {'invocation': len(self.spans), 'tag': literal_name(tag),
                       'mcid': props.get('MCID'), 'logical': text, 'glyphs': []}
            self.spans.append(context)
        elif props is not None and not isinstance(props, dict):
            self.unsupported.append('NAMED_PROPERTY_NOT_RESOLVED')
        self.stack.append(context)

    def end_tag(self):
        if self.stack:
            self.stack.pop()
        else:
            self.unsupported.append('UNBALANCED_MARKED_CONTENT')

    def render_char(self, *args, **kwargs):
        advance = super().render_char(*args, **kwargs)
        glyph = self.cur_item._objs[-1]
        index = len(self.glyphs)
        self.glyphs.append(glyph)
        for context in self.stack:
            if context is not None:
                context['glyphs'].append(index)
        return advance


def _observe(path):
    """Demonstration proof, restricted to one exact two-line source span.

    No matching dictionaries, NFKC equivalence, font/fullness inference, global
    MCID map or geometry-only JOIN. This is deliberately not a reusable provider.
    """
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        device = _MarkedDevice(pdf.rsrcmgr, pageno=1, laparams=pdf.laparams)
        PDFPageInterpreter(pdf.rsrcmgr, device).process_page(page.page_obj)
        chars = page.chars
        def key(text, x0, y0, x1, y1, font):
            return text, x0, y0, x1, y1, font
        page_index = defaultdict(list)
        for i, char in enumerate(chars):
            page_index[key(char['text'], char['x0'], char['y0'], char['x1'], char['y1'], char['fontname'])].append(i)
        mapping = []
        for glyph in device.glyphs:
            indices = page_index[key(glyph.get_text(), *glyph.bbox, glyph.fontname)]
            mapping.append(indices[0] if len(indices) == 1 else None)
        lines = PdfParser._group_chars_to_lines(chars)
        target = [line for line in lines if ''.join(c['text'] for c in line).strip()
                  in {'자료는 새', '문서로 정리된다.'}]
        source = {id(char): i for i, char in enumerate(chars)}
        target_ids = {source[id(c)] for line in target for c in line}
        candidates = [span for span in device.spans if target_ids
                      and target_ids <= {mapping[i] for i in span['glyphs']}]
        answer = {'state': 'UNKNOWN', 'reason': 'NO_UNIQUE_LOGICAL_SOURCE',
                  'glyph_count': len(chars), 'source_spans': len(device.spans),
                  'unsupported': device.unsupported}
        if len(target) != 2 or len(candidates) != 1:
            return answer
        span = candidates[0]
        mapped = [mapping[i] for i in span['glyphs']]
        ordered = [source[id(c)] for line in target for c in line]
        if mapped != ordered or any(i is None for i in mapped):
            answer['reason'] = 'NONEXACT_GLYPH_COVERAGE'
            return answer
        if any(sum(i in other['glyphs'] for other in device.spans) != 1 for i in span['glyphs']):
            answer['reason'] = 'OVERLAPPING_LOGICAL_SOURCES'
            return answer
        left, right = [''.join(c['text'] for c in line) for line in target]
        logical = span['logical']
        for separator, state in [('', 'JOIN_CONFIRMED'), (' ', 'SPACE_CONFIRMED')]:
            if logical == left + separator + right:
                if state == 'JOIN_CONFIRMED' and (left[-1:].isspace() or right[:1].isspace()):
                    answer['reason'] = 'SOURCE_SPACE_PRESENT'
                    return answer
                answer.update(state=state, reason='EXACT_ACTUALTEXT_GLYPH_COVERAGE',
                              source_invocation=span['invocation'], source_mcid=span['mcid'],
                              original_glyph_indices=mapped,
                              logical_boundary_span=[len(left), len(left) + len(separator)])
                return answer
        answer['reason'] = 'LOGICAL_GLYPH_DISAGREEMENT'
        return answer


@pytest.mark.parametrize('width,font,size,unrelated', [
    (420, 'HYSMyeongJo-Medium', 10, 0),
    (595, 'HYSMyeongJo-Medium', 12, 1),
    (720, 'HYGothic-Medium', 14, 2),
])
@pytest.mark.parametrize('separator,state', [('', 'JOIN_CONFIRMED'), (' ', 'SPACE_CONFIRMED')])
def test_exact_inline_source_capability_and_current_parser_gap(tmp_path, width, font, size, unrelated, separator, state):
    path = tmp_path / 'source.pdf'
    _pdf(path, width=width, font=font, size=size, unrelated=unrelated,
         logical='자료는 새' + separator + '문서로 정리된다.')
    evidence = _observe(path)
    assert evidence['state'] == state
    assert evidence['source_invocation'] == 0
    assert len(evidence['original_glyph_indices']) == len('자료는 새문서로 정리된다.')
    assert evidence['logical_boundary_span'] == [5, 5 + len(separator)]
    json.dumps(evidence)
    doc = parse_document(str(path), document_id='generated', filename=path.name,
                         mime_type='application/pdf', sha256='generated')
    block = next(b for b in doc.blocks if '자료는 새' in b.text)
    assert block.attributes['boundary_observations'][0]['boundary_signal'] == 'UNKNOWN'


@pytest.mark.parametrize('mode,logical,direct_space', [
    ('untagged', '자료는 새문서로 정리된다.', False),
    ('named', '자료는 새문서로 정리된다.', False),
    ('nested', '자료는 새문서로 정리된다.', False),
    ('inline', '자료는 새문서로 고쳐진다.', False),
    ('inline', '자료는 새\u200b문서로 정리된다.', False),
    ('inline', '자료는 새문서로 정리된다.', True),
])
def test_unsupported_ambiguous_or_conflicting_source_does_not_confirm_join(tmp_path, mode, logical, direct_space):
    path = tmp_path / 'opposite.pdf'
    _pdf(path, mode=mode, logical=logical, direct_space=direct_space)
    assert _observe(path)['state'] == 'UNKNOWN'


def test_visually_identical_untagged_boundary_cannot_be_resolved_from_geometry(tmp_path):
    path = tmp_path / 'no-logical-source.pdf'
    _pdf(path, mode='untagged')
    # Both author intents have exactly the same file/glyphs. No source provider
    # can certify either solely from the file's absent word-break evidence.
    assert _observe(path)['state'] == 'UNKNOWN'
    with pdfplumber.open(path) as pdf:
        assert all(c['mcid'] is None for c in pdf.pages[0].chars)
