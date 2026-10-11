"""Original case-bound dynamic event assertions, without truth certification.

Source senses and application mappings remain separate. Temporal words alone
do not prove tense; an observed accusative frame, dynamic selected action and
exact past-adnominal attachment are all required.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from .predicate_semantics import SOURCE_SENSES, sense_evidence

VERSION = 'krdict-event-temporal-1'
_SOURCE = 'https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord='
TEMPORAL_SOURCE_SENSES = (
    {'lemma': '-ㄴ', 'homonym_number': 3, 'hanja': '', 'sense_number': 1,
     'definition': '앞말이 관형어의 기능을 하게 만들고 사건이나 동작이 과거에 일어났음을 나타내는 어미.'},
    {'lemma': '-ㄴ', 'homonym_number': 3, 'hanja': '', 'sense_number': 2,
     'definition': '앞말이 관형어의 기능을 하게 만들고 사건이나 동작이 완료되어 그 상태가 유지되고 있음을 나타내는 어미.'},
    {'lemma': '이후', 'homonym_number': 0, 'hanja': '以後', 'sense_number': 2,
     'definition': '기준이 되는 때를 포함하여 그 뒤.'},
)
TEMPORAL_SOURCE_SENSES = tuple({**row,
    'source_sense_key': f"{row['lemma']}:{row['homonym_number']}:{row['sense_number']}",
    'source': _SOURCE + quote(row['lemma']), 'retrieved_on': '2026-10-11',
} for row in TEMPORAL_SOURCE_SENSES)
APPLICATION_MAPPINGS = {
    '-ㄴ:3:1': 'DYNAMIC_PAST_ADNOMINAL',
    '-ㄴ:3:2': 'DYNAMIC_COMPLETED_ADNOMINAL',
    '이후:0:2': 'RELATIVE_EVENT_TIME_AFTER',
}
_REGULAR_FORMS = {row['lemma'][:-2] + '한': row['lemma'] for row in SOURCE_SENSES
                  if row['lemma'].endswith('하다')}
_ATTACHMENT = re.compile(r'\s+(?P<predicate>[가-힣]+)\s+(?P<temporal>이후)\s*')
_NONSPACE = re.compile(r'\S')


def case_bound_event_evidence(text: str, argument_span: list[int],
                             case_span: list[int], end: int) -> dict | None:
    """Prove the immediate first event tail, bounded before another argument.

    Speaker/condition/quotation and later selection eligibility are checked
    separately by the consumer. The primitive needs no other event assertion.
    """
    first, argument_end = argument_span
    case_first, case_end = case_span
    if (not first < argument_end <= case_first < case_end <= end
            or text[case_first:case_end] not in {'을', '를'}
            or _NONSPACE.search(text, argument_end, case_first)):
        return None
    match = _ATTACHMENT.fullmatch(text, case_end, end)
    if match is None:
        return None
    lemma = _REGULAR_FORMS.get(match['predicate'])
    if lemma is None:
        return None
    meaning = sense_evidence(lemma, event_object=True)
    if not meaning['sense_resolved'] or not meaning['supports_asserted_fulfillment']:
        return None
    predicate_span = list(match.span('predicate'))
    return {
        'version': VERSION, 'kind': 'SOURCE_BOUND_PAST_EVENT_ASSERTION',
        'argument_span': list(argument_span), 'case_span': list(case_span),
        'predicate_span': predicate_span,
        # This source slice is the actual syllable 한, not invented jamo ㄴ.
        'morphology_span': [predicate_span[1] - 1, predicate_span[1]],
        'observed_morphology': '한', 'tense': 'PAST_ADNOMINAL',
        'temporal_span': list(match.span('temporal')),
        'selected_source_senses': meaning['selected_senses'],
        'temporal_source_senses': list(TEMPORAL_SOURCE_SENSES),
        'temporal_application_mappings': dict(APPLICATION_MAPPINGS),
        'supports_authored_event_assertion': True,
        'underlying_facts_verified': False, 'legal_sufficiency_verified': False,
        'mapping_authority': 'APPLICATION_NOT_NIKL_CLASSIFICATION',
    }
