"""P0-2 회귀·일반화 시험: PII 마스킹 멱등성 및 1·2차 검사 규칙 동기화 (Fail-Closed 유지)."""
from __future__ import annotations

import asyncio
from decimal import Decimal
import json
from types import SimpleNamespace

import pytest

from packages.common.enums import ExternalAIPolicy, LLMRole
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.legal_engine.evidence_pack import project_masked
from packages.llm_router import router as router_module
from packages.llm_router.budget import BudgetLedger
from packages.llm_router.privacy import inspect_request
from packages.llm_router.providers import LLMRequest, LLMResponse
from packages.pii_engine.detector import PIIMatch, detect
from packages.pii_engine.engine import PIIEngine
from packages.pii_engine.pseudonym import PSEUDONYM_PREFIXES, PseudonymStore
from packages.verification_engine.ai_document_detector import detect_ai_document


# ---------------------------------------------------------------------------
# 양성 1: 가명 토큰 인접 숫자·날짜가 2차 전화번호로 재결합되지 않음
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "masked_sample",
    [
        "[PERSON_001] (2025. 11. 16.)",
        "[PERSON_001] (2024-03-01)",
        "[AFFIL_001] 1234-5678",
        "[MILID_002] (2022. 7. 8.) 발송",
        "[COMPANY_001] 2023-4567 접수",
    ],
)
def test_pseudonym_token_digits_never_retrigger_contact_detection(masked_sample):
    assert detect(masked_sample) == []
    req = LLMRequest(system="s", user=json.dumps({"document_sample_text": masked_sample}, ensure_ascii=False))
    verdict = inspect_request(req)
    assert verdict["status"] == "PASSED"


# ---------------------------------------------------------------------------
# 양성 2: 부분 중첩·연쇄 PII에 대한 mask_text 멱등성 및 project_masked 좌표 일치
# ---------------------------------------------------------------------------
def test_mask_text_multipass_idempotent_on_partial_overlap_and_projects_segments(tmp_path, monkeypatch):
    from packages.pii_engine import engine as engine_mod

    text = "앞문장 AB-TARGET-CDEF-TAIL 뒷문장"
    # 1패스에서 AB-TARGET(11자)을 가리면 남은 -CDEF-TAIL이 인접 문맥상 추가 탐지되는 상황 모의
    def fake_detect(s, *, block_id=None, page=None):
        hits = []
        idx1 = s.find("AB-TARGET")
        if idx1 >= 0:
            hits.append(PIIMatch("PHONE", s[idx1:idx1 + 9], idx1, idx1 + 9, block_id, page, 0.95))
            # 부분 중첩 후보: [idx1+2, idx1+14) = TARGET-CDEF (s2 < e1 < e2)
            hits.append(PIIMatch("ACCOUNT", s[idx1 + 2:idx1 + 14], idx1 + 2, idx1 + 14, block_id, page, 0.9))
        idx2 = s.find("-CDEF-TAIL")
        if idx2 >= 0 and s[idx2 - 1] == "]":
            hits.append(PIIMatch("PII", s[idx2:idx2 + 10], idx2, idx2 + 10, block_id, page, 0.9))
        return hits

    monkeypatch.setattr(engine_mod, "detect", fake_detect)
    engine = PIIEngine(PseudonymStore("p02_idem", root=tmp_path))
    result = engine.mask_text(text)

    assert "AB-TARGET" not in result.masked_text
    assert "-CDEF-TAIL" not in result.masked_text
    assert "[PHONE_001]" in result.masked_text
    assert "[PII_001]" in result.masked_text
    assert fake_detect(result.masked_text) == []
    # 재호출 멱등성
    second = engine.mask_text(result.masked_text)
    assert second.masked_text == result.masked_text

    # project_masked 원문 오프셋 호환성 검증
    segments = [
        {"segment_id": "S0", "original_start": 0, "original_end": len(text)},
        {"segment_id": "S1", "original_start": text.index("앞문장"), "original_end": text.index("뒷문장") + 3},
    ]
    projected_text, projected_segs = project_masked(text, result, segments)
    assert projected_text == result.masked_text
    for seg in projected_segs:
        assert seg["text"] == projected_text[seg["masked_start"]:seg["masked_end"]]
        assert "TARGET" not in seg["text"] and "TAIL" not in seg["text"]


