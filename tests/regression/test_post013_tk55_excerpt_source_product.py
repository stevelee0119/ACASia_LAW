"""Bounded actual producer/renderer protections, no private fixtures."""
from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from packages.common.enums import ExternalAIPolicy, LLMRole
from packages.common.source_trace import model_input_renderer, MAX_SOURCE_CHARS, _Piece
from packages.llm_router import excerpt_source, privacy
from packages.llm_router.providers import LLMRequest
from packages.pii_engine import PIIEngine
from .test_post013_tk55_boundary_spike import _route, _historical_payload_request
from .test_post013_tk55_cascade_source_spike import PHONES, RRNS
from .test_post013_tk55_excerpt_offsets_spike import _claim, _source, enc
from .test_post013_tk55_trace_validation_spike import INVALID


VALUES = PHONES + RRNS


def argument(raw, *, excluded=(), opaque=False, items=1):
    from packages.legal_engine.argument_validity_verifier import _attach_ai_opinions
    from packages.verification_engine.sanitized_input import strip_injections
    requests = []
    pii = PIIEngine(SimpleNamespace(pseudonym_for=lambda kind, value: kind + '_SYNTHETIC'))
    hide = (lambda text: pii.mask_text(strip_injections(text, excluded)).masked_text) if opaque else (
        model_input_renderer(pii, excluded))
    class Capture:
        async def consult_all(self, role, request, **kwargs):
            requests.append(request)
            return []
    rows = [{'citation': SimpleNamespace(page=1, raw_text='합성 인용 자료'), 'context': raw}
            for _ in range(items)]
    asyncio.run(_attach_ai_opinions(SimpleNamespace(rows=[]), rows, Capture(), ExternalAIPolicy.MASKED, hide))
    return requests


def claim(raw, *, excluded=()):
    return _claim(raw, exclude=excluded[0] if excluded else None, historical_baseline=False)[0]


def produce(producer, raw, excluded=()):
    return argument(raw, excluded=excluded)[0] if producer == 'argument' else claim(raw, excluded=excluded)


@pytest.mark.parametrize('producer', ('argument', 'claim'))
@pytest.mark.parametrize('value', VALUES)
@pytest.mark.parametrize('form', ('closing_quote_outside', 'unicode_mid_escape', 'surrogate_before_phone',
                                 'duplicate', 'nested', 'deep_nested', 'mixed_masked_plain'))
def test_actual_selected_encoded_contact_stops_before_provider_and_budget(monkeypatch, producer, value, form):
    request = produce(producer, _source(value, form))
    assert excerpt_source.valid_excerpt_source(request)
    outcome, sent, reserved = _route(monkeypatch, request)
    assert sent == reserved == []
    receipt = outcome.executions[0].input_privacy
    assert receipt['failure_code'] == 'PII_INPUT_BLOCKED'
    assert receipt['excerpt_projection']['statuses'] == {'READY': 1}
    assert value not in json.dumps(receipt, ensure_ascii=False)


@pytest.mark.parametrize('producer', ('argument', 'claim'))
@pytest.mark.parametrize('value', VALUES)
@pytest.mark.parametrize('control', ('outside', 'masked', 'excluded'))
def test_actual_omitted_or_removed_contact_never_restored(monkeypatch, producer, value, control):
    if control == 'outside':
        raw, excluded = '{"body":"' + '가' * 1600 + '","slot":"' + enc(value) + '"}', ()
    elif control == 'masked':
        raw, excluded = '{"slot":"연락 ' + value + '가' * 1600 + '"}', ()
    else:
        raw, excluded = _source(value, 'closing_quote_outside'), (enc(value),)
    request = produce(producer, raw, excluded)
    outcome, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1
    assert sent[0].user == request.user
    assert outcome.executions[0].input_privacy['excerpt_projection']['statuses'] == {'READY': 1}


