"""Enabled source view preserves current language, original bounds and UNKNOWN."""
import copy
import pytest
from packages.legal_engine.defense_source_delta import source_defense_proof, _supported_conclusion_pattern
from packages.legal_engine.legal_rules import load_defense_groups
from test_tk45_source_negative_delta import DIRECT,run_source,check_proof
from test_tk45_conclusion_whitespace_view_spike import PATTERNS,compact_range,supported_pattern


@pytest.mark.parametrize('count',[0,256,32000])
@pytest.mark.parametrize('known',[True,False])
def test_original_conclusion_run_mapping_and_unknown_are_preserved(count,known):
    body=DIRECT.replace('채무에 관한 책임','채무에'+' '*count+('관한 책임' if known else '가'))
    proof=source_defense_proof(body,load_defense_groups())
    if not known:
        assert proof is None
        return
    assert proof['kind']=='DIRECT_REQUIREMENT_DENIAL'
    a,b=proof['source_spans']['conclusion']
    assert body[a:b]=='이 사건 채무에'+' '*count+'관한 책임을 질 수 없'
    assert proof['source_spans']['predicate']==source_defense_proof(DIRECT,load_defense_groups())['source_spans']['predicate']
    accounting=proof['accounting']
    assert accounting['conclusion_view_builds']==1
    assert accounting['conclusion_binary_queries']==1
    assert 0<accounting['conclusion_view_join_chars']<=accounting['conclusion_view_scan_chars']<=len(body)
    assert not proof['supports_asserted_fulfillment'] and not proof['facts_verified']


@pytest.mark.parametrize('known',[True,False])
def test_actual_txt_32k_conclusion_consumer_keeps_source_and_verdict(tmp_path,known):
    # This is the actual parser -> legal-rule consumer contract. The whole
    # pipeline's existing adversarial classifier stalls on this long run even
    # with new proofs disabled; ordinary whole-pipeline controls stay separate.
    from packages.document_engine import parse_document
    from packages.document_engine.reading_text import build_reading_text
    from packages.common.storage import sha256_file
    from packages.legal_engine.legal_rules import review_legal_rules
    from test_tk45_source_negative_delta import RULE
    body=DIRECT.replace('채무에 관한 책임','채무에'+' '*32000+('관한 책임' if known else '가'))
    path=tmp_path/'space-run.txt';path.write_text('청구원인\n'+body,encoding='utf-8')
    doc=parse_document(str(path),document_id='public',filename=path.name,mime_type='text/plain',sha256=sha256_file(path))
    text=build_reading_text(doc).text
    assert body in text
    findings=[finding for finding in review_legal_rules(doc) if RULE in finding.tags]
    if known:
        assert len(findings)==1
        check_proof(findings[0],text,'DIRECT_REQUIREMENT_DENIAL',expected_full_claim=body)
        proof=findings[0].confidence_features['source_defense_proof']
        a,b=proof['source_spans']['conclusion']
        assert ' '*32000 in body[a:b]
    else:
        assert not findings


@pytest.mark.parametrize('pattern',PATTERNS+[r'a b',r'a\s+',r'a\s{2}',r'a(?=\s)b',r'a(?<!\s)b',r'a(?s:.+)b',r'a\tb',r'a\s*?b',r'a\s*+b'])
def test_product_pattern_contract_matches_independent_language_spike(pattern):
    assert _supported_conclusion_pattern(pattern)==supported_pattern(pattern)


@pytest.mark.parametrize('pattern',[r'이 사건 채무에 관한 책임을 질 수 없',r'이\s+사건\s*채무에\s*관한\s*책임을\s*질\s*수\s*없',r'(?=이)이\s*사건\s*채무에\s*관한\s*책임을\s*질\s*수\s*없'])
def test_future_sensitive_configuration_abstains_only_from_new_proof(pattern):
    groups=copy.deepcopy(load_defense_groups())
    groups['structural_signals']['limited_conclusions']=[pattern]
    assert source_defense_proof(DIRECT,groups) is None


def test_product_view_and_original_nonzero_bounds_match_independent_spike():
    from packages.legal_engine.defense_source_delta import _conclusion_view
    text='앞 범위; 논항을 하지 않았으나 채무에\t\u00a0  관한 책임을 질 수 없다.'
    start=text.index('논항')
    expected,spans=compact_range(text,start)
    actual,starts,ends=_conclusion_view(text,start)
    assert actual==expected and list(zip(starts,ends))==spans


@pytest.mark.parametrize('pattern',['',r'\s*',r'(?:\s*)??',r'(?:이)?',r'(?:이|\s*)','(', 'a)'])
def test_empty_or_optional_zero_width_conclusion_cannot_make_a_proof(pattern):
    assert not _supported_conclusion_pattern(pattern)
    groups=copy.deepcopy(load_defense_groups())
    groups['structural_signals']['limited_conclusions']=[pattern]
    body=DIRECT[:DIRECT.index('이 사건')]+'다.'
    assert source_defense_proof(body,groups) is None
