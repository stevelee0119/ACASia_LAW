"""Public synthetic document-context controls; source role, not header exceptions."""
import runpy
from pathlib import Path

import pytest

from packages.claim_engine.evidence_consistency import exhibit_rows

_helpers = runpy.run_path(str(Path(__file__).with_name('test_tk73_reference_title_prefix.py')))
_parsed = _helpers['_parsed']
_duplicates = _helpers['_duplicates']

_HEADINGS = [('가. 수집문헌 목록', '나. 문헌 검토'),
             ('2. 제출문서 목록', '3. 내용 분석'),
             ('(1) 확보자료 목록', '(2) 자료 설명')]


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('heading,peer', _HEADINGS)
def test_synthetic_inventory_is_scoped_before_independent_narrative(tmp_path, extension, heading, peer):
    doc = _parsed(tmp_path, extension, [heading,
        '갑 제1호증: 점검기록, 북쪽 보관 구역. 갑 제2호증의 1: 배치대장, 별도 제출 부분.',
        peer, '갑 제1호증 점검기록: 순서를 설명한다.',
        '갑 제2호증의 1 배치대장: 경로를 기록한다.', '첨부서류'])
    rows = exhibit_rows(doc)
    assert len(rows) == 4 and not any(row['in_section'] for row in rows)
    assert not _duplicates(doc)


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('heading,peer', _HEADINGS)
def test_synthetic_inventory_genuine_distinct_definitions_remain_a(tmp_path, extension, heading, peer):
    doc = _parsed(tmp_path, extension, [heading,
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제1호증: 점검보고, 별도 부분.',
        peer, '갑 제1호증 점검기록: 순서를 설명한다.', '첨부서류'])
    found = _duplicates(doc)
    assert len(found) == 1 and str(found[0].evidence_grade) == 'A'


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('heading,peer', _HEADINGS)
@pytest.mark.parametrize('mode', ['no_heading', 'single_entry', 'no_peer', 'narrative_entries'])
def test_synthetic_inventory_heading_requires_independent_scope_evidence(tmp_path, extension, heading,
                                                                         peer, mode):
    first = '갑 제1호증: 점검기록, 북쪽 보관 구역.'
    if mode != 'single_entry':
        first += ' 갑 제2호증: 배치대장, 별도 제출 부분.'
    if mode == 'narrative_entries':
        first = '갑 제1호증 점검기록: 북쪽에 있다. 갑 제2호증 배치대장: 경로를 기록한다.'
    lines = ([] if mode == 'no_heading' else [heading]) + [first]
    if mode != 'no_peer':
        lines += [peer]
    lines += ['갑 제1호증 점검기록: 순서를 설명한다.', '첨부서류']
    found = _duplicates(_parsed(tmp_path, extension, lines))
    assert len(found) == 1 and str(found[0].evidence_grade) == 'A'


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('title,other', [('기록: 봄', '기록: 겨울'), ('관측, 동쪽', '관측, 서쪽'),
                                       ('관측 [2024. 1. 2.]', '관측 [2024. 1. 3.]')])
