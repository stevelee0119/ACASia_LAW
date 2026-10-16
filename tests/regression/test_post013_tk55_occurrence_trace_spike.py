"""Historical privatecap-free P2 comparison, not current product gate evidence."""
from __future__ import annotations

import asyncio
import copy
import json
import sys
from dataclasses import asdict, dataclass, replace
from types import SimpleNamespace

import pytest

from packages.common.enums import ExternalAIPolicy
from packages.llm_router import privacy
from packages.llm_router.providers import LLMRequest
from packages.pii_engine import PIIEngine
from packages.pii_engine.detector import detect
from .post013_occurrence_projection import occurrence_projection, _validated_tokens
from .post013_trace_rendering import Snapshot, TracedText, source_text, strip_once, mask_once
from .test_post013_tk55_boundary_spike import _route, _historical_payload_request
from .test_post013_tk55_cascade_source_spike import PHONES, RRNS
from .test_post013_tk55_excerpt_offsets_spike import _claim, _argument, _source, enc
from .post013_excerpt_projection import projected_numeric_matches


VALUES = PHONES + RRNS


def _traced_argument(raw, *, excluded=()):
    from packages.legal_engine.argument_validity_verifier import _attach_ai_opinions
    captured, rendered_traces, mask_calls = [], [], []
    snapshot = Snapshot(raw)

    class Engine(PIIEngine):
        def mask_text(self, text, **kwargs):
            if type(text) is TracedText:
                mask_calls.append(True)
            return super().mask_text(text, **kwargs)

    pii = Engine(SimpleNamespace(pseudonym_for=lambda kind, value: kind + '_SYNTHETIC'))

    def hide(text):
        if type(text) is TracedText:
            output = mask_once(pii, strip_once(text, excluded))
            rendered_traces.append(output)
            return output
        return pii.mask_text(text).masked_text

    class Capture:
        async def consult_all(self, role, request, **kwargs):
            captured.append(request)
            return []

    # The actual producer performs the cut on the same owned snapshot; the
    # callback recognizes type/capability, never source text/marker spelling.
    item = {'citation': SimpleNamespace(page=1, raw_text='합성 인용 자료'), 'context': source_text(snapshot)}
    asyncio.run(_attach_ai_opinions(SimpleNamespace(rows=[]), [item], Capture(), ExternalAIPolicy.MASKED, hide))
    assert len(rendered_traces) == len(mask_calls) == 1
    request, trace = captured[0], rendered_traces[0]
    rendered = json.loads(request.user)['items'][0]['surrounding_context_and_claim']
    assert rendered == str(trace)
    owner, origins = trace._evidence()
    assert owner is snapshot
    return _historical_payload_request(request), owner._value(), ((0, min(1000, len(raw))),), rendered, origins


def _claim_slice(raw, *, excluded=(), claim='표식단어'):
    request, source, ranges, rendered = _claim(raw, exclude=excluded[0] if excluded else None, claim=claim)
    # This is the actual post-mask source and actual selected slice, not an
    # alignment to the pre-mask original. No removed plaintext is available.
    origins = tuple(range(ranges[0][0], ranges[0][1]))
    return request, source, ranges, rendered, origins


