"""TK-186: 공식 Source cascade 개인정보 마스킹·위조 방지·비잘림 안전 진단 시험. 합성 자료만 사용한다."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.common.config import get_settings
from packages.common.enums import AdapterStatus, ExternalAIPolicy
from packages.llm_router.budget import BudgetLedger
from packages.llm_router.cascade_source import build_cascade_request
from packages.llm_router.privacy import inspect_request
from packages.llm_router.providers import LLMProvider, LLMRequest, LLMResponse
from packages.llm_router.router import LLMRouter, describe_failure
from packages.pii_engine import PIIEngine, PseudonymStore
from packages.pii_engine.detector import detect
from packages.verification_engine.pipeline import VerificationPipeline


class _StubProvider(LLMProvider):
    def __init__(self, name: str, model: str, responder):
        cfg = SimpleNamespace(name=name, kind="cloud", model=model, enabled=True, timeout_seconds=10)
        super().__init__(cfg)
        self.name = name
        self._responder = responder
        self.requests = []

    @property
    def available(self) -> bool:
        return True

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return self._responder(request)


def _router(tmp_path: Path, providers: dict) -> LLMRouter:
    from dataclasses import replace
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    base = get_settings()
    pricing = dict(base.pricing)
    for p in providers.values():
        pricing[f"{p.name}:{p.config.model}"] = {"input_per_1k": "0.001", "output_per_1k": "0.002"}
    settings = replace(
        base,
        providers={name: p.config for name, p in providers.items()},
        llm_cross_check="all",
        llm_efficient_routing=False,
        korean_law_review_profile=False,
        pricing=pricing,
    )
    engine = create_engine(f"sqlite:///{tmp_path / 'budget.sqlite'}", connect_args={"check_same_thread": False})
    ledger = BudgetLedger(factory=sessionmaker(bind=engine, expire_on_commit=False))
    return LLMRouter(providers=providers, settings=settings, ledger=ledger, run_id=f"tk186_{tmp_path.name}")


# --- 1. 양성 대조: 마스킹된 공식 전문 + 가명 토큰 인접 괄호 숫자 -----------------------------
@pytest.mark.parametrize(
    "raw_official,expected_rule",
    [
        (
            "【이유】 피고인 홍길동(연락처 010-2345-6789) 사건(2099노111)에서 채무불이행 책임이 성립한다.",
            "채무불이행 책임이 성립한다.",
        ),
        (
            "【이유】 재항고인 김도윤(19800101-1234567) 및 주식회사 봄날(대표이사 이영희)에 대하여 공소사실이 특정되어야 한다.",
            "공소사실이 특정되어야 한다.",
        ),
        (
            "【이유】 신청인 박민수(서울특별시 서초구 서초대로 999)는 010-8888-7777로 통지한 이상 해지 효력이 발생한다.",
            "해지 효력이 발생한다.",
        ),
    ],
)
def test_masked_official_cascade_passes_all_three_providers_with_grounded_quotes(tmp_path, raw_official, expected_rule):
    pii = PIIEngine(PseudonymStore("tk186_pos", root=tmp_path))
    masked_res = pii.mask_text(raw_official)
    masked_text = masked_res.masked_text

    def responder(req: LLMRequest) -> LLMResponse:
        body = json.dumps(
            {
                "status": "VERIFIED",
                "confidence": 0.9,
                "rationale": "공식 원문 법리와 일치한다.",
                "evidence_quotes": [expected_rule],
                "contradicts": False,
            },
            ensure_ascii=False,
        )
        return LLMResponse(True, text=body, provider="stub", model="m", input_tokens=50, output_tokens=30)

    providers = {
        "anthropic": _StubProvider("anthropic", "claude-stub", responder),
        "openai": _StubProvider("openai", "gpt-stub", responder),
        "gemini": _StubProvider("gemini", "gemini-stub", responder),
    }
    router = _router(tmp_path, providers)
    outcome = asyncio.run(
        router.cascade(
            question="인용된 판결의 취지가 문서 주장과 부합하는지 검토하라.",
            evidence={
                "official": {
                    "case_number": "2099다901",
                    "source_excerpt": masked_text,
                    "masking": {"attempted": True, "masked_chars": len(masked_text)},
                },
                "document": "본 서면은 2099다901 판결의 법리를 인용한다.",
            },
            policy=ExternalAIPolicy.MASKED,
        )
    )
    assert all(len(p.requests) == 1 for p in providers.values())
    assert all(e.ok and e.cost_status != "NOT_SENT" for e in outcome.executions)
    assert all(expected_rule in (s.get("verdict") or {}).get("evidence_quotes", [])
               for s in outcome.stages if s.get("used"))


def test_pseudonym_adjacent_parenthetical_digits_do_not_fabricate_phone_match(tmp_path):
    pii = PIIEngine(PseudonymStore("tk186_adj", root=tmp_path))
    masked = pii.mask_text("피고인 홍길동(19800101-1234567)은 변호인 김철수, 성명: 이영희와 공범이다.").masked_text
    assert "[PERSON_001]" in masked
    rem = [m for m in detect(masked) if m.confidence >= 0.6]
    assert not any(m.kind == "PHONE" for m in rem)


def test_live_source_check_cascade_masks_official_source_and_reports_all_three(tmp_path, monkeypatch):
    import scripts.live_source_check as lsc

    raw_text = (
        "【주문】 재항고를 기각한다. 【이유】 피고인 홍길동(연락처 010-2222-3333)에 대한 "
        "압수물은 구체적 혐의사실과 관련성이 인정되어야 한다."
    )
    providers = {
        name: _StubProvider(
            name,
            f"{name}-stub",
            lambda req, pname=name: LLMResponse(
                True,
                text=json.dumps(
                    {
                        "status": "VERIFIED",
                        "confidence": 0.9,
                        "rationale": "원문 부합",
                        "evidence_quotes": ["압수물은 구체적 혐의사실과 관련성이 인정되어야 한다."],
                        "contradicts": False,
                    },
                    ensure_ascii=False,
                ),
                provider=pname,
                model=f"{pname}-stub",
                input_tokens=40,
                output_tokens=20,
            ),
        )
        for name in ("anthropic", "openai", "gemini")
    }
    monkeypatch.setattr(lsc, "MATCHED_CASES", [{"case_number": "2099모1839", "source_id": "SRC1", "full_text": ""}])

    class FakeLaw:
        def fetch_case(self, rec):
            return SimpleNamespace(status=AdapterStatus.READY, message="", records=[{"full_text": raw_text}])

    registry = SimpleNamespace(law=FakeLaw())
    monkeypatch.setattr("packages.llm_router.LLMRouter", lambda: _router(tmp_path, providers))

    checks = asyncio.run(lsc.check_cascade(True, registry))
    summary_check = next(c for c in checks if c.name == "cascade:참여 공급자")
    assert summary_check.status == "OK" and summary_check.ok is True
    assert "3개(" in summary_check.detail
    assert "마스킹 " in summary_check.detail and "sha=" in summary_check.detail
    for p in providers.values():
        sent = p.requests[0].user
        assert "010-2222-3333" not in sent and "홍길동" not in sent


# --- 2. 비잘림 안전 진단 & 음성 보안 대조군(위조·우회·숨김·잔존 PII 차단 유지) --------------------
def test_blocked_cascade_diagnostics_preserve_full_safe_codes_without_pii(tmp_path):
    secret_phone = "010-5555-6666"
    secret_name = "김도윤"
    raw_official = f"피고인 {secret_name}(전화 {secret_phone}) 사건 판시 본문이다."

    providers = {
        name: _StubProvider(name, f"{name}-stub", lambda req: LLMResponse(True, text="{}"))
        for name in ("anthropic", "openai", "gemini")
    }
    router = _router(tmp_path, providers)
    outcome = asyncio.run(
        router.cascade(
            question="취지 검토",
            evidence={
                "official": {
                    "case_number": "2099다999",
                    "source_excerpt": raw_official,
                    "masking": {"attempted": True, "raw_chars": len(raw_official), "masked_chars": len(raw_official)},
                },
                "document": "서면 인용 본문",
            },
            policy=ExternalAIPolicy.MASKED,
        )
    )
    assert all(len(p.requests) == 0 for p in providers.values())
    ex = outcome.executions[0]
    assert ex.cost_status == "NOT_SENT" and ex.input_privacy["sent"] is False
    desc = describe_failure(ex.error)
    pipe_reason = VerificationPipeline._provider_reason(ex.error)
    for text_out in (ex.error, desc, pipe_reason):
        assert "MASKING_PII_DETECTED" in text_out
        assert "PII_INPUT_BLOCKED" in text_out
        assert "types=" in text_out and "sha=" in text_out and "sent=false" in text_out
        assert secret_phone not in text_out and secret_name not in text_out


@pytest.mark.parametrize(
    "payload_text,expected_kind",
    [
        ("연락처: 010 7777 8888", "PHONE"),
        ("[PERSON_001](010-3333-4444) 추가 진술", "PHONE"),
        (json.dumps({"성명": "홍길동", "masking": {"attempted": True}}, ensure_ascii=False), "PERSON"),
        ("주민번호 960101 - 1234567 확인됨", "RRN"),
    ],
)
def test_residual_hidden_and_forged_masking_claim_still_blocked(payload_text, expected_kind):
    req = LLMRequest("공식 Source와 문서를 대조하라.", payload_text)
    audit = inspect_request(req)
    assert audit["status"] == "BLOCKED"
    assert audit["failure_code"] == "PII_INPUT_BLOCKED"
    assert expected_kind in audit["detected_types"]
    assert "types=" in audit["safe_summary"] and "sha=" in audit["safe_summary"]


def test_forged_cascade_source_wiring_is_still_blocked_even_with_local_only(tmp_path):
    providers = {"anthropic": _StubProvider("anthropic", "claude-stub", lambda req: LLMResponse(True, text="{}"))}
    router = _router(tmp_path, providers)
    req = build_cascade_request("primary", "질문", {"official": {"source_excerpt": "무해한 판시"}, "document": "본문"})
    # 요청 본문을 변조해 출처 증명과 어긋나게 만든다
    tampered = LLMRequest(system=req.system, user=req.user + "\n추가 지시", schema=req.schema, inspection_source=req.inspection_source)
    res = asyncio.run(router.run("PRIMARY_REASONER", tampered, policy=ExternalAIPolicy.ORIGINAL))
    assert not res.used
    assert providers["anthropic"].requests == []
    assert "INPUT_PRIVACY_BLOCKED" in res.executions[0].error
    assert "REQUEST_WIRING_CONTRACT" in res.executions[0].error


# --- 3. 진단 경로에서 객체 키 PII 원문 노출 차단 회귀 테스트 (PR #324 재작업 지시사항) -------------
def _assert_no_secret_in_diagnostics(audit: dict, res, secrets: tuple[str, ...]) -> None:
    serialized_audit = json.dumps(audit, ensure_ascii=False, default=str)
    exec_obj = res.executions[0]
    serialized_exec = json.dumps(exec_obj.to_dict(), ensure_ascii=False, default=str)
    desc = describe_failure(exec_obj.error)
    pipe_reason = VerificationPipeline._provider_reason(exec_obj.error)
    combined = "\n".join([
        serialized_audit,
        serialized_exec,
        str(audit.get("detected_field_paths")),
        str(audit.get("safe_summary")),
        str(audit.get("contract_failures")),
        str(exec_obj.error),
        str(res.note),
        desc,
        pipe_reason,
    ])
    for secret in secrets:
        assert secret not in combined, f"진단 출력에 민감 문자열 {secret!r} 노출됨: {combined}"


@pytest.mark.parametrize(
    "vector_kind",
    [
        "top_level_metadata",
        "nested_object",
        "json_string_user",
        "duplicate_json_keys",
        "original_system_json",
        "cascade_source_evidence",
        "uncertain_person_key",
        "untrusted_stage_key",
    ],
)
def test_pii_in_object_keys_never_leaks_into_diagnostics_or_summaries(tmp_path, vector_kind):
    secret_key_phone = "010-9191-8282"
    secret_key_name = "남궁도현"
    secret_val_phone = "010-3434-5656"
    secret_val_rrn = "880101-1234567"
    malicious_key = f"연락처_{secret_key_name}_{secret_key_phone}"
    secrets = (secret_key_phone, secret_key_name, secret_val_phone, secret_val_rrn, malicious_key)

    providers = {"anthropic": _StubProvider("anthropic", "claude-stub", lambda req: LLMResponse(True, text="{}"))}
    router = _router(tmp_path, providers)

    if vector_kind == "top_level_metadata":
        req = LLMRequest(
            system="일반 시스템 안내",
            user="일반 질문 본문",
            metadata={malicious_key: f"전화 {secret_val_phone}"},
        )
    elif vector_kind == "nested_object":
        req = LLMRequest(
            system="일반 시스템 안내",
            user="일반 질문 본문",
            metadata={"outer": {f"내부키_{secret_key_name}": [{"항목_" + secret_key_phone: f"주민번호 {secret_val_rrn}"}]}},
        )
    elif vector_kind == "json_string_user":
        req = LLMRequest(
            system="일반 시스템 안내",
            user=json.dumps({malicious_key: {"sub_" + secret_key_name: f"연락처 {secret_val_phone}"}}, ensure_ascii=False),
        )
    elif vector_kind == "duplicate_json_keys":
        dup_json = (
            '{"' + malicious_key + '":"' + f"전화 {secret_val_phone}" + '",'
            '"' + malicious_key + '":"일반 안전 기록"}'
        )
        req = LLMRequest(system="일반 시스템 안내", user=dup_json)
    elif vector_kind == "original_system_json":
        req = LLMRequest(
            system=json.dumps({malicious_key: f"주민번호 {secret_val_rrn}"}, ensure_ascii=False),
            user="일반 질문 본문",
        )
    elif vector_kind == "cascade_source_evidence":
        req = build_cascade_request(
            "primary",
            "인용된 판결 검토",
            {
                "official": {
                    "case_number": "2099다777",
                    malicious_key: f"피고인 연락처 {secret_val_phone}",
                },
                "document": "본문",
            },
        )
    elif vector_kind == "uncertain_person_key":
        # 값에는 번호 PII가 없고 키의 '성명' 접미사로 인해 uncertain_paths로만 잡히는 경로
        uncertain_key = f"{secret_key_name}_{secret_key_phone}_성명"
        secrets = (secret_key_phone, secret_key_name, uncertain_key)
        req = LLMRequest(
            system="일반 시스템 안내",
            user=json.dumps({uncertain_key: "외국계미상표기!@#"}, ensure_ascii=False),
        )
    else:
        req = LLMRequest(
            system="일반 시스템 안내",
            user=f"전화 {secret_val_phone}",
            metadata={"stage": malicious_key},
        )

    audit = inspect_request(req, _original_system=req.system)
    res = asyncio.run(router.run("PRIMARY_REASONER", req, policy=ExternalAIPolicy.MASKED))

    assert audit["status"] == "BLOCKED"
    assert audit["failure_code"] == "PII_INPUT_BLOCKED"
    assert not res.used
    assert providers["anthropic"].requests == []
    assert audit.get("detected_field_paths"), "차단된 경로 목록이 비어 있으면 안 됨"
    if vector_kind != "untrusted_stage_key":
        assert any("key_" in p for p in audit["detected_field_paths"]), (
            f"비허용 객체 키가 정규화 토큰(key_<해시>)으로 변환되어야 함: {audit['detected_field_paths']}"
        )
    _assert_no_secret_in_diagnostics(audit, res, secrets)


def test_known_fixed_fields_remain_readable_while_unknown_keys_are_tokenized():
    secret_key = "비밀당사자_김도윤_010-7777-1111"
    payload = {
        "document": "연락처 010-8888-9999 포함 본문",
        "reference_sources": [{"text": "주민번호 900101-1234567 포함 발췌", secret_key: "010-1212-3434"}],
    }
    req = LLMRequest(system="일반 안내", user=json.dumps(payload, ensure_ascii=False))
    audit = inspect_request(req)
    assert audit["status"] == "BLOCKED"
    paths = audit["detected_field_paths"]
    assert "user.document" in paths
    assert "user.reference_sources[0].text" in paths
    assert any(p.startswith("user.reference_sources[0].key_") for p in paths)
    assert all(secret_key not in p for p in paths)
    assert secret_key not in audit["safe_summary"]


@pytest.mark.parametrize(
    "case_type,payload_fn,expected_array_index",
    [
        (
            "bracketed_phone_key",
            lambda pk, pv: {pk: f"연락처 {pv}"},
            None,
        ),
        (
            "digit_only_bracket_key",
            lambda pk, pv: {pk: f"연락처 {pv}"},
            None,
        ),
        (
            "array_element_bracketed_phone_key",
            lambda pk, pv: {"items": [{pk: f"연락처 {pv}"}]},
            "[0]",
        ),
        (
            "array_element_digit_bracket_key",
            lambda pk, pv: {"items": [{pk: f"연락처 {pv}"}]},
            "[0]",
        ),
        (
            "key_prefix_raw_key",
            lambda pk, pv: {pk: f"연락처 {pv}"},
            None,
        ),
        (
            "array_element_key_prefix_raw_key",
            lambda pk, pv: {"items": [{"text": "일반 발췌"}, {pk: f"연락처 {pv}"}]},
            "[1]",
        ),
    ],
)
def test_bracketed_phone_keys_and_array_elements_never_leak_numeric_pii(
    tmp_path, case_type, payload_fn, expected_array_index
):
    phone_digits = "01012345678"
    secret_val_phone = "010-9876-5432"
    if "digit_only" in case_type:
        malicious_key = f"[{phone_digits}]"
    elif "key_prefix" in case_type:
        malicious_key = f"key_{phone_digits}"
    else:
        malicious_key = f"phone[{phone_digits}]"

    payload = payload_fn(malicious_key, secret_val_phone)
    req = LLMRequest(
        system="일반 시스템 안내",
        user=json.dumps(payload, ensure_ascii=False),
    )

    providers = {"anthropic": _StubProvider("anthropic", "claude-stub", lambda r: LLMResponse(True, text="{}"))}
    router = _router(tmp_path, providers)

    audit = inspect_request(req)
    res = asyncio.run(router.run("PRIMARY_REASONER", req, policy=ExternalAIPolicy.MASKED))

    assert audit["status"] == "BLOCKED"
    assert audit["failure_code"] == "PII_INPUT_BLOCKED"
    assert not res.used

    # 1. 원래 전화번호 숫자 시퀀스(01012345678)와 값(010-9876-5432)이 전체 진단에서 완전 부재함을 검증
    secrets = (phone_digits, secret_val_phone, malicious_key)
    _assert_no_secret_in_diagnostics(audit, res, secrets)

    # 2. detected_field_paths 검증
    paths = audit.get("detected_field_paths", [])
    assert paths, "차단된 경로 목록이 비어 있으면 안 됨"
    for p in paths:
        assert phone_digits not in p, f"진단 경로에 전화번호 숫자 시퀀스 노출: {p}"
        assert malicious_key not in p, f"진단 경로에 원문 악성 키 노출: {p}"
        assert "key_" in p, f"비허용 키는 정규화 토큰(key_<해시>)으로 변환되어야 함: {p}"

    # 3. 실제 배열 인덱스는 안전하게 표시되는지 확인
    if expected_array_index:
        assert any(expected_array_index in p for p in paths), (
            f"실제 리스트 인덱스({expected_array_index})는 배열 구조 식별을 위해 보존되어야 함: {paths}"
        )



@pytest.mark.parametrize(
    "raw_segment",
    ["[01012345678]", "key_01012345678", "phone[01012345678]", "items[0]", "a.b[3]"],
)
def test_safe_diagnostic_path_never_trusts_string_shaped_segments(raw_segment):
    from packages.llm_router.privacy import _safe_diagnostic_path

    for raw in (raw_segment, ("user", raw_segment), ("user", "items", 0, raw_segment)):
        out = _safe_diagnostic_path(raw)
        last = out.rsplit(".", 1)[-1]
        assert last.startswith("key_") and "[" not in last, out
        assert raw_segment not in last
        assert "01012345678" not in out


@pytest.mark.parametrize(
    "typed_path,expected",
    [
        (("user", "items", 0, "text"), "user.items[0].text"),
        (("reference_sources", 2, "text"), "reference_sources[2].text"),
        (("items", 1, "surrounding_context_and_claim"), "items[1].surrounding_context_and_claim"),
    ],
)
def test_safe_diagnostic_path_preserves_real_int_indices_and_allowlisted_keys(typed_path, expected):
    from packages.llm_router.privacy import _safe_diagnostic_path

    assert _safe_diagnostic_path(typed_path) == expected
    assert _safe_diagnostic_path(typed_path, prefix="excerpt_source") == f"excerpt_source.{expected}"
    # bool은 정수 첨자로 취급하지 않는다
    assert "[True]" not in _safe_diagnostic_path(("items", True))


def test_unknown_keys_use_non_deterministic_uninvertible_tokens_without_fingerprint():
    phone_key = "01012345678"
    req = LLMRequest(
        system="일반 안내",
        user=json.dumps({phone_key: "010-9999-8888"}, ensure_ascii=False),
    )
    audit1 = inspect_request(req)
    audit2 = inspect_request(req)

    # 1. 원문 문자열이 진단에 없어야 함
    assert phone_key not in audit1["safe_summary"]
    assert all(phone_key not in p for p in audit1["detected_field_paths"])

    # 2. 낮은 엔트로피 후보의 sha256 등 원문 유래 결정적 해시 지문이 경로 및 요약에 없어야 함
    raw_sha = hashlib.sha256(phone_key.encode("utf-8")).hexdigest()
    for length in (8, 12, 16, 32, 64):
        assert raw_sha[:length] not in audit1["safe_summary"]
        assert all(raw_sha[:length] not in p for p in audit1["detected_field_paths"])

    # 3. 요청 간 동일 키라도 동일 토큰이 재사용되지 않는 비결정성(salt/nonce) 검증
    paths1 = audit1["detected_field_paths"]
    paths2 = audit2["detected_field_paths"]
    assert paths1 != paths2, f"서로 다른 감사 실행에서 비허용 키의 진단 토큰이 달라야 함: {paths1} vs {paths2}"

    # 4. 동일 요청 내에서는 동일 키에 대해 일관된 토큰 부여 확인
    req_multi = LLMRequest(
        system="일반 안내",
        user=json.dumps({"sub1": {phone_key: "010-9999-8888"}, "sub2": {phone_key: "010-8888-7777"}}, ensure_ascii=False),
    )
    audit_multi = inspect_request(req_multi)
    multi_paths = audit_multi["detected_field_paths"]
    tokens = [p.rsplit(".", 1)[-1] for p in multi_paths]
    assert len(set(tokens)) == 1, f"동일 요청 내 동일 키는 같은 토큰이어야 함: {multi_paths}"

