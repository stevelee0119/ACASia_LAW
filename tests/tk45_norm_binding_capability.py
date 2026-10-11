"""Public design-only norm attachment spike; never a finding provider.

The prototype proves source reference attachment, not an action/effect sense,
the validity of the norm, or legal sufficiency. Product consumers do not import
this module. Supported closed layouts are declared instead of scanning for a
civil article anywhere in a document.
"""
import re
from packages.legal_engine.legal_rules import load_defense_groups


def civil_articles(groups):
    cluster = groups['clusters']['CIVIL_AND_ADMIN_PRINCIPLES']
    values = set(map(str, cluster['article_numbers']))
    for span in cluster['article_ranges']:
        values.update(map(str, range(span['from'], span['to'] + 1)))
    return values


def norm_binding(body):
    groups = load_defense_groups()
    signals = groups['structural_signals']
    # Unknown source/speaker is not a license to connect separated references.
    if '\n' in body or re.search(r'["“”‘’「」『』]', body):
        return None
    if re.search(r'(?:다고|라고|라는|다는|다며|이라며)(?=\s|[,;.!?]|$)', body):
        return None
    if re.search(r'(?<![가-힣])[가-힣]+면(?=\s|[,;.!?]|$)', body):
        return None
    norm = r'(?P<norm>(?P<law>민법)\s*제\s*(?P<article>\d+)\s*조)'
    lead = '|'.join(signals['hypothetical_concessions'])
    anchor = rf'(?P<anchor>(?:{lead})\s+[^,;.!?\n]+?더라도[,;])\s*'
    argument = '(?:' + '|'.join(signals['stated_requirements']) + ')'
    req = rf'(?P<argument>{argument})'
    case = r'(?P<case>을|를)\s+'
    # Bound the source span; predicate/effect proof remains a separate consumer.
    # Only the existing direct act grammar is exercised in this first spike.
    act = (r'(?P<predicate>하지(?:는|도)?\s*않았(?:으나|지만|으므로))\s*')
    conclusion = '(?:' + '|'.join(signals['limited_conclusions']) + ')'
    end = rf'(?P<conclusion>{conclusion})다[.!]'
    layouts = (
        ('FRONT_CAUSAL_ADJUNCT', rf'{norm}(?P<link>에\s*(?:따라|의하여)),\s*{anchor}{req}\s*{case}{act}{end}'),
        ('ANCHOR_CAUSAL_ADJUNCT', rf'{anchor}{norm}(?P<link>에\s*(?:따라|의하여))\s+{req}\s*{case}{act}{end}'),
        ('ARGUMENT_PARENTHETICAL_REFERENCE', rf'{anchor}{req}\s*\({norm}\)\s*{case}{act}{end}'),
        ('CLAIM_PARENTHETICAL_REFERENCE', rf'{anchor}{req}\s*{case}{act}(?P<conclusion>{conclusion})다\s*\({norm}\)[.!]'),
    )
    for kind, pattern in layouts:
        match = re.fullmatch(pattern, body)
        if not match or match['article'] not in civil_articles(groups):
            continue
        # An absent-polarity configured event cannot reuse positive-event proof.
        absent = signals['requirement_polarities']
        if any(re.fullmatch(p, match['argument']) for p in absent if absent[p] == 'absent'):
            return None
        spans = {key: match.span(key) for key in ('norm','law','article','anchor','argument','case','predicate','conclusion')}
        if kind.endswith('ADJUNCT'):
            spans['normative_link'] = match.span('link')
        return {
            'kind': kind, 'spans': {key:list(span) for key,span in spans.items()},
            'slices': {key: body[a:b] for key,(a,b) in spans.items()},
            'scope': 'OWN_CLOSED_FIRST_BODY_STATEMENT_ONLY',
            'normative_link_observed': kind.endswith('ADJUNCT'),
            'citation_attachment_only': True,
            'legal_effect_sense_selected': False,
            'findings_created': False, 'facts_verified': False,
            'legal_sufficiency_verified': False,
            'supports_asserted_fulfillment': False,
        }
    # This second grammar binds an explicit normative adjunct to an effect
    # clause. It still does not select a legal-effect sense or create findings.
    premise = rf'{req}\s*{case}(?P<premise>[가-힣]+(?:으므로|므로))\s+'
    effect = (r'(?P<effect_argument>형사처벌|징계처분|행정제재)'
              r'(?P<effect_case>을|를)\s+'
              r'(?P<predicate>받지\s*않(?:는다|습니다))')
    effect_layouts = (
        ('FRONT_EFFECT_ADJUNCT', rf'{norm}(?P<link>에\s*(?:따라|의하여)),\s*{anchor}{premise}(?P<conclusion>{effect})[.!]'),
        ('ANCHOR_EFFECT_ADJUNCT', rf'{anchor}{norm}(?P<link>에\s*(?:따라|의하여))\s+{premise}(?P<conclusion>{effect})[.!]'),
        ('EFFECT_PARENTHETICAL_ADJUNCT', rf'{anchor}{premise}(?P<conclusion>{effect})\s*\({norm}(?P<link>에\s*(?:따라|의하여))\)[.!]'),
    )
    for kind, pattern in effect_layouts:
        match = re.fullmatch(pattern, body)
        if not match or match['article'] not in civil_articles(groups):
            continue
        if any(re.fullmatch(p, match['argument']) for p in signals['requirement_polarities']
               if signals['requirement_polarities'][p] == 'absent'):
            return None
        spans={key:list(match.span(key)) for key in ('norm','law','article','anchor','argument','case','premise','effect_argument','effect_case','predicate','conclusion')}
        spans['normative_link']=list(match.span('link'))
        return {
            'kind':kind, 'spans':spans,
            'slices':{key:body[a:b] for key,(a,b) in spans.items()},
            'scope':'OWN_CLOSED_FIRST_BODY_STATEMENT_ONLY',
            'normative_link_observed':True, 'citation_attachment_only':True,
            'legal_effect_sense_selected':False, 'findings_created':False,
            'facts_verified':False, 'legal_sufficiency_verified':False,
            'supports_asserted_fulfillment':False,
        }
    return None