def _compare(monkeypatch, evidence, *, candidate=None):
    request, source, ranges, rendered, origins = evidence
    baseline = privacy.inspect_request
    expected = (request.system, request.user, json.dumps(request.schema, sort_keys=True, ensure_ascii=False))
    payload = json.loads(request.user)
    actual_leaf = (payload['items'][0]['surrounding_context_and_claim']
                   if request.input_contract == 'argument_review_v1'
                   else payload['reference_sources'][0]['text'])
    if rendered != actual_leaf:
        status, matches = 'INVALID_TRACE', ()
    else:
        status, matches = occurrence_projection(source, ranges, rendered, origins)
    projection = json.dumps([value for _, value, _ in matches], ensure_ascii=False)

    def inspect(actual, *, _original_system=None):
        report = baseline(actual, _original_system=_original_system)
        if report['status'] == 'BLOCKED':
            return report
        extra = baseline(LLMRequest(system='', user=projection))
        if extra['status'] == 'BLOCKED':
            return extra
        if (status == 'INVALID_TRACE' or actual.user != expected[1] or _original_system != expected[0]
                or json.dumps(actual.schema, sort_keys=True, ensure_ascii=False) != expected[2]):
            return {**report, 'status': 'BLOCKED', 'failure_code': 'INPUT_CONTRACT_VIOLATION'}
        return report

    with monkeypatch.context() as scoped:
        scoped.setattr(privacy, 'inspect_request', inspect)
        outcome, sent, reserved = _route(scoped, request if candidate is None else candidate)
    return status, matches, outcome, sent, reserved


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('traced_argument', 'claim_slice'))
@pytest.mark.parametrize('value', VALUES)
@pytest.mark.parametrize('form', ('closing_quote_outside', 'unicode_mid_escape', 'surrogate_before_phone',
                                 'duplicate', 'nested', 'deep_nested', 'mixed_masked_plain'))
def test_actual_once_rendered_selected_numeric_is_blocked(monkeypatch, producer, value, form):
    evidence = producer(_source(value, form))
    _, sent, reserved = _route(monkeypatch, evidence[0])
    assert len(sent) == len(reserved) == 1
    status, matches, outcome, compared, reservations = _compare(monkeypatch, evidence)
    assert status == 'READY' and matches
    assert compared == reservations == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'PII_INPUT_BLOCKED'


@pytest.mark.parametrize('phone', PHONES)
def test_removed_occurrence_cannot_borrow_equal_escape_in_long_numeric_value(monkeypatch, phone):
    excluded = enc(phone) + ' 일반 제거 구간'
    longer_numeric = '99' + phone + '99'
    assert not any(match.kind in ('PHONE', 'RRN') for match in detect(longer_numeric))
    source = '{"slot":"' + excluded + '","slot":"' + enc(longer_numeric) + '가' * 1600 + '"}'
    for producer in (_traced_argument, _claim_slice):
        evidence = producer(source, excluded=(excluded,))
        request, inspected, ranges, rendered, origins = evidence
        # An equal spelling still exists, but it belongs to a different
        # occurrence that the unchanged detector does not call PHONE/RRN.
        assert enc(phone) in rendered and excluded not in rendered
        if producer is _traced_argument:
            assert projected_numeric_matches(inspected, ranges, rendered)  # Reproduce old P2.
        else:
            assert projected_numeric_matches(inspected, ranges, rendered) == ()
        _, sent, reserved = _route(monkeypatch, request)
        status, matches, _, compared, reservations = _compare(monkeypatch, evidence)
        assert status == 'READY' and matches == ()
        assert len(sent) == len(reserved) == len(compared) == len(reservations) == 1
        assert compared[0].user == sent[0].user == request.user


@pytest.mark.parametrize('value', VALUES)
def test_opaque_argument_masks_abstain_and_retain_explicit_mandatory_residual(monkeypatch, value):
    request, source, ranges, rendered = _argument(_source(value, 'closing_quote_outside'))
    status, matches, _, sent, reserved = _compare(monkeypatch, (request, source, ranges, rendered, None))
    assert status == 'ABSTAIN_NO_TRACE' and matches == ()
    assert len(sent) == len(reserved) == 1  # Residual, not closure or acceptance.


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
@pytest.mark.parametrize('value', VALUES)
@pytest.mark.parametrize('control', ('outside', 'already_masked', 'excluded'))
def test_actual_deleted_masked_or_omitted_units_have_no_owner(monkeypatch, producer, value, control):
    if control == 'outside':
        source, excluded = '{"body":"' + '가' * 1600 + '","slot":"' + enc(value) + '"}', ()
    elif control == 'already_masked':
        source, excluded = '{"slot":"연락 ' + value + ' ' + '가' * 1600 + '"}', ()
    else:
        source, excluded = '{"slot":"' + enc(value) + '가' * 1600 + '"}', (enc(value),)
    evidence = producer(source, excluded=excluded)
    assert value not in evidence[3] and enc(value) not in evidence[3]
    _, sent, reserved = _route(monkeypatch, evidence[0])
    status, matches, _, compared, reservations = _compare(monkeypatch, evidence)
    assert status == 'READY' and matches == ()
    assert len(sent) == len(reserved) == len(compared) == len(reservations) == 1
    assert compared[0].user == sent[0].user


