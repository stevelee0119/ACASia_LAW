"""Public source occurrence/proposition controls; no private evaluator inputs."""
import copy
import runpy
import time
from pathlib import Path

import pytest

from packages.claim_engine.evidence_consistency import (
    _duplicate_citation_anchors, _duplicate_inventory_roles, _duplicate_mention_view,
    _numbering, exhibit_rows,
)
from packages.document_engine.reading_text import build_reading_text

_helpers = runpy.run_path(str(Path(__file__).resolve().parents[1] /
    'docs/handoff/requests/TK-73_public_later_citation_diagnostic.py'))
_parsed = _helpers['parsed']
_duplicates = _helpers['HELPERS']['_duplicates']


def _lines(title='「点検記録」', label='갑 제1호증', predicate='확인되었다'):
    return ['1. 자료 제출', '가. 확보문헌 목록',
        f'{label}: {title}, 북쪽에 있다. 정 제9호증: 「배치표」, 중앙에 있다.',
        '나. 자료 확인', '기본 순서는 여러 단계로 구성되어 있다.',
        '다. 처리 분석', f'전체 경로는 {label} {title}으로 {predicate}.',
        f'{label} {title}: 순서를 설명한다.', '라. 별도 정리', '첨부서류']


def _assert(doc, expected):
    rows = exhibit_rows(doc)
    before = copy.deepcopy(rows)
    found = [f for f in _numbering(doc, rows)
             if f.confidence_features.get('rule_id') == 'EVI.EVIDENCE_NUMBER_DUPLICATE']
    assert len(found) == expected
    assert all(str(f.evidence_grade) == 'A' for f in found)
    assert rows == before
    return rows


def test_synthetic_ninety_actual_citation_documents_match_source_contract(tmp_path):
    results = _helpers['run'](tmp_path, emit=False)
    assert len(results) == 90
    assert sum(r['mode'] == 'same' for r in results) == 9
    assert all(r['current_duplicate'] == r['proposed_expected'] for r in results)
    assert all(r['original_rows_unchanged'] and r['source_slices_verified'] for r in results)
    assert not any(r['original_reader_row_free_residual'] for r in results)


@pytest.mark.parametrize('extension', ['txt', 'pdf', 'docx'])
@pytest.mark.parametrize('mode', ['second_parent', 'other_branch', 'other_party',
    'samekey_unknown', 'no_close', 'nonfinite', 'unattached_particle', 'definition',
    'condition', 'negation', 'degree', 'different_date', 'protected_inventory',
    'compatibility_inventory', 'branch_range'])
def test_synthetic_complete_citation_opposites_are_not_global_exemptions(tmp_path, extension, mode):
    lines = _lines()
    if mode == 'second_parent':
        lines = lines[:-1] + ['2. 별도 제출', '가. 확보문헌 목록',
            '갑 제1호증: 「점검보고」, 남쪽에 있다. 정 제9호증: 「배치표」, 중앙에 있다.',
            '나. 자료 확인', '기본 순서는 여러 단계로 구성되어 있다.',
            '다. 처리 분석', '전체 경로는 갑 제1호증 「점검보고」으로 확인되었다.',
            '갑 제1호증 「점검보고」: 경로를 설명한다.', '라. 별도 정리', '첨부서류']
    elif mode == 'other_branch':
        lines = _lines(label='갑 제1호증의 1')
        lines[6] = lines[6].replace('의 1', '의 2')
    elif mode == 'other_party':
        lines[6] = lines[6].replace('갑 제1', '을 제1')
    elif mode == 'samekey_unknown':
        lines.insert(3, '갑 제1호증: 「点検記録」, 별도 조건.')
    elif mode in ('protected_inventory', 'compatibility_inventory'):
        quote = ('「', '」') if mode == 'protected_inventory' else ('＂', '＂')
        lines[2] += ' ' + quote[0] + '갑 제1호증: 「다른표」, 별도 부분.' + quote[1]
    elif mode == 'branch_range':
        lines = _lines(label='갑 제1호증의 1 내지 2')
        lines[6] = lines[6].replace('의 1 내지 2', '의 1')
    elif mode == 'no_close':
        lines = lines[:-2] + ['첨부서류']
    elif mode == 'nonfinite':
        lines[6] = lines[6].replace('확인되었다.', '확인되는 부분.')
    elif mode == 'unattached_particle':
        lines[6] = lines[6].replace('으로', ' 으로')
    elif mode == 'definition':
        lines[6] = lines[6].replace('전체 경로는', '전체 경로는:')
    else:
        tail = {'condition': '조건이 성립하면 순서를 설명한다.',
                'negation': '순서를 설명하지 않는다.',
                'degree': '일부 순서를 설명한다.',
                'different_date': '2025. 3. 4. 순서를 설명한다.'}[mode]
        lines.insert(8, '갑 제1호증 「点検記録」: ' + tail)
    _assert(_parsed(tmp_path, extension, lines), 1)