def test_synthetic_context_preserves_real_inventory_title_content(tmp_path, extension, title, other):
    doc = _parsed(tmp_path, extension, ['가. 수집문헌 목록',
        f'갑 제1호증: {title}, 북쪽 보관 구역. 갑 제1호증: {other}, 별도 제출 부분.',
        '나. 문헌 검토', f'갑 제1호증 {title}: 순서를 설명한다.', '첨부서류'])
    found = _duplicates(doc)
    assert len(found) == 1 and str(found[0].evidence_grade) == 'A'


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('label', ['을 제1호증', '갑 제1호증의 2', '갑 제3호증'])
def test_synthetic_scope_does_not_exclude_other_party_number_or_branch(tmp_path, extension, label):
    doc = _parsed(tmp_path, extension, ['가. 수집문헌 목록',
        '갑 제1호증의 1: 점검기록, 북쪽 보관 구역. 갑 제2호증: 배치대장, 별도 제출 부분.',
        '나. 문헌 검토', f'{label} 표본기록', f'{label} 표본보고', '첨부서류'])
    found = _duplicates(doc)
    assert len(found) == 1 and str(found[0].evidence_grade) == 'A'


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
def test_synthetic_child_heading_does_not_prove_inventory_end(tmp_path, extension):
    doc = _parsed(tmp_path, extension, ['가. 수집문헌 목록',
        '갑 제1호증: 점검기록, 북쪽 보관 구역. 갑 제2호증: 배치대장, 별도 제출 부분.',
        '(1) 내용 설명', '갑 제1호증 점검기록: 순서를 설명한다.', '첨부서류'])
    assert len(_duplicates(doc)) == 1


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
def test_synthetic_ancestor_boundary_ends_authoritative_parent_context(tmp_path, extension):
    doc = _parsed(tmp_path, extension, ['1. 제출 경위', '가. 수집문헌 목록',
        '갑 제1호증: 점검기록, 북쪽 보관 구역. 갑 제2호증: 배치대장, 별도 제출 부분.',
        '나. 문헌 검토', '갑 제1호증 점검기록: 순서를 설명한다.',
        '2. 새로운 자료 정의', '갑 제1호증 표본기록', '갑 제1호증 표본보고', '첨부서류'])
    found = _duplicates(doc)
    assert len(found) == 1 and str(found[0].evidence_grade) == 'A'


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('reverse', [False, True])
def test_synthetic_nested_parent_repeated_scopes_and_entry_order(tmp_path, extension, reverse):
    first = ['갑 제1호증: 점검기록, 북쪽 구역.', '갑 제2호증: 배치대장, 별도 부분.']
    second = ['갑 제3호증: 확인표, 중앙 구역.', '갑 제4호증: 작업도, 동쪽 부분.']
    if reverse:
        first.reverse()
        second.reverse()
    doc = _parsed(tmp_path, extension, ['1. 자료 제출', '가. 수집문헌 목록', ' '.join(first),
        '(1) 기재 순서', '나. 문헌 검토', '갑 제2호증 배치대장: 경로를 기록한다.',
        '갑 제1호증 점검기록: 순서를 설명한다.', '2. 추가 제출', '가. 확보문서 목록',
        ' '.join(second), '나. 문서 검토', '갑 제4호증 작업도: 위치를 기록한다.',
        '갑 제3호증 확인표: 순서를 설명한다.', '첨부서류'])
    assert not _duplicates(doc)


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
def test_synthetic_next_heading_limits_narrative_exemption(tmp_path, extension):
    doc = _parsed(tmp_path, extension, ['가. 수집문헌 목록',
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
        '나. 문헌 검토', '갑 제1호증 점검기록: 순서를 설명한다.',
        '다. 다른 문서 정의', '갑 제1호증 표본기록', '갑 제1호증 표본보고', '첨부서류'])
    assert len(_duplicates(doc)) == 1


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('head,peer', [('가． 수집문헌 목록', '나. 문헌 검토'),
                                      ('가. 수집문헌 목록', '나． 문헌 검토')])
def test_synthetic_normalization_created_heading_marker_is_not_source_proof(tmp_path, extension, head, peer):
    doc = _parsed(tmp_path, extension, [head,
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
        peer, '갑 제1호증 점검기록: 순서를 설명한다.', '첨부서류'])
    assert len(_duplicates(doc)) == 1


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
def test_synthetic_scope_proofs_cover_original_source_and_keep_all_rows(tmp_path, extension):
    import copy
    from packages.claim_engine.evidence_consistency import _duplicate_inventory_roles, _numbering
    from packages.document_engine.reading_text import build_reading_text
    doc = _parsed(tmp_path, extension, ['가. 수집문헌 목록',
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증의 1: 배치대장, 별도 부분.',
        '나. 문헌 검토', '갑 제1호증 점검기록: 순서를 설명한다.',
        '갑 제2호증의 1 배치대장: 경로를 기록한다.', '첨부서류'])
    rows = exhibit_rows(doc)
    before = copy.deepcopy(rows)
    reading = build_reading_text(doc)
    excluded, scopes = _duplicate_inventory_roles(reading, rows)
    assert len(scopes) == 1 and len(excluded) == 2
    for proof in [scopes[0]['heading'], scopes[0]['close']] + scopes[0]['entry_proofs']:
        start, end = proof['reading_span']
        assert reading.text[start:end] == proof['text']
        block, _ = reading.locate(start)
        left, right = proof['block_span']
        assert block.text[left:right] == proof['text']
        assert proof['precision'] in ('block', 'original_first_line')
    assert scopes[0]['keys'] == {('갑', 1, None), ('갑', 2, 1)}
    assert not _numbering(doc, rows)
    assert rows == before


