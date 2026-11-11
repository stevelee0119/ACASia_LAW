"""TK-76 3주기 EVI-DATE PR-B(T2·T3) 및 조건부 승인 D1~D3 검증 시험.

- T2: 같은 날 시각 역전(SAME_DAY_TIME_INVERSION) 및 처분·결정 → 통지·발송 선후 규칙(DISPOSITION_BEFORE_NOTICE)
- T3: 명시적 인과·근거 연결구 일자 역전(EXPLICIT_CAUSAL_BASIS_INVERSION)
- D1: 처분→통지 statute 문자열("근로기준법 제27조 제1항(해고 통지)·논리칙") 및 사전통지 제외
- D2: TIME_RE 경계 보강('8시간 근무', '24시간 이내', '제1시', '3시점', '1시기' 오탐 0)
- D3: T3 순행·수식 인과 명사구 절 경계 제한 및 법령 조문('제N조에 따라')·규범 시행일('시행되는/시행된 규정에 따라') 제외
- 2-2 다: 어순·연결 어미·어휘/형식 3대 변형 시험 및 2만 자 선형 시간 점검
"""

from __future__ import annotations

from pathlib import Path
import time
import pytest

from packages.claim_engine.date_verifier import (
    TIME_RE,
    _CAUSAL_BASIS_REV_RE,
    _CAUSAL_NP_WITH_DATE_RE,
    _parse_time_match,
    verify_dates_in_document,
)
from packages.common.enums import EvidenceGrade, FindingType, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.verification_engine.pipeline import (
    DocumentInput,
    ProjectContext,
    VerificationPipeline,
)


def _make_doc(text: str, doc_id: str = "doc-tk76-date-t2-t3") -> NormalizedDocument:
    block = Block(block_id="b1", text=text, page=1, visible=True, source_layer="visible_text")
    page = Page(page_number=1, blocks=[block], width=595.0, height=842.0)
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="0000000000000000000000000000000000000000000000000000000000000000",
        pages=[page],
    )


def _inversion_findings(text: str):
    doc = _make_doc(text)
    return [
        f
        for f in verify_dates_in_document(doc)
        if f.type == FindingType.TIMELINE_CONTRADICTION
        and f.confidence_features.get("rule_id") == "claim_engine.date_verifier:TEMPORAL_EVENT_INVERSION"
    ]


# ==============================================================================
# 1. 메모 5.1절 합성 문장 13건 (T2 양성 3·대조 3, T3 양성 3·대조 4) + D1 검증
# ==============================================================================


