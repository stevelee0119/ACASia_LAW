"""Public synthetic source-backed boundaries through the actual PDF parser."""
import io
import json

import pytest
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen.canvas import Canvas

from packages.document_engine import parse_document
from packages.document_engine.reading_text import build_reading_text
from packages.document_engine.boundary_candidates import project_boundary_candidate


def _source(path, *, left='공개된 새', right='자료를 검토한다.', separator='', width=595,
            mode='visible', repetitions=1):
    font = 'HYSMyeongJo-Medium'
    pdfmetrics.registerFont(UnicodeCIDFont(font))
    canvas = Canvas(str(path), pagesize=(width, 842), pageCompression=1)
    canvas.setFont(font, 12)
    if mode == 'rotation':
        canvas.rotate(5)
    if mode == 'alpha':
        canvas.setFillAlpha(0)
    if mode == 'clip':
        shape = canvas.beginPath(); shape.rect(0, 0, 1, 1)
        canvas.clipPath(shape, stroke=0, fill=0)
    if mode in {'unknown_outer', 'ocg_outer'}:
        canvas.addLiteral('/OC /Unresolved BDC' if mode == 'ocg_outer' else '/Div /Unresolved BDC')
    if mode == 'prior_paint':
        canvas.setFillColorRGB(1, 1, 1)
        canvas.rect(65, 670, 200, 70, stroke=0, fill=1)
        canvas.setFillColorRGB(0, 0, 0)
    for repeat in range(repetitions):
        logical = left + separator + right
        if mode == 'disagree': logical += '추가내용'
        if mode == 'zero_width': logical = left + '\u200b' + right
        encoded = 'FEFF' + logical.encode('utf-16-be').hex()
        if mode == 'bad_utf16': encoded = 'FEFFD800'
        prop = '<< /MCID 0 /ActualText <' + encoded + '> >>'
        if mode != 'untagged':
            canvas.addLiteral(('/Div ' if mode == 'nonspan' else '/Span ') + prop + ' BDC')
        if mode == 'form':
            canvas.beginForm('Body'); canvas.setFont(font, 12)
        canvas.drawString(72, 710 - repeat * 70, left, mode=3 if mode == 'invisible' else None)
        if mode == 'overlap':
            canvas.addLiteral('/Span ' + prop + ' BDC')
        canvas.drawString(72, 692 - repeat * 70, right, mode=3 if mode == 'invisible' else None)
        if mode == 'overlap': canvas.addLiteral('EMC')
        if mode == 'form':
            canvas.endForm(); canvas.doForm('Body')
        if mode not in {'untagged', 'unclosed'}:
            canvas.addLiteral('EMC')
    if mode in {'unknown_outer', 'ocg_outer'}: canvas.addLiteral('EMC')
    if mode in {'future_paint', 'future_colored_paint'}:
        canvas.setFillColorRGB(*( (1, 1, 1) if mode == 'future_paint' else (0.2, 0.5, 0.7)))
        canvas.rect(68, 688, 200, 40, stroke=0, fill=1)
    if mode == 'future_image':
        from PIL import Image
        from reportlab.lib.utils import ImageReader
        buffer = io.BytesIO(); Image.new('RGB', (5, 5), 'white').save(buffer, format='PNG')
        buffer.seek(0)
        canvas.drawImage(ImageReader(buffer), 68, 688, width=200, height=40)
    if mode == 'unrelated_future_paint':
        canvas.rect(68, 430, 200, 40, stroke=0, fill=1)
    canvas.save()


def _parse(path):
    return parse_document(str(path), document_id='generated', filename=path.name,
                          mime_type='application/pdf', sha256='generated')


@pytest.mark.parametrize('left,right', [('공개된 새', '자료를 검토한다.'), ('내용은 전문', '가가 확인하였다.'), ('검토한 가', '능성을 설명한다.')])
@pytest.mark.parametrize('width', [420, 595, 720])
@pytest.mark.parametrize('separator,state', [('', 'JOIN_CONFIRMED'), (' ', 'SPACE_CONFIRMED')])
def test_original_logical_separator_controls_primary_reading_and_provenance(tmp_path, left, right, width, separator, state):
    path = tmp_path / 'source.pdf'
    _source(path, left=left, right=right, separator=separator, width=width)
    doc = _parse(path)
    block = next(b for b in doc.blocks if left in b.text)
    assert block.text == left + separator + right
    observation = block.attributes['boundary_observations'][0]
    assert observation['boundary_signal'] == state
    evidence = observation['logical_source_evidence']
    assert evidence['logical_boundary_span'] == [len(left), len(left) + len(separator)]
    assert evidence['balanced_scope'] is True and evidence['mcid_is_identity'] is False
    assert evidence['separator'] == separator and 'logical_text' not in evidence
    assert observation['decision']['legacy']['used_for_selection'] is False
    assert len(observation['decision']['alternatives']) == 1
    assert project_boundary_candidate(block) == block.text
    assert block.text in build_reading_text(doc).text
    json.dumps(doc.to_dict(), ensure_ascii=False)


