# -*- coding: utf-8 -*-
"""서증 번호 및 목록 불일치(EVI-NUM) 3대 변형 검출 단위 시험.

민사소송법 제277조 및 민사소송규칙 제105조에 따른 서증 정합성 검증.
- 1. 별지 목록 대조 불일치 (별지 제출목록에 없는 호증 원용)
- 2. 본문-제출목록 서증명 불일치
- 3. 연속 목록 중간 호증 누락 (순번 누락)

규정 준수:
- 실제 파이프라인 진입점 시험 1건 이상 (개수 및 내용 검증)
- 변형별 양성 3건, 대조군 3건
- 사건 고유값(사건번호, 금액, 당사자명), 서면 문구 하드코딩 없음
"""
from __future__ import annotations

import timeit
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page
from packages.claim_engine.evidence_consistency import (
    check_evidence_numbering_mismatches,
    ANNEX_LIST_RE,
    ANNEX_CLAIM_RE,
    BODY_EVI_RE,
    LIST_CONFIRM_RE,
    INTERMEDIATE_OMIT_RE,
)


def _make_doc(text: str, doc_id: str = "DOC-NUM-01") -> NormalizedDocument:
    lines = text.strip().split("\n")
    blocks = [
        Block(
            block_id=f"b_{i}",
            text=line,
            page=1,
            block_type="paragraph",
            source_layer="visible_text",
            visible=True,
        )
        for i, line in enumerate(lines)
    ]
    page = Page(page_number=1, blocks=blocks)
    return NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        pages=[page],
    )


# --- 1항: 실제 파이프라인 진입점 시험 ---------------------------------------------
def test_pipeline_entrypoint_evidence_numbering_mismatches():
    sample_text = (
        "소장\n"
        "1. 청구 원인 및 증거 방법\n"
        "별지 제출목록을 확정한다: 갑 제10호증 차용증, 갑 제11호증 입금증.\n"
        "증거요약에서는 별지에 기재된 갑 제12호증 거래명세표를 근거로 대여 사실을 주장한다.\n"
        "2. 거래 내역 검토\n"
        "본문의 입증자료는 갑 제20호증 물품인수증이다.\n"
        "제출목록에서 갑 제20호증의 자료명은 물품공급계약서로 확정한다.\n"
        "3. 추가 소명 자료\n"
        "연속된 세 자료 전부를 아래에 나열한다: 갑 제31호증 영수증, 갑 제33호증 견적서.\n"
        "중간 자료인 갑 제32호증 납품확인서도 제출목록에 적었다.\n"
    )
    doc = _make_doc(sample_text, doc_id="DOC-ENTRY-01")
    findings = check_evidence_numbering_mismatches(doc)

    assert len(findings) == 3, f"예상 finding 3건 불일치: {len(findings)}건 검출"

    # 1. 별지대조 불일치 검증
    annex_findings = [f for f in findings if f.confidence_features.get("defect_code") == "ANNEX_LIST_MISMATCH"]
    assert len(annex_findings) == 1
    f_annex = annex_findings[0]
    assert f_annex.type == FindingType.EVIDENCE_LIST_MISMATCH
    assert f_annex.evidence_grade == EvidenceGrade.B
    assert "갑 제12호증" in f_annex.title
    assert "거래명세표" in f_annex.title
    assert f_annex.evidence[0].excerpt == "갑 제12호증 거래명세표"

    # 2. 본문-목록 명칭 불일치 검증
    name_findings = [f for f in findings if f.confidence_features.get("defect_code") == "BODY_LIST_NAME_MISMATCH"]
    assert len(name_findings) == 1
    f_name = name_findings[0]
    assert f_name.type == FindingType.EVIDENCE_LIST_MISMATCH
    assert "갑 제20호증" in f_name.title
    assert "물품인수증" in f_name.title
    assert "물품공급계약서" in f_name.title
    assert f_name.evidence[0].excerpt == "갑 제20호증 물품인수증"

    # 3. 순번 누락 검증
    omit_findings = [f for f in findings if f.confidence_features.get("defect_code") == "INTERMEDIATE_EXHIBIT_OMITTED"]
    assert len(omit_findings) == 1
    f_omit = omit_findings[0]
    assert f_omit.type == FindingType.EVIDENCE_LIST_MISMATCH
    assert "갑 제32호증" in f_omit.title
    assert "납품확인서" in f_omit.title
    assert f_omit.evidence[0].excerpt == "갑 제32호증 납품확인서"


# --- 변형별 양성 3건 -------------------------------------------------------------
def test_positive_annex_list_mismatch():
    """양성 1: 별지 목록에 없는 호증을 별지 기재 서증으로 원용"""
    text = (
        "별지 제출목록을 확정한다: 을 제5호증 영수증, 을 제6호증 세금계산서.\n"
        "별지에 기재된 을 제7호증 입금확인서를 근거로 지급 사실을 주장한다.\n"
    )
    doc = _make_doc(text, doc_id="DOC-POS-01")
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 1
    assert findings[0].confidence_features.get("defect_code") == "ANNEX_LIST_MISMATCH"
    assert "을 제7호증" in findings[0].title
    assert "입금확인서" in findings[0].title