def test_synthetic_docx_scoped_inventory_and_genuine_opposite(tmp_path):
    from docx import Document
    from packages.document_engine.registry import parse_document
    for other, expected in [('점검기록', 0), ('표본보고', 1)]:
        out = Document()
        lines = ['가. 확보문서 목록',
                 f'갑 제1호증: 점검기록, 북쪽 구역. 갑 제1호증: {other}, 북쪽 구역.',
                 '나. 문서 검토', '갑 제1호증 점검기록: 순서를 설명한다.', '첨부서류']
        for line in lines:
            out.add_paragraph(line)
        path = tmp_path / 'public_scoped_inventory.docx'
        out.save(path)
        doc = parse_document(str(path), document_id='public_scoped_inventory', filename=path.name,
                             mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                             sha256='0' * 64)
        assert len(_duplicates(doc)) == expected


def test_synthetic_many_unclosed_fake_child_scopes_stay_forward_bounded(tmp_path):
    import time
    from packages.claim_engine.evidence_consistency import _duplicate_inventory_roles
    from packages.document_engine.reading_text import build_reading_text
    lines = []
    for _ in range(1000):
        lines += ['가. 확보문서 목록',
                  '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
                  '(1) 보충 설명']
    doc = _parsed(tmp_path, 'txt', lines)
    rows = exhibit_rows(doc)
    reading = build_reading_text(doc)
    started = time.perf_counter()
    excluded, scopes = _duplicate_inventory_roles(reading, rows)
    elapsed = time.perf_counter() - started
    assert not excluded and not scopes
    assert elapsed < 0.1


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('peer', ['나. 경로가 있다', '나. 기록이 없다', '나. 이것은 설명이다'])
def test_synthetic_numbered_proposition_is_not_an_independent_close_heading(tmp_path, extension, peer):
    doc = _parsed(tmp_path, extension, ['가. 수집문헌 목록',
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
        peer, '갑 제1호증 점검기록: 순서를 설명한다.', '첨부서류'])
    assert len(_duplicates(doc)) == 1


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
def test_synthetic_nested_inventory_has_more_specific_child_narrative_role(tmp_path, extension):
    doc = _parsed(tmp_path, extension, ['1. 제출문서 목록',
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
        '가. 추가문헌 목록', '갑 제3호증: 확인표, 중앙 구역. 갑 제4호증: 작업도, 동쪽 부분.',
        '나. 문헌 검토', '갑 제3호증 확인표: 순서를 설명한다.',
        '갑 제4호증 작업도: 위치를 기록한다.', '2. 자료 검토',
        '갑 제1호증 점검기록: 순서를 설명한다.', '갑 제2호증 배치대장: 경로를 기록한다.', '첨부서류'])
    assert not _duplicates(doc)


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
def test_synthetic_next_inventory_heading_is_not_a_narrative_exemption(tmp_path, extension):
    doc = _parsed(tmp_path, extension, ['가. 수집문헌 목록',
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
        '나. 추가문헌 목록', '갑 제1호증: 표본보고, 다른 부분. 갑 제3호증: 확인표, 중앙 구역.',
        '첨부서류'])
    found = _duplicates(doc)
    assert len(found) == 1 and str(found[0].evidence_grade) == 'A'


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
def test_synthetic_ancestor_close_does_not_create_a_sibling_exemption(tmp_path, extension):
    doc = _parsed(tmp_path, extension, ['1. 기존 자료', '가. 수집문헌 목록',
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
        '2. 새로운 문서 정의', '갑 제1호증 표본기록', '갑 제1호증 표본보고', '첨부서류'])
    found = _duplicates(doc)
    assert len(found) == 1 and str(found[0].evidence_grade) == 'A'


