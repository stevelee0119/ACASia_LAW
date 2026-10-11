"""Source-bound informational reference, never requirement fulfillment.

The roles below are application mappings, not NIKL classifications. A source
lemma pair is insufficient: exact object/case and governing closure are needed.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from .predicate_semantics import _past_stems, _PAST_ENDING

VERSION = 'krdict-reference-1'
_SOURCE = 'https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord='
_ROWS = (
    ('참조하다', '參照', 1, '어떤 일을 그와 관련된 다른 일과 참고로 비교하고 대조해 보다.', 'REFERENCE'),
    ('검토하다', '檢討', 1, '어떤 사실이나 내용을 자세히 따져서 조사하고 분석하다.', 'INSPECTION'),
    ('서류', '書類', 1, '글자로 기록한 문서.', 'INFORMATION_OBJECT'),
    ('자료', '資料', 1, '연구나 조사를 하는 데 기본이 되는 재료.', 'INFORMATION_OBJECT'),
    ('확인하다', '確認', 1, '틀림없이 그러한지를 알아보거나 인정하다.', 'VERACITY_OR_RECOGNITION'),
    ('기록', '記錄', 1, '주로 후일에 남길 목적으로 어떤 사실이나 생각을 적거나 영상으로 남김. 또는 그런 글이나 영상.', 'PRESERVED_INFORMATION'),
    ('기록', '記錄', 2, '운동 경기 등에서 성적이나 결과를 등급이나 수치로 나타냄.', 'PERFORMANCE_RECORD'),
)
SOURCE_SENSES = tuple({
    'lemma': lemma, 'homonym_number': 0, 'hanja': hanja, 'sense_number': sense,
    'source_sense_key': f'{lemma}:{hanja}:{sense}', 'definition': definition,
    'source': _SOURCE + quote(lemma), 'retrieved_on': '2026-10-11',
} for lemma, hanja, sense, definition, _ in _ROWS)
APPLICATION_ROLES = {f'{lemma}:{hanja}:{sense}': role
                     for lemma, hanja, sense, _, role in _ROWS}
_OBJECT_SENSES = {row['lemma']: row for row in SOURCE_SENSES
                  if APPLICATION_ROLES[row['source_sense_key']] == 'INFORMATION_OBJECT'}
_PREDICATE_SENSES = {row['lemma']: row for row in SOURCE_SENSES
                     if APPLICATION_ROLES[row['source_sense_key']] in {'REFERENCE', 'INSPECTION'}}
_FINITE = {lemma: re.compile('(?:' + '|'.join(map(re.escape, _past_stems(lemma)))
                            + ')(?P<closure>' + _PAST_ENDING + ')')
           for lemma in _PREDICATE_SENSES}
_FRAME = re.compile(r'\s+(?P<object>[가-힣]+?)(?P<case>을|를)\s+'
                    r'(?P<predicate>[가-힣]+)(?:\s+(?P<temporal>뒤|후|다음))?\s*')


def reference_frame_evidence(text: str, start: int, end: int) -> dict | None:
    """Inspect one exact source tail after a nominal modifier, using pos/endpos.

    Reports, subject/qualification scope and linkage eligibility are separate
    consumer checks. Unknown objects/predicates/embedding are not references.
    """
    match = _FRAME.fullmatch(text, start, end)
    if match is None or match['object'] not in _OBJECT_SENSES:
        return None
    token = match['predicate']
    selected = None
    closure = None
    for lemma, source in _PREDICATE_SENSES.items():
        if match['temporal']:
            # Attested regular -하다 past-adnominal -한 plus temporal closure;
            # -한 사람/적 and prospective/negative forms do not match this frame.
            if token == lemma[:-2] + '한':
                selected, closure = source, list(match.span('temporal'))
        else:
            finite = _FINITE[lemma].fullmatch(token)
            if finite:
                first = match.start('predicate')
                selected, closure = source, [first + offset for offset in finite.span('closure')]
        if selected:
            break
    if selected is None:
        return None
    return {'version': VERSION, 'kind': 'REFERENCE_NON_REQUIREMENT_ASSERTION',
            'object_span': list(match.span('object')), 'object_case_span': list(match.span('case')),
            'predicate_span': list(match.span('predicate')), 'closure_span': closure,
            'selected_source_senses': [_OBJECT_SENSES[match['object']], selected],
            'application_roles': [APPLICATION_ROLES[source['source_sense_key']]
                                  for source in (_OBJECT_SENSES[match['object']], selected)],
            'mapping_authority': 'APPLICATION_NOT_NIKL_CLASSIFICATION',
            'supports_requirement_fulfillment': False,
            'underlying_facts_verified': False, 'legal_sufficiency_verified': False}
