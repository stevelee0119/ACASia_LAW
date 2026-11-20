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

from tests.perf_scaling import assert_within


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

    # 0. 집합/목록 기반 호출은 TypeError로 거부 (per-field, per-occurrence provenance 필수)
    with pytest.raises(TypeError):
        bind_masked_tokens(
            LLMRequest("s", json.dumps({"내용": masked.masked_text}, ensure_ascii=False)),
            masked.replacements.keys(),
        )

    # 1. 실제 발급 토큰이 필드별 위치·내용 해시와 함께 바인딩된 요청은 통과
    valid_req = bind_masked_tokens(
        LLMRequest("s", json.dumps({"성명": "[PERSON_001]", "내용": masked.masked_text}, ensure_ascii=False)),
        {
            "user.성명": ("[PERSON_001]", ((0, 12, "PERSON_001"),)),
            "user.내용": masked,
        },
    )
    assert inspect_request(valid_req)["status"] == "PASSED"

    # 2. 같은 증명 요청 안에 비증명 토큰([PERSON_002])을 끼워 넣으면 차단
    injected_person = bind_masked_tokens(
        LLMRequest("s", json.dumps({"성명": "[PERSON_002]"}, ensure_ascii=False)),
        {"user.내용": masked},
    )
    assert inspect_request(injected_person)["status"] == "BLOCKED"
    assert inspect_request(injected_person)["failure_code"] == "PII_INPUT_BLOCKED"

    # 3. 다른 요청으로 inspection_source(token attestation) 객체만 복사하면 fail-closed (PII_INPUT_BLOCKED + NOT_SENT)
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


# ---------------------------------------------------------------------------
# Round 2 재현: 동일 요청 내 정상 발급 토큰([PERSON_010]/[PHONE_010]) 존재 시에도
#              별도 공격자 필드 또는 비증명 중복 결합 변형은 모두 BLOCKED + NOT_SENT
# ---------------------------------------------------------------------------
def _seed_pseudonyms_to_009(engine: PIIEngine) -> None:
    prior_names = [
        "고하은", "구도윤", "권서연", "길지후", "남수아",
        "노현우", "도하율", "류시우", "문채원",
    ]
    for idx, name in enumerate(prior_names, 1):
        res = engine.mask_text(f"원고 {name} 연락처 010-7700-000{idx}")
        assert f"PERSON_00{idx}" in res.replacements
        assert f"PHONE_00{idx}" in res.replacements


@pytest.mark.parametrize(
    "attack_text",
    [
        "[PERSON_010] 2468-1357",
        "[PHONE_010] 2468-1357",
        "[PERSON_010] 1234-5678",
    ],
)
def test_round2_repro_duplicate_token_in_separate_field_and_splice_blocked(attack_text, tmp_path, monkeypatch):
    from packages.common.source_trace import model_input_renderer
    from packages.llm_router.token_attestation import bind_masked_tokens

    engine = PIIEngine(PseudonymStore("p02_round2_repro", root=tmp_path))
    _seed_pseudonyms_to_009(engine)
    renderer = model_input_renderer(engine, [], original=False)

    # 10번째 인물/전화번호를 실제 렌더러로 마스킹 -> PERSON_010, PHONE_010 정식 발급
    safe_masked, safe_spans = renderer.mask_attested("참고인 배도현 연락처 010-5555-0010")
    assert "[PERSON_010]" in safe_masked
    assert "[PHONE_010]" in safe_masked

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

    # A. 정상 발급 필드 + 별도 공격자 제어 필드가 한 개의 유효 증명 요청 안에 공존
    req_separate = bind_masked_tokens(
        LLMRequest(
            "system_round2",
            json.dumps({"safe_field": safe_masked, "attacker_field": attack_text}, ensure_ascii=False),
        ),
        {"user.safe_field": (safe_masked, safe_spans)},
    )
    verdict_sep = inspect_request(req_separate)
    assert verdict_sep["status"] == "BLOCKED", f"Bypass in separate field for {attack_text}: {verdict_sep}"
    assert verdict_sep["failure_code"] == "PII_INPUT_BLOCKED"

    out_sep = asyncio.run(rtr.run(LLMRole.PRIMARY_REASONER, req_separate, policy=ExternalAIPolicy.MASKED))
    assert sent == []
    assert out_sep.executions[0].cost_status == "NOT_SENT"
    assert out_sep.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"

    # B. 한 필드 앞부분 토큰만 provenance로 증명되고 뒤에 비증명 중복 + 전화번호가 접합된 경우
    spliced_val = f"{safe_masked} {attack_text}"
    req_spliced = bind_masked_tokens(
        LLMRequest("system_round2", json.dumps({"mixed_field": spliced_val}, ensure_ascii=False)),
        {"user.mixed_field": (spliced_val, safe_spans)},
    )
    verdict_spliced = inspect_request(req_spliced)
    assert verdict_spliced["status"] == "BLOCKED", f"Bypass in spliced field for {attack_text}: {verdict_spliced}"
    assert verdict_spliced["failure_code"] == "PII_INPUT_BLOCKED"

    out_spliced = asyncio.run(rtr.run(LLMRole.PRIMARY_REASONER, req_spliced, policy=ExternalAIPolicy.MASKED))
    assert sent == []
    assert out_spliced.executions[0].cost_status == "NOT_SENT"
    assert out_spliced.executions[0].input_privacy["failure_code"] == "PII_INPUT_BLOCKED"


