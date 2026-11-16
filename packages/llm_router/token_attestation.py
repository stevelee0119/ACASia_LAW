"""Request-bound immutable pseudonym token attestation; never trusts shape or name alone."""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType
from typing import Any, Optional, Tuple

from packages.common.enums import LLMRole
from packages.pii_engine.pseudonym import canonical_pseudonym_token
from .providers import LLMRequest

_CAP = object()
_REDACTED = "<token attestation>"
TokenSpan = Tuple[int, int, str]


def _text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_field_provenance(
    provenance: Mapping[str, Any],
) -> MappingProxyType[str, Tuple[str, frozenset[TokenSpan]]]:
    if not isinstance(provenance, Mapping):
        raise TypeError("Token attestation requires a mapping of field_path -> (text, token_spans)")
    normalized: dict[str, Tuple[str, frozenset[TokenSpan]]] = {}
    for field_path, spec in provenance.items():
        if type(field_path) is not str or not field_path:
            raise ValueError("Invalid field path in token attestation")
        if hasattr(spec, "masked_text") and hasattr(spec, "token_spans"):
            field_text = spec.masked_text
            raw_spans = spec.token_spans
        elif isinstance(spec, tuple) and len(spec) == 2:
            field_text, raw_spans = spec
        else:
            raise TypeError("Field provenance must be MaskResult or (text, token_spans)")
        if type(field_text) is not str:
            raise TypeError("Attested field text must be plain str")
        spans: list[TokenSpan] = []
        for entry in raw_spans:
            if not isinstance(entry, tuple) or len(entry) != 3:
                raise ValueError("Invalid token span entry in attestation")
            ts, te, raw_token = entry
            if type(ts) is not int or type(te) is not int or ts < 0 or te <= ts or te > len(field_text):
                raise ValueError("Token span bounds out of range in attestation")
            canon = canonical_pseudonym_token(raw_token, bracketed=False)
            if canon is None:
                raise ValueError("Invalid pseudonym token in attestation")
            if field_text[ts:te] != f"[{canon}]":
                raise ValueError("Attested token span does not match field text")
            spans.append((ts, te, canon))
        normalized[field_path] = (_text_digest(field_text), frozenset(spans))
    return MappingProxyType(normalized)


class _TokenAttestation:
    """Immutable per-field, per-occurrence token provenance bound to one request payload."""

    __slots__ = ("__fields", "__user_sha256", "__system")

    def __init__(
        self,
        fields: MappingProxyType[str, Tuple[str, frozenset[TokenSpan]]],
        user_sha256: str,
        system: str,
        *,
        capability,
    ):
        if capability is not _CAP:
            raise TypeError("Token attestation must be created via bind_masked_tokens")
        object.__setattr__(self, "_TokenAttestation__fields", fields)
        object.__setattr__(self, "_TokenAttestation__user_sha256", user_sha256)
        object.__setattr__(self, "_TokenAttestation__system", system)

    def __setattr__(self, name, value):
        raise AttributeError("Token attestation is immutable")

    def __delattr__(self, name):
        raise AttributeError("Token attestation is immutable")

    def __repr__(self) -> str:
        return _REDACTED

    def __deepcopy__(self, memo) -> str:
        return _REDACTED

    def _field_provenance(self) -> MappingProxyType[str, Tuple[str, frozenset[TokenSpan]]]:
        return self.__fields

    def _spans_for(self, field_path: str, text: str) -> frozenset[TokenSpan]:
        if type(field_path) is not str or type(text) is not str:
            return frozenset()
        entry = self.__fields.get(field_path)
        if entry is None:
            return frozenset()
        expected_digest, spans = entry
        if _text_digest(text) != expected_digest:
            return frozenset()
        return spans

    def _matches(self, request: LLMRequest, original_system: Optional[str]) -> bool:
        from .router import SYSTEM_BASE

        if type(getattr(request, "user", None)) is not str or type(getattr(request, "system", None)) is not str:
            return False
        if _text_digest(request.user) != self.__user_sha256:
            return False
        orig_sys = request.system if original_system is None else original_system
        if orig_sys != self.__system:
            return False
        if original_system is not None:
            prefix = f"{SYSTEM_BASE}\n[역할] "
            if not request.system.startswith(prefix):
                return False
            rest = request.system[len(prefix):]
            parts = rest.split("\n", 1)
            if len(parts) != 2 or parts[1] != self.__system:
                return False
            valid_roles = {str(r) for r in LLMRole} | {r.value for r in LLMRole}
            if parts[0] not in valid_roles:
                return False
        return True