class TestMemoSection51SyntheticCases:
    """설계 메모 5.1절 합성 양성 6건·대조 7건 및 D1 근거 검증."""

    def test_t2_pos_1_same_day_disposition_before_notice_korean_time(self):
        # T2-Pos-1: 같은 날 처분 의결(오후 4시 30분)보다 통지(오전 11시 20분)가 앞선 모순
        text = (
            "피신청인은 2025. 4. 10. 오후 4시 30분에 영업정지 처분을 의결하고, "
            "같은 날 오전 11시 20분에 신청인에게 위 영업정지 처분을 통지하였다."
        )
        findings = _inversion_findings(text)
        assert len(findings) == 1
        f = findings[0]
        assert f.status == VerificationStatus.CONTRADICTED
        assert f.evidence_grade == EvidenceGrade.B
        assert f.confidence_features.get("sub_rule") == "DISPOSITION_BEFORE_NOTICE"
        assert f.confidence_features.get("statute") == "근로기준법 제27조 제1항(해고 통지)·논리칙"
        assert f.confidence_features.get("cause_date") == "2025-04-10"
        assert f.confidence_features.get("effect_date") == "2025-04-10"
        assert f.confidence_features.get("cause_time") == "오후 4시 30분"
        assert f.confidence_features.get("effect_time") == "오전 11시 20분"

    def test_t2_pos_2_same_day_send_before_receipt_hhmm(self):
        # T2-Pos-2: 같은 날 발송(15:00)보다 도달(09:40)이 앞선 모순
        text = (
            "피고는 2025. 6. 12. 15:00에 계약해지 통지서를 발송하여 "
            "원고에게 같은 날 09:40에 그 통지서가 도달하였다."
        )
        findings = _inversion_findings(text)
        assert len(findings) == 1
        f = findings[0]
        assert f.confidence_features.get("sub_rule") == "SEND_BEFORE_RECEIPT"
        assert f.confidence_features.get("statute") == "민법 제111조"
        assert f.confidence_features.get("cause_time") == "15:00"
        assert f.confidence_features.get("effect_time") == "09:40"

    def test_t2_pos_3_different_date_disposition_before_notice(self):
        # T2-Pos-3: 다른 날짜 해고 결정(8. 20.)보다 해고통지 발송(8. 18.)이 앞선 모순
        text = (
            "인사위원회가 2025. 8. 20. 해고 결정을 내렸는데, "
            "이에 앞서 2025. 8. 18. 원고에게 해고통지를 발송한 바 있다."
        )
        findings = _inversion_findings(text)
        assert len(findings) == 1
        f = findings[0]
        assert f.confidence_features.get("sub_rule") == "DISPOSITION_BEFORE_NOTICE"
        assert f.confidence_features.get("statute") == "근로기준법 제27조 제1항(해고 통지)·논리칙"
        assert f.confidence_features.get("cause_date") == "2025-08-20"
        assert f.confidence_features.get("effect_date") == "2025-08-18"

    @pytest.mark.parametrize(
        "text",
        [
            # T2-Ctrl-1: 같은 날 정상 시각 순서 (10:00 의결 -> 16:00 통지)
            "피신청인은 2025. 4. 10. 오전 10시에 영업정지 처분을 의결하고, 같은 날 오후 4시에 신청인에게 해당 처분을 통지하였다.",
            # T2-Ctrl-2: 사전통지·의견제출 통지 후 본처분 (행정절차법 제21조 정상 절차)
            "피신청인은 2025. 4. 2. 신청인에게 처분 사전통지서를 발송하여 의견제출 기회를 부여한 뒤 2025. 4. 18. 영업정지 처분을 결정하였다.",
            # T2-Ctrl-3: 시각 없는 같은 날 서술 (일자 동일 시 시각 정보 없으면 미발화)
            "피고는 2025. 6. 12. 해지 통지서를 발송하였고 원고는 같은 날 위 통지서를 수령하였다.",
        ],
    )
    def test_t2_controls_zero_fp(self, text: str):
        assert _inversion_findings(text) == []

    def test_t3_pos_1_reverse_causal_basis_inversion(self):
        # T3-Pos-1: 역행 인과 ('그 처분의 사유가 된')
        text = (
            "원고는 2025. 3. 10. 징계해고 처분을 받았으나, "
            "그 처분의 사유가 된 직장 내 비위행위는 2025. 4. 2. 발생하였다."
        )
        findings = _inversion_findings(text)
        assert len(findings) == 1
        f = findings[0]
        assert f.confidence_features.get("sub_rule") == "EXPLICIT_CAUSAL_BASIS_INVERSION"
        assert f.confidence_features.get("cause_date") == "2025-04-02"
        assert f.confidence_features.get("effect_date") == "2025-03-10"

    def test_t3_pos_2_forward_causal_link_inversion(self):
        # T3-Pos-2: 순행 인과 ('개최된 이사회 의결에 따라')
        text = "피고는 2025. 7. 15. 개최된 이사회 의결에 따라 2025. 7. 1. 원고를 해임하였다."
        findings = _inversion_findings(text)
        assert len(findings) == 1
        f = findings[0]
        assert f.confidence_features.get("sub_rule") == "EXPLICIT_CAUSAL_BASIS_INVERSION"
        assert f.confidence_features.get("cause_date") == "2025-07-15"
        assert f.confidence_features.get("effect_date") == "2025-07-01"

    def test_t3_pos_3_predicative_causal_basis_inversion(self):
        # T3-Pos-3: 수식·서술 인과 ('실시된 현장조사 결과에 기초한')
        text = "2025. 5. 1. 부과된 과징금 처분은 2025. 5. 20. 실시된 현장조사 결과에 기초한 것이다."
        findings = _inversion_findings(text)
        assert len(findings) == 1
        f = findings[0]
        assert f.confidence_features.get("sub_rule") == "EXPLICIT_CAUSAL_BASIS_INVERSION"
        assert f.confidence_features.get("cause_date") == "2025-05-20"
        assert f.confidence_features.get("effect_date") == "2025-05-01"

    @pytest.mark.parametrize(
        "text",
        [
            # T3-Ctrl-1: 사후 추인·소급 확인
            "피고는 2025. 3. 1. 긴급 조치를 시행한 뒤, 2025. 3. 15. 개최된 이사회 의결을 통해 위 조치를 사후 추인하였다.",
            # T3-Ctrl-2: 미래 예정 조건
            "2025. 9. 1. 체결될 예정인 협약에 따라 2025. 8. 20. 사전 준비 약정을 체결하였다.",
            # T3-Ctrl-3: 불복·소송·취소 청구 회고 서술
            "원고는 2025. 4. 10. 내려진 과징금 처분에 불복하여 2025. 6. 1. 취소소송을 제기하였다.",
            # T3-Ctrl-4: 정상 시간순 인과 서술 (d_Y <= d_X)
            "피고는 2025. 5. 2. 개최된 징계위원회 의결에 따라 2025. 5. 10. 해고 처분을 하였다.",
        ],
    )
    def test_t3_controls_zero_fp(self, text: str):
        assert _inversion_findings(text) == []