def test_duplicate_legitimate_occurrences_and_multipass_spans_and_pii_type_keys(tmp_path):
    from packages.common.source_trace import model_input_renderer
    from packages.llm_router.token_attestation import bind_masked_tokens
    from packages.pii_engine import engine as engine_mod

    engine = PIIEngine(PseudonymStore("p02_dup_spans", root=tmp_path))
    _seed_pseudonyms_to_009(engine)
    renderer = model_input_renderer(engine, [], original=False)

    # 동일 필드 내 정당한 중복 출현 (둘 다 마스킹기에서 생성)
    dup_masked, dup_spans = renderer.mask_attested("원고 배도현 주장과 원고 배도현 진술 (2025. 11. 16.)")
    assert dup_masked.count("[PERSON_010]") == 2
    assert len(dup_spans) == 2

    req_ok = bind_masked_tokens(
        LLMRequest("s", json.dumps({"summary": dup_masked}, ensure_ascii=False)),
        {"user.summary": (dup_masked, dup_spans)},
    )
    assert inspect_request(req_ok)["status"] == "PASSED"

    # 두 번째 출현의 span이 빠지면(첫 번째만 증명) 두 번째 출현이 비증명이지만 정식 날짜 인접은 통과,
    # 반면 비증명 중복 뒤에 전화 꼬리가 붙으면 차단됨을 구분
    spliced_text = f"{dup_masked} [PERSON_010] 2468-1357"
    req_third_forged = bind_masked_tokens(
        LLMRequest("s", json.dumps({"summary": spliced_text}, ensure_ascii=False)),
        {"user.summary": (spliced_text, dup_spans)},
    )
    assert inspect_request(req_third_forged)["status"] == "BLOCKED"

    # _PII_TYPE_KEYS ("연락처": value -> "연락처: " + value) 오프셋 보정 검증
    contact_masked, contact_spans = renderer.mask_attested("010-5555-0010")
    # 010-5555-0010을 날짜 문맥과 함께 구성해 비증명 시 경계 위험 확인
    contact_with_date = f"{contact_masked} (2025. 11. 16.)"
    req_pii_key_ok = bind_masked_tokens(
        LLMRequest("s", json.dumps({"연락처": contact_with_date}, ensure_ascii=False)),
        {"user.연락처": (contact_with_date, contact_spans)},
    )
    assert inspect_request(req_pii_key_ok)["status"] == "PASSED"

    # 다중 패스 token_spans 전파 검증
    orig_detect = engine_mod.detect
    text = "앞문장 AB-TARGET-CDEF-TAIL 뒷문장"

    def multi_fake_detect(s, *, block_id=None, page=None):
        hits = []
        idx1 = s.find("AB-TARGET")
        if idx1 >= 0:
            hits.append(PIIMatch("PHONE", s[idx1:idx1 + 9], idx1, idx1 + 9, block_id, page, 0.95))
            hits.append(PIIMatch("ACCOUNT", s[idx1 + 2:idx1 + 14], idx1 + 2, idx1 + 14, block_id, page, 0.9))
        idx2 = s.find("-CDEF-TAIL")
        if idx2 >= 0 and s[idx2 - 1] == "]":
            hits.append(PIIMatch("PII", s[idx2:idx2 + 10], idx2, idx2 + 10, block_id, page, 0.9))
        return hits

    engine_mp = PIIEngine(PseudonymStore("p02_mp_spans", root=tmp_path))
    prev = engine_mod.detect
    engine_mod.detect = multi_fake_detect
    try:
        res_mp = engine_mp.mask_text(text)
    finally:
        engine_mod.detect = prev
    assert len(res_mp.token_spans) == 2
    for ts, te, bare in res_mp.token_spans:
        assert res_mp.masked_text[ts:te] == f"[{bare}]"
    assert orig_detect is not None


