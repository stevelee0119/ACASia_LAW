"""Reference availability is never downstream action/effect evidence."""
import json
import pytest
from packages.audit_engine import AuditChain
from packages.common.storage import sha256_file
from packages.document_engine.reading_text import build_reading_text
from packages.verification_engine import DocumentInput,ProjectContext,VerificationPipeline
from tk45_norm_binding_capability import norm_binding,proposal_admission
from test_tk45_norm_binding_capability_spike import POSITIVE

EFFECT=POSITIVE[-2][1]
UNKNOWN_PREMISES=[
 ('plan','계획하였으므로'),
 ('preparation','준비하였으므로'),
 ('assumption','완료하였다고가정하므로'),
 ('joined-report','완료하였다고주장하므로'),
]


def actual(path,source):
    path.write_text(source,encoding='utf-8')
    result=VerificationPipeline(audit=AuditChain()).run('admission-public',ProjectContext('public'),[
        DocumentInput('public',str(path),path.name,'text/plain',sha256_file(path))])
    assert not result.errors
    return result,result.documents[0].normalized


@pytest.mark.parametrize('name,premise',UNKNOWN_PREMISES,ids=[r[0] for r in UNKNOWN_PREMISES])
def test_unknown_premise_reference_is_not_legal_consumer_admission(tmp_path,name,premise):
    body=EFFECT.replace('완료하였으므로',premise)
    result,doc=actual(tmp_path/'unknown.txt','청구원인\n'+body)
    node=norm_binding(body)
    assert node and node['citation_attachment_only']
    for key in ('speaker_scope_verified','first_body_verified','legal_admissibility_verified','legal_effect_sense_selected','findings_created','supports_asserted_fulfillment'):
        assert node[key] is False
    assert proposal_admission(doc) is None
    assert not any('source_defense_proof' in f.confidence_features for f in result.all_findings)


@pytest.mark.parametrize('name,body,kind',POSITIVE,ids=[r[0] for r in POSITIVE])
def test_actual_source_admission_keeps_reference_sense_finding_and_truth_separate(tmp_path,name,body,kind):
    result,doc=actual(tmp_path/'positive.txt','청구원인\n'+body)
    admitted=proposal_admission(doc);assert admitted
    assert admitted['speaker_scope_verified'] and admitted['first_body_verified']
    text=build_reading_text(doc).text
    for key,(a,b) in admitted['source_spans'].items():
        assert text[a:b]==admitted['source_slices'][key]
    for key in ('legal_effect_sense_selected','findings_created','supports_asserted_fulfillment','total_requirement_completion','facts_verified','legal_sufficiency_verified','product_consumer_installed'):
        assert admitted[key] is False
    assert json.loads(json.dumps(admitted,ensure_ascii=False))==admitted
    assert not any('source_defense_proof' in f.confidence_features for f in result.all_findings)


@pytest.mark.parametrize('prefix',[
 '상대방은 다음과 같이 주장한다.\n',
 '“상대방의 주장은 다음과 같다.”\n',
 '청구취지\n청구를 기각한다.\n',
 '이하 주장을 반박한다.\n',
])
def test_candidate_body_label_cannot_skip_original_source_prefix(tmp_path,prefix):
    body=POSITIVE[0][1]
    assert norm_binding(body)
    result,doc=actual(tmp_path/'prefix.txt',prefix+'청구원인\n'+body)
    assert proposal_admission(doc) is None


@pytest.mark.parametrize('body',[
 EFFECT.replace('완료하였으므로','완료할계획이므로'),
 EFFECT.replace('완료하였으므로','완료하였으나'),
 EFFECT.replace('변제공탁을','일부 변제공탁을'),
 EFFECT.replace('변제공탁을','변제공탁 서류를'),
 EFFECT.replace('변제공탁을','원고가 변제공탁을'),
 EFFECT.replace('징계처분을 받지 않습니다','소포를 받지 않습니다'),
 EFFECT.replace('징계처분을 받지 않습니다','징계처분을 받을 필요가 없습니다'),
])
def test_actual_opposite_consumer_never_borrows_citation(tmp_path,body):
    result,doc=actual(tmp_path/'opposite.txt','청구원인\n'+body)
    assert proposal_admission(doc) is None


@pytest.mark.parametrize('body',[POSITIVE[0][1],EFFECT])
def test_original_empty_source_prefix_contract_is_preserved(tmp_path,body):
    result,doc=actual(tmp_path/'no-heading.txt',body)
    admitted=proposal_admission(doc)
    assert admitted and admitted['source_prefix_span']==[0,0]
    assert not admitted['findings_created'] and not admitted['product_consumer_installed']
