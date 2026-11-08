"""TK-76 3주기 EVI-INCONS 범주 C(문서 안 같은 대상의 두 날짜·시각 모순) 평가 및 변형 시험.

설계 메모(docs/handoff/requests/TK-76_cycle3_evi_incons_c_design_memo.md, N1~N9 및 C1 반영) 검증:
1. 3.1 공개 합성 양성 3건 (유일성 표지 + 다른 날짜, 같은 날 두 시각, 지시어 결속 + 다른 날짜)
2. 3.2 공개 합성 대조 7건 (단계 분리, 처분 결정→통지 분리, 주체·수식어 위치 제외, '…일자' 문서 일자 분리, 차수·부정 제외, 시간 길이·근사 시각 60분 허용, 오기 정정·상대방 서면 탄핵 제외)
3. C1 지시어 정규식(_ANAPHORA_EVENT_RE) 단독 시험 ('위 통지를 발송', '위 통지서는', '그 해지 통지서를' 등)
4. 3대 변형 시험 (어순·날짜 표기, 지시어·유일성·'서' 접미, 복합 사건 명사)
5. N9 기존 EVI.INCONS_INTERNAL_DATE 우선(신규 양보) 검증 및 2만 자 선형 시간 검증
"""
from __future__ import annotations

import time
import pytest

from packages.claim_engine.internal_inconsistency import (
    _ANAPHORA_EVENT_RE,
    _UNIQUENESS_MARKER_RE,
    check_internal_inconsistency,
)
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(text: str) -> NormalizedDocument:
    block = Block(block_id="b1", text=text, page=1, visible=True, source_layer="visible_text")
    return NormalizedDocument(
        document_id="doc-tk76-incons-c",
        filename="doc-tk76-incons-c.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[Page(page_number=1, blocks=[block], width=595.0, height=842.0)],
    )


def _same_event_hits(text: str):
    return [
        f
        for f in check_internal_inconsistency(_doc(text))
        if f.confidence_features.get("rule_id") == "EVI.INCONS_SAME_EVENT_DATETIME"
    ]


@pytest.mark.parametrize(
    "text,expected_noun,val1,val2",
    [
        # 양성 1: 유일성 표지 + 서로 다른 날짜
        (
            "피고는 이 사건과 관련하여 단 한 차례 회신을 보냈는데, 2024년 3월 12일에 그 회신을 발송하였다. "
            "그러나 피고는 위 회신을 2024년 3월 19일에 발송하면서 별도 첨부서류는 동봉하지 않았다.",
            "회신",
            "2024년 3월 12일",
            "2024년 3월 19일",
        ),
        # 양성 2: 유일성/동일 사건 + 같은 날 서로 다른 시각
        (
            "원고는 2024년 6월 5일 단 한 번 해지 통보를 발송하였다. "
            "당시 원고는 같은 날 오전 9시 30분에 해당 해지 통보를 발송하였고, "
            "같은 날 오후 4시 20분에 그 해지 통보를 발송한 직후 담당자에게 연락하였다.",
            "통보",
            "오전 9시 30분",
            "오후 4시 20분",
        ),
        # 양성 3: 지시어 결속('위 시정명령 통지') + 작성자 자신의 서로 다른 날짜 서술 (N8 반영)
        (
            "피신청인은 2024년 8월 14일 신청인에게 시정명령 통지를 발송하였다. "
            "당시 피신청인은 위 시정명령 통지를 2024년 8월 22일 등기우편으로 발송하면서 안내문을 함께 동봉하였다.",
            "통지",
            "2024년 8월 14일",
            "2024년 8월 22일",
        ),
    ],
)
def test_memo_section_3_1_positive_cases(text: str, expected_noun: str, val1: str, val2: str):
    hits = _same_event_hits(text)
    assert len(hits) == 1
    f = hits[0]
    assert f.type == FindingType.FACT_CONTRADICTION
    assert f.evidence_grade == EvidenceGrade.C
    assert f.status == VerificationStatus.SUSPICIOUS
    assert f.severity == Severity.MEDIUM
    excerpt = f.evidence[0].excerpt if f.evidence else ""
    assert expected_noun in excerpt
    assert val1 in excerpt and val2 in excerpt


