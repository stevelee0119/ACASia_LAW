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
# 양성 4: 모든 KIND_PREFIX 가명 토큰이 구조화 인명/역할 필드에서 허용됨
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("prefix", PSEUDONYM_PREFIXES)
def test_structured_person_fields_accept_all_canonical_pseudonym_prefixes(prefix):
    req = LLMRequest(
        system="s",
        user=json.dumps({"당사자": f"[{prefix}_001]", "담당자": f"[{prefix}_012]"}, ensure_ascii=False),
    )
    verdict = inspect_request(req)
    assert verdict["status"] == "PASSED", f"Prefix {prefix} wrongly blocked: {verdict}"


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
# 대조군 (Fail-Closed 계약 유지 검증 4건)
# ---------------------------------------------------------------------------
def test_fail_closed_blocks_unmasked_pii_in_router_and_inspect_request(monkeypatch):
    sent = []

    class Provider:
        name, available = "anthropic", True
        config = SimpleNamespace(name="anthropic", kind="cloud", model="fake", enabled=True)

        async def generate(self, request):
            sent.append(request)
            return LLMResponse(True, text="{}")

    monkeypatch.setattr(router_module, "estimate_call", lambda *a: (Decimal("0.01"), {}))
    ledger = SimpleNamespace(reserve=lambda *a, **k: SimpleNamespace(id="r", amount=Decimal("0.01")), dispatch=lambda *a, **k: None)
    rtr = router_module.LLMRouter(providers={"anthropic": Provider()}, ledger=ledger)

    raw_req = LLMRequest("s", json.dumps({"연락처": "010-2468-1357", "성명": "강태민"}, ensure_ascii=False))
    assert inspect_request(raw_req)["status"] == "BLOCKED"
    outcome = asyncio.run(rtr.run(LLMRole.PRIMARY_REASONER, raw_req, policy=ExternalAIPolicy.MASKED))
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
    ],
)
def test_fail_closed_rejects_token_suffix_spoofing_and_unknown_prefixes(spoofed_payload):
    req = LLMRequest("s", json.dumps(spoofed_payload, ensure_ascii=False))
    verdict = inspect_request(req)
    assert verdict["status"] == "BLOCKED"
    assert verdict["failure_code"] == "PII_INPUT_BLOCKED"


def test_real_vehicle_and_contact_pii_still_detected():
    assert any(m.kind == "VEHICLE" for m in detect("차량번호 12가 3456 확인"))
    assert any(m.kind == "PHONE" for m in detect("연락처 010-2468-1357"))
    assert any(m.kind == "RRN" for m in detect("주민번호 780512-1******"))
