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

# Individual source meanings are not application aspect classifications.
_AUXILIARY_ROWS = (
    ('하다', 1, 1, '어떤 행동이나 동작, 활동 등을 행하다.'),
    ('놓다', 2, 1, '앞말이 뜻하는 행동을 끝내고 그 결과를 유지함을 나타내는 말.'),
    ('놓다', 2, 2, '앞말이 뜻하는 상태가 계속됨을 강조하는 말.'),
    ('두다', 2, 1, '앞말이 나타내는 행동을 하고 그 결과를 그대로 계속 유지되게 함을 나타내는 말.'),
    ('-여', 1, 3, '동사와 형용사를 보조 용언인 ‘두다’, ‘버리다’, ‘보다’, ‘있다’, ‘주다’ 등과 이어 줄 때 쓰는 연결 어미.'),
    ('-은', 1, 1, '앞말이 관형어의 기능을 하게 만들고 사건이나 동작이 과거에 일어났음을 나타내는 어미.'),
    ('-은', 1, 2, '앞말이 관형어의 기능을 하게 만들고 사건이나 동작이 완료되어 그 상태가 유지되고 있음을 나타내는 어미.'),
    ('-은', 1, 3, '앞말이 관형어의 기능을 하게 만들고 현재의 상태를 나타내는 어미.'),
)
AUXILIARY_SOURCE_SENSES = tuple({
    'lemma': lemma, 'homonym_number': homonym, 'sense_number': number,
    'hanja': '', 'definition': definition,
    'source_sense_key': f'{lemma}:{homonym}:{number}',
    'source': _SOURCE + quote(lemma), 'retrieved_on': '2026-10-11',
} for lemma, homonym, number, definition in _AUXILIARY_ROWS)
_AUXILIARY_SENSES = {row['source_sense_key']: row for row in AUXILIARY_SOURCE_SENSES}
AUXILIARY_APPLICATION_MAPPINGS = {
    '하다:1:1': 'AUTHORED_DIRECT_ACTION',
    '놓다:2:1': 'COMPLETED_ACTION_RESULT_MAINTENANCE',
    '놓다:2:2': 'STATE_CONTINUATION_NOT_ACTION_PROOF',
    '두다:2:1': 'ACTION_RESULT_MAINTENANCE',
    '-여:1:3': 'OBSERVED_HEAD_AUXILIARY_CONNECTION',
    '-은:1:1': 'DYNAMIC_PAST_ADNOMINAL',
    '-은:1:2': 'DYNAMIC_COMPLETED_ADNOMINAL',
    '-은:1:3': 'CURRENT_STATE_NOT_ACTION_PROOF',
}
_CONNECTIVE_FORMS = {
    row['lemma'][:-2] + ending: row['lemma']
    for row in SOURCE_SENSES if row['lemma'].endswith('하다')
    for ending in ('하여', '해')
}
_AUXILIARY_FORMS = {'놓은': ('놓다:2:1', '-은'), '둔': ('두다:2:1', '-ㄴ')}
_AUXILIARY_ATTACHMENT = re.compile(
    r'\s+(?P<head>[가-힣]+)\s+(?P<auxiliary>[가-힣]+)\s+(?P<temporal>이후)\s*')


def _composed_event_evidence(text: str, argument_span: list[int],
                             case_span: list[int], end: int) -> dict | None:
    """An exact head/auxiliary frame proves only its own authored action.

    Bare lexical 하다 is distinct from completion. A separately selected
    dynamic head excludes the auxiliary's state-continuation reading;
    unknown compounds, complements and unselected source senses abstain.
    """
    match = _AUXILIARY_ATTACHMENT.fullmatch(text, case_span[1], end)
    if match is None or match['auxiliary'] not in _AUXILIARY_FORMS:
        return None
    if match['head'] in {'해', '하여'}:
        lemma = '하다'
        selected = [_AUXILIARY_SENSES['하다:1:1']]
        category = 'AUTHORED_DIRECT_ACTION'
        fulfillment = False
    else:
        lemma = _CONNECTIVE_FORMS.get(match['head'])
        if lemma is None:
            return None
        meaning = sense_evidence(lemma, event_object=True)
        if not meaning['sense_resolved'] or not meaning['supports_asserted_fulfillment']:
            return None
        selected = meaning['selected_senses']
        category = selected[0]['category']
        fulfillment = meaning['supports_asserted_fulfillment']
    auxiliary_key, ending = _AUXILIARY_FORMS[match['auxiliary']]
    head_span = list(match.span('head'))
    auxiliary_span = list(match.span('auxiliary'))
    morphology_span = [auxiliary_span[1] - 1, auxiliary_span[1]]
    grammar = ([row for row in AUXILIARY_SOURCE_SENSES
                if row['lemma'] == '-은' and row['sense_number'] in {1, 2}]
               if ending == '-은' else [row for row in TEMPORAL_SOURCE_SENSES if row['lemma'] == '-ㄴ'])
    return {
        'version': 'krdict-event-composition-1', 'kind': 'SOURCE_BOUND_PAST_EVENT_ASSERTION',
        'attachment_kind': 'DYNAMIC_RESULTATIVE_AUXILIARY',
        'argument_span': list(argument_span), 'case_span': list(case_span),
        'predicate_span': [head_span[0], auxiliary_span[1]],
        'head_span': head_span, 'head_lemma': lemma, 'head_category': category,
        'connective_span': [head_span[1] - 1, head_span[1]],
        'observed_connective': text[head_span[1] - 1:head_span[1]],
        'connective_source_sense': _AUXILIARY_SENSES['-여:1:3'],
        # Contracted 해 is the observed source, not an invented 하+여 slice.
        'connective_reference': {
            'lemma': '해-', 'homonym_number': 2, 'source_entry_kind': 'CONJUGATION_REFERENCE',
            'definition': '→ 하다1, 하다2', 'source': _SOURCE + quote('해'),
            'retrieved_on': '2026-10-11',
        } if match['head'].endswith('해') else None,
        'auxiliary_span': auxiliary_span, 'auxiliary_source_sense': _AUXILIARY_SENSES[auxiliary_key],
        'morphology_span': morphology_span, 'observed_morphology': text[slice(*morphology_span)],
        'analytical_adnominal_ending': ending, 'adnominal_source_senses': grammar,
        'temporal_span': list(match.span('temporal')), 'tense': 'PAST_ADNOMINAL',
        'selected_source_senses': selected,
        'temporal_source_senses': [row for row in TEMPORAL_SOURCE_SENSES if row['lemma'] == '이후'],
        'temporal_application_mappings': {'이후:0:2': APPLICATION_MAPPINGS['이후:0:2']},
        'auxiliary_application_mappings': dict(AUXILIARY_APPLICATION_MAPPINGS),
        'supports_authored_event_assertion': True,
        'supports_asserted_fulfillment': fulfillment,
        'total_completion_asserted': category == 'COMPLETION',
        'total_requirement_completion': False, 'fulfillment_verified': False,
        'underlying_facts_verified': False, 'legal_sufficiency_verified': False,
        'mapping_authority': 'APPLICATION_NOT_NIKL_CLASSIFICATION',
    }


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
        return _composed_event_evidence(text, argument_span, case_span, end)
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
