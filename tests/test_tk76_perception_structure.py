"""TK-76 EVI-LOGIC: 같은 문장이 지각할 수 없던 조건을 밝히면서 직접 지각을 주장하는 진술(합성 문장만)."""
import pytest

from packages.claim_engine.evidence_consistency import check_statements, perception_conflict
from tests.test_v2_root_causes import paged

POSITIVE = [
    ("UNOPENED_INSIDE", "저는 우편함을 열어 보지 않았는데도 그 속에 있던 고지서의 금액을 읽었습니다."),
    ("UNOPENED_INSIDE", "증인은 가방을 뜯어 보지 않은 채 그 안쪽 수첩의 메모를 확인했습니다."),
    ("CLOSED_INSIDE", "참고인은 밀봉된 상자 속의 장부 기재를 분명히 보았다고 하였습니다."),
    ("NEVER_PRESENT", "저는 그 창고에 방문한 적이 없지만 물건이 쌓여 있던 모습을 직접 보았습니다."),
    ("INCAPACITATED", "본인은 기절해 있던 동안 상대방이 지갑을 가져가는 것을 목격하였습니다."),
    ("ELSEWHERE_SAME_TIME", "증인은 병원 대기실에 있었지만 같은 시각 공사 현장에서 소장이 한 지시를 들었습니다."),
    ("SOUND_ONLY_VISUAL", "복도에서 들린 문소리만으로 들어온 사람이 관리인이었음을 직접 확인했습니다."),
    # 2판: 어미·범주 변형
    ("UNOPENED_INSIDE", "저는 수납장을 열지 못했으나 그 속에 놓인 상장의 이름을 읽었습니다."),          # 못 + 했으나
    ("UNOPENED_INSIDE", "증인은 공책을 펼쳐 보지 않았지만 그 안의 메모를 분명히 확인했습니다."),        # 펼쳐 보
    ("INCAPACITATED", "진술인은 마취에서 깨어나지 못한 동안 의사들이 한 말을 들었습니다."),            # 깨어나지 못
    ("SOUND_ONLY_VISUAL", "경적 소리만 듣고 운전자가 피고였음을 직접 확인했습니다."),                 # '들은' 없이 소리만 듣고
    ("NEVER_PRESENT", "저는 그 매장에 들어간 일이 없었지만 직원이 물건을 숨기는 것을 직접 보았습니다."),  # 없었지만
]
CONTROL = [
    "저는 우편함을 열어 고지서를 꺼낸 뒤 그 안의 금액을 읽었습니다.",               # 연 뒤 지각
    "가방을 열어 보지 않았으므로 그 안에 무엇이 있었는지는 모릅니다.",               # 지각 주장 없음
    "증인은 창고에 간 적은 없지만 사진으로 물건의 상태를 확인했습니다.",             # 매개 경로
    "저는 그 회의에 참석한 적이 없어 직접 들은 바는 없습니다.",                     # 지각 부정
    "아들이 잠든 사이 저는 거실에서 뉴스를 보았습니다.",                           # 다른 사람이 잠듦
    "본인은 기절해 있던 동안의 일은 기억나지 않습니다.",                           # 기억 없음
    "증인은 병원에 있었으나 같은 시각 현장 상황을 전화로 보고받았습니다.",             # 매개 경로
    "밖에서 들린 소리만으로는 누가 왔는지 알 수 없었습니다.",                       # 시각 주장 없음
    "피고는 지체하지 않고 전액을 지급하였고 원고는 영수증을 확인했습니다.",           # 정상 항변
    "닫힌 문 안에서 큰 소리가 나는 것을 들었습니다.",                             # 소리는 닫힌 문 너머로 들림
    "수납장을 열지 못했으므로 그 속에 무엇이 있었는지 모릅니다.",                    # 지각 주장 없음
    "경적 소리를 듣고 창밖을 내다보아 운전자를 직접 확인했습니다.",                   # 소리 뒤 눈으로 확인
    "진술인은 마취에서 깨어난 뒤 간호사에게서 경과를 전해 들었습니다.",               # 매개 경로
]


@pytest.mark.parametrize("pattern,sentence", POSITIVE)
def test_structural_perception_conflict_is_found(pattern, sentence):
    assert perception_conflict(sentence) == pattern


@pytest.mark.parametrize("sentence", CONTROL)
def test_controls_are_not_flagged(sentence):
    assert perception_conflict(sentence) is None


def statement_doc(*lines):
    return paged(["진 술 서¶", "성 명 김○○¶", *[f"{line}¶" for line in lines], "2025. 4. 2.¶", "진술인 김○○ (인)¶"],
                 doc_id="S", filename="진술서.pdf")


def test_entrypoint_reports_suspicious_c_grade_once_per_sentence():
    found = [f for f in check_statements(statement_doc(POSITIVE[0][1], CONTROL[0]))
             if str(f.type) == "STATEMENT_BEYOND_PERCEPTION"]
    assert len(found) == 1
    finding = found[0]
    assert finding.status.value == "SUSPICIOUS" and finding.evidence_grade.value == "C"
    assert finding.confidence_features["pattern"] == "UNOPENED_INSIDE" and finding.confidence_features["human_review"]
    assert "고지서" in finding.evidence[0].excerpt


def test_existing_limitation_rule_keeps_its_status_and_is_not_duplicated():
    sentence = "본인은 멀리 있어 대화를 들을 수 없었으나 원고가 폭언하지 않은 것은 확실합니다."
    found = [f for f in check_statements(statement_doc(sentence)) if str(f.type) == "STATEMENT_BEYOND_PERCEPTION"]
    assert [f.status.value for f in found] == ["UNVERIFIED"]


def test_absence_of_observation_turned_into_settled_fact_uses_existing_rule():
    sentence = "직원이 서류를 꺼내는 모습을 보지 못했다는 사정만으로 서류가 반출되지 않았음이 확정됩니다."
    found = [f for f in check_statements(statement_doc(sentence)) if str(f.type) == "STATEMENT_BEYOND_PERCEPTION"]
    assert [f.status.value for f in found] == ["UNVERIFIED"]


def test_document_without_statement_conflict_is_unchanged():
    found = check_statements(statement_doc(*CONTROL))
    assert [f for f in found if str(f.type) == "STATEMENT_BEYOND_PERCEPTION"] == []