@pytest.mark.parametrize('mode', ['untagged', 'rotation', 'alpha', 'clip', 'unknown_outer', 'ocg_outer',
                                'nonspan', 'bad_utf16', 'zero_width', 'disagree', 'invisible', 'unclosed',
                                'form', 'overlap', 'future_paint', 'future_colored_paint', 'future_image'])
def test_unproved_scope_rendering_or_mapping_has_no_join_proof(tmp_path, mode):
    path = tmp_path / 'opposite.pdf'
    _source(path, mode=mode)
    doc = _parse(path)
    observations = [o for block in doc.blocks for o in block.attributes.get('boundary_observations', [])]
    assert not any(o['boundary_signal'] == 'JOIN_CONFIRMED' for o in observations)


@pytest.mark.parametrize('mode', ['visible', 'prior_paint', 'unrelated_future_paint'])
def test_reused_mcid_has_independent_invocations_and_unrelated_paint_is_local(tmp_path, mode):
    path = tmp_path / 'repeat.pdf'
    _source(path, mode=mode, repetitions=2)
    doc = _parse(path)
    proofs = [o['logical_source_evidence'] for b in doc.blocks for o in b.attributes.get('boundary_observations', [])
              if o['boundary_signal'] == 'JOIN_CONFIRMED']
    assert len(proofs) == 2
    assert {p['invocation_id'] for p in proofs} == {0, 1}


def test_direct_source_space_is_not_overridden_by_disagreeing_actualtext(tmp_path):
    path = tmp_path / 'conflict.pdf'
    _source(path, left='자료는 새 ', right='기록이다.')
    # Logical text also includes that painted space; direct glyph provider wins.
    doc = _parse(path)
    observation = next(o for b in doc.blocks for o in b.attributes.get('boundary_observations', []))
    assert observation['boundary_signal'] == 'SPACE_CONFIRMED'
    assert observation['reason'] == 'DIRECT_SPACE_GLYPH'


@pytest.mark.parametrize('repetitions', [16, 64, 256])
def test_mapping_accounting_is_bounded_without_per_boundary_text_copies(tmp_path, repetitions):
    # Deliberately exceed page bounds as the count grows; unsupported later rows
    # do not change the bounded traversal/association of original source glyphs.
    path = tmp_path / 'growth.pdf'
    _source(path, repetitions=repetitions)
    doc = _parse(path)
    stats = doc.pages[0].attributes['actualtext_boundary_provider']
    assert stats['association_visits'] <= 32 * stats['rendered_glyphs']
    assert stats['paint_candidate_visits'] <= 32 * max(1, stats['rendered_glyphs'])
    assert stats['source_spans'] == repetitions


@pytest.mark.parametrize('format', ['txt', 'docx'])
@pytest.mark.parametrize('separator', ['', ' '])
def test_original_logical_text_other_formats_remains_unmodified(tmp_path, format, separator):
    text = '공개된 새' + separator + '자료를 검토한다.'
    path = tmp_path / ('source.' + format)
    if format == 'txt':
        path.write_text(text, encoding='utf-8')
        mime = 'text/plain'
    else:
        from docx import Document
        source = Document(); source.add_paragraph(text); source.save(path)
        mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    doc = parse_document(str(path), document_id='generated', filename=path.name,
                         mime_type=mime, sha256='generated')
    assert text in build_reading_text(doc).text
    assert all('actualtext_boundary_evidence' not in b.attributes for b in doc.blocks)


@pytest.mark.parametrize('separator', ['', ' '])
def test_actual_pipeline_consumes_certified_primary_without_claiming_hypotheses_checked(tmp_path, separator):
    from packages.audit_engine import AuditChain
    from packages.common.storage import sha256_file
    from packages.verification_engine import DocumentInput, ProjectContext, VerificationPipeline
    path = tmp_path / 'pipeline.pdf'
    _source(path, separator=separator)
    item = DocumentInput('generated', str(path), path.name, 'application/pdf', sha256_file(path))
    result = VerificationPipeline(audit=AuditChain()).run('source-' + tmp_path.name, ProjectContext('public'), [item])
    assert not result.errors
    metadata = result.documents[0].engine_data['input_boundary_associations']
    assert metadata['unknown_count'] == 0
    assert metadata['alternatives_checked'] is False
    assert metadata['boundaries'][0]['observed_state'] == ('JOIN_CONFIRMED' if not separator else 'SPACE_CONFIRMED')