# ==============================================================================
# 2. D2 시각 정규식(TIME_RE) 경계 및 시간 길이 대조 시험
# ==============================================================================


class TestD2TimeRegexBoundaries:
    """D2: TIME_RE가 시간 길이·서수·합성 명사를 시각으로 오인하지 않는지 검증."""

    @pytest.mark.parametrize(
        "non_time_expr",
        [
            "하루 8시간",
            "8시간 근무",
            "24시간 이내",
            "제1시",
            "3시점",
            "1시기",
            "2시각",
            "1시행",
            "3시효",
            "2시장",
            "1시설",
        ],
    )
    def test_time_re_rejects_duration_and_compound_nouns(self, non_time_expr: str):
        assert TIME_RE.search(non_time_expr) is None

    @pytest.mark.parametrize(
        "time_expr,expected_min",
        [
            ("오후 4시 10분", 16 * 60 + 10),
            ("16시", 16 * 60),
            ("10시경", 10 * 60),
            ("09:30", 9 * 60 + 30),
            ("오전 12시 15분", 15),
            ("오후 12시 30분", 12 * 60 + 30),
        ],
    )
    def test_time_re_accepts_valid_time_expressions(self, time_expr: str, expected_min: int):
        m = TIME_RE.search(time_expr)
        assert m is not None
        parsed = _parse_time_match(m)
        assert parsed is not None
        assert parsed[1] == expected_min

    @pytest.mark.parametrize(
        "text",
        [
            "원고는 2025. 4. 10. 하루 8시간 근무를 마친 뒤 같은 날 1시간 연장근로를 신청하였다.",
            "피신청인은 2025. 4. 10. 영업정지 처분을 의결하고 같은 날 24시간 이내에 신청인에게 위 영업정지 처분을 통지하였다.",
            "피고는 2025. 6. 12. 제3시점에 해지 통지서를 발송하였고 원고는 같은 날 제1시기에 그 통지서를 수령하였다.",
        ],
    )
    def test_duration_and_compound_nouns_in_document_do_not_trigger_t2(self, text: str):
        assert _inversion_findings(text) == []


# ==============================================================================
# 3. D3 인과 결합 범위 제한(절 경계·법령 조문·규범 시행일 제외) 시험
# ==============================================================================


class TestD3CausalScopeRestrictions:
    """D3: 날짜와 인과 표지 사이 절 경계, 법령 조문('제N조에 따라'), 규범 시행일 제외 검증."""

    @pytest.mark.parametrize(
        "text",
        [
            # 법령·조문 인용 뒤 '…에 따라'
            "피고는 2025. 7. 15. 개정된 근로기준법 제27조에 따라 2025. 7. 1. 원고에게 해고 사유를 통지하였다.",
            "처분청은 2025. 8. 10. 공포된 행정절차법 제24조 제1항에 따라 2025. 8. 1. 문서로 처분하였다.",
            # 규범 시행일 ('시행되는/시행된 규정에 따라')
            "피고는 2025. 7. 15. 시행된 인사규정에 따라 2025. 7. 1. 징계 처분을 내렸다.",
            "피신청인은 2025. 9. 1. 시행되는 업무지침에 따라 2025. 8. 15. 현장 점검을 실시하였다.",
            # 날짜와 인과 연결 표지 사이에 절 경계(쉼표·연결 어미) 존재
            "2025. 7. 15. 이사회가 개최되었고, 관련 절차에 따라 2025. 7. 1. 체결된 계약을 검토하였다.",
            "피고는 2025. 7. 15. 감사를 실시하였으며, 내부 기준에 근거하여 2025. 7. 1. 지급된 수당을 확인하였다.",
        ],
    )
    def test_d3_statute_norm_and_clause_boundary_controls(self, text: str):
        assert _inversion_findings(text) == []


