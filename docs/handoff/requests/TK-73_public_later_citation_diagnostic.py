"""Design-only public actual-document controls, never a private evaluator input."""
import copy
import json
import runpy
from pathlib import Path

from packages.claim_engine.evidence_consistency import (
    _EXHIBIT_REF_SENTENCE_RE, _duplicate_inventory_roles,
    _duplicate_mention_view, _TITLE_BRACKETS, _TITLE_PREDICATE_ENDINGS, exhibit_rows,
)
from packages.claim_engine.exhibits import parse_exhibits
from packages.document_engine.reading_text import build_reading_text
from packages.document_engine.registry import parse_document

ROOT = Path(__file__).resolve().parents[3]
HELPERS = runpy.run_path(str(ROOT / 'tests/test_tk73_reference_title_prefix.py'))


def parsed(directory, extension, lines):
    if extension != 'docx':
        return HELPERS['_parsed'](directory, extension, lines)
    from docx import Document
    out = Document()
    for line in lines:
        out.add_paragraph(line)
    path = directory / 'public_later_citation.docx'
    out.save(path)
    return parse_document(str(path), document_id='public_later_citation', filename=path.name,
        mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        sha256='0' * 64)


def citation_source(reading, citation, title):
    start = reading.text.find(citation)
    if start < 0:
        return None
    end = start + len(citation)
    paragraph_start = reading.text.rfind('\n', 0, start) + 1
    paragraph_end = reading.text.find('\n', end)
    if paragraph_end < 0:
        paragraph_end = len(reading.text)
    paragraph = reading.text[paragraph_start:paragraph_end]
    stack, mask = [], []
    for char in paragraph:
        mask.append(bool(stack))
        if stack and char == stack[-1]:
            stack.pop()
        elif stack and stack[-1] in ('"', "'", '”', '’', '」', '』'):
            pass
        elif char in _TITLE_BRACKETS:
            stack.append(_TITLE_BRACKETS[char])
        elif char in ('"', "'"):
            stack.append(char)
    reference = parse_exhibits(citation)[0]['span']
    left, right = start + reference[0], start + reference[1]
    atom_start = start + citation.index(title, reference[1])
    atom_end = atom_start + len(title)
    segment = next(s for s in reading.segments if s.start <= start < s.end)
    assert end <= segment.end
    leading = len(segment.block.text) - len(segment.block.text.lstrip())
    raw_start = leading + start - segment.start
    assert segment.block.text[raw_start:raw_start + len(citation)] == citation
    assert reading.text[left:right] == citation[reference[0]:reference[1]]
    assert reading.text[atom_start:atom_end] == title
    return {'reading_span': (start, end), 'block_id': segment.block.block_id,
            'block_span': (raw_start, raw_start + len(citation)),
            'reference_span': (left, right), 'complete_title_span': (atom_start, atom_end),
            'observed_particle': reading.text[atom_end:atom_end + 2],
            'non_leading': left > paragraph_start,
            'reference_unprotected': not any(mask[left-paragraph_start:right-paragraph_start]),
            'complete_native_title': title[0] in _TITLE_BRACKETS and
                                     title[-1] == _TITLE_BRACKETS[title[0]],
            'complete_proposition': citation.endswith('.') and
                                    citation[:-1].endswith(_TITLE_PREDICATE_ENDINGS),
            'predicate_unprotected': not mask[end - paragraph_start - 2],
            'competing_definition_colon': any(char in ':：' and not mask[index]
                                              for index, char in enumerate(paragraph)),
            'source_slice_verified': True}


def run(directory):
    examples = [('갑 제1호증', '「점검기록」', '「점검보고」'),
                ('을 제2호증의 1', '『작업대장』', '『작업도면』'),
                ('병 제3호증', '“관측 [2024. 1. 2.]”', '“관측 [2024. 1. 3.]”')]
    results = []
    for extension in ('txt', 'pdf', 'docx'):
        for number, (label, title, other) in enumerate(examples):
            for mode in ('same', 'different_title', 'inventory_conflict',
                         'proposition_conflict', 'missing_citation',
                         'quoted_citation', 'ancestor', 'opaque_tail', 'qualified_title', 'no_inventory'):
                citation = f'전체 경로는 {label} {title}으로 확인되었다.'
                inventory = f'{label}: {title}, 북쪽에 있다. 정 제9호증: 「배치표」, 중앙에 있다.'
                if mode == 'inventory_conflict':
                    inventory += f' {label}: {title}, 남쪽에 있다.'
                if mode == 'opaque_tail':
                    inventory = f'{label}: {title}, 별도 보관 부분. 정 제9호증: 「배치표」, 중앙 부분.'
                lines = ['1. 자료 제출', '가. 확보문헌 목록', inventory,
                         '나. 자료 확인', '기본 순서는 여러 단계로 구성되어 있다.',
                         '다. 처리 분석']
                if mode == 'ancestor':
                    lines[-1] = '2. 새로운 자료 정의'
                if mode != 'missing_citation':
                    lines.append(f'「{citation}」' if mode == 'quoted_citation' else citation)
                body_title = other if mode == 'different_title' else title + ' 추가 조건' if mode == 'qualified_title' else title
                lines.append(f'{label} {body_title}: 순서를 설명한다.')
                if mode == 'proposition_conflict':
                    lines.append(f'{label} {title}: 순서를 설명하지 않는다.')
                if mode == 'no_inventory':
                    lines = lines[5:] + [f'{label} {other}: 경로를 설명한다.']
                lines += ['라. 별도 정리', '첨부서류']
                folder = directory / f'{extension}_{number}_{mode}'
                folder.mkdir(parents=True, exist_ok=True)
                doc = parsed(folder, extension, lines)
                rows = exhibit_rows(doc)
                before = copy.deepcopy(rows)
                reading = build_reading_text(doc)
                excluded, scopes = _duplicate_inventory_roles(reading, rows)
                found = HELPERS['_duplicates'](doc)
                assert rows == before
                origins_verified = all(reading.text[s['reading_span'][0]:s['reading_span'][1]] == s['text']
                    for row in rows for s in row.get('duplicate_sources', []))
                assert origins_verified
                citation_proof = citation_source(reading, citation, title)
                if mode == 'missing_citation':
                    assert citation_proof is None
                else:
                    assert citation_proof and citation_proof['non_leading']
                    assert citation_proof['complete_native_title']
                    assert citation_proof['observed_particle'] == '으로'
                    assert citation_proof['reference_unprotected'] is (mode != 'quoted_citation')
                    if mode != 'quoted_citation':
                        assert citation_proof['predicate_unprotected']
                    assert citation_proof['complete_proposition']
                    assert not citation_proof['competing_definition_colon']
                expected = 0 if mode == 'same' else 1
                row_free_residual = mode == 'quoted_citation' and len(rows) < 3
                if row_free_residual:
                    expected = None  # Existing reader coverage, not genuine-A preservation evidence.
                results.append({'format': extension, 'example': number, 'mode': mode,
                    'current_duplicate': len(found), 'proposed_expected': expected,
                    'rows': len(rows), 'scopes': len(scopes), 'excluded': len(excluded),
                    'kinds': [_duplicate_mention_view(r)['kind'] for r in rows],
                    'existing_citation_cue': bool(_EXHIBIT_REF_SENTENCE_RE.search(citation)),
                    'citation_source_proof': citation_proof,
                    'original_reader_row_free_residual': row_free_residual,
                    'source_slices_verified': origins_verified, 'original_rows_unchanged': rows == before})
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import sys
    run(Path(sys.argv[1]))
