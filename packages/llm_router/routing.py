"""Task-based cost controls. Source text never selects a model or skips legal review."""
from __future__ import annotations

import hashlib
import json
from copy import copy
from dataclasses import replace

from packages.common.enums import LLMRole


def sampled(request, percent):
    """Stable sampling, independent of a model's confidence or reported verdict."""
    digest = hashlib.sha256((request.system + "\0" + request.user).encode()).digest()
    return int.from_bytes(digest[:4], "big") % 100 < percent


def task_provider(provider, role, request, settings):
    from .providers import PROVIDER_CLASSES

    if not getattr(settings, "llm_efficient_routing", False):
        return provider
    # Custom adapters/test doubles retain their own model and mutable state.
    if type(provider) not in PROVIDER_CLASSES.values():
        return provider
    purpose = ""
    if provider.name == "anthropic":
        purpose = "anthropic_escalation" if request.model_tier == "escalation" else "anthropic_review"
    elif provider.name == "openai":
        purpose = ("openai_extraction" if role == LLMRole.LOW_COST_EXTRACTOR
                   or request.input_contract == "ai_document_v1" else "openai_review")
    model = getattr(settings, "llm_routing", {}).get(purpose)
    overrides = getattr(settings, "llm_model_overrides", {})
    explicit_task_model = overrides.get(purpose)
    if purpose and not explicit_task_model:
        default_model = getattr(settings, "llm_default_models", {}).get(provider.name)
        if (overrides.get(provider.name)
                or provider.config.model != default_model):
            return provider  # Explicit operator/API model choices are authoritative.
    if not model or model == provider.config.model:
        return provider
    selected = copy(provider)
    selected.config = replace(provider.config, model=model)
    return selected


def request_key(request, provider, role, policy, expected_task):
    # The cache is scoped to a single pipeline run and never persisted.
    payload = [provider.name, provider.config.model, str(role), str(policy), expected_task,
               request.system, request.user, request.schema, request.max_tokens,
               request.temperature, request.input_contract, request.model_tier, request.metadata]
    try:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    except (TypeError, ValueError):
        return None  # Opaque metadata is never a cache identity.
    return hashlib.sha256(encoded).hexdigest()


def needs_additional_review(answer):
    if not answer.used or answer.quarantined or not isinstance(answer.parsed, dict):
        return True
    verdict = answer.parsed.get("verdict")
    # Authorship is advisory. Any affirmative claim receives a second opinion.
    return verdict not in {"UNCERTAIN", "HUMAN_AUTHORED_LIKELY"}


def conflicting(answers):
    signatures = []
    for answer in answers:
        if not answer.used or not isinstance(answer.parsed, dict):
            continue
        value = answer.parsed
        if "rows" in value:
            signatures.append(tuple(sorted((str(r.get("item_id")), r.get("validity_verdict"))
                                           for r in value["rows"])))
        else:
            signatures.append(value.get("status") or value.get("verdict"))
    return len(set(signatures)) > 1


def complete_argument_reviews(request, answers):
    """Two empty/partial envelopes do not satisfy item-level independent review."""
    try:
        expected = {str(item["item_id"]) for item in json.loads(request.user)["items"]}
    except (KeyError, ValueError, TypeError):
        return False
    if not expected:
        return False
    for item_id in expected:
        families = {answer.executions[-1].provider for answer in answers if answer.used
                    and answer.executions and isinstance(answer.parsed, dict)
                    and any(str(row.get("item_id")) == item_id
                            for row in answer.parsed.get("rows", []))}
        if len(families) < 2:
            return False
    return True


def argument_escalation_item_ids(request, answers):
    """법리 검토(argument_review_v1)에서 엇갈리거나(conflicting) 완결성이 미비한(incomplete) item_id 집합을 반환한다."""
    try:
        payload = json.loads(request.user)
        expected_items = payload.get("items", [])
        expected_ids = [str(item["item_id"]) for item in expected_items if "item_id" in item]
    except (KeyError, ValueError, TypeError):
        return set()

    if not expected_ids:
        return set()

    successes = [a for a in answers if a.used and a.executions and isinstance(a.parsed, dict)]
    if len(successes) < 2:
        return set(expected_ids)

    conflicting_ids = set()
    incomplete_ids = set()

    for item_id in expected_ids:
        verdicts_by_provider = {}
        for a in successes:
            provider = a.executions[-1].provider
            for row in a.parsed.get("rows", []):
                if str(row.get("item_id")) == item_id:
                    verdicts_by_provider[provider] = row.get("validity_verdict")

        # 1) 완결성 검사: 독립된 공급자 2곳 이상의 의견이 있는지 확인
        if len(verdicts_by_provider) < 2:
            incomplete_ids.add(item_id)
        # 2) 판정 일치 검사: 2곳 이상의 공급자 의견 간 판정이 서로 다른지 확인
        elif len(set(verdicts_by_provider.values())) > 1:
            conflicting_ids.add(item_id)

    return conflicting_ids | incomplete_ids


def build_partial_argument_request(request, escalation_item_ids):
    """에스컬레이션 대상 항목만으로 축소된 LLMRequest를 생성하고 원본 발췌 증거를 바인딩한다."""
    try:
        payload = json.loads(request.user)
        original_items = payload.get("items", [])
    except (KeyError, ValueError, TypeError):
        return request

    escalation_set = {str(i) for i in escalation_item_ids}
    reduced_items = [item for item in original_items if str(item.get("item_id")) in escalation_set]
    if not reduced_items or len(reduced_items) == len(original_items):
        return request

    reduced_payload = {**payload, "items": reduced_items}
    reduced_user = json.dumps(reduced_payload, ensure_ascii=False)

    from .providers import LLMRequest
    from .excerpt_source import is_excerpt_request, bind_argument_excerpts

    if is_excerpt_request(request):
        source = getattr(request, "inspection_source", None)
        entries = getattr(source, "_ExcerptSource__entries", ()) if source else ()
        pieces_by_orig_index = {
            path[1]: piece for path, piece in entries
            if isinstance(path, tuple) and len(path) > 1 and path[0] == "items"
        }
        reduced_pieces = []
        for orig_idx, item in enumerate(original_items):
            if str(item.get("item_id")) in escalation_set:
                piece = pieces_by_orig_index.get(orig_idx)
                if piece is not None:
                    reduced_pieces.append(piece)

        base_request = LLMRequest(
            system=request.system,
            user=reduced_user,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            schema=copy(request.schema),
            input_contract=request.input_contract,
            model_tier=request.model_tier,
            metadata=copy(request.metadata),
        )
        if len(reduced_pieces) == len(reduced_items):
            return bind_argument_excerpts(base_request, tuple(reduced_pieces))
        return base_request

    return LLMRequest(
        system=request.system,
        user=reduced_user,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        schema=copy(request.schema),
        input_contract=request.input_contract,
        model_tier=request.model_tier,
        metadata=copy(request.metadata),
    )