@pytest.mark.parametrize(
    "text",
    [
        # 대조 1: 같은 사건의 서로 다른 단계 날짜 (작성 DRAFT -> 발송 NOTIFY_SEND -> 도착 ARRIVE_RECEIVE)
        "피고는 2024년 4월 10일 단 한 차례 회신서를 작성하여 2024년 4월 11일 오전 10시에 발송하였고, "
        "위 회신서는 2024년 4월 12일 오후 3시에 원고에게 도착하였다.",
        # 대조 2 (N2): 처분 결정(DECIDE) 후 위 처분 통지(NOTIFY_SEND) 정상 경과
        "피고는 2024년 6월 10일 원고에 대한 정직 처분을 결정하고, 2024년 6월 15일 원고에게 위 처분을 통지하였다.",
        # 대조 3a (N3): 서로 다른 주체(원고 vs 피고)
        "원고는 2024년 3월 4일 단 한 차례 회신을 발송하였고, 피고는 2024년 3월 11일 회신을 발송하였다.",
        # 대조 3b (N3): 수식어 안의 지시어+명사('위 해지 통지에 대한', '위 해지 통지의')
        "피고는 2024년 5월 2일 해지 통지를 발송하였다. "
        "원고는 위 해지 통지에 대한 반박 의견서를 2024년 5월 9일 발송하였고, 위 해지 통지의 내용을 2024년 5월 3일 확인하였다.",
        # 대조 4 (N5): 문서 표시 일자('…일자', DATED) 대 실제 발송일(NOTIFY_SEND)
        "피고가 보낸 위 통지는 2024년 3월 5일자였으나, 실제로 피고는 그 통지를 2024년 3월 8일에 발송하였다.",
        # 대조 5 (N6): 차수 표지('1차·2차') 구분 및 '단 한 번도' 부정 표현
        "원고는 2024년 5월 2일 1차 이행청구 통지를 발송하였고 2024년 5월 16일 2차 이행청구 통지를 발송하였으나, "
        "피고는 단 한 번도 회신하지 않았다.",
        # 대조 6 (N9): 시간 길이('8시간', '24시간 이내') 및 근사 시각('경') 60분 미만 차이
        "신청인은 단 한 차례 답변을 2024년 7월 3일 오후 2시경에 발송하였으며, "
        "하루 8시간 검토와 24시간 이내 회신 원칙에 따라 같은 날 오후 2시 20분경 그 답변을 발송하였다.",
        # 대조 7 (N8): 오기 정정 및 상대방 서면 모순 탄핵 서술('…기재하여 앞뒤가 맞지 않는다')
        "피신청인은 2024년 8월 14일 시정명령 통지를 하였다고 주장하면서 다른 쪽에서는 위 통지를 2024년 8월 22일에 하였다고 기재하여 앞뒤가 맞지 않는다"
        "(준비서면 제3쪽의 8월 15일 기재는 단순 오기이므로 바로잡는다).",
    ],
)
def test_memo_section_3_2_control_cases(text: str):
    assert _same_event_hits(text) == []


def test_c1_anaphora_regex_decomposition():
    """C1 필수 조건: 기본 꼴 오분해 방지 및 '서' 접미 수용, 앞 경계 검증."""
    cases = [
        ("위 통지를 발송하였다", (None, "통지", None)),
        ("위 통지서는 2024. 3. 5.에", (None, "통지", "서")),
        ("그 회신서를 발송하였다", (None, "회신", "서")),
        ("위 답변서에 기재된", (None, "답변", "서")),
        ("그 해지 통지서를 송부하였다", ("해지", "통지", "서")),
        ("위 시정명령 통지를 발송하였다", ("시정명령", "통지", None)),
        ("해당 해지 통보를 보냈다", ("해지", "통보", None)),
    ]
    for text, expected in cases:
        m = _ANAPHORA_EVENT_RE.search(text)
        assert m is not None, text
        assert (m.group("content"), m.group("head"), m.group("doc")) == expected, text

    assert _ANAPHORA_EVENT_RE.search("행위 통지를 하였다") is None
    assert _ANAPHORA_EVENT_RE.search("행동 통지를 하였다") is None
    assert _UNIQUENESS_MARKER_RE.search("단 한 번도 회신하지 않았다") is None