def _extract_attestation(request: LLMRequest):
    source = getattr(request, "inspection_source", None)
    if type(source) is _TokenAttestation:
        return source
    from .excerpt_source import _ExcerptSource
    from .cascade_source import _CascadeSource

    if type(source) in (_ExcerptSource, _CascadeSource):
        try:
            return source._token_attestation()
        except AttributeError:
            return None
    return None


def _attach_attestation(request: LLMRequest, att: _TokenAttestation) -> LLMRequest:
    source = getattr(request, "inspection_source", None)
    if source is None or type(source) is _TokenAttestation:
        return replace(request, inspection_source=att)
    from .excerpt_source import _ExcerptSource, _with_excerpt_attestation
    from .cascade_source import _CascadeSource, _with_cascade_attestation

    if type(source) is _ExcerptSource:
        return replace(request, inspection_source=_with_excerpt_attestation(source, att))
    if type(source) is _CascadeSource:
        return replace(request, inspection_source=_with_cascade_attestation(source, att))
    raise TypeError("Cannot attach token attestation over unknown inspection_source")


def bind_masked_tokens(request: LLMRequest, provenance: Mapping[str, Any]) -> LLMRequest:
    """Bind per-field, per-occurrence store-issued token provenance to this exact request."""
    if type(getattr(request, "user", None)) is not str or type(getattr(request, "system", None)) is not str:
        raise TypeError("Request user and system must be plain str")
    att = _TokenAttestation(
        _normalize_field_provenance(provenance),
        _text_digest(request.user),
        request.system,
        capability=_CAP,
    )
    return _attach_attestation(request, att)


def has_token_attestation(request: LLMRequest) -> bool:
    return _extract_attestation(request) is not None


def valid_token_attestation(request: LLMRequest, *, original_system: Optional[str] = None) -> bool:
    att = _extract_attestation(request)
    if att is None:
        return True
    if type(att) is not _TokenAttestation:
        return False
    try:
        return att._matches(request, original_system)
    except (AttributeError, TypeError, ValueError):
        return False


def attested_spans_for(
    request: LLMRequest,
    field_path: str,
    text: str,
    *,
    original_system: Optional[str] = None,
) -> Optional[frozenset[TokenSpan]]:
    """Return attested token spans for this exact field path and text; None if unattested."""
    att = _extract_attestation(request)
    if att is None:
        return None
    if type(att) is not _TokenAttestation:
        return frozenset()
    if valid_token_attestation(request, original_system=original_system):
        return att._spans_for(field_path, text)
    return frozenset()


def _rebind_token_attestation(
    before: LLMRequest,
    after: LLMRequest,
    *,
    item_index_map: Optional[Mapping[int, int]] = None,
) -> LLMRequest:
    """Internal helper used after first-party request transforms (review profile / partial split)."""
    att = _extract_attestation(before)
    if att is None:
        return after
    if type(att) is _TokenAttestation and valid_token_attestation(before):
        if type(getattr(after, "user", None)) is not str or type(getattr(after, "system", None)) is not str:
            return after
        fields = att._field_provenance()
        if item_index_map is not None:
            remapped: dict[str, Tuple[str, frozenset[TokenSpan]]] = {}
            for path, entry in fields.items():
                if path.startswith("user.items["):
                    end_bracket = path.find("]", 11)
                    if end_bracket != -1 and path[11:end_bracket].isdigit():
                        orig_idx = int(path[11:end_bracket])
                        if orig_idx in item_index_map:
                            new_path = f"user.items[{item_index_map[orig_idx]}]{path[end_bracket + 1:]}"
                            remapped[new_path] = entry
                        continue
                remapped[path] = entry
            fields = MappingProxyType(remapped)
        new_att = _TokenAttestation(fields, _text_digest(after.user), after.system, capability=_CAP)
        return _attach_attestation(after, new_att)
    return after  # Keep invalid attestation attached so inspection fails closed.
