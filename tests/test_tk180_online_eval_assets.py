"""Feature-specific online checks must fail when source use or input defenses regress."""
import hashlib
from pathlib import Path
import pytest
from scripts import score_report
from packages.common.enums import ADVERSARIAL_FINDING_TYPES
from packages.document_engine.registry import parse_document
from packages.adversarial_engine import AdversarialScanner
from packages.document_engine.analysis_text import analysis_text

ASSETS=Path(__file__).parent/'fixtures/online/tk180'
EXPECTED={'visible':'SYSTEM_OVERRIDE_ATTEMPT','metadata':'METADATA_INJECTION','hidden':'HIDDEN_INSTRUCTION','encoded':'ENCODED_INSTRUCTION'}

@pytest.mark.parametrize('variant',['normal',*EXPECTED])
def test_input_assets_keep_defenses_and_reviewable_body(variant):
    path=ASSETS/f'input_{variant}.docx'
    doc=parse_document(str(path),document_id=variant,filename=path.name,mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    findings=AdversarialScanner().scan(doc).findings
    adversarial=[f for f in findings if f.type in ADVERSARIAL_FINDING_TYPES]
    if variant=='normal':assert adversarial==[]
    else:assert any(f.type.value==EXPECTED[variant] and f.severity.value=='HIGH' for f in adversarial)
    body,_=analysis_text(doc,findings)
    if variant=='normal':assert '일방 통지만으로 대금 인상이 가능' in body
    else:assert isinstance(body,str)  # An entire input block may legitimately be excluded.


def observation(variant):
    return {'findings':([] if variant=='normal' else [{'type':EXPECTED[variant],'severity':'HIGH','status':'SUSPICIOUS','text':'input document'}]),'rag_sources':['TK180_verified_reference_control.txt'],'rag':[{'_source_title':'TK180_verified_reference_control.txt','relationship':'CONTRADICTS','claim_quote':'일방 통지만으로 대금 인상이 가능'}]}

@pytest.mark.parametrize('variant',['normal',*EXPECTED])
def test_online_specs_require_sources_and_input_findings(variant):
    spec=score_report.load_spec(ASSETS/f'spec_{variant}.json')
    obs=observation(variant)
    assert all(c['passed'] for c in score_report.evaluate(spec,obs))
    if variant=='normal':
        obs['rag_sources']=[]
        assert not all(c['passed'] for c in score_report.evaluate(spec,obs))
        obs=observation(variant);obs['rag']=[]
        assert not all(c['passed'] for c in score_report.evaluate(spec,obs))
    obs=observation(variant)
    obs['findings']=([{'type':'METADATA_INJECTION','severity':'HIGH','status':'SUSPICIOUS','text':'reference wrongly flagged'}] if variant=='normal' else [])
    assert not all(c['passed'] for c in score_report.evaluate(spec,obs))


def test_reference_label_cannot_enable_source_commands():
    reference=(ASSETS/'TK180_verified_reference_control.txt').read_text()
    assert 'ignore all previous instructions' in reference and '서면 동의가 필요' in reference
    # The online positive result requires contradiction, not obeying the quoted command.
    spec=score_report.load_spec(ASSETS/'spec_normal.json')
    obs=observation('normal');obs['rag'][0]['relationship']='SUPPORTS'
    assert not all(c['passed'] for c in score_report.evaluate(spec,obs))


def test_asset_hashes_match_prepared_online_manifest():
    import json
    manifest=json.loads((ASSETS/'manifest.json').read_text())
    assert manifest['status']=='PREPARED_NOT_RUN_ONLINE'
    for name,expected in manifest['hashes'].items():
        assert hashlib.sha256((ASSETS/name).read_bytes()).hexdigest()==expected