def test_positive_body_list_name_mismatch():
    """양성 2: 본문 입증자료명과 제출목록 확정 자료명이 상이"""
    text = (
        "본문의 입증자료는 갑 제15호증 근무일지이다.\n"
        "제출목록에서 갑 제15호증의 자료명은 급여대장으로 확정한다.\n"
    )
    doc = _make_doc(text, doc_id="DOC-POS-02")
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 1
    assert findings[0].confidence_features.get("defect_code") == "BODY_LIST_NAME_MISMATCH"
    assert "갑 제15호증" in findings[0].title
    assert "근무일지" in findings[0].title


def test_positive_intermediate_exhibit_omitted():
    """양성 3: 연속 목록 표방 시 중간 호증 누락"""
    text = (
        "연속된 세 자료를 제출합니다: 갑 제1호증 계약서, 갑 제3호증 확인서.\n"
        "중간 자료인 갑 제2호증 시방서도 제출목록에 적었다.\n"
    )
    doc = _make_doc(text, doc_id="DOC-POS-03")
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 1
    assert findings[0].confidence_features.get("defect_code") == "INTERMEDIATE_EXHIBIT_OMITTED"
    assert "갑 제2호증" in findings[0].title
    assert "시방서" in findings[0].title


# --- 대조군 3건 -----------------------------------------------------------------
def test_control_annex_list_consistent():
    """대조군 1: 별지 목록에 정상 포함된 호증 원용"""
    text = (
        "별지 제출목록을 확정한다: 갑 제1호증 계약서, 갑 제2호증 영수증.\n"
        "별지에 기재된 갑 제2호증 영수증을 근거로 지급 사실을 주장한다.\n"
    )
    doc = _make_doc(text, doc_id="DOC-CTRL-01")
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"정상 별지 인용에서 오탐 발생: {findings}"


def test_control_body_list_name_consistent():
    """대조군 2: 본문과 제출목록의 서증명이 동일하게 일치"""
    text = (
        "본문의 입증자료는 갑 제10호증 거래내역서이다.\n"
        "제출목록에서 갑 제10호증의 자료명은 거래내역서로 확정한다.\n"
    )
    doc = _make_doc(text, doc_id="DOC-CTRL-02")
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"일치하는 서증명에서 오탐 발생: {findings}"


def test_control_normal_pleading_no_defects():
    """대조군 3: 일반 소송서면 본문 서술 (규칙 어구 없음)"""
    text = (
        "준비서면\n"
        "1. 원고의 주장에 대하여\n"
        "원고는 피고가 공사대금을 미지급하였다고 주장하나 이는 사실과 다릅니다.\n"
        "피고는 공사 완료 확인 후 약정된 대금을 전액 계좌로 송금하였습니다.\n"
        "이에 관한 객관적 자료를 추후 입증방법으로 제출하겠습니다.\n"
    )
    doc = _make_doc(text, doc_id="DOC-CTRL-03")
    findings = check_evidence_numbering_mismatches(doc)
    assert len(findings) == 0, f"일반 서면 서술에서 오탐 발생: {findings}"


# --- 2항: 정규식 성능비 검증 (< 8.0x, 4배 < 1.0s) -------------------------------
def _check_perf(name: str, pattern, sample_line: str):
    text_1x = sample_line * 10
    text_4x = sample_line * 40
    runs = 50
    t1 = min(timeit.repeat(lambda: list(pattern.finditer(text_1x)), number=runs, repeat=3)) / runs
    t4 = min(timeit.repeat(lambda: list(pattern.finditer(text_4x)), number=runs, repeat=3)) / runs
    t1_adj = max(t1, 0.0001)
    ratio = t4 / t1_adj
    assert ratio < 8.0, f"{name} 정규식 성능비 초과: {ratio:.2f} >= 8.0"
    assert t4 < 1.0, f"{name} 정규식 4배 수행시간 초과: {t4:.4f}s >= 1.0s"


def test_regex_performance():
    _check_perf("ANNEX_LIST_RE", ANNEX_LIST_RE, "별지 제출목록을 확정한다: 갑 제1호증 발송표, 갑 제2호증 분류표.\n")
    _check_perf("ANNEX_CLAIM_RE", ANNEX_CLAIM_RE, "별지에 기재된 갑 제3호증 도착표를 근거로 도착 사실을 주장한다.\n")
    _check_perf("BODY_EVI_RE", BODY_EVI_RE, "본문의 입증자료는 갑 제4호증 송금내역이다.\n")
    _check_perf("LIST_CONFIRM_RE", LIST_CONFIRM_RE, "제출목록에서 갑 제4호증의 자료명은 통화내역으로 확정한다.\n")
    _check_perf("INTERMEDIATE_OMIT_RE", INTERMEDIATE_OMIT_RE, "중간 자료인 갑 제5호증 인수증도 제출목록에 적었다.\n")