@pytest.mark.parametrize('producer', ('argument', 'claim'))
@pytest.mark.parametrize('phone', PHONES)
def test_p2_deleted_duplicate_cannot_borrow_surviving_longer_spelling(monkeypatch, producer, phone):
    removed = enc(phone) + ' 일반 제거 구간'
    raw = '{"slot":"' + removed + '","slot":"' + enc('99' + phone + '99') + '가' * 1600 + '"}'
    request = produce(producer, raw, (removed,))
    outcome, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1
    assert outcome.executions[0].input_privacy['detected_types'].get('PHONE', 0) == 0
    assert outcome.executions[0].input_privacy['detected_types'].get('RRN', 0) == 0


@pytest.mark.parametrize('producer', ('argument', 'claim'))
@pytest.mark.parametrize('value', ('문서함', '초록환경 관측자료', '일반 법령 검토 자료',
                                  '123-45-67890', '2024-06-18', '2022다123456'))
def test_benign_json_evidence_and_legal_numbers_remain_allowed(monkeypatch, producer, value):
    request = produce(producer, _source(value, 'closing_quote_outside'))
    _, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1


@pytest.mark.parametrize('producer', ('argument', 'claim'))
@pytest.mark.parametrize('mutation', ('user', 'system', 'schema', 'removed', 'marker', 'deepcopy', 'other_source'))
def test_invalid_present_request_binding_never_falls_back(monkeypatch, producer, mutation):
    request = produce(producer, _source('일반 자료', 'closing_quote_outside'))
    if mutation == 'user':
        request = replace(request, user=request.user + ' ')
    elif mutation == 'system':
        request = replace(request, system=request.system + ' ')
    elif mutation == 'schema':
        request = replace(request, schema={**request.schema, 'additionalProperties': False})
    elif mutation == 'removed':
        request = replace(request, inspection_source=None)
    elif mutation == 'marker':
        request = replace(request, inspection_source={'source': 'marker'})
    elif mutation == 'other_source':
        request = replace(request, inspection_source=produce(producer, _source('다른 자료', 'closing_quote_outside')).inspection_source)
    else:
        request = copy.deepcopy(request)
    outcome, sent, reserved = _route(monkeypatch, request)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'INPUT_CONTRACT_VIOLATION'


@pytest.mark.parametrize('producer', ('argument', 'claim'))
@pytest.mark.parametrize('kind', ('ranges', 'origins', 'source', 'rendered'))
def test_present_invalid_piece_shape_is_failclosed_with_pii_priority(monkeypatch, producer, kind):
    for pii in (False, True):
        request = produce(producer, _source('일반 자료', 'closing_quote_outside'))
        piece = request.inspection_source._ExcerptSource__entries[0][1]
        # Simulate corrupted internal capture, bypassing Python immutability
        # only in this public fault-injection test. No caller gets a setter.
        value = {'ranges': (('0', 1),), 'origins': [0], 'source': None, 'rendered': 'foreign'}[kind]
        object.__setattr__(piece, '_Piece__' + kind, value)
        if pii:
            request = replace(request, metadata={**request.metadata, 'contact': PHONES[0]})
        outcome, sent, reserved = _route(monkeypatch, request)
        assert sent == reserved == []
        assert outcome.executions[0].input_privacy['failure_code'] == (
            'PII_INPUT_BLOCKED' if pii else 'INPUT_CONTRACT_VIOLATION')


@pytest.mark.parametrize('producer', ('argument', 'claim'))
@pytest.mark.parametrize('mode', ('unsupported', 'capture_limit', 'work', 'decoder'))
def test_valid_projection_abstention_preserves_existing_requests(monkeypatch, producer, mode):
    from packages.llm_router import excerpt_projection as module
    raw = ('일반 자료 ' + '가' * 1600) if mode == 'unsupported' else _source('일반 자료', 'closing_quote_outside')
    if mode == 'capture_limit':
        raw = '{"slot":"' + '가' * (MAX_SOURCE_CHARS + 1) + '"}'
    request = produce(producer, raw)
    if mode in ('work', 'decoder'):
        def fail(*args):
            raise RuntimeError('Local work budget') if mode == 'work' else ValueError('Decoder failure')
        monkeypatch.setattr(module, '_validated_tokens' if mode == 'work' else '_mapped_nodes', fail)
    outcome, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1
    expected = {'unsupported': 'ABSTAIN_UNSUPPORTED', 'capture_limit': 'ABSTAIN_CAPTURE_LIMIT',
                'work': 'ABSTAIN_WORK', 'decoder': 'ABSTAIN_DECODER'}[mode]
    assert outcome.executions[0].input_privacy['excerpt_projection']['statuses'] == {expected: 1}