def _fragmented_peer_document(tmp_path, extension, heading, peer, fragmented):
    if extension == 'txt':
        marker, title = peer.split(' ', 1)
        peer_lines = [marker, title + ' A 설명'] if fragmented else [peer + ' A 설명']
        return _parsed(tmp_path, extension, [heading,
            '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.'] + peer_lines +
            ['갑 제1호증 점검기록: 순서를 설명한다.', '첨부서류'])
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen import canvas
    from scripts.audit.corpus import _register_font, FONT
    from packages.document_engine.registry import parse_document
    _register_font()
    path = tmp_path / 'public_fragmented_peer.pdf'
    out = canvas.Canvas(str(path), pagesize=A4)
    part = peer + ' A'
    width_size = 450 / pdfmetrics.stringWidth(part, FONT, 1)
    lines = [(11, 790, heading),
             (11, 740, '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.')]
    lines += [(width_size, 650, part), (11, 550, '설명')] if fragmented else [(11, 650, part + ' 설명')]
    lines += [(11, 450, '갑 제1호증 점검기록: 순서를 설명한다.'), (11, 400, '첨부서류')]
    for size, y, text in lines:
        out.setFont(FONT, size)
        out.drawString(50, y, text)
    out.save()
    return parse_document(str(path), document_id='public_fragmented_peer', filename=path.name,
                          mime_type='application/pdf', sha256='0' * 64)


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('heading,peer', _HEADINGS)
@pytest.mark.parametrize('fragmented', [False, True])
def test_synthetic_original_peer_heading_vs_virtual_or_incomplete_source(tmp_path, extension, heading,
                                                                       peer, fragmented):
    from packages.claim_engine.evidence_consistency import _duplicate_inventory_roles
    from packages.document_engine.reading_text import build_reading_text
    doc = _fragmented_peer_document(tmp_path, extension, heading, peer, fragmented)
    rows = exhibit_rows(doc)
    assert len(rows) == 3
    reading = build_reading_text(doc)
    if extension == 'pdf' and fragmented:
        first = next(segment for segment in reading.segments if segment.block.text == peer + ' A')
        assert reading.text[first.end:first.end + 1] == ' '
        assert not any(segment.start <= first.end < segment.end for segment in reading.segments)
    _, scopes = _duplicate_inventory_roles(reading, rows)
    assert bool(scopes) is not fragmented
    assert len(_duplicates(doc)) == (1 if fragmented else 0)


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('legacy', ['가. 증거 목록', '가. 입증방법', '가. 소명방법'])
@pytest.mark.parametrize('new_heading', [False, True])
def test_synthetic_original_recognized_sticky_population_is_not_rescoped(tmp_path, extension, legacy,
                                                                      new_heading):
    doc = _parsed(tmp_path, extension, [legacy] + (['나. 수집문헌 목록'] if new_heading else []) + [
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
        '다. 문헌 검토', '갑 제1호증 점검기록: 순서를 설명한다.', '첨부서류'])
    rows = exhibit_rows(doc)
    assert len(rows) == 3 and all(row['in_section'] for row in rows)
    assert len(_duplicates(doc)) == 1


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('opening,closing', [('「', '」'), ('『', '』'), ('“', '”')])
def test_synthetic_multiline_quoted_numbered_lines_do_not_certify_document_scope(
        tmp_path, extension, opening, closing):
    doc = _parsed(tmp_path, extension, [opening, '가. 수집문헌 목록',
        '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
        '나. 문헌 검토', '갑 제1호증 표본보고', closing, '첨부서류'])
    from packages.claim_engine.evidence_consistency import _duplicate_inventory_roles
    from packages.document_engine.reading_text import build_reading_text
    rows = exhibit_rows(doc)
    excluded, scopes = _duplicate_inventory_roles(build_reading_text(doc), rows)
    assert not scopes and not excluded
    found = _duplicates(doc)
    assert len(found) == 1 and str(found[0].evidence_grade) == 'A'


@pytest.mark.parametrize('extension', ['pdf', 'txt'])
@pytest.mark.parametrize('opening,closing', [('「', '」'), ('『', '』'), ('“', '”')])
@pytest.mark.parametrize('mode', ['hidden_reference', 'unclosed', 'quoted_close', 'balanced_title'])
def test_synthetic_quote_context_witnesses_and_balanced_title_opposites(
        tmp_path, extension, opening, closing, mode):
    if mode == 'hidden_reference':
        lines = ['가. 수집문헌 목록',
            f'갑 제1호증: 진술서 {opening}갑 제2호증: 참고 기재{closing}',
            '나. 문헌 검토', '갑 제1호증 확인서, 다른 자료.', '첨부서류']
    elif mode == 'unclosed':
        lines = [opening, '가. 수집문헌 목록',
            '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
            '나. 문헌 검토', '갑 제1호증 표본보고', '첨부서류']
    elif mode == 'quoted_close':
        lines = ['가. 수집문헌 목록',
            '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
            opening, '나. 문헌 검토', closing, '갑 제1호증 표본보고', '첨부서류']
    else:
        lines = ['(1) 수집문헌 목록',
            f'갑 제1호증: {opening}점검기록{closing}, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.',
            '(2) 문헌 검토', f'갑 제1호증 {opening}점검기록{closing}: 순서를 설명한다.', '첨부서류']
    doc = _parsed(tmp_path, extension, lines)
    assert len(_duplicates(doc)) == (0 if mode == 'balanced_title' else 1)