@pytest.mark.parametrize('value', VALUES)
def test_actual_claim_slice_starts_inside_owned_literal(monkeypatch, value):
    source = '{"slot":"' + '가' * 600 + enc(value) + '표식단어' + '나' * 1600 + '"}'
    evidence = _claim_slice(source)
    assert evidence[2][0][0] > source.index(':') + 2
    status, matches, _, sent, reserved = _compare(monkeypatch, evidence)
    assert status == 'READY' and matches
    assert sent == reserved == []


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
@pytest.mark.parametrize('value', ('문서함', '초록환경 관측자료', '일반 법령 검토 자료',
                                  '123-45-67890', '2024-06-18', '2022다123456'))
def test_actual_benign_and_legal_numeric_payloads_are_unchanged(monkeypatch, producer, value):
    evidence = producer(_source(value, 'closing_quote_outside'))
    _, sent, reserved = _route(monkeypatch, evidence[0])
    status, matches, _, compared, reservations = _compare(monkeypatch, evidence)
    assert status == 'READY' and matches == ()
    assert len(sent) == len(reserved) == len(compared) == len(reservations) == 1
    assert compared[0].user == sent[0].user


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
@pytest.mark.parametrize('recursion_limit', (1000, 3000), ids=('ordinary_python_limit', 'pytest_limit'))
def test_complete_1200_deep_source_does_not_change_final_request_baseline(monkeypatch, producer, recursion_limit):
    source = '[' * 1200 + '"자료"' + ']' * 1200
    previous_limit = sys.getrecursionlimit()
    try:
        # Resource-environment comparison only; baseline and proposal run at
        # the same limit. No product parser/PII threshold is changed.
        sys.setrecursionlimit(recursion_limit)
        evidence = producer(source)
        before, sent, reserved = _route(monkeypatch, evidence[0])
        status, matches, after, compared, reservations = _compare(monkeypatch, evidence)
        try:
            privacy._try_json_parse(source)
            old_extra_parser = 'READY'
        except RecursionError:
            old_extra_parser = 'RECURSION_ERROR'
    finally:
        sys.setrecursionlimit(previous_limit)
    assert status == 'READY' and matches == ()
    assert len(compared) == len(sent) and len(reservations) == len(reserved)
    if producer is _claim_slice:
        assert len(sent) == len(reserved) == 1
    elif not sent:
        # The existing final-leaf parser fails closed before dispatch; the
        # new extra decoder neither raises nor relabels that old behavior.
        assert sent == reserved == []
        assert before.executions[0].input_privacy['reason'] == 'INSPECTION_FAILED'
        assert after.executions[0].input_privacy == before.executions[0].input_privacy
    else:
        assert len(sent) == len(reserved) == 1
    # Python's JSON recursion budget differs by interpreter. The evaluator's
    # Python 3.11 RecursionError remains recorded; Python 3.12 may accept this
    # same source. Additional projection must preserve the observed baseline.
    assert old_extra_parser in ('READY', 'RECURSION_ERROR')


@pytest.mark.parametrize('source', ('{"x":}', '{"x":"\\uZZZZ"}', '[1,]', 'untyped prose', 'NaN'))
def test_unsupported_complete_source_abstains_without_an_exception(source):
    status, matches = occurrence_projection(source, ((0, len(source)),), source, tuple(range(len(source))))
    assert status == 'ABSTAIN_UNSUPPORTED' and matches == ()