@pytest.mark.parametrize('value', VALUES)
def test_opaque_argument_retains_explicit_encoded_residual(monkeypatch, value):
    request = argument(_source(value, 'closing_quote_outside'), opaque=True)[0]
    outcome, sent, reserved = _route(monkeypatch, request)
    assert len(sent) == len(reserved) == 1
    assert outcome.executions[0].input_privacy['excerpt_projection']['statuses'] == {'ABSTAIN_NO_TRACE': 1}


def test_real_masker_runs_once_and_preserves_baseline_rendered_bytes(monkeypatch):
    from packages.pii_engine import engine as module
    source = _source(PHONES[0], 'mixed_masked_plain')
    expected = argument(source, opaque=True)[0]
    calls, original = [], module.detect
    def detecting(text, **kwargs):
        calls.append(text)
        return original(text, **kwargs)
    monkeypatch.setattr(module, 'detect', detecting)
    actual = argument(source)[0]
    assert calls == ['합성 인용 자료', source[:1000]]
    assert actual.user == expected.user and actual.system == expected.system
    assert actual.schema == expected.schema and actual.max_tokens == expected.max_tokens


def test_batch_and_truncated_single_retry_use_only_their_actual_item_proofs(monkeypatch):
    from packages.legal_engine.argument_validity_verifier import _retry_truncated_singly
    batch_request = argument(_source('일반 자료', 'closing_quote_outside'), items=3)[0]
    batch = json.loads(batch_request.user)['items']
    pieces = {item['item_id']: entry[1] for item, entry in zip(batch, batch_request.inspection_source._ExcerptSource__entries)}
    captured = []
    class Capture:
        async def run(self, role, request, **kwargs):
            captured.append(request)
            return SimpleNamespace(used=False, executions=[])
    reply = SimpleNamespace(used=False, executions=[SimpleNamespace(provider='anthropic', error='OUTPUT_TRUNCATED')])
    asyncio.run(_retry_truncated_singly(Capture(), [reply], batch, ExternalAIPolicy.MASKED, excerpt_pieces=pieces))
    assert len(captured) == 2
    for request in captured:
        assert excerpt_source.valid_excerpt_source(request)
        assert len(request.inspection_source._ExcerptSource__entries) == 1
        _, sent, reserved = _route(monkeypatch, request)
        assert len(sent) == len(reserved) == 1


@pytest.mark.parametrize('enabled', (False, True))
@pytest.mark.parametrize('when', (None, '2024-05-04', 'invalid-date'))
def test_actual_profile_renderer_rebinds_only_unchanged_authenticated_evidence(monkeypatch, enabled, when):
    from packages.rag_engine.review_profile import build_review_comparison_request
    request = claim(_source('일반 자료', 'closing_quote_outside'))
    profiled = build_review_comparison_request(request, korean_profile=enabled, reference_date=when)
    assert excerpt_source.valid_excerpt_source(profiled)
    _, sent, reserved = _route(monkeypatch, profiled)
    assert len(sent) == len(reserved) == 1
    changed = replace(request, user=request.user + ' ')
    invalid = build_review_comparison_request(changed, korean_profile=enabled, reference_date=when)
    assert not excerpt_source.valid_excerpt_source(invalid)
    outcome, sent, reserved = _route(monkeypatch, invalid)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'INPUT_CONTRACT_VIOLATION'