# ---------------------------------------------------------------------------
# 통합 시험: argument_validity_verifier, rag_engine.review_document, LLMRouter.cascade
# ---------------------------------------------------------------------------
def test_consumer_integrations_propagate_per_occurrence_provenance(tmp_path, monkeypatch):
    from packages.common.schemas import Citation
    from packages.common.enums import CitationType
    from packages.common.source_trace import model_input_renderer
    from packages.legal_engine.argument_validity_verifier import verify_argument_validity
    from packages.legal_engine.evidence_pack import build_evidence_pack, project_masked, projected_token_spans, render
    from packages.llm_router.token_attestation import has_token_attestation
    from packages.rag_engine.review import review_document

    engine = PIIEngine(PseudonymStore("p02_consumers", root=tmp_path))
    _seed_pseudonyms_to_009(engine)
    renderer = model_input_renderer(engine, [], original=False)

    # 1. argument_validity_verifier (배치 + 잘림 1건 재시도 경로)
    arg_body = "원고 배도현(010-5555-0010)은 대법원 94누4615 판결 및 대법원 86다카1122 판결(2025. 11. 16.)을 근거로 주장합니다."
    arg_doc = NormalizedDocument(
        document_id="doc_arg", filename="배도현_서면.pdf", mime_type="application/pdf", sha256="sha_arg",
        pages=[Page(1, blocks=[Block("b1", arg_body, 1, source_layer="visible_text")])],
    )
    arg_doc.raw_layers["visible_text"] = arg_body
    cit1 = Citation(citation_id="c1", document_id="doc_arg", type=CitationType.CASE, raw_text="대법원 94누4615 판결", page=1, context=arg_body)
    cit2 = Citation(citation_id="c2", document_id="doc_arg", type=CitationType.CASE, raw_text="대법원 86다카1122 판결", page=1, context=arg_body)
    verdicts = [
        {"citation_id": cit1.citation_id, "status": "NOT_FOUND", "levels": {}, "official_record": None},
        {"citation_id": cit2.citation_id, "status": "NOT_FOUND", "levels": {}, "official_record": None},
    ]

    sent_arg = []

    class ArgProvider:
        def __init__(self, name, truncate_first=False):
            self.name = name
            self.available = True
            self.truncate_first = truncate_first
            self.calls = 0
            self.config = SimpleNamespace(name=name, kind="cloud", model=f"{name}-test", enabled=True)

        async def generate(self, request):
            self.calls += 1
            sent_arg.append(request)
            if self.truncate_first and self.calls == 1:
                return LLMResponse(False, text="", error="OUTPUT_TRUNCATED")
            req_items = json.loads(request.user)["items"]
            return LLMResponse(
                True,
                text=json.dumps({
                    "overall_summary": "검토 완료",
                    "rows": [
                        {
                            "item_id": item["item_id"],
                            "claim_text": "주장",
                            "validity_verdict": "판단 불가",
                            "legal_reasoning": "확인 필요",
                            "recommended_check": "원문 대조",
                        }
                        for item in req_items
                    ],
                }, ensure_ascii=False),
            )

    monkeypatch.setattr(router_module, "estimate_call", lambda *a, **k: (Decimal("0.01"), {}))
    rtr = router_module.LLMRouter(
        providers={"anthropic": ArgProvider("anthropic"), "openai": ArgProvider("openai", truncate_first=True)},
        ledger=BudgetLedger(),
    )
    arg_res = asyncio.run(verify_argument_validity(
        arg_doc, [cit1, cit2], verdicts, [],
        router=rtr, external_ai_policy=ExternalAIPolicy.MASKED, mask=renderer,
    ))
    assert len(sent_arg) == 4  # anthropic 배치 1 + openai 배치 1(잘림) + openai 단건 2건
    assert all(has_token_attestation(req) for req in sent_arg)
    assert all(len(row.ai_opinions) == 2 for row in arg_res.rows)

    # 2. rag_engine.review_document (korean_law_review_profile=True + >1000자 주장 슬라이싱)
    long_claim = ("원고 배도현(010-5555-0010)의 손해배상 청구 주장은 구체적 사실관계에 기초합니다. " * 30).strip()
    rag_body = f"문서 서두 원고 배도현.\n{long_claim}"
    rag_doc = NormalizedDocument(
        document_id="doc_rag", filename="참고검토.pdf", mime_type="application/pdf", sha256="sha_rag",
        pages=[Page(1, blocks=[Block("b1", rag_body, 1, source_layer="visible_text")])],
    )
    rag_doc.raw_layers["visible_text"] = rag_body
    doc_result = SimpleNamespace(
        document_id="doc_rag", filename="참고검토.pdf", normalized=rag_doc, quarantined=False,
        findings=[], claims=[{"claim_id": "clm1", "text": long_claim}],
        engine_data={},
    )
    ref_hit = {
        "source_id": "R1",
        "file_id": "df1",
        "title": "배도현 관련 계약자료.pdf",
        "text": "계약 당사자 배도현(010-5555-0010)은 2025. 11. 16. 합의서를 작성함.",
        "folder_path": "/",
        "page": 1,
        "relevance": 0.9,
        "text_coverage": 0.8,
        "shared_terms": ["배도현"],
        "source_type": "CONTRACT",
        "role": "REFERENCE",
    }

    class FakeRefLib:
        summary = {"status": "READY", "folder_id": "fld1", "snapshot_hash": "snap_consumers"}

        def select(self, query_text):
            return {"sources": [dict(ref_hit)], "files_selected": 1, "decision": "SELECTED", "reason": "SELECTED"}

    rag_reqs = []

    class RagProvider:
        name, available = "anthropic", True
        config = SimpleNamespace(name="anthropic", kind="cloud", model="rag-test", enabled=True)

        async def generate(self, request):
            rag_reqs.append(request)
            if "claim_assessments" in (request.system or "") or "relationship" in (request.system or ""):
                return LLMResponse(True, text=json.dumps({
                    "observations": [], "claim_assessments": [], "unassessed_reason": "없음",
                }, ensure_ascii=False))
            return LLMResponse(True, text=json.dumps({"observations": []}, ensure_ascii=False))

    from packages.common.enums import VerificationProfile

    rag_rtr = router_module.LLMRouter(providers={"anthropic": RagProvider()}, ledger=BudgetLedger())
    rag_rtr.settings = SimpleNamespace(**{**vars(rag_rtr.settings), "korean_law_review_profile": True})
    rag_ctx = SimpleNamespace(
        external_ai_policy=ExternalAIPolicy.MASKED,
        profile=VerificationProfile.STANDARD,
        korean_law_review_profile=True,
        requested_issues=["배도현 관련 쟁점"],
    )
    rag_review = review_document(doc_result, FakeRefLib(), rag_rtr, rag_ctx, pii=engine)
    assert rag_review["model_executed"] is True
    assert len(rag_reqs) >= 1
    assert all(has_token_attestation(req) for req in rag_reqs)

    # 3. LLMRouter.cascade + projected_token_spans / doc_mask.token_spans + unattested question 차단
    official_full = "판결 이유 원고 배도현(010-5555-0010)은 2025. 11. 16. 계약을 체결하였다."
    pack = build_evidence_pack(official_full, quotes=[], claim=official_full, structured=[], budget=2000)
    official_mask = engine.mask_text(official_full)
    _, projected = project_masked(official_full, official_mask, pack["segments"])
    doc_mask = engine.mask_text("준비서면 원고 배도현(010-5555-0010) 주장 (2025. 11. 16.)")
    source_text = render([seg["text"] for seg in projected])

    cascade_reqs = []

    class CascadeProvider:
        def __init__(self, name):
            self.name = name
            self.available = True
            self.config = SimpleNamespace(name=name, kind="cloud", model=f"{name}-cas", enabled=True)

        async def generate(self, request):
            cascade_reqs.append(request)
            return LLMResponse(
                True,
                text=json.dumps({
                    "status": "VERIFIED", "confidence": 0.8,
                    "rationale": "정상 확인", "evidence_quotes": [source_text[:10]],
                }, ensure_ascii=False),
            )

    cas_rtr = router_module.LLMRouter(
        providers={"anthropic": CascadeProvider("anthropic"), "openai": CascadeProvider("openai")},
        ledger=BudgetLedger(),
    )
    cas_outcome = asyncio.run(cas_rtr.cascade(
        question="판결과 주장을 대조하라.",
        evidence={
            "official": {
                "case_number": "대법원 2024다123456",
                "source_excerpt": source_text,
                "confirmed_metadata": {"court": "대법원", "case_name": "손해배상"},
            },
            "document": doc_mask.masked_text,
        },
        policy=ExternalAIPolicy.MASKED,
        attested_tokens={
            "official_excerpt_spans": projected_token_spans(official_mask, projected),
            "document_spans": doc_mask.token_spans,
        },
    ))
    assert any(s.get("used") for s in cas_outcome.stages)
    assert all(has_token_attestation(req) for req in cascade_reqs)

    # cascade에 비증명 [PERSON_010] 2468-1357을 question 또는 case_name에 주입하면 즉시 차단 + 0 호출
    cas_rtr2 = router_module.LLMRouter(
        providers={"anthropic": CascadeProvider("anthropic")},
        ledger=BudgetLedger(),
    )
    cas_reqs_before = len(cascade_reqs)
    bad_cas = asyncio.run(cas_rtr2.cascade(
        question="[PERSON_010] 2468-1357 확인하라.",
        evidence={
            "official": {
                "case_number": "대법원 2024다123456",
                "source_excerpt": source_text,
                "confirmed_metadata": {"case_name": "[PHONE_010] 2468-1357"},
            },
            "document": doc_mask.masked_text,
        },
        policy=ExternalAIPolicy.MASKED,
        attested_tokens={
            "official_excerpt_spans": projected_token_spans(official_mask, projected),
            "document_spans": doc_mask.token_spans,
        },
    ))
    assert len(cascade_reqs) == cas_reqs_before
    assert not any(s.get("used") for s in bad_cas.stages)
    assert all(e.cost_status == "NOT_SENT" for e in bad_cas.executions)