def test_iterative_json_validator_accepts_deep_and_rejects_incomplete_structure():
    assert _validated_tokens('[' * 1200 + '0' + ']' * 1200) == ()
    with pytest.raises(ValueError):
        _validated_tokens('[' * 1200 + '0' + ']' * 1199)


def test_source_and_actual_strip_mask_trace_are_immutable_redacted_and_same_snapshot():
    from packages.verification_engine.sanitized_input import PLACEHOLDER
    snapshot = Snapshot('연락 ' + PHONES[0] + ' 제거 구간 자료')
    owned = source_text(snapshot)
    stripped = strip_once(owned, ('제거 구간',))
    assert PLACEHOLDER in str(stripped)
    pii = PIIEngine(SimpleNamespace(pseudonym_for=lambda kind, value: kind + '_SYNTHETIC'))
    actual = mask_once(pii, stripped)
    owner, origins = actual._evidence()
    assert owner is snapshot
    assert any(index is None for index in origins)
    for output, origin in enumerate(origins):
        if origin is not None:
            assert str(actual)[output] == snapshot._value()[origin]
    with pytest.raises(AttributeError):
        snapshot._Snapshot__text = 'mutated'
    with pytest.raises(AttributeError):
        actual._TracedText__origins = ()
    with pytest.raises(AttributeError):
        del actual._TracedText__snapshot
    with pytest.raises(ValueError):
        actual + source_text(Snapshot(snapshot._value()))
    with pytest.raises(TypeError):
        TracedText('marker', snapshot, (), capability=object())
    @dataclass
    class Holder:
        trace: object
    assert asdict(Holder(snapshot)) == {'trace': '<source snapshot>'}
    assert asdict(Holder(actual)) == {'trace': '<source trace>'}
    assert copy.deepcopy(actual) == '<source trace>'
    assert snapshot._value() not in repr(actual) + repr(snapshot)


@pytest.mark.parametrize('invalid', ('length', 'source_index', 'reordered', 'copied_occurrence'))
def test_invalid_positional_evidence_is_not_reinterpreted_as_a_text_match(invalid):
    source = '{"x":"' + enc(PHONES[0]) + '"}'
    origins = list(range(len(source)))
    if invalid == 'length':
        origins.pop()
    elif invalid == 'source_index':
        origins[0] = len(source)
    elif invalid == 'reordered':
        origins.reverse()
    else:
        origins[2] = origins[1]
    status, matches = occurrence_projection(source, ((0, len(source)),), source, tuple(origins))
    assert status == 'INVALID_TRACE' and matches == ()


@pytest.mark.parametrize('value', VALUES)
@pytest.mark.parametrize('part', ('escape_cut', 'escape_start', 'surrogate_cut', 'discontinuous'))
def test_atomic_trace_does_not_restore_omitted_escape_units_or_join_gaps(value, part):
    source = '{"slot":"' + enc(value) + '\\ud83d\\ude00' + ' 가' * 30 + '"}'
    begin, last = source.index(enc(value)), source.index(enc(value)) + len(enc(value))
    if part == 'escape_cut':
        ranges = ((0, last - 1),)
    elif part == 'escape_start':
        ranges = ((begin + 1, last),)
    elif part == 'surrogate_cut':
        ranges = ((0, last + 6),)
    else:
        ranges = ((begin, begin + 18), (begin + 24, last))
    origins = tuple(index for start, end in ranges for index in range(start, end))
    rendered = ''.join(source[index] for index in origins)
    status, matches = occurrence_projection(source, ranges, rendered, origins)
    assert status == 'READY'
    if part == 'escape_cut':
        expected = [(m.kind, m.text) for m in detect(value[:-1])
                    if m.kind in ('PHONE', 'RRN') and m.confidence >= 0.6]
        assert [(kind, text) for kind, text, _ in matches] == expected
        assert all(text != value and text in value[:-1] for _, text, _ in matches)
    else:
        assert bool(matches) == (part == 'surrogate_cut')