@pytest.mark.parametrize('hidden', [False, True])
def test_synthetic_docx_quoted_scope_and_hidden_reference_remain_unknown(tmp_path, hidden):
    from docx import Document
    from packages.document_engine.registry import parse_document
    lines = (['가. 수집문헌 목록', '갑 제1호증: 진술서 「갑 제2호증: 참고 기재」']
             if hidden else ['「', '가. 수집문헌 목록',
              '갑 제1호증: 점검기록, 북쪽 구역. 갑 제2호증: 배치대장, 별도 부분.'])
    lines += ['나. 문헌 검토', '갑 제1호증 확인서, 다른 자료.', '」', '첨부서류']
    out = Document()
    for line in lines:
        out.add_paragraph(line)
    path = tmp_path / 'public_quoted_scope.docx'
    out.save(path)
    doc = parse_document(str(path), document_id='public_quoted_scope', filename=path.name,
        mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', sha256='0' * 64)
    assert len(_duplicates(doc)) == 1


@pytest.mark.parametrize('extension', ['pdf', 'txt', 'docx'])
@pytest.mark.parametrize('item_prefix', ['1. ', ''])
def test_synthetic_quote_mask_uses_absolute_reference_origin_after_item_prefix(
        tmp_path, extension, item_prefix):
    lines = ['가. 수집문헌 목록',
        item_prefix + '갑 제1호증: 관측기록. 갑 제2호증: 측정대장. 「갑 제3호증: 인용표」',
        '나. 문헌 검토', '갑 제3호증 다른표', '첨부서류']
    if extension == 'docx':
        from docx import Document
        from packages.document_engine.registry import parse_document
        out = Document()
        for line in lines:
            out.add_paragraph(line)
        path = tmp_path / 'public_reference_origin_scope.docx'
        out.save(path)
        doc = parse_document(str(path), document_id='public_reference_origin_scope', filename=path.name,
            mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', sha256='0' * 64)
    else:
        doc = _parsed(tmp_path, extension, lines)
    from packages.claim_engine.evidence_consistency import _duplicate_inventory_roles
    from packages.document_engine.reading_text import build_reading_text
    reading = build_reading_text(doc)
    rows = exhibit_rows(doc)
    _, scopes = _duplicate_inventory_roles(reading, rows)
    assert scopes and scopes[0]['keys'] == {('갑', 1, None), ('갑', 2, None)}
    reference = next(row for row in rows if row['number'] == 3)['duplicate_sources'][0]['reference_span']
    assert reading.text[slice(*reference)] == '갑 제3호증'
    found = _duplicates(doc)
    assert len(found) == 1 and str(found[0].evidence_grade) == 'A'


@pytest.mark.parametrize('extension', ['pdf', 'txt', 'docx'])
def test_synthetic_unquoted_prefixed_inventory_keeps_source_role_positive(tmp_path, extension):
    lines = ['가. 수집문헌 목록',
        '1. 갑 제1호증: 관측기록. 갑 제2호증: 측정대장. 갑 제3호증: 인용표',
        '나. 문헌 검토', '갑 제3호증 인용표: 순서를 설명한다.', '첨부서류']
    if extension == 'docx':
        from docx import Document
        from packages.document_engine.registry import parse_document
        out = Document()
        for line in lines:
            out.add_paragraph(line)
        path = tmp_path / 'public_unquoted_origin_scope.docx'
        out.save(path)
        doc = parse_document(str(path), document_id='public_unquoted_origin_scope', filename=path.name,
            mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', sha256='0' * 64)
    else:
        doc = _parsed(tmp_path, extension, lines)
    assert not _duplicates(doc)