# ---------------------------------------------------------------------------
# 양성 3: detect_ai_document + 실 inspect_request 통합 통과 (INPUT_PRIVACY_BLOCKED 0건)
# ---------------------------------------------------------------------------
def test_ai_document_detector_passes_real_privacy_inspection(tmp_path, monkeypatch):
    body = (
        "준비서면\n"
        "원고 강태민(010-2468-1357)은 2024. 5. 12. 훈령 제2021-4호 및 "
        "대법원 94누4615 판결, 86다카1122 판결을 인용하여 주장합니다.\n"
        "신고자 이서윤 (2025. 11. 16.) 참고인 박준형(1998. 3. 4.생) 기록 "
        "계좌 110-234-567890 확인.\n"
    )
    doc = NormalizedDocument(
        document_id="doc_p02_ai",
        filename="강태민_준비서면.pdf",
        mime_type="application/pdf",
        sha256="sha_p02_ai",
        pages=[Page(1, blocks=[Block("b1", body, 1, source_layer="visible_text")])],
    )
    doc.raw_layers["visible_text"] = body

    engine = PIIEngine(PseudonymStore("p02_ai", root=tmp_path))
    dispatched = []

    class InspectingProvider:
        def __init__(self, name):
            self.name = name
            self.available = True
            self.config = SimpleNamespace(name=name, kind="cloud", model=f"{name}-test", enabled=True)

        async def generate(self, request):
            dispatched.append(self.name)
            return LLMResponse(
                True,
                text=json.dumps(
                    {
                        "verdict": "UNCERTAIN",
                        "confidence": 0.45,
                        "reasons": [{"kind": "style", "text": "합성 테스트 응답"}],
                    },
                    ensure_ascii=False,
                ),
            )

    monkeypatch.setattr(router_module, "estimate_call", lambda *a: (Decimal("0.01"), {}))
    rtr = router_module.LLMRouter(
        providers={
            "anthropic": InspectingProvider("anthropic"),
            "openai": InspectingProvider("openai"),
            "gemini": InspectingProvider("gemini"),
        },
        ledger=BudgetLedger(),
    )

    res = asyncio.run(
        detect_ai_document(
            doc,
            citation_findings=[],
            router=rtr,
            mask=lambda s: engine.mask_text(s).masked_text,
            external_ai_policy=ExternalAIPolicy.MASKED,
        )
    )
    assert set(dispatched) == {"anthropic", "openai", "gemini"}
    assert res.signals["llm_failures"] == {}
    assert res.signals["coverage"]["model_executed"] is True
    assert res.signals["coverage"]["inspected_chars"] > 0


# ---------------------------------------------------------------------------
# 양성 4: 필드 종류별 정식 가명 접두사 허용 및 비대상 접두사 차단 구분
# ---------------------------------------------------------------------------
def test_structured_person_fields_distinguish_name_vs_role_prefixes():
    # 순수 인명 키('성명')는 PERSON만 허용하고 PHONE·RRN·ACCOUNT·COMPANY·PII는 차단
    assert inspect_request(LLMRequest("s", json.dumps({"성명": "[PERSON_001]"}, ensure_ascii=False)))["status"] == "PASSED"
    for non_person_prefix in ("COMPANY", "AFFIL", "PHONE", "RRN", "ACCOUNT", "BIZNO", "PII"):
        verdict = inspect_request(
            LLMRequest("s", json.dumps({"성명": f"[{non_person_prefix}_001]"}, ensure_ascii=False))
        )
        assert verdict["status"] == "BLOCKED", f"Prefix {non_person_prefix} should be blocked in 성명"

    # 법인·기관 겸용 역할 키('담당자', '원고', '대표자')는 PERSON·COMPANY·AFFIL 허용, 그 외 차단
    for role_key in ("담당자", "원고", "대표자"):
        for allowed in ("PERSON", "COMPANY", "AFFIL"):
            verdict = inspect_request(
                LLMRequest("s", json.dumps({role_key: f"[{allowed}_012]"}, ensure_ascii=False))
            )
            assert verdict["status"] == "PASSED", f"{role_key} should allow {allowed}: {verdict}"
        for denied in ("PHONE", "RRN", "ACCOUNT", "BIZNO", "PASSPORT", "MILID", "PII"):
            verdict = inspect_request(
                LLMRequest("s", json.dumps({role_key: f"[{denied}_012]"}, ensure_ascii=False))
            )
            assert verdict["status"] == "BLOCKED", f"{role_key} should reject {denied}: {verdict}"