# ==============================================================================
# 4. 2-2 다: 3대 변형 시험 (어순·연결 어미·어휘/형식 변형)
# ==============================================================================


class TestThreeAxisVariations:
    """2-2 다: 어순·연결 어미·어휘/형식 3대 변형에서 T2·T3가 일반화되어 동작하는지 검증."""

    @pytest.mark.parametrize(
        "text,expected_sub_rule",
        [
            # (a) 어순 변형: 통지 절 선행 + 처분 절 후행 / 피동형 어순 / 한 문장 내 단일 날짜 연속 시각
            (
                "신청인은 2025. 4. 10. 오전 9시 30분에 과징금 처분을 통지받았으나, "
                "피신청인이 위 과징금 처분을 의결한 것은 같은 날 오후 3시 15분이었다.",
                "DISPOSITION_BEFORE_NOTICE",
            ),
            (
                "2025. 4. 10. 오후 5시 10분에 피신청인이 인가취소 처분을 결정하였고 "
                "당일 오전 10시 40분에 신청인에게 위 인가취소 처분이 통보되었다.",
                "DISPOSITION_BEFORE_NOTICE",
            ),
            (
                "피신청인은 2025. 4. 10. 16:20에 영업정지 처분을 내리고 "
                "11:10에 신청인에게 위 영업정지 처분을 통지하였다.",
                "DISPOSITION_BEFORE_NOTICE",
            ),
            # (b) 연결 어미 변형: -며 / -는데 / 마침표 분리 후 '같은 날'
            (
                "피신청인은 2025. 5. 14. 17:00에 직위해제 처분을 명령하며 "
                "같은 날 10:30에 원고에게 위 직위해제 처분을 고지하였다.",
                "DISPOSITION_BEFORE_NOTICE",
            ),
            (
                "피신청인은 2025. 5. 14. 오후 3시에 징계 처분을 결정하였는데, "
                "동일자 오전 9시에 원고에게 해당 처분을 통지하였다.",
                "DISPOSITION_BEFORE_NOTICE",
            ),
            (
                "피신청인은 2025. 5. 14. 오후 4시에 해고 결정을 내렸다. "
                "같은 날 오전 11시에 원고에게 해고통지를 발송하였다.",
                "DISPOSITION_BEFORE_NOTICE",
            ),
            # (c) 어휘·형식 변형: 신청->처분 같은 날 시각 역전 / 서술 순서 연결어 같은 날 시각 역전
            (
                "신청인은 2025. 6. 1. 오후 2시 20분에 변경허가 신청을 제출하였는데, "
                "피신청인은 같은 날 오전 9시 50분에 위 변경허가 신청에 대한 거부처분을 내렸다.",
                "TARGET_BOUND_DISPOSITION",
            ),
            (
                "원고는 2025. 6. 1. 15:30에 소장을 접수한 뒤 "
                "같은 날 10:00에 법원으로부터 보정명령을 송달받았다.",
                "SAME_DAY_TIME_INVERSION",
            ),
        ],
    )
    def test_t2_variations_positive(self, text: str, expected_sub_rule: str):
        findings = _inversion_findings(text)
        assert len(findings) == 1
        assert findings[0].confidence_features.get("sub_rule") == expected_sub_rule

    @pytest.mark.parametrize(
        "text",
        [
            # T3 (a) 어순 변형: 주어절 선행 + '이는 ... 에 따른 것이다' / 결과 일자 주어구 + 부사구 인과
            "피고는 2025. 7. 1. 원고를 해임하였는데, 이는 2025. 7. 15. 개최된 이사회 의결에 따른 것이다.",
            "2025. 7. 1. 단행된 전보발령은 2025. 7. 15. 열린 인사위원회 결정에 근거한 처분이다.",
            # T3 (b) 연결 어미·문장 분리 변형: -고 / -며 / 2문장 분리 역행 인과
            "원고는 2025. 3. 10. 해고 처분을 받았고, 위 해고의 근거가 된 감사 결과는 2025. 4. 2. 확정되었다.",
            "원고는 2025. 3. 10. 정직 처분을 받았으며 그 처분의 원인이 된 비위 사실은 2025. 4. 2. 발생하였다.",
            "원고는 2025. 3. 10. 징계해고 처분을 받았다. 그런데 그 처분의 사유가 된 비위행위는 2025. 4. 2. 발생하였다.",
            # T3 (c) 어휘·날짜 형식 변형: 에 근거하여 / 에 기하여 / 을 사유로 / YYYY년 M월 D일
            "피고는 2025년 7월 15일 열린 징계위원회 결정에 근거하여 2025년 7월 1일 감봉 처분을 내렸다.",
            "처분청은 2025-07-15 이루어진 현지조사 결과에 기하여 2025-07-01 과징금 부과처분을 하였다.",
            "원고는 2025. 7. 15. 발생한 누수 사고를 사유로 2025. 7. 1. 계약 해지를 통보하였다.",
        ],
    )
    def test_t3_variations_positive(self, text: str):
        findings = _inversion_findings(text)
        assert len(findings) == 1
        assert findings[0].confidence_features.get("sub_rule") == "EXPLICIT_CAUSAL_BASIS_INVERSION"


