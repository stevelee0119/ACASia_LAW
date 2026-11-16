"""Request-bound immutable pseudonym token attestation; never trusts shape alone."""
from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Iterable, Optional

from packages.common.enums import LLMRole
from packages.pii_engine.pseudonym import canonical_pseudonym_token
from .providers import LLMRequest

_CAP = object()
_REDACTED = "<token attestation>"


def _user_digest(user: str) -> str:
    return hashlib.sha256(user.encode("utf-8")).hexdigest()


def _normalize_tokens(tokens: Iterable[str]) -> frozenset[str]:
    normalized = []
    for raw in tokens:
        canon = canonical_pseudonym_token(raw)
        if canon is None:
            raise ValueError("Invalid pseudonym token in attestation")
        normalized.append(canon)
    return frozenset(normalized)


class _TokenAttestation:
    """Immutable set of store-issued tokens bound to one request payload."""

    __slots__ = ("__tokens", "__user_sha256", "__system")

    def __init__(self, tokens: frozenset[str], user_sha256: str, system: str, *, capability):
        if capability is not _CAP:
            raise TypeError("Token attestation must be created via bind_masked_tokens")
        object.__setattr__(self, "_TokenAttestation__tokens", tokens)
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

    def _tokens(self) -> frozenset[str]:
        return self.__tokens

    def _matches(self, request: LLMRequest, original_system: Optional[str]) -> bool:
        from .router import SYSTEM_BASE

        if type(getattr(request, "user", None)) is not str or type(getattr(request, "system", None)) is not str:
            return False
        if _user_digest(request.user) != self.__user_sha256:
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


def bind_masked_tokens(request: LLMRequest, tokens: Iterable[str]) -> LLMRequest:
    """Bind store-issued pseudonym tokens to this exact request payload."""
    att = _TokenAttestation(
        _normalize_tokens(tokens),
        _user_digest(request.user),
        request.system,
        capability=_CAP,
    )
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


def attested_tokens_for(
    request: LLMRequest, *, original_system: Optional[str] = None,
) -> Optional[frozenset[str]]:
    """Return attested tokens if bound and valid; None if unattested; empty set if invalid."""
    att = _extract_attestation(request)
    if att is None:
        return None
    if type(att) is not _TokenAttestation:
        return frozenset()
    if valid_token_attestation(request, original_system=original_system):
        return att._tokens()
    return frozenset()


def _rebind_token_attestation(before: LLMRequest, after: LLMRequest) -> LLMRequest:
    """Internal helper used after first-party request transforms (review profile / partial split)."""
    att = _extract_attestation(before)
    if att is None:
        return after
    if type(att) is _TokenAttestation and valid_token_attestation(before):
        return bind_masked_tokens(after, att._tokens())
    return after  # Keep invalid attestation attached so inspection fails closed.
