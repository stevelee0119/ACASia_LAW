"""Fabricated UUIDs exercise Claim creation, real review/router and privacy gates."""
from __future__ import annotations

import asyncio
import json
from uuid import UUID

import pytest
from sqlalchemy import select

from packages.common import config, schemas
from packages.common.enums import ClaimType, LLMRole
from packages.common.schemas import Claim
from packages.llm_router.budget import BudgetReservation
from packages.rag_engine.review import review_document
from korean_law_profile.test_review_path import (
    inputs, make_router, pii_engine, request_for,
)


# Public fabricated seeds, never user identifiers or documents.
OVERLAPPING = ("a0212345678b", "a03123456789", "b05123456789")
SAFE = ("abcdefabcdef", "fedcbafedcba", "abcdef123abc")
CONTACTS = ("02-3456-7890", "031-456-7890", "010-2468-1357")


@pytest.fixture(autouse=True)
def isolated_identifier_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("LV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LV_STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("LV_ALLOW_NETWORK", "0")
    monkeypatch.setenv("LV_KOREAN_LAW_REVIEW_PROFILE", "0")
    monkeypatch.setattr(config, "_settings", None)


def generated_claim(monkeypatch, seed):
    draws = []
    def draw():
        draws.append(True)
        return UUID(hex=seed.ljust(32, "0"))
    with monkeypatch.context() as scoped:
        scoped.setattr(schemas.uuid, "uuid4", draw)
        claim = Claim.create(ClaimType.LEGAL_ARGUMENT, "서명 뒤 철회는 가능하다고 주장한다.")
    assert draws == [True]  # No retry/resampling or reduction of seed space.
    return claim


def reservation_count(router):
    with router.ledger.factory() as session:
        return len(session.scalars(select(BudgetReservation)).all())


@pytest.mark.parametrize("seed", OVERLAPPING + SAFE)
@pytest.mark.parametrize("profile", (False, True))
def test_generated_claim_reaches_real_review_router_without_pii_exemption(monkeypatch, seed, profile):
    claim = generated_claim(monkeypatch, seed)
    result, library, context = inputs()
    result.claims = [claim.to_dict()]
    router, providers = make_router(profile)
    review_document(result, library, router, context, pii_engine())
    sent = providers["anthropic"].requests
    assert len(sent) == reservation_count(router) == 2
    request = next(r for r in sent if r.input_contract == "claim_review_v1")
    assert json.loads(request.user)["claim_id"] == request.metadata["claim_id"] == claim.claim_id
    assert claim.claim_id.startswith("CLM_") and len(claim.claim_id) == 16
    assert claim.claim_id[4:].isalpha() and claim.claim_id[4:].isascii()


@pytest.mark.parametrize("seed", OVERLAPPING)
@pytest.mark.parametrize("profile", (False, True))
def test_legacy_contact_shaped_claim_id_keeps_prebudget_block(monkeypatch, seed, profile):
    result, library, context = inputs()
    result.claims[0]["claim_id"] = "CLM_" + seed
    router, providers = make_router(profile)
    review_document(result, library, router, context, pii_engine())
    # Document review succeeds; the unsafe legacy claim never reserves/sends.
    assert len(providers["anthropic"].requests) == reservation_count(router) == 1
    blocked = [e for e in result.engine_data["model_executions"]
               if e["input_privacy"].get("status") == "BLOCKED"]
    assert len(blocked) == 1 and blocked[0]["input_privacy"]["failure_code"] == "PII_INPUT_BLOCKED"


@pytest.mark.parametrize("contact", CONTACTS)
@pytest.mark.parametrize("location", ("metadata", "user", "system"))
def test_real_contacts_still_block_before_real_router_budget(contact, location):
    request = request_for()
    if location == "metadata":
        request.metadata["claim_id"] = "CLM_" + contact
    elif location == "user":
        payload = json.loads(request.user)
        payload["claim_id"] = "CLM_" + contact
        request.user = json.dumps(payload, ensure_ascii=False)
    else:
        request.system += "\n연락처: " + contact
    router, providers = make_router()
    result = asyncio.run(router.run(LLMRole.PRIMARY_REASONER, request))
    assert providers["anthropic"].requests == [] and reservation_count(router) == 0
    assert result.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"


@pytest.mark.parametrize("position", range(12))
def test_each_random_nibble_remains_distinguishable(monkeypatch, position):
    ids = set()
    for digit in "0123456789abcdef":
        seed = "0" * position + digit + "0" * (11 - position)
        claim = generated_claim(monkeypatch, seed)
        assert len(claim.claim_id) == 16 and claim.claim_id[4:].isalpha()
        ids.add(claim.claim_id)
    assert len(ids) == 16


@pytest.mark.parametrize("identifier", ("CLM_" + OVERLAPPING[0], "legacy-reference", "CLM_" + SAFE[0]))
def test_existing_claim_identity_is_not_rewritten(identifier):
    claim = Claim(identifier, ClaimType.LEGAL_ARGUMENT, "합성 주장")
    assert claim.to_dict()["claim_id"] == identifier


def test_other_identifier_generators_keep_their_existing_format(monkeypatch):
    with monkeypatch.context() as scoped:
        scoped.setattr(schemas.uuid, "uuid4", lambda: UUID(hex="123456789abc" + "0" * 20))
        assert schemas.new_id("CIT") == "CIT_123456789abc"
