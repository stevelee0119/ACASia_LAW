# -*- coding: utf-8 -*-
"""TK-76 3주기 EVI-FORM(서증 형식 결함) 구조 규칙 단위 및 변형 시험.

설계 메모(docs/handoff/requests/TK-76_cycle3_evi_form_design_memo.md) 6.1·6.2절 및
평가 측 판정 지시(M1~M7, C1~C3)의 양성·대조·변형·중복방지·ReDoS 시간 시험을 검증한다.
모든 예시는 말뭉치·고정 세트·은퇴 세트·비공개 탐침 문장과 무관한 순수 창작 합성예다(2-2 규약).
"""
from __future__ import annotations

import time
import unittest

from packages.claim_engine import evidence_consistency as E
from packages.claim_engine.evidence_consistency import (
    _form_findings,
    check_document,
    check_evidence_form_structure,
    exhibit_rows,
)
from packages.common.enums import EvidenceGrade, FindingType, Severity, VerificationStatus
from packages.common.schemas import Block, NormalizedDocument, Page


def _make_doc(text: str, doc_id: str = "doc_form_test") -> NormalizedDocument:
    """단일 블록 또는 줄 단위 블록으로 구성된 시험용 문서를 생성한다."""
    doc = NormalizedDocument(
        document_id=doc_id,
        filename=f"{doc_id}.pdf",
        mime_type="application/pdf",
        sha256="a" * 64,
    )
    page = Page(page_number=1, width=595.0, height=842.0)
    page.blocks.append(Block(block_id="b1", page=1, text=text))
    doc.pages.append(page)
    return doc


def _run_structure(text: str):
    """문서에 대해 신규 구조 규칙(check_evidence_form_structure) 결과를 반환한다."""
    doc = _make_doc(text)
    rows = exhibit_rows(doc)
    return check_evidence_form_structure(doc, rows)


def _by_rule(findings, rule_id: str):
    return [f for f in findings if (f.confidence_features or {}).get("rule_id") == rule_id]


