"""Bounded first-party excerpt evidence; additive inspection, never exemption."""
from __future__ import annotations

import json
import copy
from dataclasses import fields

from packages.common.enums import LLMRole
from packages.common.source_trace import _Piece, MAX_SOURCE_CHARS, MAX_TRACE_CHARS
from .providers import LLMRequest
from .excerpt_projection import _validated_trace, occurrence_projection

_CAP = object()
_REDACTED = '<excerpt inspection source>'


class _ExcerptRequest(LLMRequest):
    """replace retains consumer identity even if inspection context is removed."""


def _leaf(user, path):
    value = json.loads(user)
    for key in path:
        value = value[key]
    return value


class _ExcerptSource:
    __slots__ = ('__consumer', '__system', '__user', '__schema', '__entries')

    def __init__(self, request, consumer, entries, *, capability):
        if capability is not _CAP:
            raise TypeError('Internal excerpt consumer required')
        for name, value in (
            ('consumer', consumer), ('system', request.system), ('user', request.user),
            ('schema', json.dumps(request.schema, sort_keys=True, ensure_ascii=False)),
            ('entries', tuple(entries)),
        ):
            object.__setattr__(self, '_ExcerptSource__' + name, value)

    def __setattr__(self, name, value):
        raise AttributeError('Immutable excerpt inspection source')

    def __delattr__(self, name):
        raise AttributeError('Immutable excerpt inspection source')

    def __repr__(self):
        return _REDACTED

    def __deepcopy__(self, memo):
        return _REDACTED

    def _matches(self, request, original_system):
        from .input_contracts import _consumer_binding
        from .router import SYSTEM_BASE
        if self.__consumer not in ('argument_review_v1', 'claim_review_v1'):
            return False
        systems, schema = _consumer_binding(self.__consumer)
        system = request.system if original_system is None else original_system
        assembled = self.__system if original_system is None else (
            f'{SYSTEM_BASE}\n[역할] {LLMRole.PRIMARY_REASONER}\n{self.__system}')
        if (request.input_contract != self.__consumer or system != self.__system
                or self.__system not in systems or request.system != assembled
                or request.user != self.__user or request.schema != schema
                or json.dumps(request.schema, sort_keys=True, ensure_ascii=False) != self.__schema):
            return False
        if (self.__consumer == 'claim_review_v1'
                and (request.metadata.get('stage') != 'claim_rag_advisory'
                     or request.metadata.get('claim_id') != json.loads(self.__user)['claim_id'])):
            return False
        return self._valid_entries() and all(self._valid_piece(path, piece) for path, piece in self.__entries)

    def _valid_entries(self):
        if type(self.__entries) is not tuple or not self.__entries:
            return False
        if any(type(entry) is not tuple or len(entry) != 2 or type(entry[0]) is not tuple
               for entry in self.__entries):
            return False
        payload = json.loads(self.__user)
        collection = 'items' if self.__consumer == 'argument_review_v1' else 'reference_sources'
        leaf = 'surrounding_context_and_claim' if collection == 'items' else 'text'
        expected = tuple((collection, index, leaf) for index in range(len(payload[collection])))
        actual = tuple(entry[0] for entry in self.__entries)
        return (actual == expected and all(tuple(type(key) for key in path) == (str, int, str)
                                          for path in actual))

    def _valid_piece(self, path, piece):
        if type(path) is not tuple or type(piece) is not _Piece:
            return False
        source, ranges, rendered, origins, status = piece._data()
        if type(rendered) is not str or _leaf(self.__user, path) != rendered:
            return False
        if status == 'CAPTURED':
            return (type(source) is str and len(source) <= MAX_SOURCE_CHARS
                    and type(origins) is tuple and len(origins) <= MAX_TRACE_CHARS
                    and _validated_trace(source, ranges, rendered, origins)[0] == 'VALID_TRACE')
        return (status in ('ABSTAIN_NO_TRACE', 'ABSTAIN_CAPTURE_LIMIT')
                and source is None and ranges is None and origins is None)

    def _project(self):
        if not self._valid_entries():
            return ('INVALID_TRACE',), ()
        statuses, matches = [], []
        for path, piece in self.__entries:
            if not self._valid_piece(path, piece):
                statuses.append('INVALID_TRACE')
                continue
            source, ranges, rendered, origins, status = piece._data()
            if status == 'CAPTURED':
                status, selected = occurrence_projection(source, ranges, rendered, origins)
                matches.extend((path, kind, value) for kind, value, _ in selected)
            statuses.append(status)
        return tuple(statuses), tuple(matches)


def _bind(request, consumer, entries):
    source = _ExcerptSource(request, consumer, entries, capability=_CAP)
    values = {field.name: getattr(request, field.name) for field in fields(LLMRequest)}
    values['schema'] = copy.deepcopy(request.schema)
    return _ExcerptRequest(**{**values, 'inspection_source': source})


def bind_argument_excerpts(request, pieces):
    return _bind(request, 'argument_review_v1', tuple(
        (('items', index, 'surrounding_context_and_claim'), piece) for index, piece in enumerate(pieces)))


def bind_claim_excerpts(request, pieces):
    return _bind(request, 'claim_review_v1', tuple(
        (('reference_sources', index, 'text'), piece) for index, piece in enumerate(pieces)))


def _rebind_review_profile(before, after):
    """Called only by the actual profile renderer after it builds new bytes."""
    if (type(before) is _ExcerptRequest and type(before.inspection_source) is _ExcerptSource
            and valid_excerpt_source(before)):
        source = before.inspection_source
        return _bind(after, 'claim_review_v1', source._ExcerptSource__entries)
    return after  # Invalid-present evidence remains attached and fails closed.


def is_excerpt_request(request):
    return type(request) is _ExcerptRequest


def valid_excerpt_source(request, *, original_system=None):
    if not isinstance(request, _ExcerptRequest):
        return type(request.inspection_source) is not _ExcerptSource
    if type(request) is not _ExcerptRequest or type(request.inspection_source) is not _ExcerptSource:
        return False
    try:
        return request.inspection_source._matches(request, original_system)
    except (AttributeError, KeyError, TypeError, ValueError, RecursionError, IndexError):
        return False


def excerpt_inspection(request):
    if type(request) is not _ExcerptRequest or type(request.inspection_source) is not _ExcerptSource:
        return (), ()
    try:
        return request.inspection_source._project()
    except (AttributeError, KeyError, TypeError, ValueError, RecursionError, IndexError):
        return ('INVALID_TRACE',), ()