def test_three_axis_variations():
    """3대 변형 시험: 어순·날짜 표기, 지시어·유일성·C1 '서' 접미, 복합 사건 명사 변형."""
    positive_variations = [
        # 변형 1: 점 날짜 표기('2024. 3. 12.') + '같은 달 19일' + C1 '그 해지 통지서를'
        "원고는 2024. 3. 12. 피고에게 해지 통지서를 발송하였다. "
        "그런데 원고는 같은 달 19일 피고에게 그 해지 통지서를 발송하면서 내용증명 우편을 이용하였다.",
        # 변형 2: 유일성 표지 변형('오직 한 번') + '위 답변서를' + 24시간제 시각('10:15' vs '16:40')
        "피고는 2024. 9. 18. 오직 한 번 답변서를 보냈는데, 같은 날 10:15에 해당 답변서를 발송하였고 "
        "뒤에서는 같은 날 16:40에 위 답변서를 발송하였다고 적었다.",
        # 변형 3: 결정/결의 단계(DECIDE) 자체의 두 날짜 모순 ('이 사건 징계 결의')
        "이사회는 2024년 11월 4일 유일한 징계 결의를 하였다. "
        "그러나 이사회는 이 사건 징계 결의를 2024년 11월 12일에 의결하여 절차상 의문이 있다.",
    ]
    for s in positive_variations:
        assert len(_same_event_hits(s)) == 1, s

    control_variations = [
        # '행위 통지'·'행동 통지'는 지시어가 아니므로 유일성 표지 없이 서로 다른 날 통지는 미발화
        "피고는 2024. 4. 2. 행위 통지를 발송하였고, 2024. 4. 9. 행동 통지를 발송하였다.",
        # 내용 수식이 서로 다른 별건 통지('해지 통지서' vs '갱신 통지서')
        "원고는 2024. 5. 3. 해지 통지서를 발송하였고, 그 갱신 통지서는 2024. 5. 10. 발송하였다.",
        # 선행 수령('위 통지서를 받은') 뒤 다른 행위 날짜
        "피고는 2024. 6. 1. 통지서를 발송하였다. 원고는 위 통지서를 받은 뒤 2024. 6. 8. 내용증명을 발송하였다.",
    ]
    for s in control_variations:
        assert _same_event_hits(s) == [], s


def test_yields_to_existing_internal_date_rule():
    """N9: 기존 EVI.INCONS_INTERNAL_DATE가 이미 발화한 사건(계약·해지·해제)에는 새 규칙이 양보한다."""
    text = (
        "원고는 2024년 2월 10일 이 사건 매매계약을 체결하였다. "
        "그러나 원고는 뒤에서 위 매매계약을 2024년 2월 20일에 체결하였다고 진술한다."
    )
    all_findings = check_internal_inconsistency(_doc(text))
    rule_ids = [f.confidence_features.get("rule_id") for f in all_findings]
    assert "EVI.INCONS_INTERNAL_DATE" in rule_ids
    assert "EVI.INCONS_SAME_EVENT_DATETIME" not in rule_ids


def test_linear_time_on_20k_chars():
    """2만 자 악성 입력 선형 시간 검증."""
    evil_1 = ("위그해당이사건본건동 통지서 회신서 시정명령 " * 600)[:20000]
    evil_2 = ("단 한 차례 단 한 번도 회신 통지 발송 " * 600)[:20000]

    t0 = time.perf_counter()
    _ANAPHORA_EVENT_RE.findall(evil_1)
    _UNIQUENESS_MARKER_RE.findall(evil_2)
    check_internal_inconsistency(_doc(evil_1))
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5, f"Too slow on 20k chars: {elapsed:.3f}s"