class TestEviFormG1TranslationMissing(unittest.TestCase):
    """G1. 외국어 문서 번역문 미첨부 (EVI.TRANSLATION_MISSING) 양성 3건 / 대조 4건."""

    def test_g1_positives(self):
        # 양성 1: 영문 계약서 서증명, 번역문 없음
        t1 = (
            "소 장\n원고 갑동이\n피고 을돌이\n청구원인\n갑 제1호증에 의하면 계약이 성립하였습니다.\n"
            "입증방법\n1. 갑 제1호증 Exclusive Distribution Agreement\n2024. 5. 1.\n원고 소송대리인 (인)"
        )
        f1 = _by_rule(_run_structure(t1), "EVI.TRANSLATION_MISSING")
        self.assertEqual(len(f1), 1)
        self.assertEqual(f1[0].status, VerificationStatus.SUSPICIOUS)
        self.assertEqual(f1[0].evidence_grade, EvidenceGrade.B)
        self.assertEqual(f1[0].severity, Severity.MEDIUM)

        # 양성 2: 영문 대여약정서 서증명
        t2 = (
            "준비서면\n원고 갑동이\n갑 제2호증을 제출합니다.\n"
            "입증방법\n1. 갑 제2호증 Loan Agreement & Promissory Note\n2024. 6. 1.\n원고 갑동이 (인)"
        )
        f2 = _by_rule(_run_structure(t2), "EVI.TRANSLATION_MISSING")
        self.assertEqual(len(f2), 1)

        # 양성 3: KS X 1001 한자 집합 밖 간체자 서증명 (M4 반영)
        t3 = (
            "소 장\n원고 갑동이\n갑 제3호증을 제출합니다.\n"
            "입증방법\n1. 갑 제3호증 股权转让协议\n2024. 7. 1.\n원고 갑동이 (인)"
        )
        f3 = _by_rule(_run_structure(t3), "EVI.TRANSLATION_MISSING")
        self.assertEqual(len(f3), 1)

    def test_g1_controls(self):
        # 대조 1: 가지번호에 번역문 첨부
        c1 = (
            "소 장\n원고 갑동이\n"
            "입증방법\n1. 갑 제1호증의 1 Exclusive Distribution Agreement\n"
            "2. 갑 제1호증의 2 번역문\n2024. 5. 1.\n원고 갑동이 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c1), "EVI.TRANSLATION_MISSING"), [])

        # 대조 2: 서증명 자체에 번역본 표기
        c2 = (
            "소 장\n원고 갑동이\n"
            "입증방법\n1. 갑 제2호증 ABC Solutions Supply Contract (국문 번역본 첨부)\n"
            "2024. 5. 1.\n원고 갑동이 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c2), "EVI.TRANSLATION_MISSING"), [])

        # 대조 3: 국문 명칭 속 영문 규격 약어 병기
        c3 = (
            "소 장\n원고 갑동이\n"
            "입증방법\n1. 갑 제3호증 ISO-9001 품질인증서 사본\n2024. 5. 1.\n원고 갑동이 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c3), "EVI.TRANSLATION_MISSING"), [])

        # 대조 4: KS X 1001 범위 내 한자로 된 국한문 서증명 보호 (M4 반영)
        c4 = (
            "소 장\n원고 갑동이\n"
            "입증방법\n1. 갑 제4호증 株式讓渡契約書\n2024. 5. 1.\n원고 갑동이 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c4), "EVI.TRANSLATION_MISSING"), [])


class TestEviFormG2PartyMarkMismatch(unittest.TestCase):
    """G2. 자기 입증방법의 부호 불일치 (EVI.PARTY_MARK_MISMATCH) 양성 3건 / 대조 3건."""

    def test_g2_positives(self):
        # 양성 1: 원고 서면에 을 호증만 기재
        t1 = (
            "소 장\n원고 김철수\n피고 박영희\n청구원인\n대여금을 청구합니다.\n"
            "입증방법\n1. 을 제1호증 차용증\n2. 을 제2호증 입금증\n2024. 5. 1.\n원고 소송대리인 (인)"
        )
        f1 = _by_rule(_run_structure(t1), "EVI.PARTY_MARK_MISMATCH")
        self.assertEqual(len(f1), 1)
        self.assertEqual(f1[0].status, VerificationStatus.SUSPICIOUS)

        # 양성 2: 피고 답변서에 갑 호증만 기재
        t2 = (
            "답 변 서\n원고 김철수\n피고 박영희\n청구원인에 대한 답변\n원고 주장은 부당합니다.\n"
            "입증방법\n1. 갑 제1호증 부동산매매계약서\n2024. 5. 10.\n피고 박영희 (인)"
        )
        f2 = _by_rule(_run_structure(t2), "EVI.PARTY_MARK_MISMATCH")
        self.assertEqual(len(f2), 1)

        # 양성 3: 신청인(채권자) 서면 소명방법에 소을 호증만 기재 (M6 반영)
        t3 = (
            "가압류신청서\n채권자 김철수\n채무자 박영희\n신청이유\n보전의 필요성이 있습니다.\n"
            "소명방법\n1. 소을 제1호증 영수증\n2. 소을 제2호증 각서\n2024. 5. 12.\n채권자 김철수 (인)"
        )
        f3 = _by_rule(_run_structure(t3), "EVI.PARTY_MARK_MISMATCH")
        self.assertEqual(len(f3), 1)

    def test_g2_controls(self):
        # 대조 1: 원고 서면 본문에서 피고의 을 호증을 탄핵하고 입증방법은 갑 호증
        c1 = (
            "준비서면\n원고 김철수\n피고가 제출한 을 제1호증 차용증은 위조된 것입니다.\n"
            "입증방법\n1. 갑 제1호증 금융거래내역서\n2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c1), "EVI.PARTY_MARK_MISMATCH"), [])

        # 대조 2: 피고 서면 본문에서 원고 갑 호증을 반박하고 입증방법은 을 호증
        c2 = (
            "답 변 서\n피고 박영희\n원고의 갑 제2호증 기재는 사실과 다릅니다.\n"
            "입증방법\n1. 을 제1호증 통장사본\n2024. 5. 2.\n피고 박영희 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c2), "EVI.PARTY_MARK_MISMATCH"), [])

        # 대조 3: 입증방법에 갑 호증과 을 호증이 혼합된 경우
        c3 = (
            "준비서면\n원고 김철수\n"
            "입증방법\n1. 갑 제1호증 영수증\n2. 을 제2호증 합의서\n2024. 5. 3.\n원고 김철수 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c3), "EVI.PARTY_MARK_MISMATCH"), [])


class TestEviFormG3SignatureDateBlank(unittest.TestCase):
    """G3. 진술·확인 문서의 서명·작성일 칸 공란 (EVI.SIGNATURE_DATE_BLANK) 양성 3건 / 대조 3건."""

    def test_g3_positives(self):
        # 양성 1: 확인서 서명 줄 공란
        t1 = "확 인 서\n상기 사실이 틀림없음을 확인합니다.\n2024. 5. 1.\n확인자 성명 : ________ (서명 또는 날인)"
        f1 = _by_rule(_run_structure(t1), "EVI.SIGNATURE_DATE_BLANK")
        self.assertEqual(len(f1), 1)
        self.assertEqual(f1[0].status, VerificationStatus.SUSPICIOUS)

        # 양성 2: 진술서 작성일 줄 공란
        t2 = "진 술 서\n본인은 위 내용을 목격하였음을 진술합니다.\n2024.   .   .\n진술인 : 홍길동 (인)"
        f2 = _by_rule(_run_structure(t2), "EVI.SIGNATURE_DATE_BLANK")
        self.assertEqual(len(f2), 1)

        # 양성 3: 각서 작성자 및 작성일 공란
        t3 = "각  서\n차용금을 기일 내에 변제하겠습니다.\n2023년    월    일\n작성자 :          (인)"
        f3 = _by_rule(_run_structure(t3), "EVI.SIGNATURE_DATE_BLANK")
        self.assertEqual(len(f3), 1)

    def test_g3_controls(self):
        # 대조 1: 가림 표기(익명화)는 공란이 아님
        c1 = "확 인 서\n상기 사실을 확인합니다.\n2024. 5. 1.\n확인자 : 김○○ (인)"
        self.assertEqual(_by_rule(_run_structure(c1), "EVI.SIGNATURE_DATE_BLANK"), [])

        # 대조 2: 작성일 및 서명 완비
        c2 = "진 술 서\n위와 같이 진술합니다.\n2024. 5. 12.\n진술인 : 이몽룡 (서명)"
        self.assertEqual(_by_rule(_run_structure(c2), "EVI.SIGNATURE_DATE_BLANK"), [])

        # 대조 3: 본안 소송서면(소장)의 전자서명 생략
        c3 = "소  장\n원고 김철수\n피고 박영희\n청구취지\n원고 소송대리인 변호사 박문수 (전자서명 생략)"
        self.assertEqual(_by_rule(_run_structure(c3), "EVI.SIGNATURE_DATE_BLANK"), [])


class TestEviFormG4FormElementAdmitted(unittest.TestCase):
    """G4. 형식 요소 부재·불능 자인 + 증명 주장 (EVI.FORM_ELEMENT_ADMITTED) 양성 3건 / 대조 5건."""

    def test_g4_positives(self):
        # 양성 1: 판독성 불능 자인 + 증명 주장 (C1 반영)
        t1 = (
            "소 장\n원고 김철수\n"
            "갑 제1호증 영수증은 잉크가 심하게 바래 금액 숫자를 판독하기 어려우나, 피고가 공사대금을 완납한 사실은 분명히 증명됩니다.\n"
            "입증방법\n1. 갑 제1호증 영수증\n2024. 5. 1.\n원고 김철수 (인)"
        )
        f1 = _by_rule(_run_structure(t1), "EVI.FORM_ELEMENT_ADMITTED")
        self.assertEqual(len(f1), 1)
        self.assertEqual(f1[0].status, VerificationStatus.SUSPICIOUS)

        # 양성 2: 작성명의 불능 자인 + 입증 주장 (M2, C1 반영)
        t2 = (
            "소 장\n원고 김철수\n"
            "갑 제2호증 사실확인서를 작성한 사람의 이름을 현재 확인할 수 없지만, 본건 합의가 존재하였음은 본 서증으로 명백히 입증됩니다.\n"
            "입증방법\n1. 갑 제2호증 사실확인서\n2024. 5. 1.\n원고 김철수 (인)"
        )
        f2 = _by_rule(_run_structure(t2), "EVI.FORM_ELEMENT_ADMITTED")
        self.assertEqual(len(f2), 1)

        # 양성 3: 원본 부재 자인 + 확인 주장
        t3 = (
            "소 장\n원고 김철수\n"
            "갑 제3호증 계약서는 원본을 보관하고 있지 아니하나, 피고의 채무불이행 사실은 충분히 확인됩니다.\n"
            "입증방법\n1. 갑 제3호증 계약서\n2024. 5. 1.\n원고 김철수 (인)"
        )
        f3 = _by_rule(_run_structure(t3), "EVI.FORM_ELEMENT_ADMITTED")
        self.assertEqual(len(f3), 1)

    def test_g4_controls(self):
        # 대조 1: 서증 자체의 흠결이 아닌 일반 사실관계 부지 양보
        c1 = (
            "소 장\n원고 김철수\n"
            "원고는 피고 회사의 구체적 내부 사정을 알 수 없었으나, 갑 제1호증에 의하여 계약 체결 사실은 입증됩니다.\n"
            "입증방법\n1. 갑 제1호증 계약서\n2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c1), "EVI.FORM_ELEMENT_ADMITTED"), [])

        # 대조 2: 상대방 탄핵 주장에 대한 반박
        c2 = (
            "소 장\n원고 김철수\n"
            "피고는 을 제2호증에 작성일자가 없어 효력이 없다고 주장하나, 원고의 갑 제1호증으로 사실이 증명됩니다.\n"
            "입증방법\n1. 갑 제1호증 확인서\n2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c2), "EVI.FORM_ELEMENT_ADMITTED"), [])

        # 대조 3: 원본 변론기일 지참 예정 정상 실무
        c3 = (
            "소 장\n원고 김철수\n"
            "갑 제3호증의 원본은 다음 변론기일에 지참하여 확인시켜 드릴 예정이며, 본 서증으로 입증을 마칩니다.\n"
            "입증방법\n1. 갑 제3호증 계약서\n2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c3), "EVI.FORM_ELEMENT_ADMITTED"), [])

        # 대조 4: M2/C1 오탐 방지 — '채무자'의 '자' 또는 지각 동사 없는 '금액 산정 곤란'
        c4 = (
            "소 장\n원고 김철수\n"
            "갑 제1호증에 채무자의 주소가 적혀 있지 않으나 대여 사실은 증명됩니다. "
            "또한 갑 제2호증에 따라 금액을 산정하기 어려우나 채무 사실은 입증됩니다.\n"
            "입증방법\n1. 갑 제1호증 차용증\n2. 갑 제2호증 정산서\n2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c4), "EVI.FORM_ELEMENT_ADMITTED"), [])

        # 대조 5: M3 오결속 방지 — '계약서'에서 '서'를 떼어 앞 절의 일반 명사 '계약'에 오결속하지 않음
        c5 = (
            "소 장\n원고 김철수\n"
            "구두 계약의 정확한 일자를 현재 알 수 없으나, 갑 제1호증에 의하여 지급 사실은 증명됩니다.\n"
            "입증방법\n1. 갑 제1호증 계약서 사본\n2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(c5), "EVI.FORM_ELEMENT_ADMITTED"), [])


class TestEviFormVariationsAndDedup(unittest.TestCase):
    """6.2절 3대 변형 시험(어순·연결어미·어휘), M5 기존 축 우선 보존, C2 ReDoS 선형 시간 검증."""

    def test_variation_1_word_order_in_antecedent_clause(self):
        # [서증명 선행형]: 서증명 -> 형식 요소
        v1 = (
            "소 장\n원고 김철수\n"
            "갑 제1호증 영수증은 잉크가 번져 금액을 판독하기 어려우나, 피고의 변제 사실은 증명됩니다.\n"
            "입증방법\n1. 갑 제1호증 영수증 사본\n2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(len(_by_rule(_run_structure(v1), "EVI.FORM_ELEMENT_ADMITTED")), 1)

        # [형식요소 선행형]: 형식 요소 -> 서증명 (선행 절 내부 어순 교환, M3 반영)
        v2 = (
            "소 장\n원고 김철수\n"
            "금액 숫자의 판독이 곤란한 영수증이나, 갑 제1호증에 의하여 피고의 변제 사실은 증명됩니다.\n"
            "입증방법\n1. 갑 제1호증 영수증 사본\n2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(len(_by_rule(_run_structure(v2), "EVI.FORM_ELEMENT_ADMITTED")), 1)

    def test_variation_2_concessive_endings(self):
        # 다양한 양보 연결 어미(-으나, -지만, -더라도, -는데도, -음에도)
        endings = ["없으나,", "없지만,", "없더라도,", "없는데도,", "없음에도,"]
        for end_tok in endings:
            text = (
                f"소 장\n원고 김철수\n"
                f"갑 제1호증은 작성일자를 확인할 수 {end_tok} 대여 사실은 명백히 입증됩니다.\n"
                f"입증방법\n1. 갑 제1호증 각서\n2024. 5. 1.\n원고 김철수 (인)"
            )
            res = _by_rule(_run_structure(text), "EVI.FORM_ELEMENT_ADMITTED")
            self.assertEqual(len(res), 1, f"Failed on concessive ending: {end_tok}")

    def test_variation_3_lexical_variants(self):
        # 동일 꼴 다른 낱말 변형 (명의인/날인/원본/글자해독 x 다양한 불능 술어)
        clauses = [
            "갑 제1호증은 작성명의인을 찾을 수 없으나,",
            "갑 제1호증은 도장 날인이 남아 있지 아니하나,",
            "갑 제1호증은 원래 문서를 분실하였으나,",
            "갑 제1호증은 글자 해독이 불가하나,",
        ]
        for pre_clause in clauses:
            text = (
                f"소 장\n원고 김철수\n"
                f"{pre_clause} 본건 거래 사실은 분명히 확인됩니다.\n"
                f"입증방법\n1. 갑 제1호증 거래장부\n2024. 5. 1.\n원고 김철수 (인)"
            )
            res = _by_rule(_run_structure(text), "EVI.FORM_ELEMENT_ADMITTED")
            self.assertEqual(len(res), 1, f"Failed on lexical variant: {pre_clause}")

    def test_m5_existing_axis_takes_precedence_no_duplicate(self):
        # 기존 축 2(원본 미제출 자인 CONTRADICTED)에 잡히는 문장은 기존 판정이 유지되고 새 규칙(SUSPICIOUS)이 중복 생성되지 않음
        text = (
            "소 장\n원고 김철수\n"
            "갑 제1호증은 원본을 분실하여 제출하지 못하나 사본으로 입증합니다.\n"
            "입증방법\n1. 갑 제1호증 차용증\n2024. 5. 1.\n원고 김철수 (인)"
        )
        doc = _make_doc(text)
        rows = exhibit_rows(doc)
        findings = _form_findings(doc, rows)
        ex1 = [f for f in findings if (f.confidence_features or {}).get("exhibit") == "갑 제1호증"]
        self.assertEqual(len(ex1), 1)
        # 기존 축이 먼저 판정하였으므로 새 규칙(EVI.FORM_ELEMENT_ADMITTED)으로 덮어쓰지 않음
        self.assertNotEqual((ex1[0].confidence_features or {}).get("rule_id"), "EVI.FORM_ELEMENT_ADMITTED")

    def test_c2_redos_linear_time_on_20k_adversarial_inputs(self):
        # C2: 모든 새 정규식 및 함수를 길이 20,000자의 긴 공백·밑줄·반복 음절 입력으로 시간 시험
        adv_inputs = [
            "2024" + " " * 20000 + "x",
            "확인자 성명 : " + "_" * 20000 + "x",
            "글씨" + "가" * 20000 + "판독",
            "작성한" + " " * 20000 + "사람",
            "(" * 20000 + "사본",
            "알 " + "수 " * 10000 + "없",
        ]
        regexes = [
            E._TRAIL_DATE_RE,
            E._BLANK_RUN_RE,
            E._SIGN_BLANK_LINE_RE,
            E._DATE_BLANK_LINE_RE,
            E._STATEMENT_TITLE_RE,
            E._FORM_ELEMENT_RE,
            E._LEGIBILITY_RE,
            E._INABILITY_RE,
            E._CONCESSIVE_RE,
            E._PROOF_CLAIM_RE,
            E._FORM_SECTION_HEAD_RE,
            E._FORM_LIST_LINE_RE,
            E._CORE_STRIP_RE,
            E._NAME_PAREN_RE,
            E._APPLICANT_SIGN_RE,
        ]
        for s in adv_inputs:
            start = time.perf_counter()
            folded = E._fold_blanks(s)
            norm = " ".join(s.split())
            E._foreign_script_name(s)
            for rx in regexes:
                rx.search(folded)
                rx.search(norm)
            elapsed = time.perf_counter() - start
            self.assertLess(elapsed, 1.0, f"Slow regex on input prefix {s[:20]!r}: {elapsed:.3f}s")


class TestEviFormD1ToD5Supplement(unittest.TestCase):
    """D1~D5 보완 사항 각각에 대한 양성·대조 시험 (순수 창작 합성예)."""

    def test_d1_parenthetical_abbreviation_positive_and_control(self):
        # D1 양성: 본체 서증명이 영문이고 괄호 속에 국문 부연이 있는 경우 -> 번역문 미첨부 검출
        pos = (
            "소 장\n원고 김철수\n"
            "입증방법\n1. 갑 제1호증 Non-Disclosure Agreement (비밀유지협약)\n"
            "2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(len(_by_rule(_run_structure(pos), "EVI.TRANSLATION_MISSING")), 1)

        # D1 대조: 국문 서증명 안의 반각·전각 괄호 속 영문 원어 약어 풀이 -> 외국 문서 오탐 제외
        ctrl1 = (
            "소 장\n원고 김철수\n"
            "입증방법\n1. 갑 제1호증 MOU(Memorandum of Understanding) 체결 내역서\n"
            "2. 갑 제2호증 CRM（Customer Relationship Management） 고객 응대 기록\n"
            "2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(ctrl1), "EVI.TRANSLATION_MISSING"), [])

    def test_d2_address_domain_email_positive_and_control(self):
        # D2 양성: 도메인이 일부 포함되었더라도 나머지 본체가 영문 계약서 명칭인 경우 -> 번역문 미첨부 검출
        pos = (
            "소 장\n원고 김철수\n"
            "입증방법\n1. 갑 제1호증 Cloud Hosting Service Level Agreement\n"
            "2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(len(_by_rule(_run_structure(pos), "EVI.TRANSLATION_MISSING")), 1)

        # D2 대조: 웹사이트 도메인이나 전자우편 주소가 포함된 국문 서증명 -> 외국 문서 오탐 제외
        ctrl = (
            "소 장\n원고 김철수\n"
            "입증방법\n1. 갑 제1호증 portal.koreatrade-center.or.kr 공고문 캡처\n"
            "2. 갑 제2호증 support-team@koreatrade-center.co.kr 발송 내역\n"
            "2024. 5. 1.\n원고 김철수 (인)"
        )
        self.assertEqual(_by_rule(_run_structure(ctrl), "EVI.TRANSLATION_MISSING"), [])

    def test_d3_applicant_sign_line_positive_and_control(self):
        # D3 양성: 당사자 표시 없이 말미 서명 줄에만 '위 채권자 ○○○ (인)'이 있는 신청서에서 소갑 외국어 서증 제출 -> G1 검출
        doc_pos = NormalizedDocument(
            document_id="d3_pos", filename="d3_pos.pdf", mime_type="application/pdf", sha256="c" * 64
        )
        page_pos = Page(page_number=1, width=595.0, height=842.0)
        for i, line in enumerate([
            "가처분신청서",
            "신 청 이 유",
            "채무자는 해외 공급계약을 위반하였습니다(소갑 제1호증).",
            "소 명 방 법",
            "1. 소갑 제1호증 International Supply and License Contract",
            "2024. 5. 1.",
            "위 채권자 ○○○ (인)",
        ]):
            page_pos.blocks.append(Block(block_id=f"b{i}", page=1, text=line))
        doc_pos.pages.append(page_pos)
        res_pos = check_evidence_form_structure(doc_pos, exhibit_rows(doc_pos))
        self.assertEqual(len(_by_rule(res_pos, "EVI.TRANSLATION_MISSING")), 1)

        # D3 대조: 말미 서명 줄이 '위 채무자 ○○○ (인)'인 답변/이의서에서 소을 국문 서증 제출 -> 부호 불일치(G2) 및 번역문(G1) 미검출
        doc_ctrl = NormalizedDocument(
            document_id="d3_ctrl", filename="d3_ctrl.pdf", mime_type="application/pdf", sha256="d" * 64
        )
        page_ctrl = Page(page_number=1, width=595.0, height=842.0)
        for i, line in enumerate([
            "가처분이의신청서",
            "이 의 이 유",
            "채권자의 소갑 제1호증 주장은 부당합니다.",
            "소 명 방 법",
            "1. 소을 제1호증 대금정산 내역서",
            "2024. 5. 10.",
            "위 채무자 ○○○ (인)",
        ]):
            page_ctrl.blocks.append(Block(block_id=f"b{i}", page=1, text=line))
        doc_ctrl.pages.append(page_ctrl)
        res_ctrl = check_evidence_form_structure(doc_ctrl, exhibit_rows(doc_ctrl))
        self.assertEqual(_by_rule(res_ctrl, "EVI.PARTY_MARK_MISMATCH"), [])
        self.assertEqual(_by_rule(res_ctrl, "EVI.TRANSLATION_MISSING"), [])

    def test_d4_same_exhibit_g4_suppresses_g1_positive_and_control(self):
        # D4 양성(우선순위 작동): 같은 호증(갑 제1호증)에 G4(형식 요소 불능 자인)와 G1(번역문 미첨부)이 모두 해당할 때 _form_findings는 G4 1건만 반환
        text_same = (
            "소 장\n원고 김철수\n"
            "갑 제1호증 Commercial Invoice and Packing List는 작성일자를 알아볼 수 없으나, 물품 공급 사실은 증명됩니다.\n"
            "입증방법\n1. 갑 제1호증 Commercial Invoice and Packing List\n"
            "2024. 5. 1.\n원고 김철수 (인)"
        )
        doc_same = _make_doc(text_same)
        f_same = _form_findings(doc_same, exhibit_rows(doc_same))
        self.assertEqual(len(_by_rule(f_same, "EVI.FORM_ELEMENT_ADMITTED")), 1)
        self.assertEqual(len(_by_rule(f_same, "EVI.TRANSLATION_MISSING")), 0)

        # D4 대조(서로 다른 호증): 갑 제1호증은 G4, 갑 제2호증은 G1일 때 각각 독립 검출
        text_diff = (
            "소 장\n원고 김철수\n"
            "갑 제1호증 영수증은 서명을 확인할 수 없으나, 대금 지급 사실은 증명됩니다.\n"
            "입증방법\n1. 갑 제1호증 영수증\n2. 갑 제2호증 Commercial Invoice and Packing List\n"
            "2024. 5. 1.\n원고 김철수 (인)"
        )
        doc_diff = _make_doc(text_diff)
        f_diff = _form_findings(doc_diff, exhibit_rows(doc_diff))
        self.assertEqual(len(_by_rule(f_diff, "EVI.FORM_ELEMENT_ADMITTED")), 1)
        self.assertEqual(len(_by_rule(f_diff, "EVI.TRANSLATION_MISSING")), 1)

    def test_d5_mixed_blanks_and_partial_year_positive_and_control(self):
        # D5 양성: 공백과 밑줄이 섞인 서명 칸('  ____  ') 및 앞 두 자리만 적힌 연도('20   .   .   .') -> G3 검출
        pos1 = "진 술 서\n위와 같이 목격하였음을 진술합니다.\n20   년   월   일\n진술인 성명 :   ____   (서명)"
        self.assertEqual(len(_by_rule(_run_structure(pos1), "EVI.SIGNATURE_DATE_BLANK")), 1)

        pos2 = "확 인 서\n위 사실을 확인합니다.\n19   .   .   .\n확인자 : 정약용 (인)"
        self.assertEqual(len(_by_rule(_run_structure(pos2), "EVI.SIGNATURE_DATE_BLANK")), 1)

        # D5 대조: 한 칸 띄어쓰기로 정상 작성된 연월일 및 성명 -> G3 미검출
        ctrl = "진 술 서\n위와 같이 진술합니다.\n2024 년 5 월 12 일\n진술인 성명 : 정약용 (서명)"
        self.assertEqual(_by_rule(_run_structure(ctrl), "EVI.SIGNATURE_DATE_BLANK"), [])


if __name__ == "__main__":
    unittest.main()