# ---------------------------------------------------------------------------
# 양성 5: 하이픈 포함 행정규칙·호증 및 2자리 구 사건번호 무마스킹
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "legal_text",
    [
        "국방부 훈령 제2021-4호 제3조",
        "행정지침 제2024-12호",
        "갑 제12-12345호증",
        "대법원 1986. 10. 14. 선고 86다카1122 판결",
        "대법원 94누4615 판결",
    ],
)
def test_hyphenated_rule_numbers_and_historical_cases_not_masked(legal_text):
    assert detect(legal_text) == []


# ---------------------------------------------------------------------------
# 양성 6: _ModelInputRenderer 실경로 detect_ai_document 증명 및 다중 패스 _EditTrace
# ---------------------------------------------------------------------------
def test_ai_detector_with_model_input_renderer_attaches_valid_attestation(tmp_path, monkeypatch):
    from packages.common.source_trace import model_input_renderer

    body = "준비서면\n원고 강태민(010-2468-1357)은 2024. 5. 12. 계좌 110-234-567890 기록을 제출합니다.\n"
    doc = NormalizedDocument(
        document_id="doc_p02_renderer",
        filename="강태민_준비서면.pdf",
        mime_type="application/pdf",
        sha256="sha_p02_renderer",
        pages=[Page(1, blocks=[Block("b1", body, 1, source_layer="visible_text")])],
    )
    doc.raw_layers["visible_text"] = body

    engine = PIIEngine(PseudonymStore("p02_renderer", root=tmp_path))
    renderer = model_input_renderer(engine, [], original=False)
    seen_requests = []

    class Provider:
        def __init__(self, name):
            self.name = name
            self.available = True
            self.config = SimpleNamespace(name=name, kind="cloud", model=f"{name}-test", enabled=True)

        async def generate(self, request):
            seen_requests.append(request)
            return LLMResponse(
                True,
                text=json.dumps({"verdict": "UNCERTAIN", "confidence": 0.4, "reasons": []}, ensure_ascii=False),
            )

    monkeypatch.setattr(router_module, "estimate_call", lambda *a: (Decimal("0.01"), {}))
    rtr = router_module.LLMRouter(
        providers={"anthropic": Provider("anthropic"), "openai": Provider("openai"), "gemini": Provider("gemini")},
        ledger=BudgetLedger(),
    )
    res = asyncio.run(
        detect_ai_document(
            doc, citation_findings=[], router=rtr, mask=renderer, external_ai_policy=ExternalAIPolicy.MASKED,
        )
    )
    from packages.llm_router.token_attestation import has_token_attestation
    assert res.used_llm is True
    assert len(seen_requests) == 3
    assert all(has_token_attestation(req) for req in seen_requests)


def test_mask_text_with_edit_trace_handles_multipass_and_preserves_court_address(tmp_path):
    from packages.common.source_trace import _EditTrace

    engine = PIIEngine(PseudonymStore("p02_trace", root=tmp_path))
    sample = "원고 강태민(010-2468-1357) 연락처 및 계좌 110-234-567890"
    trace = _EditTrace(sample, 0, len(sample))
    res = engine.mask_text(sample, _trace=trace)
    assert "강태민" not in res.masked_text and "010-2468-1357" not in res.masked_text
    assert len(trace.origins) == len(res.masked_text)

    # mask_document에서 소송대리인/법원 주소는 보존
    court_body = "서울중앙지방법원 귀중\n서울특별시 서초구 서초중앙로 157\n원고 강태민"
    court_doc = NormalizedDocument(
        document_id="doc_court_addr",
        filename="sample.pdf",
        mime_type="application/pdf",
        sha256="sha_court",
        pages=[Page(1, blocks=[
            Block("b1", "서울중앙지방법원 귀중", 1, source_layer="visible_text"),
            Block("b2", "서울특별시 서초구 서초중앙로 157", 1, source_layer="visible_text"),
            Block("b3", "원고 강태민", 1, source_layer="visible_text"),
        ])],
    )
    masked_doc = engine.mask_document(court_doc, policy=ExternalAIPolicy.MASKED)
    assert "서초중앙로 157" in masked_doc.blocks[1]["text"]
    assert "강태민" not in masked_doc.blocks[2]["text"]


