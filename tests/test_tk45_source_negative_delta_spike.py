"""Design-only actual TXT baseline witnesses; not an implemented proof parser.

Future contract: six missing direct denial/effect findings, preserving all
opposite baseline results. Source spans below are explicit synthetic fixture
annotations, not certified semantic output from the product.
"""
import re
import pytest
from packages.audit_engine import AuditChain
from packages.common.storage import sha256_file
from packages.legal_engine.legal_rules import get_defense_overclaim_pattern, load_defense_groups, _defense_requirement_state
from packages.verification_engine import DocumentInput, ProjectContext, VerificationPipeline
RULE='GEN.DEFENSE_OVERCLAIM_WITHOUT_REQUIREMENTS'
rows=[]
def add(name, body, relation, desired): rows.append((name,body,relation,desired))
for anchor in ['유효하더라도','성립하더라도','존속하더라도']:
 add('direct-'+anchor, f'설령 계약이 {anchor}, 민법 제487조의 변제공탁을 하지 않았으나 이 사건 채무에 관한 책임을 질 수 없다.', 'DIRECT_CASE_BOUND_DENIAL',1)
for obj in ['형사처벌','징계처분','행정제재']:
 add('effect-'+obj, f'설령 계약이 인정되더라도, 민법 제487조에 따라 변제공탁을 완료하였으므로 {obj}를 받지 않는다.', 'LEGAL_OBJECT_TYPED_EFFECT',1)
for act in ['완료하였으므로','이행하였으므로','하였으므로']:
 add('normal-'+act, f'설령 계약이 인정되더라도, 민법 제487조에 따라 변제공탁을 {act} 이 사건 채무에 관한 책임을 질 수 없다.', 'PRESERVE_BASELINE',None)
add('bare', '설령 계약이 유효하더라도, 민법 제487조와 변제공탁에 관하여 이 사건 채무에 관한 책임을 질 수 없다.', 'UNKNOWN_NOT_NEW_PROOF',None)
add('adjunct', '설령 계약이 유효하더라도, 민법 제487조의 변제공탁을 지체하지 않고 완료하였으므로 이 사건 채무에 관한 책임을 질 수 없다.', 'ADJUNCT_NOT_REQUIREMENT_DENIAL',None)
add('nested', '설령 계약이 유효하더라도, 민법 제487조의 변제공탁을 하지 않은 것은 아니므로 이 사건 채무에 관한 책임을 질 수 없다.', 'NESTED_NO_PROOF',None)
add('quote', '피고는 “설령 계약이 유효하더라도, 민법 제487조의 변제공탁을 하지 않았으나 이 사건 채무에 관한 책임을 질 수 없다”라고 주장하나 원고는 이를 다툰다.', 'REPORT_NO_PROOF',None)
add('opponent', '설령 계약이 유효하더라도, 민법 제487조의 변제공탁을 하지 않았으나 이 사건 채무에 관한 책임을 질 수 없다고 피고는 주장하지만 원고는 이를 부인한다.', 'REPORT_NO_PROOF',None)
add('factual-receipt', '설령 계약이 인정되더라도, 민법 제487조에 따라 변제공탁을 완료하였으므로 소포를 받지 않는다.', 'FACTUAL_RECEIPT_NOT_LEGAL_EFFECT',None)
add('conditional', '설령 계약이 유효하더라도, 민법 제487조의 변제공탁을 하지 않았다면 이 사건 채무에 관한 책임을 질 수 없다.', 'CONDITIONAL_NO_DIRECT_DENIAL',None)
add('necessity', '설령 계약이 유효하더라도, 민법 제487조의 변제공탁을 할 필요가 없으므로 이 사건 채무에 관한 책임을 질 수 없다.', 'NECESSITY_NOT_ACT_DENIAL',None)
add('other-argument', '설령 계약이 유효하더라도, 민법 제487조의 변제공탁 서류를 작성하지 않았으나 이 사건 채무에 관한 책임을 질 수 없다.', 'OTHER_ARGUMENT_NO_DIRECT_DENIAL',None)

add('quote-two', '피고는 “설령 계약이 유효하더라도, 민법 제487조의 변제공탁을 하지 않았으나 이 사건 채무에 관한 책임을 질 수 없다”라고 말했으며 원고는 이를 다툰다.', 'REPORT_NO_PROOF',None)
add('opponent-two', '피고는 설령 계약이 유효하더라도 민법 제487조의 변제공탁을 하지 않았으나 이 사건 채무에 관한 책임을 질 수 없다고 주장하였지만 원고는 반대한다.', 'REPORT_NO_PROOF',None)
add('rebuttal-one', '설령 계약이 유효하더라도, 민법 제487조의 변제공탁을 하지 않았으나 이 사건 채무에 관한 책임을 질 수 없다는 피고의 주장은 이유 없다.', 'REBUTTAL_NO_PROOF',None)
add('rebuttal-two', '설령 계약이 유효하더라도, 민법 제487조의 변제공탁을 하지 않았으나 이 사건 채무에 관한 책임을 질 수 없다는 피고의 항변은 받아들일 수 없다.', 'REBUTTAL_NO_PROOF',None)

for suffix in ['하지 않았으나','하지 않았지만','하지 않았으므로']:
 add('existing-warning-'+suffix, f'설령 계약이 인정되더라도, 민법 제487조의 변제공탁을 {suffix} 이 사건 채무에 관한 책임을 질 수 없다.', 'PRESERVE_EXISTING_WARNING',None)

@pytest.mark.parametrize('name,body,relation,desired',rows,ids=[r[0] for r in rows])
def test_public_actual_txt_baseline_and_declared_delta(tmp_path,name,body,relation,desired):
    path=tmp_path/'public.txt';path.write_text('청구원인\n'+body,encoding='utf-8')
    result=VerificationPipeline(audit=AuditChain()).run('public-'+name,ProjectContext('public'),[
        DocumentInput('public',str(path),path.name,'text/plain',sha256_file(path))])
    assert not result.errors
    findings=[f for f in result.all_findings if RULE in f.tags]
    assert len(findings) == (1 if relation == 'PRESERVE_EXISTING_WARNING' else 0)
    # Baseline witness, not the desired future positives. Existing warning stays.
    if relation == 'DIRECT_CASE_BOUND_DENIAL':
        signals=load_defense_groups()['structural_signals']
        state=_defense_requirement_state(body,signals['stated_requirements'],signals['limited_conclusions'],signals.get('requirement_polarities',{}))
        assert state[1] is True  # Existing denial branch is gated before rule selection.
        assert not get_defense_overclaim_pattern().search(body)
        event=re.search('변제공탁',body);assert event
        argument=event.span();case=(event.end(),event.end()+1)
        predicate=re.search('하지 않았으나',body);assert predicate
        assert body[slice(*argument)]=='변제공탁' and body[slice(*case)]=='을'
        assert not body[case[1]:predicate.start()].strip()
        assert body[slice(*predicate.span())]=='하지 않았으나'
        assert desired==1
    elif relation == 'LEGAL_OBJECT_TYPED_EFFECT':
        # Fixture annotation distinguishes object/case/finite predicate; product
        # currently produces no selected sense or new categorical verdict here.
        m=re.search(r'(형사처벌|징계처분|행정제재)(를) (받지 않는다)',body);assert m
        assert body[slice(*m.span(2))]=='를'
        assert body[slice(*m.span(3))]=='받지 않는다'
        assert desired==1
    else:
        assert desired is None
