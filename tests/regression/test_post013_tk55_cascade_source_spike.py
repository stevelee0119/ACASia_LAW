"""Comparison-only actual cascade source scan; original product is untouched."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from packages.common.enums import LLMRole
from packages.llm_router import privacy, router as module
from packages.llm_router.providers import LLMRequest, LLMResponse


PHONES = ("010-4826-7139", "010-5937-8241", "010-6148-9352")
RRNS = ("850425-1647293", "860526-2758314", "870627-3869425")
NAMES = ("한예솔", "유다린", "남궁서율")
SYSTEMS = (
    "공식 Source와 문서를 대조해 판단하고 근거를 제시하라. JSON으로만 답하라.",
    "1차 판단이 틀렸다고 가정하고 반증하라. 반증 근거가 없으면 없다고 답하라. 새로운 판례나 문헌을 지어내지 마라. JSON으로만 답하라.",
    "공개 자료를 근거로 사실관계만 확인하라. 확인되지 않으면 UNVERIFIED로 답하라. JSON으로만 답하라.",
)


@pytest.fixture(autouse=True)
def _historical_cascade_requests(monkeypatch):
    """Keep the pre-product comparison explicit after the real fix is added."""
    from packages.llm_router import cascade_source

    def old_builder(stage, question, evidence, *, primary_verdict=None):
        index = {"primary": 0, "critic": 1, "grounder": 2}[stage]
        return LLMRequest(system=SYSTEMS[index], user=module._build_prompt(question, evidence, primary_verdict),
                          schema=module._VERDICT_SCHEMA, max_tokens=module._VERDICT_MAX_TOKENS)

    monkeypatch.setattr(cascade_source, "build_cascade_request", old_builder)


def _escaped_record(value, key="opaque"):
    encoded = "".join(f"\\u{ord(char):04x}" for char in value)
    return '{"' + key + '":"' + encoded + '","' + key + '":"일반 기록"}'


@dataclass(frozen=True)
class _TestSource:
    snapshot: str


def _install_source_comparison(monkeypatch):
    """Only real test-observed builders enter this out-of-band registry."""
    build, inspect = module._build_prompt, privacy.inspect_request
    sources = {}

    def capture(question, evidence, primary_verdict=None):
        prompt = build(question, evidence, primary_verdict)
        source = {"question": question, "official": evidence.get("official", {}),
                  "document": evidence.get("document", ""), "primary_verdict": primary_verdict}
        sources[prompt] = _TestSource(json.dumps(source, ensure_ascii=False))
        return prompt

    def checked(llm_request, *, _original_system=None):
        report = inspect(llm_request, _original_system=_original_system)
        source = sources.get(llm_request.user)
        if source is None or report["status"] == "BLOCKED":
            return report
        original = llm_request.system if _original_system is None else _original_system
        source_report = inspect(LLMRequest(system="", user=source.snapshot))
        if source_report["status"] == "BLOCKED":
            return {**report, "status": "BLOCKED", "failure_code": "PII_INPUT_BLOCKED",
                    "detected_types": source_report["detected_types"],
                    "detected_field_paths": ["cascade_source." + path for path in source_report.get("detected_field_paths", [])]}
        frozen = json.loads(source.snapshot)
        rendered = build(frozen["question"], {"official": frozen["official"], "document": frozen["document"]}, frozen["primary_verdict"])
        role_prefix = module.SYSTEM_BASE + "\n[역할] "
        role = llm_request.system[len(role_prefix):].split("\n", 1)[0] if llm_request.system.startswith(role_prefix) else None
        expected = {str(LLMRole.PRIMARY_REASONER): SYSTEMS[0], str(LLMRole.INDEPENDENT_CRITIC): SYSTEMS[1],
                    str(LLMRole.WEB_GROUNDER): SYSTEMS[2]}.get(role)
        critic_source = frozen["primary_verdict"] is not None
        if (expected != original or critic_source != (role == str(LLMRole.INDEPENDENT_CRITIC))
                or llm_request.schema != module._VERDICT_SCHEMA or rendered != llm_request.user):
            return {**report, "status": "BLOCKED", "failure_code": "SPIKE_SOURCE_CONTRACT_INVALID"}
        return report

    monkeypatch.setattr(module, "_build_prompt", capture)
    monkeypatch.setattr(privacy, "inspect_request", checked)
    return sources


def _router(monkeypatch, *, primary_rationale="일반 자료 확인", transient=False, primary_failure=False):
    sent, reserved, attempts = [], [], {}
    monkeypatch.setattr(module, "estimate_call", lambda *args: (Decimal("0.01"), {}))

    class Provider:
        available = True

        def __init__(self, name):
            self.name = name
            self.config = SimpleNamespace(name=name, kind="cloud", model="synthetic", enabled=True)

        async def generate(self, llm_request):
            sent.append((self.name, llm_request))
            attempts[self.name] = attempts.get(self.name, 0) + 1
            if primary_failure and self.name == "anthropic":
                return LLMResponse(False, error="synthetic permanent failure")
            if transient and attempts[self.name] == 1:
                return LLMResponse(False, error="HTTP 503 synthetic overload")
            verdict = {"status": "VERIFIED", "rationale": primary_rationale if self.name == "anthropic" else "일반 자료 확인",
                       "confidence": 0.95, "evidence_quotes": [], "contradicts": False}
            return LLMResponse(True, text=json.dumps(verdict, ensure_ascii=False), provider=self.name, model="synthetic")

    def reserve(*args, **kwargs):
        reserved.append(True)
        return SimpleNamespace(id="synthetic", amount=Decimal("0.01"))

    ledger = SimpleNamespace(reserve=reserve, dispatch=lambda *a, **k: None, settle=lambda *a, **k: None,
                             release=lambda *a, **k: None)
    router = module.LLMRouter(providers={name: Provider(name) for name in ("anthropic", "openai", "gemini")}, ledger=ledger)
    router.settings = replace(router.settings, llm_cross_check="all")
    router.retry_delays = (0.001,) if transient else ()
    return router, sent, reserved


def _cascade(monkeypatch, evidence, **kwargs):
    router, sent, reserved = _router(monkeypatch, **kwargs)
    result = asyncio.run(router.cascade(question="제공 자료 대조", evidence=evidence))
    return result, sent, reserved


@pytest.mark.parametrize("value", PHONES + RRNS + NAMES)
@pytest.mark.parametrize("position", ("official", "document"))
def test_actual_source_loss_and_recovery_before_budget(monkeypatch, value, position):
    record = _escaped_record(value, "fullName" if value in NAMES else "opaque")
    evidence = {"official": {"full_text": record}} if position == "official" else {"document": record}
    _, baseline_sent, baseline_reserved = _cascade(monkeypatch, evidence)
    assert len(baseline_sent) == len(baseline_reserved) == 3
    _install_source_comparison(monkeypatch)
    result, sent, reserved = _cascade(monkeypatch, evidence)
    assert sent == reserved == []
    assert result.executions and all(item.input_privacy["failure_code"] == "PII_INPUT_BLOCKED" for item in result.executions)


@pytest.mark.parametrize("control", (
    {"official": {"case_number": "2091다24680", "full_text": '{"holding":"일반 법령 검토 자료"}'}, "document": "기관의 일반 자료 검토"},
    {"official": {"confirmed_metadata": {"court": "초록행정법원", "case_name": "자료 열람"}}, "document": '{"date":"2092-03-04"}'},
    {"official": {"full_text": '{"holding":"일반 자료","holding":"초록환경 관측자료"}'}, "document": '{"opaque":"문서함"}'},
))
def test_actual_three_producers_keep_benign_wire_payload_and_reservations(monkeypatch, control):
    _, baseline_sent, baseline_reserved = _cascade(monkeypatch, control)
    assert len(baseline_sent) == len(baseline_reserved) == 3
    _install_source_comparison(monkeypatch)
    _, sent, reserved = _cascade(monkeypatch, control)
    assert len(sent) == len(reserved) == 3
    assert [(name, req.system, req.user, req.schema) for name, req in sent] == [
        (name, req.system, req.user, req.schema) for name, req in baseline_sent]


@pytest.mark.parametrize("value", PHONES + RRNS + NAMES)
def test_actual_critic_inspects_decoded_primary_reply_before_its_budget(monkeypatch, value):
    rationale = _escaped_record(value, "fullName" if value in NAMES else "opaque")
    _, baseline_sent, baseline_reserved = _cascade(monkeypatch, {"official": {}}, primary_rationale=rationale)
    assert len(baseline_sent) == len(baseline_reserved) == 3
    _install_source_comparison(monkeypatch)
    result, sent, reserved = _cascade(monkeypatch, {"official": {}}, primary_rationale=rationale)
    assert len(sent) == len(reserved) == 1
    assert [name for name, _ in sent] == ["anthropic"]
    assert any(item.input_privacy.get("failure_code") == "PII_INPUT_BLOCKED" for item in result.executions)


@pytest.mark.parametrize("mutation", ("system", "schema", "source", "role"))
def test_source_snapshot_binding_rejects_mismatch_without_budget(monkeypatch, mutation):
    sources = _install_source_comparison(monkeypatch)
    user = module._build_prompt("제공 자료 대조", {"official": {"full_text": "일반 자료"}})
    request = LLMRequest(system=SYSTEMS[0], user=user, schema=module._VERDICT_SCHEMA)
    if mutation == "system":
        request = replace(request, system="다른 검토")
    elif mutation == "schema":
        request = replace(request, schema={"type": "object"})
    elif mutation == "role":
        request = replace(request, system=SYSTEMS[1])  # a real, but wrong, consumer stage
    else:
        data = json.loads(sources[user].snapshot)
        data["official"]["full_text"] = "대체 자료"
        sources[user] = _TestSource(json.dumps(data, ensure_ascii=False))
    router, sent, reserved = _router(monkeypatch)
    result = asyncio.run(router.run(LLMRole.PRIMARY_REASONER, request))
    assert sent == reserved == []
    assert result.executions[0].input_privacy["failure_code"] == "SPIKE_SOURCE_CONTRACT_INVALID"


@pytest.mark.parametrize("marker", ("cascade_source", "primary", "critic"))
def test_json_marker_never_creates_out_of_band_consumer_provenance(monkeypatch, marker):
    _install_source_comparison(monkeypatch)
    request = LLMRequest(system="일반 기록", user='{"opaque":"임하늘"}', metadata={"source_contract": marker})
    router, sent, reserved = _router(monkeypatch)
    result = asyncio.run(router.run(LLMRole.PRIMARY_REASONER, request))
    assert len(sent) == len(reserved) == 1
    assert result.executions[0].input_privacy["status"] == "PASSED"  # legacy residual, no new inference


@pytest.mark.parametrize("mode", ("retry", "fallback"))
def test_actual_retry_and_fallback_preserve_payload_and_reservation_counts(monkeypatch, mode):
    kwargs = {"transient": mode == "retry", "primary_failure": mode == "fallback"}
    evidence = {"official": {"full_text": "일반 법령 검토 자료"}, "document": "일반 문서 자료"}
    _, baseline_sent, baseline_reserved = _cascade(monkeypatch, evidence, **kwargs)
    _install_source_comparison(monkeypatch)
    _, sent, reserved = _cascade(monkeypatch, evidence, **kwargs)
    assert len(sent) == len(baseline_sent)
    assert len(reserved) == len(baseline_reserved)
    assert [(name, req.system, req.user, req.schema) for name, req in sent] == [
        (name, req.system, req.user, req.schema) for name, req in baseline_sent]


@pytest.mark.parametrize("long_sample", (False, True))
def test_existing_actual_ai_builder_does_not_claim_cascade_provenance(monkeypatch, long_sample):
    from .test_tk55_first_party_input_contracts import test_actual_ai_builder_sampling_contracts_are_valid
    sources = _install_source_comparison(monkeypatch)
    test_actual_ai_builder_sampling_contracts_are_valid(monkeypatch, long_sample)
    assert sources == {}


@pytest.mark.parametrize("profile", (False, True))
@pytest.mark.parametrize("reference_date", ("2024-05-04", None, "invalid-date"))
def test_existing_actual_reference_and_claim_builders_keep_their_own_provenance(monkeypatch, profile, reference_date):
    from .test_tk55_first_party_input_contracts import test_actual_rag_and_claim_builders_preserve_profile_context
    sources = _install_source_comparison(monkeypatch)
    test_actual_rag_and_claim_builders_preserve_profile_context(reference_date, profile)
    assert sources == {}


def test_existing_actual_argument_batch_and_retries_keep_their_own_provenance(monkeypatch):
    from .test_tk55_first_party_input_contracts import test_actual_argument_batch_and_retry_builders_keep_contract
    sources = _install_source_comparison(monkeypatch)
    test_actual_argument_batch_and_retry_builders_keep_contract(monkeypatch)
    assert sources == {}


@pytest.mark.parametrize("where", ("metadata", "payload"))
def test_existing_legacy_marker_residual_is_unchanged(monkeypatch, where):
    from .test_tk55_first_party_input_contracts import test_json_or_metadata_marker_does_not_enable_contract_or_exemption
    _install_source_comparison(monkeypatch)
    test_json_or_metadata_marker_does_not_enable_contract_or_exemption(monkeypatch, where)


def test_existing_duplicate_unknown_role_residual_is_unchanged(monkeypatch):
    from .test_tk55_lossless_json_privacy import test_unknown_role_residual_is_not_promoted_to_new_person_inference
    _install_source_comparison(monkeypatch)
    test_unknown_role_residual_is_not_promoted_to_new_person_inference(monkeypatch)
