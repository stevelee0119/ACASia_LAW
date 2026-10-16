"""Generated public actual TXT and source-index comparisons, product diff zero."""
import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

from packages.audit_engine import AuditChain
from packages.common.storage import sha256_file
from packages.document_engine.reading_text import build_reading_text
from packages.legal_engine.legal_rules import load_defense_groups
from packages.verification_engine import DocumentInput, ProjectContext, VerificationPipeline
from tk45_norm_binding_capability import norm_binding

ANCHOR = '설령 계약이 인정되더라도, '
ACT = '변제공탁을 하지 않았으나 '
END = '이 사건 채무에 관한 책임을 질 수 없다.'
POSITIVE = [
 ('front', '민법 제487조에 따라, '+ANCHOR+ACT+END, 'FRONT_CAUSAL_ADJUNCT'),
 ('immediate', ANCHOR+'민법 제487조에 따라 '+ACT+END, 'ANCHOR_CAUSAL_ADJUNCT'),
 ('argument-paren', ANCHOR+'변제공탁(민법 제487조)을 하지 않았으나 '+END, 'ARGUMENT_PARENTHETICAL_REFERENCE'),
 ('claim-paren', ANCHOR+ACT+END[:-1]+'(민법 제487조).', 'CLAIM_PARENTHETICAL_REFERENCE'),
 ('other-event', '민법 제493조에 의하여, '+ANCHOR+'상계의 의사표시를 하지 않았지만 '+END, 'FRONT_CAUSAL_ADJUNCT'),
 ('focus', ANCHOR+'민법 제487조에 의하여 변제공탁을 하지는 않았으므로 '+END, 'ANCHOR_CAUSAL_ADJUNCT'),
 ('front-effect', '민법 제487조에 따라, '+ANCHOR+'변제공탁을 완료하였으므로 행정제재를 받지 않는다.', 'FRONT_EFFECT_ADJUNCT'),
 ('immediate-effect', ANCHOR+'민법 제487조에 따라 변제공탁을 완료하였으므로 징계처분을 받지 않습니다.', 'ANCHOR_EFFECT_ADJUNCT'),
 ('after-effect', ANCHOR+'변제공탁을 완료하였으므로 형사처벌을 받지 않는다(민법 제487조에 따라).', 'EFFECT_PARENTHETICAL_ADJUNCT'),
]
BASE = POSITIVE[0][1]
NEGATIVE = [
 ('bare-number', BASE.replace('민법 ','')),
 ('wrong-law', BASE.replace('민법','형법')),
 ('constitutional', BASE.replace('민법 제487조','헌법 제10조')),
 ('unconfigured', BASE.replace('487','9999')),
 ('unrelated-cite', '민법 제487조를 검토하였다. '+ANCHOR+ACT+END),
 ('opponent', '상대방은 '+BASE),
 ('quote', '“'+BASE+'”'),
 ('report', BASE[:-1]+'고 주장한다.'),
 ('preceding-report', '상대방의 주장은 다음과 같다. '+BASE),
 ('rebuttal', '다음 주장에 동의하지 않는다. '+BASE),
 ('multiline', BASE.replace(', ', ',\n',1)),
 ('condition', BASE.replace('하지 않았으나','하지 않았다면')),
 ('nested-denial', BASE.replace('하지 않았으나','하지 않은 것은 아니므로')),
 ('necessity', BASE.replace('하지 않았으나','할 필요가 없으므로')),
 ('plan', BASE.replace('하지 않았으나','하지 않을 계획이므로')),
 ('incidental', BASE.replace('하지 않았으나','지체하지 않고 완료하였으므로')),
 ('normal', BASE.replace('하지 않았으나','완료하였으므로')),
 ('other-argument', BASE.replace('변제공탁을','변제공탁 서류를')),
 ('partial', BASE.replace('변제공탁을','일부 변제공탁을')),
 ('actor', BASE.replace('변제공탁을','원고가 변제공탁을')),
 ('absent-polarity', BASE.replace('변제공탁을','상계 금지사유를')),
 ('unattached-parenthesis', ANCHOR+'절차(민법 제487조)를 검토하고 '+ACT+END),
 ('post-other-claim', ANCHOR+ACT+END+' 민법 제487조에 따른 절차를 검토한다.'),
 ('bare-reference-link', BASE.replace('에 따라','을 검토하고')),
 ('after-bare-effect', POSITIVE[-1][1].replace('민법 제487조에 따라','제487조에 따라')),
 ('after-wrong-law-effect', POSITIVE[-1][1].replace('민법','형법')),
 ('after-effect-report', POSITIVE[-1][1][:-1]+'고 주장한다.'),
 ('effect-necessity', POSITIVE[-1][1].replace('받지 않는다','받을 필요가 없다')),
 ('factual-receipt', POSITIVE[-1][1].replace('형사처벌','소포')),
 ('effect-other-actor', POSITIVE[-1][1].replace('형사처벌','원고가 형사처벌')),
]