@pytest.mark.parametrize('value', VALUES)
def test_discontinuous_trace_preserves_two_complete_independent_occurrences(value):
    source = '{"a":"' + enc(value) + '","b":"' + '가' * 30 + '","a":"' + enc(value) + '"}'
    first, second = source.index(enc(value)), source.rindex(enc(value))
    ranges = ((first, first + len(enc(value))), (second, second + len(enc(value))))
    origins = tuple(index for start, end in ranges for index in range(start, end))
    rendered = ''.join(source[index] for index in origins)
    status, matches = occurrence_projection(source, ranges, rendered, origins)
    assert status == 'READY' and len(matches) == 2
    assert [item[2] for item in matches] == list(ranges)


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
@pytest.mark.parametrize('position', ('user', 'system', 'schema'))
def test_exact_trace_request_binding_rejects_replace_without_legacy_fallback(monkeypatch, producer, position):
    evidence = producer(_source('일반 법령 검토 자료', 'closing_quote_outside'))
    request = evidence[0]
    if position == 'user':
        changed = replace(request, user=request.user + ' ')
    elif position == 'system':
        changed = replace(request, system=request.system + ' ')
    else:
        changed = replace(request, schema={**request.schema, 'additionalProperties': False})
    _, _, outcome, sent, reserved = _compare(monkeypatch, evidence, candidate=changed)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'INPUT_CONTRACT_VIOLATION'


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
@pytest.mark.parametrize('position', ('user', 'system', 'schema', 'metadata', 'projection'))
def test_existing_pii_precedence_survives_invalid_trace_binding(monkeypatch, producer, position):
    evidence = producer(_source(PHONES[0] if position == 'projection' else '일반 자료', 'closing_quote_outside'))
    request = evidence[0]
    if position in ('user', 'projection'):
        changed = replace(request, user=request.user + (' ' if position == 'projection' else PHONES[1]))
    elif position == 'system':
        changed = replace(request, system=PHONES[1])
    elif position == 'schema':
        changed = replace(request, schema={'dynamic': PHONES[1]})
    else:
        changed = replace(request, metadata={**request.metadata, 'dynamic': PHONES[1]})
    _, _, outcome, sent, reserved = _compare(monkeypatch, evidence, candidate=changed)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'PII_INPUT_BLOCKED'


@pytest.mark.parametrize('value', VALUES)
@pytest.mark.parametrize('form', ('closing_quote_outside', 'mixed_masked_plain', 'duplicate'))
def test_actual_once_argument_renderer_preserves_opaque_baseline_bytes(value, form):
    source = _source(value, form)
    baseline, _, _, rendered = _argument(source)
    traced, _, _, traced_rendered, _ = _traced_argument(source)
    # These are independent baseline/proposal executions. Authentication uses
    # only the proposal's one execution events, never this comparison.
    assert traced_rendered == rendered
    assert (traced.system, traced.user, traced.schema, traced.metadata,
            traced.temperature, traced.max_tokens, traced.input_contract) == (
        baseline.system, baseline.user, baseline.schema, baseline.metadata,
        baseline.temperature, baseline.max_tokens, baseline.input_contract)


def test_no_extra_allocation_or_detection_replay_in_actual_mask_edit_trace(monkeypatch):
    from packages.pii_engine import engine as module
    source = '연락 ' + PHONES[0] + ' 자료 ' + RRNS[0] + ' 끝'
    snapshot, calls, tokens = Snapshot(source), [], []
    original = module.detect
    def detecting(actual, **kwargs):
        calls.append(str(actual))
        return original(actual, **kwargs)
    def token(kind, value):
        tokens.append((kind, value))
        return kind + '_SYNTHETIC'
    monkeypatch.setattr(module, 'detect', detecting)
    result = mask_once(PIIEngine(SimpleNamespace(pseudonym_for=token)), source_text(snapshot))
    assert calls == [source] and len(tokens) == 2
    owner, origins = result._evidence()
    assert owner is snapshot
    for value in VALUES[:1] + RRNS[:1]:
        start = source.index(value)
        assert not set(range(start, start + len(value))).intersection(index for index in origins if index is not None)


