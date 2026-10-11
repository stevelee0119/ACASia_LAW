"""Local finite effect propositions, interpreted separately from candidates.

Source senses are NIKL definitions; frames/categories are application mappings.
The evidence concerns an authored proposition, never its truth or sufficiency.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from .polarity import ASSERTED, polarity
from .predicate_semantics import assertion_extent_evidence

VERSION = 'krdict-effect-1'
_SOURCE = 'https://krdict.korean.go.kr/m/kor/searchResult?mainSearchWord='
_ROWS = (
    ('면하다', 1, '免', 1, '책임이나 의무를 지지 않게 되다.'),
    ('면하다', 1, '免', 2, '어떤 일을 당하지 않게 되다.'),
    ('면하다', 1, '免', 3, '어떤 어려운 상태나 처지에서 벗어나다.'),
    ('면하다', 2, '面', 1, '어떤 대상이나 방향을 정면으로 향하다.'),
    ('면하다', 2, '面', 2, '좋지 않은 상황을 직접 당하다.'),
    ('면제하다', 0, '免除', 1, '책임이나 의무에서 벗어나게 하다.'),
    ('면제되다', 0, '免除', 1, '책임이나 의무에서 벗어나게 되다.'),
    ('소멸하다', 0, '消滅', 1, '사라져 없어지다.'),
    ('처벌', 0, '處罰', 1, '범죄를 저지른 사람에게 국가나 특정 기관이 제재나 벌을 줌. 또는 그러한 벌.'),
    ('징계', 0, '懲戒', 1, '잘못을 뉘우치도록 나무라고 타이름.'),
    ('징계', 0, '懲戒', 2, '옳지 않은 행동에 대하여 벌을 줌.'),
    ('제재', 1, '制裁', 1, '일정한 규칙이나 관습을 어기지 못하게 함. 또는 그런 일.'),
    ('제재', 1, '制裁', 2, '법이나 규정을 어겼을 때 국가가 처벌이나 금지 등을 행함. 또는 그런 일.'),
    ('제재', 2, '題材', 1, '예술 작품이나 학문 연구의 바탕이 되는 재료.'),
    ('책임', 0, '責任', 1, '맡은 일이나 의무.'),
    ('책임', 0, '責任', 2, '어떤 일의 결과에 대해서 가지는 의무나 부담. 또는 그 결과에 따른 불이익.'),
    ('책임', 0, '責任', 3, '법을 어긴 사람에게 법적 불이익을 주거나 제한을 두는 일.'),
    ('처분', 0, '處分', 1, '물건이나 재산 등을 처리하여 치움.'),
    ('처분', 0, '處分', 2, '일을 어떻게 처리할 것인가에 대해 지시하거나 결정함. 또는 그런 지시나 결정.'),
    ('처분', 0, '處分', 3, '행정, 사법 관청이 특별한 사건에 대해 법규를 적용하여 처리하는 일.'),
    ('형사', 0, '刑事', 1, '형법의 적용을 받는 사건.'),
    ('형사', 0, '刑事', 2, '범죄를 수사하고 범인을 체포하는 등의 일을 하는 사복 경찰관.'),
    ('행정', 0, '行政', 1, '규정이나 규칙에 의하여 공적인 일들을 처리함.'),
    ('행정', 0, '行政', 2, '정부가 법률에 따라 행하는 통치 행위.'),
    ('우편', 2, '郵便', 1, '편지나 소포 등을 보내거나 받는 것.'),
    ('우편', 2, '郵便', 2, '편지나 소포 등과 같이 우편으로 받거나 보내는 물건.'),
    ('우편', 1, '右便', 1, '사람이 북쪽을 보고 있을 때 동쪽과 같은 쪽. 오른쪽.'),
    ('우편물', 0, '郵便物', 1, '편지나 소포 등과 같이 우편으로 받거나 보내는 물건.'),
    ('소포', 0, '小包', 1, '우편으로 보내는, 포장된 작은 짐.'),
    ('받다', 1, '', 1, '다른 사람이 주거나 보내온 것을 가지다.'),
    ('받다', 1, '', 3, '다른 사람이 하는 행동, 심리적인 작용 등을 당하거나 입다.'),
    ('받다', 1, '', 10, '어떠한 결정이나 판결을 당하다.'),
    ('필요', 0, '必要', 1, '꼭 있어야 함.'),
    ('권리', 0, '權利', 1, '어떤 일을 하거나 다른 사람에게 요구할 수 있는 정당한 힘이나 자격.'),
    ('채무', 0, '債務', 1, '어떤 사람이 다른 사람에게 어떤 행위를 해야 할 의무.'),
    ('의무', 0, '義務', 1, '마땅히 해야 할 일.'),
    ('의무', 0, '義務', 2, '법으로 정해져 강제성이 있는, 반드시 해야 하는 일.'),
    ('배제하다', 0, '排除', 1, '받아들이거나 포함하지 않고 제외시켜 빼놓다.'),
    ('효력', 0, '效力', 1, '약 등을 사용한 뒤에 얻는 좋은 결과.'),
    ('효력', 0, '效力', 2, '법률이나 규칙 등이 영향을 미침.'),
    ('무효', 0, '無效', 1, '아무런 효력이나 효과가 없음.'),
)
SOURCE_SENSES = tuple({'lemma': lemma, 'homonym_number': homonym, 'sense_number': number,
                       'hanja': hanja, 'definition': definition,
                       'source_sense_key': f'{lemma}:{homonym}:{number}',
                       'source': _SOURCE + quote('우편' if lemma == '우편물' else lemma),
                       'retrieved_on': '2026-10-11'}
                      for lemma, homonym, hanja, number, definition in _ROWS)
_SENSES = {row['source_sense_key']: row for row in SOURCE_SENSES}
_SENSES_BY_LEMMA = {}
for _row in SOURCE_SENSES:
    _SENSES_BY_LEMMA.setdefault(_row['lemma'], []).append(_row)

# Application nominal frames, not immunity/exemption words. Ambiguous heads
# require a compositional modifier or predicate frame; all alternatives remain
# available as independent source evidence.
_ATOMIC_ROLES = {
    '처벌': ('SANCTION', ['처벌:0:1']),
    '채무': ('LEGAL_OBLIGATION', ['채무:0:1']),
    '우편물': ('TRANSFER_OBJECT', ['우편물:0:1']),
    '소포': ('TRANSFER_OBJECT', ['소포:0:1']),
}
_MODIFIER_FRAMES = {
    '형사': ('LEGAL_DOMAIN', ['형사:0:1']),
    '행정': ('LEGAL_DOMAIN', ['행정:0:2']),
    '징계': ('DISCIPLINARY_DECISION', ['징계:0:2']),
}
_COMPOSED_HEADS = {
    ('LEGAL_DOMAIN', '책임'): ('LEGAL_OBLIGATION', ['책임:0:3']),
    ('LEGAL_DOMAIN', '제재'): ('SANCTION_DECISION', ['제재:1:2']),
    ('LEGAL_DOMAIN', '징계'): ('SANCTION_DECISION', ['징계:0:2']),
    ('LEGAL_DOMAIN', '처분'): ('SANCTION_DECISION', ['처분:0:3']),
    ('LEGAL_DOMAIN', '의무'): ('LEGAL_OBLIGATION', ['의무:0:2']),
    ('LEGAL_DOMAIN', '효력'): ('LEGAL_VALIDITY', ['효력:0:2']),
    ('DISCIPLINARY_DECISION', '처분'): ('SANCTION_DECISION', ['처분:0:2']),
}

# The morphological candidate is independent of legal/factual noun selection.
_PROPOSITION_RE = re.compile(
    r'(?<![가-힣])(?P<argument>[가-힣]+?)(?P<case>을|를|이|가|은|는|도|조차|마저)\s+'
    r'(?P<adjunct>(?:[가-힣]+\s+){0,4}?)'
    r'(?P<predicate>'
    r'받을\s+필요(?:가|는|도)?\s+없(?:다|고)|'
    r'받지\s+않을\s+권리(?:가|는|도)?\s+있(?:다|고)|'
    r'[가-힣]+(?:할|될|을)\s+수\s+(?:있다|없다)|'
    r'[가-힣]+?지\s*(?:않는다|않습니다)|[가-힣]+?(?:한다|된다|하고|되고|하지만|다))'
    r'(?=\s|[,;.!?]|$)')
_BOUNDARY_RE = re.compile(
    r'[,;.!?\n]|(?:으므로|므로|기에|더라도|으나|지만|하였고|했고|없고|하고)(?=\s|$)|'
    r'[가-힣]+?(?:한다|된다|습니다|다)(?=\s|[,;.!?]|$)')
_ACTOR_RE = re.compile(r'(?<![가-힣])[가-힣]+(?:이|가|은|는)(?=\s|[,;.!?]|$)')
_INDEPENDENT_ARGUMENT_RE = re.compile(r'(?<![가-힣])[가-힣]+(?:을|를|이|가|은|는|도|조차|마저)(?=\s|[,;.!?]|$)')
_MODAL_RE = re.compile(r'(?:라면|다면|으면|가능|예정|계획|가정)(?=\s|[,;.!?]|$)')


def _source(keys: list[str]) -> list[dict]:
    return [_SENSES[key] for key in keys]


def argument_role(argument: str, *, receipt: bool = False) -> dict:
    """Source-grounded nominal role; legal noun presence alone resolves nothing."""
    role, keys = _ATOMIC_ROLES.get(argument, ('UNKNOWN', []))
    components = []
    if role == 'UNKNOWN':
        for modifier, (frame, modifier_keys) in _MODIFIER_FRAMES.items():
            if not argument.startswith(modifier):
                continue
            head = argument[len(modifier):]
            head_role = _COMPOSED_HEADS.get((frame, head), _ATOMIC_ROLES.get(head))
            if head_role:
                role, head_keys = head_role
                keys = modifier_keys + head_keys
                components = [modifier, head]
                break
    if receipt and argument == '우편':
        role, keys = 'TRANSFER_OBJECT', ['우편:2:2']
    if role == 'TRANSFER_OBJECT' and not receipt:
        role, keys = 'UNKNOWN', []
    return {'role': role, 'selected_senses': _source(keys), 'components': components,
            'candidate_senses': _SENSES_BY_LEMMA.get(argument, _source(keys)),
            'mapping_authority': 'APPLICATION_NOT_NIKL_CLASSIFICATION'}


def effect_candidates(text: str, *, previous: str = '') -> list[dict]:
    """Single forward traversal of local boundaries and finite propositions."""
    boundaries = list(_BOUNDARY_RE.finditer(text))
    cursor, prefix_start = 0, 0
    rows = []
    position = 0
    while (match := _PROPOSITION_RE.search(text, position)) is not None:
        # Advance to the argument rather than consuming a possibly unbound
        # predicate: an intervening independent argument gets its own turn.
        position = match.end('case')
        while cursor < len(boundaries) and boundaries[cursor].end() <= match.start():
            prefix_start = boundaries[cursor].end()
            cursor += 1
        if cursor < len(boundaries) and boundaries[cursor].start() < match.start('predicate'):
            continue
        scope_end = (boundaries[cursor].start() if cursor < len(boundaries) else len(text))
        scope_end = max(scope_end, match.end())
        local = text[prefix_start:scope_end]
        speaker = polarity(local, (match.start() - prefix_start, match.end() - prefix_start), previous=previous)
        actor = _ACTOR_RE.search(text[prefix_start:match.start()])
        intervening_actor = _ACTOR_RE.search(match.group('adjunct'))
        intervening_argument = _INDEPENDENT_ARGUMENT_RE.search(match.group('adjunct'))
        specific_scope = re.search(r'(?:이\s*사건|해당|본건|위)\s*$', text[prefix_start:match.start()])
        specific_debt = bool(specific_scope and match.group('argument') == '채무')
        rows.append({'span': list(match.span()), 'argument_span': list(match.span('argument')),
                     'case_span': list(match.span('case')), 'case_form': match.group('case'),
                     'predicate_span': list(match.span('predicate')), 'clause_end': scope_end,
                     'argument_text': match.group('argument'), 'predicate_text': match.group('predicate'),
                     'adjunct_text': match.group('adjunct'),
                     'adjunct_span': list(match.span('adjunct')),
                     'candidate_kind': 'FINITE_PROPOSITION', 'speaker': speaker,
                     'authored': speaker == ASSERTED and not actor and not intervening_argument,
                     'actor_span': ([prefix_start + offset for offset in actor.span()] if actor
                                    else [match.start('adjunct') + offset for offset in intervening_actor.span()]
                                    if intervening_actor else None),
                     'scope_span': [prefix_start, scope_end],
                     'limited_argument_scope': specific_debt,
                     'limit_span': ([prefix_start + specific_scope.start(), match.end('argument')]
                                    if specific_debt else None),
                     'prefix_text': text[prefix_start:match.start()],
                     'argument_binding': 'UNRESOLVED' if intervening_argument else 'LOCAL_PREDICATE_ARGUMENT',
                     'modal': bool(_MODAL_RE.search(local) or re.search(r'\s수\s', match.group('predicate'))),
                     'tense': 'PAST' if re.search(r'(?:했|하였|됐|되었|았|었)', match.group('predicate')) else 'NONPAST'})
    return rows


def interpret_effect(candidate: dict) -> dict:
    """Compose observed argument, predicate and grammatical negation scope."""
    predicate = candidate['predicate_text']
    normative = '권리' in predicate
    necessity = '필요' in predicate
    role = argument_role(candidate['argument_text'], receipt=normative)
    keys, category = [], 'UNKNOWN'
    if normative:
        keys, category = ['받다:1:1', '권리:0:1'], 'NORMATIVE_PERMISSION'
    elif necessity and role['role'] in {'SANCTION', 'SANCTION_DECISION'}:
        keys, category = ['받다:1:10', '필요:0:1'], 'EXEMPTION_FROM_NECESSITY'
    elif predicate.startswith('면제'):
        keys = ['면제되다:0:1' if predicate.startswith('면제되') else '면제하다:0:1']
        if role['role'] in {'SANCTION', 'SANCTION_DECISION', 'LEGAL_OBLIGATION'}:
            category = 'OBLIGATION_RELEASE'
    elif predicate.startswith('면'):
        if role['role'] in {'SANCTION', 'SANCTION_DECISION'}:
            keys, category = ['면하다:1:2'], 'SANCTION_AVOIDANCE'
        elif role['role'] == 'LEGAL_OBLIGATION':
            keys, category = ['면하다:1:1'], 'OBLIGATION_RELEASE'
        else:
            keys = [row['source_sense_key'] for row in SOURCE_SENSES if row['lemma'] == '면하다']
    elif predicate.startswith('소멸'):
        keys = ['소멸하다:0:1']
        if role['role'] in {'SANCTION', 'SANCTION_DECISION', 'LEGAL_OBLIGATION'}:
            category = 'LEGAL_EFFECT_ELIMINATION'
    elif predicate.startswith('배제'):
        keys = ['배제하다:0:1']
        if role['role'] in {'SANCTION', 'SANCTION_DECISION', 'LEGAL_OBLIGATION'}:
            category = 'LEGAL_EFFECT_EXCLUSION'
    denial = bool(re.search(r'지\s*(?:않는다|않습니다)', predicate))
    semantic_candidate = normative or necessity or bool(keys)
    if predicate.startswith(('소멸', '배제')) and role['role'] == 'UNKNOWN':
        # Disappearance/exclusion alone does not assert a legal exemption.
        # A known ambiguous legal nominal retains a verification candidate;
        # an unrelated unknown noun is not proof of legal effect. Existing
        # configured/negative candidates retain their own review path.
        semantic_candidate = bool(role['candidate_senses'])
    past = candidate['tense'] == 'PAST'
    extent = assertion_extent_evidence(candidate.get('adjunct_text', ''))
    for row in extent:
        row['span'] = [candidate['adjunct_span'][0] + offset for offset in row['span']]
        row['attachment'] = 'PREDICATE_ARGUMENT'
    prefix = candidate.get('prefix_text', '')
    end = len(prefix)
    for row in reversed(assertion_extent_evidence(prefix)):
        if prefix[row['span'][1]:end].strip():
            break
        end = row['span'][0]
        row['span'] = [candidate['scope_span'][0] + offset for offset in row['span']]
        row['attachment'] = 'ARGUMENT_PREFIX'
        extent.append(row)
    if candidate['modal'] or extent:
        category = 'UNKNOWN'
    return {'version': VERSION, 'argument': role, 'predicate_senses': _source(keys),
            'category': category, 'sense_resolved': category != 'UNKNOWN',
            'necessity_negation': necessity, 'normative_permission': normative,
            'authored_actor': candidate['authored'], 'actor_span': candidate['actor_span'],
            'exemption_denied': denial, 'known_extension': category != 'UNKNOWN' and not denial and not past,
            'eligible_effect': semantic_candidate and not past,
            'scope_limitations': extent,
            'mapping_authority': 'APPLICATION_NOT_NIKL_CLASSIFICATION',
            'underlying_facts_verified': False, 'legal_sufficiency_verified': False}


def factual_receipt_evidence(text: str, candidate: dict) -> dict | None:
    """Only observed object + plain receipt negation, never mail noun immunity."""
    argument = text[slice(*candidate['argument_span'])]
    predicate = text[slice(*candidate['predicate_span'])]
    if not re.fullmatch(r'받(?:지는|지도|지)\s*(?:않는다|않습니다)', predicate):
        return None
    role = argument_role(argument, receipt=True)
    if role['role'] != 'TRANSFER_OBJECT':
        return None
    return {'version': VERSION, 'argument': role, 'predicate_senses': _source(['받다:1:1']),
            'category': 'FACTUAL_TRANSFER_NEGATION', 'argument_span': candidate['argument_span'],
            'predicate_span': candidate['predicate_span'],
            'mapping_authority': 'APPLICATION_NOT_NIKL_CLASSIFICATION',
            'underlying_facts_verified': False, 'legal_sufficiency_verified': False}


def negative_receipt_evidence(text: str, candidate: dict) -> dict | None:
    """Undergoing a sanction need not itself assert a normative exemption."""
    predicate = text[slice(*candidate['predicate_span'])]
    if not re.fullmatch(r'받(?:지는|지도|지)\s*(?:않는다|않습니다)', predicate):
        return None
    role = argument_role(text[slice(*candidate['argument_span'])])
    return {'version': VERSION, 'argument': role,
            'predicate_senses': _source(['받다:1:10']) if role['role'] == 'SANCTION_DECISION' else [],
            'category': 'SANCTION_RECEIPT_NEGATION' if role['role'] in {'SANCTION', 'SANCTION_DECISION'} else 'UNKNOWN',
            'known_extension': False, 'normative_scope_unresolved': True,
            'mapping_authority': 'APPLICATION_NOT_NIKL_CLASSIFICATION',
            'underlying_facts_verified': False, 'legal_sufficiency_verified': False}