@pytest.fixture(scope='module')
def historical_provider(tmp_path_factory):
    # Byte-identical test-only snapshot of public f8f6e08. Shallow/no-Git
    # checkouts must not depend on an unrelated branch's object store.
    path=tmp_path_factory.mktemp('historical')/'source_delta.py'
    data=Path(__file__).with_name('tk45_f8_source_delta_baseline.py').read_bytes()
    assert hashlib.sha256(data).hexdigest()=='dbdb261ef1d4543d7ba25f62d3a668397ef1dcd0c3516341088659541d515e06'
    path.write_bytes(data)
    spec=importlib.util.spec_from_file_location('historical_source_delta',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.source_defense_proof


@pytest.mark.parametrize('name,body,kind',POSITIVE,ids=[r[0] for r in POSITIVE])
def test_actual_txt_source_positions(tmp_path,historical_provider,name,body,kind):
    path=tmp_path/'public.txt';path.write_text('청구원인\n'+body,encoding='utf-8')
    result=VerificationPipeline(audit=AuditChain()).run('norm-public',ProjectContext('public'),[
        DocumentInput('public',str(path),path.name,'text/plain',sha256_file(path))])
    assert not result.errors
    text=build_reading_text(result.documents[0].normalized).text
    assert body in text
    proof=norm_binding(body);assert proof and proof['kind']==kind
    for key,(a,b) in proof['spans'].items():
        assert body[a:b]==proof['slices'][key]
        assert 0<=a<b<=len(body)
    assert proof['slices']['law']=='민법'
    assert proof['citation_attachment_only'] and not proof['findings_created']
    assert not proof['supports_asserted_fulfillment'] and not proof['legal_effect_sense_selected']
    assert json.loads(json.dumps(proof,ensure_ascii=False))==proof
    old=historical_provider(body,load_defense_groups())
    assert bool(old)==(kind in ('ANCHOR_CAUSAL_ADJUNCT','ANCHOR_EFFECT_ADJUNCT'))
    assert not any('source_defense_proof' in f.confidence_features for f in result.all_findings)


@pytest.mark.parametrize('name,body',NEGATIVE,ids=[r[0] for r in NEGATIVE])
def test_actual_txt_opposites_preserve_source_unknown(tmp_path,historical_provider,name,body):
    path=tmp_path/'negative.txt';path.write_text('청구원인\n'+body,encoding='utf-8')
    result=VerificationPipeline(audit=AuditChain()).run('norm-negative',ProjectContext('public'),[
        DocumentInput('public',str(path),path.name,'text/plain',sha256_file(path))])
    assert not result.errors
    assert norm_binding(body) is None
    assert historical_provider(body,load_defense_groups()) is None
    assert not any('source_defense_proof' in f.confidence_features for f in result.all_findings)