def test_snapshot_capture_is_separate_from_mutable_source_container():
    original = {'context': '합성 원문'}
    snapshot = Snapshot(original['context'])
    traced = source_text(snapshot)
    original['context'] = '이후 교체'
    assert snapshot._value() == str(traced) == '합성 원문'
    owner, origins = traced._evidence()
    assert owner is snapshot and origins == tuple(range(len(str(traced))))


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
@pytest.mark.parametrize('value', VALUES)
def test_masked_duplicate_value_cannot_hide_selected_second_occurrence(monkeypatch, producer, value):
    source = '{"slot":"연락 ' + value + '","slot":"' + enc(value) + '가' * 1600 + '"}'
    evidence = producer(source)
    assert value not in evidence[3] and enc(value) in evidence[3]
    status, matches, outcome, sent, reserved = _compare(monkeypatch, evidence)
    assert status == 'READY' and any(match[1] == value for match in matches)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'PII_INPUT_BLOCKED'


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
def test_retry_replace_retains_same_trace_without_cross_request_reuse(monkeypatch, producer):
    evidence = producer(_source('일반 법령 검토 자료', 'closing_quote_outside'))
    request = evidence[0]
    retry = replace(request, max_tokens=request.max_tokens + 1)
    status, matches, outcome, sent, reserved = _compare(monkeypatch, evidence, candidate=retry)
    assert status == 'READY' and matches == ()
    assert len(sent) == len(reserved) == 1
    other = producer(_source('다른 일반 자료', 'closing_quote_outside'))[0]
    _, _, outcome, sent, reserved = _compare(monkeypatch, evidence, candidate=other)
    assert sent == reserved == []
    assert outcome.executions[0].input_privacy['failure_code'] == 'INPUT_CONTRACT_VIOLATION'


def test_encoded_layer_work_exhaustion_abstains_without_changing_legacy_request(monkeypatch):
    source = '0'
    for _ in range(14):
        source = json.dumps(source)
    status, matches = occurrence_projection(source, ((0, len(source)),), source, tuple(range(len(source))))
    # Encoding grows exponentially, so all decoded layers together remain
    # under the proportional budget. Ordinary deeper structures never recurse.
    assert status == 'READY' and matches == ()
    from . import post013_occurrence_projection as projection
    def exhausted(text):
        raise RuntimeError('Synthetic local decoder work exhaustion')
    monkeypatch.setattr(projection, '_validated_tokens', exhausted)
    benign = '{"body":"일반 자료"}'
    status, matches = occurrence_projection(benign, ((0, len(benign)),), benign, tuple(range(len(benign))))
    assert status == 'ABSTAIN_WORK' and matches == ()


@pytest.mark.parametrize('producer', (_traced_argument, _claim_slice), ids=('argument', 'claim'))
def test_source_snapshot_does_not_enter_request_wire_repr_or_receipt(monkeypatch, producer):
    source = '{"body":"' + '가' * 1600 + '","omitted":"' + enc(PHONES[0]) + '"}'
    evidence = producer(source)
    _, _, outcome, sent, reserved = _compare(monkeypatch, evidence)
    assert len(sent) == len(reserved) == 1
    wire = json.dumps(asdict(sent[0]), ensure_ascii=False, default=str)
    receipt = repr(outcome.executions[0].input_privacy)
    assert source not in wire + receipt + repr(evidence[0])
    assert enc(PHONES[0]) not in wire + receipt + repr(evidence[0])
    assert PHONES[0] not in wire + receipt + repr(evidence[0])
