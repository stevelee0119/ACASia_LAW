"""Public clause-first candidate/proposition controls, frozen before rework."""
import json
import pytest

from packages.legal_engine import legal_rules
from tests.test_tk45_authored_predicate_scope import LIMIT, LIMIT_CONNECTIVE, _pipeline_warnings

LEAD = '설령 계약이 인정되더라도, '
FULFILLED = '변제공탁을 하였으므로'


def _trace_pipeline(monkeypatch, tmp_path, text):
    trace = {'units': [], 'requirements': [], 'conclusions': [], 'selected_findings': []}
    review = legal_rules._review_defense_statement
    requirements = legal_rules._defense_requirement_observations
    conclusions = legal_rules.conclusion_scopes
    finding = legal_rules._finding

    def record_review(doc, rule, unit, pattern, *args, **kwargs):
        trace['units'].append({'unit': unit, 'legacy_gate': bool(pattern.search(unit))})
        return review(doc, rule, unit, pattern, *args, **kwargs)

    def record_requirements(*args, **kwargs):
        rows = requirements(*args, **kwargs)
        trace['requirements'].extend(rows)
        return rows

    def record_conclusions(*args, **kwargs):
        rows = conclusions(*args, **kwargs)
        trace['conclusions'].extend(rows)
        return rows

    def record_finding(doc, rule, claim, sources):
        if rule['rule_id'] == 'GEN.DEFENSE_OVERCLAIM_WITHOUT_REQUIREMENTS':
            trace['selected_findings'].append({'status': rule.get('status'), 'verdict': rule['verdict']})
        return finding(doc, rule, claim, sources)

    monkeypatch.setattr(legal_rules, '_review_defense_statement', record_review)
    monkeypatch.setattr(legal_rules, '_defense_requirement_observations', record_requirements)
    monkeypatch.setattr(legal_rules, 'conclusion_scopes', record_conclusions)
    monkeypatch.setattr(legal_rules, '_finding', record_finding)
    return _pipeline_warnings(tmp_path, text), trace


@pytest.mark.parametrize('effect', [
    '형사처벌도 면한다.', '징계처분은 소멸한다.', '행정제재를 받을 필요가 없다.',
])
@pytest.mark.parametrize('limited_first', [False, True])
def test_authored_exemption_proposition_has_a_candidate_without_legacy_p3(monkeypatch, tmp_path, effect, limited_first):
    text = LEAD + FULFILLED + (LIMIT_CONNECTIVE if limited_first else ' ') + effect
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings, trace
    assert trace['conclusions'], trace
    assert trace['selected_findings'], trace
    assert all(row.status.value == 'SUSPICIOUS' for row in findings)


@pytest.mark.parametrize('object_text,particle', [('우편물', '을'), ('소포', '를'), ('우편', '을')])
def test_typed_receipt_fact_is_not_a_legal_exemption(monkeypatch, tmp_path, object_text, particle):
    text = LEAD + FULFILLED + LIMIT_CONNECTIVE + object_text + particle + ' 받지 않는다.'
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace


@pytest.mark.parametrize('tail', [
    '형사처벌도 면한다는 뜻은 아니다.',
    '징계처분은 소멸하는 것이 아니다.',
    '행정제재를 받을 필요가 없다고 주장하는 것은 아니다.',
    '형사처벌은 별도 절차에서 심리된다.',
    '징계처분은 별도로 판단되어야 한다.',
    '행정제재에 관한 결론은 유보한다.',
])
def test_opposite_denied_embedded_or_separately_reviewed_effect_is_not_an_extension(monkeypatch, tmp_path, tail):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + FULFILLED + LIMIT_CONNECTIVE + tail)
    assert not findings, trace


@pytest.mark.parametrize('effect', ['형사처벌도 면한다.', '징계처분은 소멸한다.'])
@pytest.mark.parametrize('speaker', ['원고는 ', '상대방은 '])
def test_reported_effect_does_not_supply_authored_extension(monkeypatch, tmp_path, effect, speaker):
    text = LEAD + FULFILLED + LIMIT_CONNECTIVE + speaker + '“' + effect[:-1] + '”고 주장하나 그 항변은 이유 없다.'
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings, trace


@pytest.mark.parametrize('source', [
    '변제공탁을 하였으므로',
    '지체하지 않고 전액을 지급하였으므로',
    '상계의 의사표시가 도달하였고 원고가 이의하지 않았으므로',
])
def test_existing_normal_finite_requirement_and_limited_conclusion_survive(monkeypatch, tmp_path, source):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + source + LIMIT)
    assert not findings, trace