@pytest.mark.parametrize('producer', ('argument', 'claim'))
def test_source_capability_is_immutable_and_redacted_from_generic_serialization(monkeypatch, producer):
    raw = '{"body":"' + '가' * 1600 + '","omitted":"' + enc(PHONES[0]) + '"}'
    request = produce(producer, raw)
    source = request.inspection_source
    with pytest.raises(AttributeError):
        source._ExcerptSource__user = '{}'
    piece = source._ExcerptSource__entries[0][1]
    with pytest.raises(AttributeError):
        piece._Piece__source = raw + 'mutation'
    serialized = json.dumps(asdict(request), ensure_ascii=False)
    assert asdict(request)['inspection_source'] == '<excerpt inspection source>'
    assert raw not in serialized + repr(source) + repr(piece) + repr(request)
    assert enc(PHONES[0]) not in serialized
    outcome, sent, reserved = _route(monkeypatch, replace(request, max_tokens=100))
    assert len(sent) == len(reserved) == 1
    assert raw not in repr(outcome.executions[0].input_privacy)


@pytest.mark.parametrize('producer', ('argument', 'claim'))
def test_historical_helper_preserves_payload_but_never_reports_current_gate_evidence(monkeypatch, producer):
    actual = produce(producer, _source(PHONES[0], 'closing_quote_outside'))
    historical = _historical_payload_request(actual)
    assert actual.inspection_source is not None and historical.inspection_source is None
    assert type(historical) is LLMRequest
    actual_fields, historical_fields = asdict(actual), asdict(historical)
    actual_fields.pop('inspection_source')
    historical_fields.pop('inspection_source')
    assert actual_fields == historical_fields
    outcome, sent, reserved = _route(monkeypatch, actual)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'PII_INPUT_BLOCKED'
    _, sent, reserved = _route(monkeypatch, historical)
    assert len(sent) == len(reserved) == 1  # Explicit historical counterfactual only.


@pytest.mark.parametrize('producer', ('argument', 'claim'))
def test_complete_1200_deep_source_projection_does_not_raise_or_change_legacy_baseline(monkeypatch, producer):
    source = '[' * 1200 + '"자료"' + ']' * 1200
    actual = produce(producer, source)
    statuses, matches = excerpt_source.excerpt_inspection(actual)
    assert statuses == ('READY',) and matches == ()
    historical = _historical_payload_request(actual)
    before, calls_before, reservations_before = _route(monkeypatch, historical)
    after, calls_after, reservations_after = _route(monkeypatch, actual)
    assert len(calls_after) == len(calls_before)
    assert len(reservations_after) == len(reservations_before)
    if calls_after:
        assert calls_after[0].user == calls_before[0].user
    else:
        assert after.executions[0].input_privacy['reason'] == before.executions[0].input_privacy['reason'] == 'INSPECTION_FAILED'


@pytest.mark.parametrize('adapter_name', ('OpenAIProvider', 'AnthropicProvider', 'GeminiProvider', 'LocalLLMProvider'))
def test_actual_adapter_wire_never_contains_added_source(monkeypatch, caplog, adapter_name):
    import httpx
    from packages.common.config import ProviderConfig
    from packages.llm_router import providers
    raw = '{"body":"' + '가' * 1600 + '","omitted":"' + enc(PHONES[0]) + '"}'
    request = argument(raw)[0]
    bodies = []
    class Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, *, headers=None, json=None, **kwargs):
            bodies.append(json)
            return httpx.Response(200, json={'choices': [{'message': {'content': '{}'}}],
                'content': [{'type': 'text', 'text': '{}'}],
                'candidates': [{'content': {'parts': [{'text': '{}'}]}}]})
    monkeypatch.setattr(httpx, 'AsyncClient', Client)
    monkeypatch.setenv('SYNTHETIC_PROVIDER_KEY', 'synthetic')
    config = ProviderConfig(name='synthetic', enabled=True, api_key_env='SYNTHETIC_PROVIDER_KEY',
                            model='synthetic', base_url='https://synthetic.invalid',
                            kind='local' if adapter_name == 'LocalLLMProvider' else 'cloud')
    adapter = getattr(providers, adapter_name)(config)
    adapter.settings = replace(adapter.settings, allow_network=True)
    asyncio.run(adapter.generate(request))
    wire = json.dumps(bodies, ensure_ascii=False)
    assert bodies and raw not in wire and enc(PHONES[0]) not in wire and PHONES[0] not in wire
    assert 'inspection_source' not in wire and raw not in caplog.text


