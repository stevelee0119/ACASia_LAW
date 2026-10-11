"""Request-local immutable source for cascade inspection; never a PII exemption."""
from __future__ import annotations

import json
from types import MappingProxyType

from packages.common.enums import LLMRole
from .providers import LLMRequest


_STAGES = MappingProxyType({
    "primary": (LLMRole.PRIMARY_REASONER,
                "공식 Source와 문서를 대조해 판단하고 근거를 제시하라. JSON으로만 답하라."),
    "critic": (LLMRole.INDEPENDENT_CRITIC,
               "1차 판단이 틀렸다고 가정하고 반증하라. 반증 근거가 없으면 없다고 답하라. "
               "새로운 판례나 문헌을 지어내지 마라. JSON으로만 답하라."),
    "grounder": (LLMRole.WEB_GROUNDER,
                 "공개 자료를 근거로 사실관계만 확인하라. 확인되지 않으면 UNVERIFIED로 답하라. JSON으로만 답하라."),
})
_CAPABILITY = object()
_REDACTED = "<cascade inspection source>"


class _CascadeRequest(LLMRequest):
    """Consumer identity survives replace even if someone strips its context."""


class _CascadeSource:
    # Only immutable strings are retained; no caller-owned dictionary survives.
    __slots__ = ("__stage", "__snapshot", "__schema")

    def __init__(self, stage, snapshot, schema, *, capability):
        if capability is not _CAPABILITY:
            raise TypeError("Source must be constructed by the cascade consumer")
        object.__setattr__(self, "_CascadeSource__stage", stage)
        object.__setattr__(self, "_CascadeSource__snapshot", snapshot)
        object.__setattr__(self, "_CascadeSource__schema", schema)

    def __setattr__(self, name, value):
        raise AttributeError("Cascade inspection source is immutable")

    def __delattr__(self, name):
        raise AttributeError("Cascade inspection source is immutable")

    def __repr__(self):
        return _REDACTED

    def __deepcopy__(self, memo):
        # dataclasses.asdict deep-copies non-dataclass fields. Its output must
        # contain neither a source object nor any additional source text.
        return _REDACTED

    def _inspection_text(self):
        return self.__snapshot

    def _output_schema(self):
        return json.loads(self.__schema)

    def _render(self):
        from .router import _build_prompt

        value = json.loads(self.__snapshot)
        return _build_prompt(value["question"], {"official": value["official"], "document": value["document"]},
                             primary_verdict=value["primary_verdict"])

    def _matches(self, request, original_system):
        from .router import SYSTEM_BASE

        role, system = _STAGES[self.__stage]
        value = json.loads(self.__snapshot)
        if (type(value) is not dict or set(value) != {"question", "official", "document", "primary_verdict"}
                or type(value["question"]) is not str):
            return False
        primary = value["primary_verdict"]
        if (self.__stage == "critic" and type(primary) is not dict
                or self.__stage != "critic" and primary is not None):
            return False
        expected_system = system if original_system is None else f"{SYSTEM_BASE}\n[역할] {role}\n{system}"
        original = request.system if original_system is None else original_system
        return (original == system and request.system == expected_system
                and json.dumps(request.schema, sort_keys=True, ensure_ascii=False) == self.__schema
                and request.user == self._render())


def build_cascade_request(stage, question, evidence, *, primary_verdict=None):
    """Render and inspect the same frozen source, without changing wire payloads."""
    from .router import _VERDICT_MAX_TOKENS, _VERDICT_SCHEMA

    source = _CascadeSource(
        stage,
        json.dumps({"question": question, "official": evidence.get("official", {}),
                    "document": evidence.get("document", ""), "primary_verdict": primary_verdict}, ensure_ascii=False),
        json.dumps(_VERDICT_SCHEMA, sort_keys=True, ensure_ascii=False),
        capability=_CAPABILITY,
    )
    return _CascadeRequest(system=_STAGES[stage][1], user=source._render(), schema=source._output_schema(),
                           max_tokens=_VERDICT_MAX_TOKENS, inspection_source=source)


def valid_cascade_source(request, *, original_system=None):
    source = request.inspection_source
    if source is None:
        return not isinstance(request, _CascadeRequest)
    if type(request) is not _CascadeRequest or type(source) is not _CascadeSource:
        return False
    try:
        return source._matches(request, original_system)
    except (AttributeError, KeyError, TypeError, ValueError, RecursionError):
        return False


def cascade_inspection_text(request):
    """Only the internal consumer type can contribute extra inspection text."""
    source = request.inspection_source
    if type(source) is not _CascadeSource:
        return None
    try:
        return source._inspection_text()
    except AttributeError:
        return None
