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