@pytest.mark.parametrize('effect,argument,predicate,category,sense', [
    ('형사처벌도 면한다.', '형사처벌', '면한다', 'SANCTION_AVOIDANCE', '면하다:1:2'),
    ('징계처분은 소멸한다.', '징계처분', '소멸한다', 'LEGAL_EFFECT_ELIMINATION', '소멸하다:0:1'),
    ('행정제재를 받을 필요가 없다.', '행정제재', '받을 필요가 없다', 'EXEMPTION_FROM_NECESSITY', '필요:0:1'),
])
def test_known_extension_is_composed_and_source_bound_not_only_a_finding(monkeypatch, tmp_path, effect, argument, predicate, category, sense):
    text = LEAD + FULFILLED + ' ' + effect
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings and all('요건 확인 요청' not in row.confidence_features['verdict'] for row in findings)
    source = findings[0].confidence_features['claim']
    row = next(row for row in trace['conclusions'] if row.get('candidate_kind') == 'FINITE_PROPOSITION' and row['is_conclusion'])
    interpretation = row['effect_interpretation']
    assert source[slice(*row['argument_span'])] == argument
    assert source[slice(*row['predicate_span'])] == predicate
    assert interpretation['category'] == category and interpretation['known_extension']
    assert interpretation['authored_actor'] and not interpretation['actor_span']
    assert any(item['source_sense_key'] == sense for item in interpretation['predicate_senses'])
    assert interpretation['argument']['selected_senses']
    assert interpretation['necessity_negation'] is ('필요' in predicate)
    assert not interpretation['legal_sufficiency_verified'] and not interpretation['underlying_facts_verified']
    assert json.loads(json.dumps(row, ensure_ascii=False)) == row


@pytest.mark.parametrize('effect', ['제재가 소멸한다.', '책임을 면한다.'])
def test_unresolved_source_senses_keep_verification_not_known_extension(monkeypatch, tmp_path, effect):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + FULFILLED + LIMIT_CONNECTIVE + effect)
    assert findings and all('요건 확인 요청' in row.confidence_features['verdict'] for row in findings)
    row = next(row for row in trace['conclusions'] if row.get('candidate_kind') == 'FINITE_PROPOSITION' and row['is_conclusion'])
    assert row['effect_interpretation']['category'] == 'UNKNOWN'
    assert not row['effect_interpretation']['known_extension']
    assert not row['effect_interpretation']['argument']['selected_senses']
    assert row['effect_interpretation']['argument']['candidate_senses']


def test_mail_oblique_does_not_change_the_actual_legal_object(monkeypatch, tmp_path):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + FULFILLED + LIMIT_CONNECTIVE + '우편으로 행정제재를 받지 않는다.')
    assert findings and all('요건 확인 요청' in row.confidence_features['verdict'] for row in findings)
    row = next(row for row in trace['conclusions'] if row.get('effect_interpretation', {}).get('category') == 'SANCTION_RECEIPT_NEGATION')
    assert row['effect_interpretation']['argument']['role'] == 'SANCTION_DECISION'
    source = findings[0].confidence_features['claim']
    assert source[slice(*row['argument_span'])] == '행정제재'
    assert not row['effect_interpretation']['known_extension']


def test_material_object_can_have_an_authored_normative_permission(monkeypatch, tmp_path):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + FULFILLED + LIMIT_CONNECTIVE + '소포를 받지 않을 권리가 있다.')
    assert findings and all('요건 확인 요청' not in row.confidence_features['verdict'] for row in findings)
    row = next(row for row in trace['conclusions'] if row.get('effect_interpretation', {}).get('category') == 'NORMATIVE_PERMISSION')
    assert row['effect_interpretation']['normative_permission']
    assert row['effect_interpretation']['argument']['role'] == 'TRANSFER_OBJECT'


@pytest.mark.parametrize('effect', [
    '원고는 형사처벌도 면한다.', '새 당사자는 징계처분을 면한다.',
    '형사처벌도 면하지 않는다.', '행정제재를 받을 필요가 없다는 것은 아니다.',
    '형사처벌도 면하지 않습니다.', '행정제재를 면제하지 않습니다.',
    '형사처벌을 면했다.', '징계처분은 소멸하였다.',
])
def test_independent_actor_denied_embedded_and_past_facts_do_not_inherit_extension(monkeypatch, tmp_path, effect):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + FULFILLED + LIMIT_CONNECTIVE + effect)
    assert not findings, trace


@pytest.mark.parametrize('effect', ['형사처벌도 면할 수 있다.', '행정제재를 일부 면제한다.'])
def test_modal_or_partial_effect_is_verification_not_known_certainty(monkeypatch, tmp_path, effect):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + FULFILLED + LIMIT_CONNECTIVE + effect)
    assert findings and all('요건 확인 요청' in row.confidence_features['verdict'] for row in findings)
    assert any(row.get('effect_interpretation', {}).get('category') == 'UNKNOWN' for row in trace['conclusions'])


