"""Design-only source mapping/language comparison; product remains unchanged."""
import re
import pytest
from packages.legal_engine.legal_rules import load_defense_groups


def compact_range(text,start=0):
    chars=[];spans=[]
    for index in range(start,len(text)):
        char=text[index]
        if char.isspace():
            if chars and chars[-1]==' ':
                spans[-1]=(spans[-1][0],index+1)
            else:
                chars.append(' ');spans.append((index,index+1))
        else:
            chars.append(char);spans.append((index,index+1))
    return ''.join(chars),spans


def supported_pattern(pattern):
    index=0
    while index<len(pattern):
        if pattern.startswith(r'\s*',index):
            index+=3
            if index<len(pattern) and pattern[index] in '?+': return False
            continue
        if pattern.startswith('(?:',index): index+=3;continue
        char=pattern[index]
        if char.isspace() or char in r'\.^$[]{}*+': return False
        if char=='(' and pattern[index+1:index+2]=='?': return False
        index+=1
    return re.compile(pattern).match('') is None


PATTERNS=load_defense_groups()['structural_signals']['limited_conclusions']
CLAUSES=['이 사건 채무에 관한 책임을 질 수 없다','해당 의무를 이행할 책임이 없다','본건 채무에 대한 책임이 없습니다','대등액에서 소멸','한도에서 면책']

@pytest.mark.parametrize('index',range(len(PATTERNS)))
@pytest.mark.parametrize('separator',['',' ','  ','\t','\u00a0\u3000'])
@pytest.mark.parametrize('unknown',[False,True])
def test_current_language_and_original_spans_match_the_compact_view(index,separator,unknown):
    pattern=PATTERNS[index];assert supported_pattern(pattern)
    body=separator.join(CLAUSES[index].split())+(' x' if unknown else '')
    if unknown: body=body.replace('책임','관측불명',1).replace('소멸','관측불명',1).replace('면책','관측불명',1)
    view,mapping=compact_range(body)
    original=re.compile(pattern).match(body);compact=re.compile(pattern).match(view)
    assert bool(original) is (not unknown)
    assert bool(original)==bool(compact)
    if original:
        assert (mapping[compact.start()][0],mapping[compact.end()-1][1])==original.span()
    assert all(body[a:b].isspace() if view[n]==' ' else body[a:b]==view[n] for n,(a,b) in enumerate(mapping))


@pytest.mark.parametrize('pattern',[r'a b',r'a\s+',r'a\s{2}',r'a(?=\s)b',r'a(?<!\s)b',r'a(?s:.+)b',r'a\tb',r'a\s*?b',r'a\s*+b'])
def test_sensitive_future_patterns_require_a_new_contract(pattern):
    assert not supported_pattern(pattern)


def test_nonzero_local_range_preserves_whole_original_whitespace_run():
    text='이전 범위; 논항을 하지 않았으나 채무에\t\u00a0  관한 책임을 질 수 없다.'
    start=text.index('채무에')
    view,mapping=compact_range(text,start)
    original=re.compile(PATTERNS[0]).match(text,start)
    compact=re.compile(PATTERNS[0]).match(view)
    assert original and compact
    assert original.span()==(mapping[compact.start()][0],mapping[compact.end()-1][1])
    whitespace=view.index(' ')
    a,b=mapping[whitespace]
    assert text[a:b]=='\t\u00a0  '