# ---------------------------------------------------------------------------
# 대조군 (Fail-Closed: 위조 가명 토큰 · 순번 상한 · 경계 PII · 증명 변조 차단)
# ---------------------------------------------------------------------------
def test_fail_closed_blocks_unmasked_pii_in_router_and_inspect_request(monkeypatch):
    sent = []

    class Provider:
        name, available = "anthropic", True
        config = SimpleNamespace(name="anthropic", kind="cloud", model="fake", enabled=True)

        async def generate(self, request):
            sent.append(request)
            return LLMResponse(True, text="{}")

    monkeypatch.setattr(router_module, "estimate_call", lambda *a, **k: (Decimal("0.01"), {}))
    ledger = SimpleNamespace(reserve=lambda *a, **k: SimpleNamespace(id="r", amount=Decimal("0.01")), dispatch=lambda *a, **k: None)
    rtr = router_module.LLMRouter(providers={"anthropic": Provider()}, ledger=ledger)

    raw_req = LLMRequest("s", json.dumps({"연락처": "010-2468-1357", "성명": "강태민"}, ensure_ascii=False))
    assert inspect_request(raw_req)["status"] == "BLOCKED"
    outcome = asyncio.run(rtr.run(LLMRole.PRIMARY_REASONER, raw_req, policy=ExternalAIPolicy.MASKED))
    assert sent == []
    assert outcome.executions[0].cost_status == "NOT_SENT"
    assert outcome.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"


@pytest.mark.parametrize(
    "forged_payload",
    [
        {"당사자": "[PERSON_01024681357]"},
        {"성명": "[PERSON_01024681357]"},
        {"당사자": "[PHONE_01024681357]"},
        {"당사자": "[RRN_7805121234567]"},
        {"당사자": "PERSON_01024681357"},
        {"성명": "PERSON_01024681357"},
        {"내용": "[PHONE_010]-2468-1357"},
        {"내용": "[PHONE_010] 2468-1357"},
        {"내용": "010-[PERSON_246]-1357"},
        {"내용": "780512-[PERSON_123]4567"},
        {"내용": "110-[ACCOUNT_234]-567890"},
    ],
)
def test_forged_pii_digit_and_bridged_tokens_blocked_before_provider(forged_payload, monkeypatch):
    sent = []

    class Provider:
        name, available = "openai", True
        config = SimpleNamespace(name="openai", kind="cloud", model="fake", enabled=True)

        async def generate(self, request):
            sent.append(request)
            return LLMResponse(True, text="{}")

    monkeypatch.setattr(router_module, "estimate_call", lambda *a, **k: (Decimal("0.01"), {}))
    ledger = SimpleNamespace(reserve=lambda *a, **k: SimpleNamespace(id="r", amount=Decimal("0.01")), dispatch=lambda *a, **k: None)
    rtr = router_module.LLMRouter(providers={"openai": Provider()}, ledger=ledger)

    req = LLMRequest("s", json.dumps(forged_payload, ensure_ascii=False))
    verdict = inspect_request(req)
    assert verdict["status"] == "BLOCKED", f"Bypass detected for {forged_payload}: {verdict}"
    assert verdict["failure_code"] == "PII_INPUT_BLOCKED"

    outcome = asyncio.run(rtr.run(LLMRole.PRIMARY_REASONER, req, policy=ExternalAIPolicy.MASKED))
    assert sent == []
    assert outcome.executions[0].cost_status == "NOT_SENT"
    assert outcome.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"


@pytest.mark.parametrize(
    "spoofed_payload",
    [
        {"성명": "[PERSON_001] 박서준"},
        {"대표자": "박서준"},
        {"성명": "[FAKEPREFIX_001]"},
        {"담당자": "미확인문자열!"},
        {"성명": "[PERSON_001"},
        {"성명": "PERSON_001]"},
        {"성명": "[PERSON_001_extra]"},
        {"성명": "PERSON_001 extra"},
        {"성명": "[PERSON_000]"},
        {"성명": "[PERSON_1000]"},
        {"성명": "PERSON_000"},
    ],
)
def test_fail_closed_rejects_malformed_brackets_bounds_and_suffixes(spoofed_payload):
    req = LLMRequest("s", json.dumps(spoofed_payload, ensure_ascii=False))
    verdict = inspect_request(req)
    assert verdict["status"] == "BLOCKED", f"Expected BLOCKED for {spoofed_payload}: {verdict}"
    assert verdict["failure_code"] == "PII_INPUT_BLOCKED"


def test_pseudonym_store_enforces_upper_sequence_bound(tmp_path):
    store = PseudonymStore("p02_cap", root=tmp_path)
    store._counters["PERSON"] = 999
    with pytest.raises(ValueError):
        store.pseudonym_for("PERSON", "강태민")