# ==============================================================================
# 5. 파이프라인 진입점(VerificationPipeline.run) 및 2만 자 선형 시간 점검
# ==============================================================================


def test_pipeline_entrypoint_emits_t2_and_t3(tmp_path: Path):
    doc_path = tmp_path / "t2_t3_brief.txt"
    doc_path.write_text(
        "1. 처분 및 통지 경위\n"
        "피신청인은 2025. 4. 10. 오후 4시 30분에 영업정지 처분을 의결하고, "
        "같은 날 오전 11시 20분에 신청인에게 위 영업정지 처분을 통지하였다.\n"
        " 또한 피고는 2025. 7. 15. 개최된 이사회 의결에 따라 2025. 7. 1. 원고를 해임하였다.\n",
        encoding="utf-8",
    )
    pipeline = VerificationPipeline()
    context = ProjectContext(project_id="proj_tk76_t2_t3")
    inputs = [
        DocumentInput(
            document_id="doc_tk76_t2_t3",
            path=str(doc_path),
            filename="t2_t3_brief.txt",
            mime_type="text/plain",
        )
    ]
    run_res = pipeline.run("run_tk76_t2_t3", context, inputs)
    doc_res = run_res.documents[0]
    sub_rules = {
        f.confidence_features.get("sub_rule")
        for f in doc_res.findings
        if f.type == FindingType.TIMELINE_CONTRADICTION
    }
    assert "DISPOSITION_BEFORE_NOTICE" in sub_rules
    assert "EXPLICIT_CAUSAL_BASIS_INVERSION" in sub_rules


def test_new_regexes_linear_time_on_20k_chars():
    unit = (
        "피신청인은 2025. 4. 10. 하루 8시간 근무 기준과 24시간 이내 처리 원칙을 확인하고 "
        "오후 4시 10분에 영업정지 처분을 의결한 뒤 2025. 4. 12. 개정된 규정 제27조에 따라 통지하였다. "
    )
    text_5k = unit * 60
    text_20k = unit * 240
    assert len(text_20k) >= 20000

    def _run_regexes(s: str) -> int:
        c = 0
        for _ in TIME_RE.finditer(s):
            c += 1
        for _ in _CAUSAL_BASIS_REV_RE.finditer(s):
            c += 1
        for _ in _CAUSAL_NP_WITH_DATE_RE.finditer(s):
            c += 1
        return c

    t1 = min(time.perf_counter() - (st := time.perf_counter()) or _run_regexes(text_5k) and (time.perf_counter() - st) for _ in range(3))
    t4 = min(time.perf_counter() - (st := time.perf_counter()) or _run_regexes(text_20k) and (time.perf_counter() - st) for _ in range(3))
    assert t4 < 1.0
    assert t4 / max(t1, 1e-6) < 8.0
