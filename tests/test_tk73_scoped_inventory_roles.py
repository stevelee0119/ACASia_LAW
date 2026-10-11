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