# ---------------------------------------------------------------------------
# Fail-Closed: PseudonymSequenceLimitError 발생 시 부분 가림 유출·외부 LLM 호출·500 없음
# ---------------------------------------------------------------------------
def test_pseudonym_sequence_limit_fail_closed_across_runtime_paths(tmp_path, monkeypatch):
    from fastapi import HTTPException
    from apps.api.routers import workspace as workspace_router
    from packages.legal_engine.argument_validity_verifier import _context_review
    from packages.pii_engine import PIIEngine as RealPIIEngine, PseudonymSequenceLimitError, PseudonymStore as RealStore
    from packages.rag_engine.review import review_document
    from packages.verification_engine import pipeline as pipeline_mod

    # 1. workspace.external_prompt_texts -> HTTP 422 (부분 가림 텍스트 반환 안 함)
    monkeypatch.setattr(
        workspace_router,
        "project_or_404",
        lambda session, pid: SimpleNamespace(id=pid, external_ai_policy="MASKED"),
    )
    monkeypatch.setattr("packages.pii_engine.PseudonymStore", lambda project_id=None: RealStore(project_id or "cap", root=tmp_path))

    cap_store = RealStore("proj_cap_ws", root=tmp_path)
    cap_store._counters["PERSON"] = 999
    monkeypatch.setattr("packages.pii_engine.PIIEngine", lambda store=None: RealPIIEngine(cap_store))

    with pytest.raises(HTTPException) as exc_info:
        workspace_router.external_prompt_texts(
            "proj_cap_ws",
            workspace_router.ExternalPromptTexts(texts=["원고 강태민 주장"]),
            session=SimpleNamespace(),
        )
    assert exc_info.value.status_code == 422

    # 2. rag_engine.review_document -> UNVERIFIED + PSEUDONYM_SEQUENCE_LIMIT_EXCEEDED + 0 LLM calls
    rag_calls = []

    class NoCallProvider:
        name, available = "anthropic", True
        config = SimpleNamespace(name="anthropic", kind="cloud", model="m", enabled=True)

        async def generate(self, request):
            rag_calls.append(request)
            return LLMResponse(True, text="{}")

    cap_store_rag = RealStore("proj_cap_rag", root=tmp_path)
    cap_store_rag._counters["PERSON"] = 999
    cap_engine_rag = RealPIIEngine(cap_store_rag)

    doc_rag = NormalizedDocument(
        document_id="d_cap", filename="문서.pdf", mime_type="application/pdf", sha256="s_cap",
        pages=[Page(1, blocks=[Block("b1", "원고 강태민 청구", 1, source_layer="visible_text")])],
    )
    doc_rag.raw_layers["visible_text"] = "원고 강태민 청구"
    res_rag = SimpleNamespace(
        document_id="d_cap", filename="문서.pdf", normalized=doc_rag, quarantined=False,
        findings=[], claims=[], engine_data={},
    )
    ref_lib = SimpleNamespace(
        summary={"status": "READY", "folder_id": "f1", "snapshot_hash": "snap_cap"},
        select=lambda *a, **k: {
            "sources": [{"source_id": "R1", "file_id": "d1", "title": "참고.pdf", "text": "원고 박서준", "folder_path": "/", "page": 1}],
            "files_selected": 1,
        },
    )
    monkeypatch.setattr(router_module, "estimate_call", lambda *a, **k: (Decimal("0.01"), {}))
    rtr_nocall = router_module.LLMRouter(providers={"anthropic": NoCallProvider()}, ledger=BudgetLedger())
    rag_out = review_document(
        res_rag, ref_lib, rtr_nocall,
        SimpleNamespace(external_ai_policy=ExternalAIPolicy.MASKED, requested_issues=[]),
        pii=cap_engine_rag,
    )
    assert rag_calls == []
    assert rag_out["status"] == "UNVERIFIED"
    assert rag_out["reason"] == "PSEUDONYM_SEQUENCE_LIMIT_EXCEEDED"
    assert rag_out["sources"] == []
    assert rag_out["model_executed"] is False

    # 3. detect_ai_document & _context_review -> 0 LLM calls, fail-closed
    ai_out = asyncio.run(detect_ai_document(
        doc_rag, citation_findings=[], router=rtr_nocall,
        mask=lambda s: cap_engine_rag.mask_text(s).masked_text,
        external_ai_policy=ExternalAIPolicy.MASKED,
    ))
    assert rag_calls == []
    assert ai_out.signals.get("llm_error") == "PSEUDONYM_SEQUENCE_LIMIT_EXCEEDED"

    ctx_out = _context_review(
        {"citation_id": "c1", "review_id": "r1", "official_record": {"full_text": "원고 강태민 판결"}},
        [],
        mask=lambda s: cap_engine_rag.mask_text(s).masked_text,
    )
    assert ctx_out["status"] == "UNVERIFIED"

    # 4. VerificationPipeline.run -> 처리 실패로 안전 종료, 부분 masked_preview 유출 0, LLM 호출 0
    sample_txt = tmp_path / "cap_brief.txt"
    sample_txt.write_text("준비서면\n원고 강태민(010-2468-1357)은 주장합니다.\n", encoding="utf-8")
    cap_store_pipe = RealStore("proj_cap_pipe", root=tmp_path)
    cap_store_pipe._counters["PERSON"] = 999
    monkeypatch.setattr(pipeline_mod, "PseudonymStore", lambda project_id="default": cap_store_pipe)

    pipe = pipeline_mod.VerificationPipeline(router=rtr_nocall)
    pipe_res = pipe.run(
        "run_cap",
        pipeline_mod.ProjectContext(project_id="proj_cap_pipe"),
        [pipeline_mod.DocumentInput(document_id="d_pipe", path=str(sample_txt), filename="cap_brief.txt")],
    )
    assert rag_calls == []
    assert len(pipe_res.documents) == 1
    assert pipe_res.documents[0].masked_preview == {}
    assert any("999" in err or "상한" in err for err in pipe_res.errors)