@pytest.mark.parametrize('producer', ('argument', 'claim'))
@pytest.mark.parametrize('case', INVALID)
@pytest.mark.parametrize('pii', (False, True))
def test_every_invalid_present_capture_variant_blocks_actual_router(monkeypatch, producer, case, pii):
    from .test_post013_tk55_trace_validation_spike import _invalid
    request = produce(producer, _source('일반 자료', 'closing_quote_outside'))
    piece = request.inspection_source._ExcerptSource__entries[0][1]
    raw, ranges, rendered, origins, _ = piece._data()
    _, raw, ranges, rendered, origins = _invalid((request, raw, ranges, rendered, origins), case)
    for name, value in (('source', raw), ('ranges', ranges), ('rendered', rendered), ('origins', origins)):
        object.__setattr__(piece, '_Piece__' + name, value)
    if pii:
        request = replace(request, metadata={**request.metadata, 'contact': PHONES[0]})
    outcome, sent, reserved = _route(monkeypatch, request)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == (
        'PII_INPUT_BLOCKED' if pii else 'INPUT_CONTRACT_VIOLATION')


@pytest.mark.parametrize('mutation', ('omitted_item', 'duplicate_path', 'bool_path', 'swapped_items'))
def test_batch_proof_collection_is_complete_and_bound_to_exact_item_indices(monkeypatch, mutation):
    request = argument(_source('일반 자료', 'closing_quote_outside'), items=2)[0]
    source = request.inspection_source
    entries = source._ExcerptSource__entries
    if mutation == 'omitted_item':
        entries = entries[:1]
    elif mutation == 'duplicate_path':
        entries = (entries[0], entries[0])
    elif mutation == 'bool_path':
        entries = ((('items', False, 'surrounding_context_and_claim'), entries[0][1]), entries[1])
    else:
        entries = entries[::-1]
    object.__setattr__(source, '_ExcerptSource__entries', entries)
    outcome, sent, reserved = _route(monkeypatch, request)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'INPUT_CONTRACT_VIOLATION'


@pytest.mark.parametrize('value', VALUES)
def test_actual_claim_selected_start_inside_literal_is_protected(monkeypatch, value):
    raw = '{"slot":"' + '가' * 600 + enc(value) + '표식단어' + '나' * 1600 + '"}'
    request, _, ranges, _ = _claim(raw, historical_baseline=False)
    assert ranges[0][0] > 0
    outcome, sent, reserved = _route(monkeypatch, request)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'PII_INPUT_BLOCKED'


def test_trace_work_capture_limit_abstains_before_allocating_large_insertions(monkeypatch):
    from packages.common.source_trace import _EditTrace, MAX_TRACE_CHARS
    trace = _EditTrace('資料', 0, 2)
    trace.replace(0, 1, MAX_TRACE_CHARS + 1)
    trace.keep(0, 1)
    trace.insert(MAX_TRACE_CHARS + 1)
    trace.finish_mask()
    assert trace.exhausted and trace.origins == () and trace.parts == []
    assert trace.seal('資料')._data() == (None, None, '資料', None, 'ABSTAIN_CAPTURE_LIMIT')


def test_output_schema_mutation_never_mutates_consumer_constant(monkeypatch):
    from packages.legal_engine.argument_validity_verifier import _OPINION_SCHEMA
    before = copy.deepcopy(_OPINION_SCHEMA)
    request = argument(_source('일반 자료', 'closing_quote_outside'))[0]
    request.schema['additionalProperties'] = False
    assert _OPINION_SCHEMA == before
    outcome, sent, reserved = _route(monkeypatch, request)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'INPUT_CONTRACT_VIOLATION'