def test_token_attestation_binds_to_request_and_blocks_copy_mutation_and_injection(tmp_path, monkeypatch):
    from packages.llm_router.token_attestation import bind_masked_tokens

    engine = PIIEngine(PseudonymStore("p02_att", root=tmp_path))
    masked = engine.mask_text("원고 강태민")
    assert set(masked.replacements.keys()) == {"PERSON_001"}

    # 1. 실제 발급 토큰이 바인딩된 해당 요청은 통과
    valid_req = bind_masked_tokens(
        LLMRequest("s", json.dumps({"성명": "[PERSON_001]", "내용": masked.masked_text}, ensure_ascii=False)),
        masked.replacements.keys(),
    )
    assert inspect_request(valid_req)["status"] == "PASSED"

    # 2. 같은 증명 요청 안에 비증명 토큰([PERSON_002] 또는 공백 전화 결합)을 끼워 넣으면 차단
    injected_person = bind_masked_tokens(
        LLMRequest("s", json.dumps({"성명": "[PERSON_002]"}, ensure_ascii=False)),
        masked.replacements.keys(),
    )
    assert inspect_request(injected_person)["status"] == "BLOCKED"
    assert inspect_request(injected_person)["failure_code"] == "PII_INPUT_BLOCKED"

    # 3. 다른 요청으로 inspection_source(token attestation) 객체만 복사하면 fail-closed (INPUT_CONTRACT_VIOLATION + NOT_SENT)
    sent = []

    class Provider:
        name, available = "anthropic", True
        config = SimpleNamespace(name="anthropic", kind="cloud", model="fake", enabled=True)

        async def generate(self, request):
            sent.append(request)
            return LLMResponse(True, text="{}")

    monkeypatch.setattr(router_module, "estimate_call", lambda *a, **k: (Decimal("0.01"), {}))
    ledger = SimpleNamespace(reserve=lambda *a, **k: SimpleNamespace(id="r", amount=Decimal("0.01")), dispatch=lambda *a, **k: None)
    rtr = router_module.LLMRouter(providers={"anthropic": Provider()}, ledger=ledger)

    copied_req = LLMRequest(
        "s",
        json.dumps({"성명": "[PERSON_001]", "추가": "변조"}, ensure_ascii=False),
        inspection_source=valid_req.inspection_source,
    )
    copied_verdict = inspect_request(copied_req)
    assert copied_verdict["status"] == "BLOCKED"
    assert copied_verdict["failure_code"] == "PII_INPUT_BLOCKED"
    assert "token_attestation" in copied_verdict.get("contract_failures", [])

    outcome = asyncio.run(rtr.run(LLMRole.PRIMARY_REASONER, copied_req, policy=ExternalAIPolicy.MASKED))
    assert sent == []
    assert outcome.executions[0].cost_status == "NOT_SENT"
    assert outcome.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"

    # 4. 토큰 없이 증명만 복사한 요청도 INPUT_CONTRACT_VIOLATION + NOT_SENT로 차단
    contract_only_req = LLMRequest(
        "s",
        json.dumps({"내용": "변조"}, ensure_ascii=False),
        inspection_source=valid_req.inspection_source,
    )
    contract_only_verdict = inspect_request(contract_only_req)
    assert contract_only_verdict["status"] == "BLOCKED"
    assert contract_only_verdict["failure_code"] == "INPUT_CONTRACT_VIOLATION"
    assert "token_attestation" in contract_only_verdict.get("contract_failures", [])
    outcome2 = asyncio.run(rtr.run(LLMRole.PRIMARY_REASONER, contract_only_req, policy=ExternalAIPolicy.MASKED))
    assert sent == []
    assert outcome2.executions[0].cost_status == "NOT_SENT"
    assert outcome2.executions[0].input_privacy["failure_code"] == "INPUT_CONTRACT_VIOLATION"


def test_real_vehicle_and_contact_pii_still_detected():
    assert any(m.kind == "VEHICLE" for m in detect("차량번호 12가 3456 확인"))
    assert any(m.kind == "PHONE" for m in detect("연락처 010-2468-1357"))
    assert any(m.kind == "RRN" for m in detect("주민번호 780512-1******"))


def test_privacy_masked_value_and_detect_redos_linear():
    import time
    from packages.llm_router.privacy import _uncertain_person_value

    adversarial_value = "[PERSON_001], " * 2000 + "박서준"
    t0 = time.perf_counter()
    assert _uncertain_person_value(adversarial_value, explicit_name=True) is True
    assert time.perf_counter() - t0 < 0.1

    adversarial_text = ("[PERSON_01024681357] " * 200) + ("010-" + "[PERSON_001]-" * 50)
    t1 = time.perf_counter()
    detect(adversarial_text)
    assert time.perf_counter() - t1 < 0.25
