"""TK-76 3주기 후속 B 묶음 — EVI-LOGIC 지각 구조(L1a~L4)·EVI-OVR(O1~O6) (평가 측 공개 합성 문장)."""
from __future__ import annotations

import pytest

from packages.claim_engine.evidence_consistency import check_document, check_evidence_overreach
from packages.common.enums import FindingType
from packages.common.schemas import Block, NormalizedDocument, Page


def _doc(lines):
    blocks = [Block(block_id=f"b{i}", text=t, page=1, visible=True, source_layer="visible_text") for i, t in enumerate(lines)]
    return NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                              pages=[Page(page_number=1, blocks=blocks, width=595.0, height=842.0)])


def _perception(lines):
    d = _doc(["진 술 서", "진술인 오○○"] + lines + ["2024. 12. 2.", "진술인 오○○ (인)"])
    return [f for f in check_document(d) if f.type == FindingType.STATEMENT_BEYOND_PERCEPTION]


def _overreach(body, ev):
    d = _doc(["청구원인", body, "입증방법", ev])
    return [f for f in check_evidence_overreach(d) if f.type == FindingType.EVIDENCE_PURPOSE_MISMATCH]


# --- L1a: '[인칭 대명사] 눈으로'도 직접 지각 표지 ---
def test_l1a_pronoun_eye_marker():
    assert _perception(["당시 저는 목포 물류센터에 있었습니다.", "그때 피고가 원고의 차량을 긁는 장면을 저의 눈으로 보았습니다."])


# --- L2: 장소 조사 없는 체재('[장소] [자리를 떠난 일] 중이었다') ---
@pytest.mark.parametrize("stay", ["강릉 연수 중이었습니다", "베트남 파견 중이었습니다", "제주 여행 중이었습니다"])
def test_l2_particleless_away_stay(stay):
    assert _perception([f"그 시각 저는 {stay}.", "그때 피고가 원고의 차량을 긁는 장면을 직접 보았습니다."])


# --- L3: 체재 장소가 곧 현장이거나 같은 자리이면 '다른 장소'가 아니다 ---
@pytest.mark.parametrize("stay", ["그 시각 저는 주차장 현장에 있었습니다.", "그 시각 저는 원고와 함께 휴게실에 있었습니다.",
                                  "그 시각 저는 강릉 연수 중이었습니다."])
def test_l3_control_colocated(stay):
    second = "그때 강릉 연수원 주차장에서 피고가 원고의 차량을 긁는 장면을 직접 보았습니다." if "연수" in stay \
        else "그때 피고가 원고의 차량을 긁는 장면을 직접 보았습니다."
    assert not _perception([stay, second])


# --- L4: 체재한 사람이 진술인이 아니면 해당 없음 ---
def test_l4_control_other_person_stay():
    assert not _perception(["그 시각 제 배우자는 목포 물류센터에 있었습니다.", "그때 저는 피고가 원고의 차량을 긁는 장면을 직접 보았습니다."])


# --- O1: '특정 채무 전부·전액 변제' 대 영수·입금 서증 금액 ---
def test_o1_receipt_amount_less_than_debt():
    assert _overreach("원고는 피고로부터 매매대금 2,000,000원을 받기로 하였고, 피고가 매매대금 전액을 지급하였음은 갑 제2호증 입금확인증으로 증명됩니다.",
                      "1. 갑 제2호증 입금확인증 (금 700,000원)")


def test_o1_receipt_amount_without_debt_amount():
    assert _overreach("피고가 임차보증금 전부를 송금하였음은 을 제2호증 계좌이체영수증으로 증명됩니다.",
                      "1. 을 제2호증 계좌이체영수증 (금 4,000,000원)")


@pytest.mark.parametrize("body,ev", [
    ("매매대금은 700,000원이고, 피고가 매매대금 전액을 지급하였음은 갑 제2호증 입금확인증으로 증명됩니다.", "1. 갑 제2호증 입금확인증 (금 700,000원)"),
    ("피고가 매매대금 중 700,000원을 지급하였음은 갑 제2호증 입금확인증으로 증명됩니다.", "1. 갑 제2호증 입금확인증 (금 700,000원)"),
    ("피고가 매매대금 전액을 지급하였음은 갑 제2호증 입금확인증으로 증명됩니다.", "1. 갑 제2호증 입금확인증"),
])
def test_o1_control(body, ev):
    assert not _overreach(body, ev)


# --- O2: 자기 측 의사표시는 '상대방 의사표시'가 아니다 / O3: '피신청인' 작성자 ---
@pytest.mark.parametrize("body,ev", [
    ("피고 회사가 원고의 연장 요청에 승낙하였다는 점은 을 제5호증 사실확인서로 증명됩니다.", "1. 을 제5호증 사실확인서 (작성자: 피고)"),
    ("채권자가 채무자의 분할 상환 제안에 동의하였다는 점은 갑 제5호증 확인서로 증명됩니다.", "1. 갑 제5호증 확인서 (작성자: 채권자)"),
])
def test_o2_control_self_side_declaration(body, ev):
    assert not _overreach(body, ev)


def test_o2_opposite_side_still_flagged():
    assert _overreach("원고가 피고의 연장 요청에 승낙하였다는 점은 을 제5호증 사실확인서로 증명됩니다.", "1. 을 제5호증 사실확인서 (작성자: 피고)")


def test_o2_mutual_agreement_still_flagged():
    assert _overreach("피고와 원고가 공급 단가에 합의하였다는 점은 을 제5호증 확인서로 증명됩니다.", "1. 을 제5호증 확인서 (작성자: 피고)")


# --- O4: 완료 술어 목적어에 '차임·원리금' ---
def test_o4_rent_full_payment():
    assert _overreach("원고가 차임 전부를 지급하였음은 갑 제2호증 영수증으로 증명됩니다.", "1. 갑 제2호증 영수증 (금 600,000원)")


# --- O5: 본문의 '소을 제N호증' 인용 ---
def test_o5_so_eul_citation():
    assert _overreach("신청인이 피신청인의 공사 중지 요청에 동의하였다는 점은 소을 제3호증 확인서로 소명됩니다.", "1. 소을 제3호증 확인서 (작성자: 피신청인)")


# --- O6: 명사형 의사표시('…의 승낙이 있었다') ---
def test_o6_nominal_declaration():
    assert _overreach("피고의 승낙이 있었다는 점은 갑 제5호증 진술서로 증명됩니다.", "1. 갑 제5호증 진술서 (작성자: 원고)")


def test_o6_control_interrogative():
    assert not _overreach("피고의 승낙이 있었는지는 갑 제5호증 진술서만으로 알 수 없습니다.", "1. 갑 제5호증 진술서 (작성자: 원고)")
