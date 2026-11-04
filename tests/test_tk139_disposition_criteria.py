# -*- coding: utf-8 -*-
"""TK-139 처분기준 별표 대조 1유형 단위/통합 테스트 (W1~W5, G1~G4 검증)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from packages.common.enums import AdapterStatus, CitationType
from packages.common.schemas import Citation
from packages.legal_engine.disposition_criteria import (
    char_2grams,
    extract_document_claim,
    jaccard_similarity,
    parse_and_propagate_table,
    parse_criteria_value_and_unit,
    verify_disposition_criteria,
)
from packages.legal_engine.related_authorities import (
    _discover_tk139_disposition_criteria,
    review_related_authorities,
    report_lines,
)
from packages.source_adapters.law_go_kr import LawGoKrAdapter


class TestTK139DispositionCriteria(unittest.TestCase):
    """TK-139 처분기준 별표 대조 검증 테스트."""

    def test_w5_jaccard_similarity_calculation(self):
        """W5 & Q5: 문자 단위 2-gram Jaccard 유사도 계산 검증."""
        s1 = "유통기한 경과제품 보관"
        s2 = "유통기한이 경과된 제품을 보관한 경우"
        score = jaccard_similarity(s1, s2)
        self.assertGreaterEqual(score, 0.40)

        # 완전 일치 시 1.0
        self.assertEqual(jaccard_similarity("영업정지 1개월", "영업정지 1개월"), 1.0)
        # 공백/특수문자 무시 검증
        self.assertEqual(jaccard_similarity("유통기한·경과", "유통기한 경과"), 1.0)

    def test_w1_and_w5_extract_document_claim_industry_and_clause(self):
        """W1 & W5: 서면 주장 요소, 업종(일반음식점->식품접객업), 위반 사실 절 추출 검증."""
        doc_text = (
            "원고는 서울 마포구에서 일반음식점을 운영하는 자로서, "
            "유통기한이 경과된 식재료를 조리 목적으로 보관하였다는 이유로 "
            "피고로부터 2023. 5. 1.자 1차 위반에 따른 영업정지 2개월 처분을 받았습니다."
        )
        claim = extract_document_claim(doc_text)
        self.assertIsNotNone(claim)
        self.assertEqual(claim["raw_disposition"], "영업정지 2개월")
        self.assertEqual(claim["claimed_val"], 2)
        self.assertEqual(claim["claimed_unit"], "월")
        self.assertEqual(claim["claimed_order"], 1)
        self.assertEqual(claim["matched_industry"], "식품접객업")
        self.assertIn("유통기한이 경과된 식재료", claim["violation_clause"])

    def test_w3_table_merges_and_propagation(self):
        """W3: 파서의 merges와 covered를 반영하여 대분류 및 병합 셀 전파 검증."""
        # 모의 표 구조 (5행 5열)
        mock_cells = [
            ["위반사항", "근거 법령", "1차 위반", "2차 위반", "3차 위반"],
            ["Ⅱ. 개별기준 1. 식품접객업", "", "", "", ""],
            ["1. 유통기한 경과제품을 조리·판매 목적으로 보관한 경우", "법 제44조", "영업정지 15일", "영업정지 1개월", "영업정지 3개월"],
            ["2. 위생모 미착용 등 개인위생 관리기준 위반", "법 제3조", "시정명령", "영업정지 7일", "영업정지 15일"],
            ["가. 건강진단을 받지 아니한 경우", "", "과태료", "영업정지 5일", "영업정지 10일"],
        ]
        # merges: 4행 0열("가. 건강진단을 받지...")이 3행 0열("2. 위생모 미착용...")과 결합되어 있는 상황 모의
        mock_table = {
            "row_count": 5,
            "column_count": 5,
            "cells": mock_cells,
            # 실제 HWP 파서 꼴(평가 측 보완 J2·J12): 업종 절 머리(1행)는 표 전체 폭 병합, 3행 0열은 2행에 걸쳐 병합
            "merges": [{"row": 1, "col": 0, "row_span": 1, "col_span": 5}, {"row": 3, "col": 0, "row_span": 2, "col_span": 1}],
            "covered": [[1, 1], [1, 2], [1, 3], [1, 4], [4, 0]],
            "complete": True,
        }

        with patch("packages.document_engine.hwp_parser._extract_hwp_table_structures",
                   return_value=([mock_table], [], [])):
            rows, success, status = parse_and_propagate_table(b"MOCK_HWP_BYTES")

        self.assertTrue(success)
        self.assertEqual(status, "COMPLETED")
        self.assertTrue(len(rows) >= 3)
        # 3행(0-based idx 2)은 식품접객업 개별기준
        self.assertTrue(rows[0]["industry"].startswith("식품접객업"))
        self.assertIn("유통기한 경과제품", rows[0]["violation_text"])
        self.assertEqual(rows[0]["criteria_raw"][1], "영업정지 15일")

    def test_w2_unit_mismatch_no_conversion_unverified(self):
        """W2 & G2: 단위 환산 금지 규칙 (개월->일수 환산 금지, 단위 상이 시 UNVERIFIED)."""
        doc_text = "원고는 일반음식점을 영위하며, 유통기한이 경과된 제품을 조리 목적으로 보관하여 1차 위반으로 영업정지 60일 처분을 받았다."

        mock_rows = [{
            "row_idx": 2,
            "industry": "식품접객업",
            "violation_text": "유통기한이 경과된 제품을 조리 목적으로 보관한 경우",
            "law_text": "법 제44조",
            "criteria_raw": {1: "영업정지 2개월", 2: "영업정지 3개월", 3: "영업소 폐쇄"},
        }]

        with patch("packages.legal_engine.disposition_criteria.parse_and_propagate_table",
                   return_value=(mock_rows, True, "COMPLETED")):
            res = verify_disposition_criteria(
                doc_text,
                b"MOCK_HWP",
                case_date="2023-05-01",
                law_name="식품위생법 시행규칙",
                table_title="[별표 23] 행정처분의 기준",
                mst="289161",
            )

        # W2: 60일과 2개월을 30일 환산하여 같다고 보지 않고, 단위 상이로 UNVERIFIED 처리
        self.assertIn("UNVERIFIED", res["status"])
        self.assertIn("단위 상이 및 환산 금지", res["status"])
        self.assertEqual(res["comparison_result"], "UNVERIFIED")

    def test_w2_unit_match_comparison_discrepancy_and_match(self):
        """W2: 같은 단위일 때 수치 비교 (MATCHED vs DISCREPANCY_DETECTED)."""
        mock_rows = [{
            "row_idx": 2,
            "industry": "식품접객업",
            "violation_text": "유통기한이 경과된 식재료를 조리 목적으로 보관한 경우",
            "law_text": "법 제44조",
            "criteria_raw": {1: "영업정지 15일", 2: "영업정지 1개월", 3: "영업정지 3개월"},
        }]

        # 1. 일치(MATCHED) 시나리오: 서면 15일 vs 별표 15일
        doc_matched = "일반음식점에서 유통기한이 경과된 식재료를 조리 목적으로 보관하여 1차 영업정지 15일 처분을 받았다."
        with patch("packages.legal_engine.disposition_criteria.parse_and_propagate_table",
                   return_value=(mock_rows, True, "COMPLETED")):
            res_m = verify_disposition_criteria(
                doc_matched, b"MOCK_HWP", case_date="2023-05-01",
                appendix_plain_text="위반 동기에 따라 1/2 범위에서 감경할 수 있다."
            )
        self.assertEqual(res_m["status"], "COMPLETED")
        self.assertEqual(res_m["comparison_result"], "MATCHED")
        self.assertIn("1/2", res_m["discretionary_notes"])

        # 2. 불일치(DISCREPANCY_DETECTED) 시나리오: 서면 30일 vs 별표 15일
        doc_disc = "일반음식점에서 유통기한이 경과된 식재료를 조리 목적으로 보관하여 1차 영업정지 30일 처분을 받았다."
        with patch("packages.legal_engine.disposition_criteria.parse_and_propagate_table",
                   return_value=(mock_rows, True, "COMPLETED")):
            res_d = verify_disposition_criteria(doc_disc, b"MOCK_HWP", case_date="2023-05-01")
        self.assertEqual(res_d["status"], "COMPLETED")
        self.assertEqual(res_d["comparison_result"], "DISCREPANCY_DETECTED")
        self.assertEqual(res_d["advisory_only"], True)

    def test_g1_row_unverified_on_low_score_or_ambiguity(self):
        """G1 & W5: 유사도 0.60 미만이거나 1·2위 격차 0.20 미만 시 UNVERIFIED 복귀."""
        doc_text = "일반음식점에서 영업정지 15일 처분을 받았으나 위반 사실 기재가 불분명함."

        # 1. 최고 유사도가 0.60 미만인 경우
        mock_low_score_rows = [{
            "row_idx": 1,
            "industry": "식품접객업",
            "violation_text": "원산지 거짓 표시 및 혼동 우려 표시",
            "criteria_raw": {1: "영업정지 15일"},
        }]
        with patch("packages.legal_engine.disposition_criteria.parse_and_propagate_table",
                   return_value=(mock_low_score_rows, True, "COMPLETED")):
            res1 = verify_disposition_criteria(doc_text, b"MOCK_HWP", case_date="2023-05-01")
        self.assertIn("UNVERIFIED", res1["status"])
        self.assertIn("< 0.60", res1["status"])

        # 2. 1위와 2위 후보가 0.20 이내로 경합하는 경우
        doc_ambiguous = "일반음식점 시설기준 위반으로 영업정지 15일 처분을 받았다."
        mock_competing_rows = [
            {"row_idx": 1, "industry": "식품접객업", "violation_text": "시설기준 위반 가목", "criteria_raw": {1: "영업정지 15일"}},
            {"row_idx": 2, "industry": "식품접객업", "violation_text": "시설기준 위반 나목", "criteria_raw": {1: "영업정지 15일"}},
        ]
        with patch("packages.legal_engine.disposition_criteria.parse_and_propagate_table",
                   return_value=(mock_competing_rows, True, "COMPLETED")):
            res2 = verify_disposition_criteria(doc_ambiguous, b"MOCK_HWP", case_date="2023-05-01")
        self.assertIn("UNVERIFIED", res2["status"])
        self.assertIn("1·2위 유사도 격차", res2["status"])

    def test_g3_criteria_date_not_determined_guard(self):
        """G3 & Q7: 처분일/기준일 미확정 시 UNVERIFIED 복귀 (구버전 혼동 원천 차단)."""
        doc_text = "일반음식점 유통기한 경과제품 보관으로 영업정지 15일 처분을 받았다."
        res = verify_disposition_criteria(doc_text, b"MOCK_HWP", case_date=None)
        self.assertEqual(res["status"], "UNVERIFIED (처분 기준일 미확정)")

    def test_w4_ssrf_and_domain_restriction(self):
        """W4: 별표 다운로드 시 www.law.go.kr 고정 도메인 외 차단 및 크기 상한 검증."""
        adapter = LawGoKrAdapter()
        adapter.settings.law_go_kr_oc = "TEST_OC"
        adapter.status = MagicMock(return_value=AdapterStatus.READY)

        # 1. 비인가 도메인 차단
        malicious_link = "http://evil.com/malicious.hwp"
        self.assertIsNone(adapter.download_appendix_hwp(malicious_link))

        # 2. www.law.go.kr 외 다른 공공기관 도메인도 차단 (SSRF 원칙)
        other_gov_link = "https://korea.kr/download.hwp"
        self.assertIsNone(adapter.download_appendix_hwp(other_gov_link))

        # 3. www.law.go.kr 정상 상대경로는 허용 및 다운로드 수행
        mock_resp = MagicMock(status_code=200, content=b"VALID_HWP_CONTENT")
        adapter._http_get = MagicMock(return_value=mock_resp)
        result_bytes = adapter.download_appendix_hwp("/LSW/flDownload.do?flSeq=12345")
        self.assertEqual(result_bytes, b"VALID_HWP_CONTENT")
        call_url = adapter._http_get.call_args[0][0]
        self.assertTrue(call_url.startswith("https://www.law.go.kr/LSW/flDownload.do"))

    def test_report_lines_disposition_criteria(self):
        """Q6 & P8: report_lines에서 [처분기준] 라인 정상 렌더링 검증."""
        doc = MagicMock()
        doc.filename = "disposition_case.pdf"
        doc.engine_data = {
            "related_authorities": {
                "status": "SOURCE_REVIEW_ONLY",
                "disposition_criteria": {
                    "status": "COMPLETED",
                    "law_name": "식품위생법 시행규칙",
                    "table_title": "행정처분의 기준(제89조 관련)",
                    "appendix_label": "[별표 23]",
                    "matched_row": {
                        "industry": "식품접객업 영 제21조제8호의 식품접객업을 말한다.",
                        "violation_text": "유통기한 경과제품 보관",
                        "criteria_raw": {1: "영업정지 15일"},
                    },
                    "document_claim": {
                        "raw_disposition": "영업정지 1개월",
                        "claimed_order": 1,
                    },
                    "comparison_result": "DISCREPANCY_DETECTED",
                    "discretionary_notes": "동기·결과에 따라 1/2 범위 감경 가능",
                },
            }
        }

        lines = report_lines([doc])
        matched = [l for l in lines if "[처분기준 검토]" in l]
        self.assertEqual(len(matched), 1)
        line = matched[0]
        self.assertIn("식품위생법 시행규칙 [별표 23]", line)
        self.assertIn("식품접객업", line)
        self.assertNotIn("영 제21조", line)
        self.assertIn("1차 위반 '유통기한 경과제품 보관'", line)
        self.assertIn("별표 영업정지 15일 / 서면 영업정지 1개월", line)
        self.assertIn("불일치(확인 필요)", line)
        self.assertNotIn("DISCREPANCY_DETECTED", line)
        self.assertIn("1/2 범위 감경 가능", line)
        self.assertIn("검토 자료", line)


class TestTK139EvaluatorSupplement(unittest.TestCase):
    """평가 측 보완 J1~J8 시험(11-04). 표는 실제 HWP 파서 출력 꼴(merges 목록·covered 목록)로 만든다."""

    def _table(self):
        general = "Ⅰ. 일반기준 1. 위반행위가 1차·2차·3차로 나뉘면 해당 차수의 기준을 따른다"
        cells = [
            [general, "", "", "", ""],
            ["Ⅱ. 개별기준 1. 식품접객업", "", "", "", ""],
            ["위반사항", "근거 법령", "행정처분기준", "", ""],
            ["", "", "1차 위반", "2차 위반", "3차 위반"],
            ["1. 법 제44조를 위반한 경우 가. 손님에게 갑 행위를 한 경우", "법 제75조", "영업정지 7일", "영업정지 1개월", "영업정지 2개월"],
            ["나. 손님에게 을 행위를 한 경우", "", "품목류 제조정지 1개월", "영업정지 1개월", "영업정지 3개월"],
        ]
        return {
            "cells": cells, "row_count": len(cells), "column_count": 5,
            "merges": [{"row": 0, "col": 0, "row_span": 1, "col_span": 5},
                       {"row": 1, "col": 0, "row_span": 1, "col_span": 5},
                       {"row": 2, "col": 2, "row_span": 1, "col_span": 3},
                       {"row": 2, "col": 0, "row_span": 2, "col_span": 1},
                       {"row": 2, "col": 1, "row_span": 2, "col_span": 1}],
            "covered": [[0, 1], [0, 2], [0, 3], [0, 4], [1, 1], [1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 0], [3, 1]],
        }

    def _run(self, text, table=None):
        with patch("packages.document_engine.hwp_parser._extract_hwp_table_structures",
                   return_value=([table or self._table()], [], None)):
            return verify_disposition_criteria(text, b"HWP", case_date="2026-10-01")

    def test_j2_j3_real_parser_shape_and_order_columns(self):
        with patch("packages.document_engine.hwp_parser._extract_hwp_table_structures",
                   return_value=([self._table()], [], None)):
            rows, ok, msg = parse_and_propagate_table(b"HWP")
        self.assertTrue(ok, msg)
        first = [r for r in rows if "갑 행위" in r["violation_text"]][0]
        self.assertEqual(first["criteria_raw"], {1: "영업정지 7일", 2: "영업정지 1개월", 3: "영업정지 2개월"})
        self.assertEqual(first["industry"], "식품접객업")

    def test_j3_j5_match_and_discrepancy(self):
        base = "원고는 일반음식점을 운영한다. 피고는 원고가 손님에게 갑 행위를 하였다는 이유로 1차 위반으로 영업정지 {}일 처분을 하였다."
        self.assertEqual(self._run(base.format(7))["comparison_result"], "MATCHED")
        self.assertEqual(self._run(base.format(15))["comparison_result"], "DISCREPANCY_DETECTED")

    def test_j4_missing_order_is_unverified(self):
        res = self._run("원고는 일반음식점을 운영한다. 피고는 원고가 손님에게 갑 행위를 하였다는 이유로 영업정지 1개월 처분을 하였다.")
        self.assertEqual(res["comparison_result"], "UNVERIFIED")
        self.assertIn("차수", res["status"])

    def test_j6_no_industry_section_is_unverified(self):
        res = self._run("원고는 식품소분·판매업을 한다. 피고는 원고가 손님에게 갑 행위를 하였다는 이유로 1차 위반으로 영업정지 7일 처분을 하였다.")
        self.assertEqual(res["comparison_result"], "UNVERIFIED")

    def test_j7_other_disposition_kind_is_unverified(self):
        res = self._run("원고는 일반음식점을 운영한다. 피고는 원고가 손님에게 을 행위를 하였다는 이유로 1차 위반으로 영업정지 1개월 처분을 하였다.")
        self.assertEqual(res["comparison_result"], "UNVERIFIED")

    def test_j1_download_uses_real_http_get_signature(self):
        import inspect
        from packages.source_adapters.base import SourceAdapter
        adapter = LawGoKrAdapter()
        adapter.status = MagicMock(return_value=AdapterStatus.READY)
        resp = MagicMock(status_code=200, content=b"HWP")
        def fake(url, **kw):
            inspect.signature(SourceAdapter._http_get).bind(adapter, url, **kw)
            return resp
        adapter._http_get = fake
        self.assertEqual(adapter.download_appendix_hwp("/LSW/flDownload.do?flSeq=1"), b"HWP")


if __name__ == "__main__":
    unittest.main()


class TestTK139SectionJ12(unittest.TestCase):
    def test_j12_section_only_from_full_width_header_rows(self):
        cells = [
            ["Ⅱ. 개별기준 1. 갑종가공업 등 영 제21조제1호의 갑종가공업, 같은 조 제5호가목의 을종소분업", "", "", "", ""],
            ["위반사항", "근거 법령", "행정처분기준", "", ""],
            ["", "", "1차 위반", "2차 위반", "3차 위반"],
            ["가. 갑 행위를 한 경우", "법 제1조", "영업정지 7일", "영업정지 15일", "영업정지 1개월"],
            ["다. 을종소분업의 준수사항 위반은 2. 병종판매업 등의 제9호에 따른다.", "", "", "", ""],
            ["라. 을 행위를 한 경우", "법 제2조", "영업정지 5일", "영업정지 10일", "영업정지 20일"],
            ["2. 병종판매업 등 영 제21조제4호의 정종운반업 및 같은 조 제5호나목의 병종판매업을 말한다.", "", "", "", ""],
            ["가. 을 행위를 한 경우", "법 제2조", "영업정지 1개월", "영업정지 2개월", "영업정지 3개월"],
        ]
        table = {"cells": cells, "row_count": len(cells), "column_count": 5,
                 "merges": [{"row": 0, "col": 0, "row_span": 1, "col_span": 5}, {"row": 1, "col": 2, "row_span": 1, "col_span": 3},
                            {"row": 1, "col": 0, "row_span": 2, "col_span": 1}, {"row": 1, "col": 1, "row_span": 2, "col_span": 1},
                            {"row": 6, "col": 0, "row_span": 1, "col_span": 5}],
                 "covered": [[0, 1], [0, 2], [0, 3], [0, 4], [1, 3], [1, 4], [2, 0], [2, 1], [6, 1], [6, 2], [6, 3], [6, 4]]}
        with patch("packages.document_engine.hwp_parser._extract_hwp_table_structures", return_value=([table], [], None)):
            rows, ok, msg = parse_and_propagate_table(b"HWP")
            self.assertTrue(ok, msg)
            eul = [r for r in rows if "을 행위" in r["violation_text"]]
            self.assertTrue(eul[0]["industry"].startswith("갑종가공업"))   # 문장 속 '2. 병종판매업'으로 절이 바뀌지 않는다
            self.assertTrue(eul[1]["industry"].startswith("병종판매업"))
            res = verify_disposition_criteria(
                "원고는 을종소분업 영업자이다. 피고는 원고가 을 행위를 하였다는 이유로 2차 위반으로 영업정지 10일 처분을 하였다.",
                b"HWP", case_date="2026-10-01")
        self.assertEqual(res["comparison_result"], "MATCHED", res["status"])


class TestTK139BudgetJ11(unittest.TestCase):
    def test_j11_separate_budget_stops_before_external_call(self):
        """사용자 결정(11-04): TK-139 별도 상한 10초, 외부 호출 전 잔여 3초 미만이면 '시간 예산 소진'."""
        from packages.common.schemas import Block, NormalizedDocument, Page
        from packages.legal_engine.related_authorities import _discover_tk139_disposition_criteria
        adapter = MagicMock()
        adapter.name = "law_go_kr"
        adapter.settings.allow_network = True
        adapter.status.return_value = AdapterStatus.READY
        verifier = MagicMock()
        verifier.registry.law = adapter
        text = "원고는 일반음식점을 한다. 가법 시행규칙 [별표 1]에 따라 피고는 1차 위반으로 영업정지 7일 처분을 하였다."
        doc = NormalizedDocument(document_id="d", filename="d.pdf", mime_type="application/pdf", sha256="0" * 64,
                                 pages=[Page(page_number=1, blocks=[Block(block_id="b", text=text, page=1, visible=True,
                                                                         source_layer="visible_text")])])
        ticks = iter([100.0, 108.5, 108.5, 108.5])
        with patch("packages.legal_engine.related_authorities.time.monotonic", side_effect=lambda: next(ticks)):
            res, status = _discover_tk139_disposition_criteria(doc, [], verifier, case_date="2026-10-01")
        self.assertEqual(status, "BUDGET_EXHAUSTED")
        self.assertIn("시간 예산 소진", res["status"])
        adapter.resolve_statute.assert_not_called()


class TestTK139ReportRoundTrip(unittest.TestCase):
    def test_j10_report_line_after_json_round_trip(self):
        import json
        from types import SimpleNamespace
        crit = {"status": "COMPLETED", "law_name": "가법 시행규칙", "table_title": "행정처분 기준",
                "matched_row": {"violation_text": "가. 갑 행위를 한 경우", "criteria_raw": {1: "영업정지 7일", 2: "영업정지 1개월", 3: ""}},
                "document_claim": {"raw_disposition": "영업정지 15일", "claimed_order": 1},
                "comparison_result": "DISCREPANCY_DETECTED", "discretionary_notes": ""}
        ed = json.loads(json.dumps({"related_authorities": {"status": "SOURCE_REVIEW_ONLY", "disposition_criteria": crit}}))
        lines = report_lines([SimpleNamespace(engine_data=ed, filename="a.pdf")])
        self.assertTrue(any("별표 영업정지 7일" in line for line in lines))