def test_real_vehicle_and_contact_pii_still_detected():
    assert any(m.kind == "VEHICLE" for m in detect("차량번호 12가 3456 확인"))
    assert any(m.kind == "PHONE" for m in detect("연락처 010-2468-1357"))
    assert any(m.kind == "RRN" for m in detect("주민번호 780512-1******"))


def test_privacy_masked_value_and_detect_redos_linear():
    """가명 토큰 반복 입력의 ReDoS 선형성.

    상한(0.1초·0.25초)은 그대로 두고, 측정 방식만 같은 엔진의 선형성 시험
    `tests/test_pii_redos_linear.py`와 맞춘다: ROUNDS회 반복의 **최솟값**을 쓰고
    측정 구간에는 GC를 멈춘다(TK-142에서 채택한 방식). 한 번만 재면 실행기 부하가
    그 한 번에 몰릴 때 선형성과 무관하게 넘친다 — CI PostgreSQL 잡에서 단일 측정이
    0.5612초로 넘쳤고, 같은 실행의 서비스 로그에 체크포인트 `write=66.498 s`가 찍혀
    I/O 경합이 확인됐다(로컬 median 0.0125초, 한도 대비 20배 여유).
    """
    import gc
    import time
    from packages.llm_router.privacy import _uncertain_person_value

    rounds = 5

    def _best(func, arg):
        """반복 측정 최솟값과 마지막 반환값. 측정 구간 GC 중지는 finally로 복구한다."""
        best = float("inf")
        result = None
        gc.collect()
        gc.disable()
        try:
            for _ in range(rounds):
                started = time.perf_counter()
                result = func(arg)
                best = min(best, time.perf_counter() - started)
        finally:
            gc.enable()
        return result, best

    adversarial_value = "[PERSON_001], " * 2000 + "박서준"
    verdict, elapsed_value = _best(
        lambda value: _uncertain_person_value(value, explicit_name=True), adversarial_value)
    assert verdict is True
    assert_within(elapsed_value, 0.1, f'가명 토큰 반복 값 판정 {elapsed_value:.4f}초')

    adversarial_text = ("[PERSON_01024681357] " * 200) + ("010-" + "[PERSON_001]-" * 50)
    _, elapsed_detect = _best(detect, adversarial_text)
    assert_within(elapsed_detect, 0.25, f'가명 토큰 반복 본문 탐지 {elapsed_detect:.4f}초')