@pytest.mark.parametrize('effect', ['형사처벌도 면한다.', '징계처분은 소멸한다.'])
def test_reported_normal_does_not_hide_own_categorical_rebuttal(monkeypatch, tmp_path, effect):
    text = '상대방은 “' + LEAD + FULFILLED + LIMIT[:-1] + '”고 주장하나; ' + LEAD + FULFILLED + ' ' + effect
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings and all('요건 확인 요청' not in row.confidence_features['verdict'] for row in findings)


@pytest.mark.parametrize('effect', ['따라서 형사처벌도 면한다.', '그러므로 행정제재를 받을 필요가 없다.'])
def test_explicit_immediate_link_supports_a_current_typed_consequence(monkeypatch, tmp_path, effect):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + FULFILLED + LIMIT + ' ' + effect)
    assert findings and all('요건 확인 요청' not in row.confidence_features['verdict'] for row in findings)
    assert all('context_link' in row.confidence_features['defense_scope'] for row in findings)


@pytest.mark.parametrize('effect', ['이 사건 채무는 소멸한다.', '해당 채무를 면제한다.'])
def test_known_specific_debt_release_is_still_a_normal_limited_effect(monkeypatch, tmp_path, effect):
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + FULFILLED + ' ' + effect)
    assert not findings, trace
    assert any(row.get('limited_argument_scope') for row in trace['conclusions'])


def test_partial_effect_evidence_keeps_original_local_span(monkeypatch, tmp_path):
    text = LEAD + FULFILLED + LIMIT_CONNECTIVE + '행정제재를 일부 면제한다.'
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings
    source = findings[0].confidence_features['claim']
    row = next(row for row in trace['conclusions'] if row.get('effect_interpretation', {}).get('scope_limitations'))
    extent = row['effect_interpretation']['scope_limitations'][0]
    assert source[slice(*extent['span'])] == '일부'
    assert extent['attachment'] == 'PREDICATE_ARGUMENT'


@pytest.mark.parametrize('length', [8000, 16000, 32000])
def test_local_candidate_traversal_does_not_recheck_the_growing_prefix(monkeypatch, length):
    from packages.legal_engine import effect_propositions
    original = effect_propositions.polarity
    checked = []

    def measured(sentence, span, **kwargs):
        checked.append(len(sentence))
        return original(sentence, span, **kwargs)

    monkeypatch.setattr(effect_propositions, 'polarity', measured)
    block = '형사처벌도 면한다 '
    text = (block * (length // len(block) + 1))[:length]
    rows = effect_propositions.effect_candidates(text)
    assert len(rows) > length // (2 * len(block))
    assert sum(checked) <= len(text) * 2
    assert max(checked) <= len(block) * 2
    assert all(row['predicate_span'][1] <= len(text) for row in rows)


def test_32k_actual_txt_passes_local_units_not_document_prefixes(monkeypatch, tmp_path):
    block = LEAD + FULFILLED + ' 형사처벌도 면한다. '
    text = (block * (32000 // len(block) + 1))[:32000]
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert findings
    assert sum(len(row['unit']) for row in trace['units']) <= len(text) * 2
    assert max(len(row['unit']) for row in trace['units']) <= len(block) * 2


@pytest.mark.parametrize('requirement,argument,predicate', [
    ('전액을 지급하였으므로', '전액', '지급하였으므로'),
    ('변제공탁을 하였으므로', '변제공탁', '하였으므로'),
])
def test_embedded_and_nominal_requirement_anchors_retain_event_argument_predicate_spans(monkeypatch, tmp_path, requirement, argument, predicate):
    text = LEAD + requirement + LIMIT
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, text)
    assert not findings
    row = next(row for row in trace['requirements'] if row['state'] == 'POSITIVE')
    frame = row['event_frame']
    assert text[slice(*frame['argument_span'])] == argument
    assert text[slice(*frame['predicate_span'])] == predicate
    assert not frame['polarity_changed']


@pytest.mark.parametrize('effect', ['형사처벌도 면한다.', '제재가 소멸한다.'])
def test_pipeline_later_claim_stage_excludes_the_same_judged_source(monkeypatch, tmp_path, effect):
    from packages.verification_engine import pipeline
    original = pipeline.review_claims
    seen = []

    def measured(*args, **kwargs):
        seen.extend(kwargs.get('skip_sentences', []))
        return original(*args, **kwargs)

    monkeypatch.setattr(pipeline, 'review_claims', measured)
    findings, trace = _trace_pipeline(monkeypatch, tmp_path, LEAD + FULFILLED + LIMIT_CONNECTIVE + effect)
    assert len(findings) == 1
    assert findings[0].confidence_features['claim'] in seen