@pytest.mark.parametrize('extension', ['txt', 'pdf', 'docx'])
@pytest.mark.parametrize('mode', ['repeat', 'other_parent_only', 'negation', 'degree', 'condition'])
def test_synthetic_repeated_citations_use_occurrences_and_whole_propositions(tmp_path, extension, mode):
    lines = _lines()
    if mode == 'repeat':
        lines[8:8] = ['라. 추가 분석', lines[6], '마. 별도 정리']
        expected = 0
    elif mode == 'other_parent_only':
        citation = lines.pop(6)
        lines = ['0. 별도 설명', '가. 처리 분석', citation, '나. 별도 정리'] + lines
        expected = 1
    else:
        predicate = {'negation': '확인되지 않았다', 'degree': '일부 확인되었다',
                     'condition': '조건이 성립하면 확인되었다'}[mode]
        lines.insert(7, _lines(predicate=predicate)[6])
        expected = 1
    _assert(_parsed(tmp_path, extension, lines), expected)


@pytest.mark.parametrize('extension', ['txt', 'pdf', 'docx'])
@pytest.mark.parametrize('mode', ['missing_source', 'missing_origin', 'missing_reference',
    'out_of_range', 'continuation', 'wrong_origin', 'missing_group'])
def test_synthetic_all_inventory_origin_alternatives_checked_before_projection(tmp_path, extension, mode):
    doc = _parsed(tmp_path, extension, _lines())
    rows = exhibit_rows(doc)
    inventory = rows[0]
    origin = inventory['duplicate_sources'][0]
    if mode == 'missing_source':
        inventory['duplicate_sources'] = []
    elif mode == 'missing_origin':
        origin.pop('origin')
    elif mode == 'missing_reference':
        origin.pop('reference_span')
    elif mode == 'out_of_range':
        origin['reference_span'] = (999999, 1000000)
    elif mode == 'continuation':
        inventory['duplicate_sources'].append(copy.deepcopy(origin))
    elif mode == 'wrong_origin':
        origin['origin'] = 'continuation'
    else:
        inventory.pop('line_group')
    before = copy.deepcopy(rows)
    found = [f for f in _numbering(doc, rows)
             if f.confidence_features.get('rule_id') == 'EVI.EVIDENCE_NUMBER_DUPLICATE']
    assert len(found) == 1
    assert rows == before


def test_synthetic_citation_forward_work_is_bounded_after_old_parser(tmp_path):
    lines = _lines()
    lines[6:6] = [' '.join([lines[6]] * 2000), '라. 추가 분석']
    lines[-2] = '마. 별도 정리'
    doc = _parsed(tmp_path, 'txt', lines)
    rows = exhibit_rows(doc)  # Existing parser explicitly outside this budget.
    reading = build_reading_text(doc)
    started = time.perf_counter()
    metadata = {}
    _, scopes = _duplicate_inventory_roles(reading, rows, metadata)
    views = {id(row): _duplicate_mention_view(row) for row in rows}
    anchors = _duplicate_citation_anchors(rows, scopes, metadata, views)
    elapsed = time.perf_counter() - started
    assert anchors['certified']
    assert elapsed < 0.1
    assert not _duplicates(doc)
