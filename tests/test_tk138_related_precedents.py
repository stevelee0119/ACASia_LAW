# -*- coding: utf-8 -*-
"""TK-138 관련 판례 탐색 및 판례 권위 가중 단위/통합 테스트 (U1~U5, P1~P9 검증)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from packages.common.enums import AdapterStatus, CitationType
from packages.common.schemas import Citation
from packages.legal_engine.argument_validity_verifier import _attach_ai_opinions, ArgumentValidityResult, HallucinationTableRow
from packages.legal_engine.normalize import canonical_case_number, extract_all_case_numbers
from packages.legal_engine.related_authorities import (
    AuthorityBudget,
    _calculate_authority_score,
    _discover_tk138_precedents,
    review_related_authorities,
    report_lines,
)
from packages.source_adapters.law_go_kr import LawGoKrAdapter


class TestTK138RelatedPrecedents(unittest.TestCase):
    """TK-138 관련 판례 탐색 및 권위 가중치 평가 테스트."""

    def test_u1_search_cases_by_query_supreme_court_filter_and_counts(self):
        """U1: 대법원 한정 질의(org=400201) 및 검색 N건 중 M건 메타 반환 검증."""
        adapter = LawGoKrAdapter()
        adapter.settings.law_go_kr_oc = "TEST_OC"
        adapter.status = MagicMock(return_value=AdapterStatus.READY)

        mock_payload = {
            "PrecSearch": {
                "totalCnt": "1402",
                "prec": [
                    {
                        "사건번호": "2020다12345",
                        "판례일련번호": "1001",
                        "법원명": "대법원",
                        "선고일자": "20230515",
                        "사건명": "해고무효확인",
                        "판결유형": "판결",
                        "판례상세링크": "http://...",
                    }
                ],
            }
        }
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = mock_payload
        adapter._http_get = MagicMock(return_value=mock_response)

        resp = adapter.search_cases_by_query("근로기준법 제23조", org="400201", display=100)

        self.assertEqual(resp.status, AdapterStatus.READY)
        adapter._http_get.assert_called_once()
        call_params = adapter._http_get.call_args[1]["params"]
        self.assertEqual(call_params["org"], "400201")
        self.assertEqual(call_params["search"], 2)
        self.assertEqual(call_params["query"], "근로기준법 제23조")

        attrs = resp.source_record.attributes
        self.assertEqual(attrs["total_count"], 1402)
        self.assertEqual(attrs["returned_count"], 1)
        self.assertIn("1402건 중 1건", resp.message)

    def test_u2_en_banc_deterministic_identification_and_scoring(self):
        """U2: 전원합의체는 판결유형 메타로만 식별하며 권위 점수 가산(+50점) 부여."""
        # 1. 대법원 전원합의체 판결 (2016다248998)
        en_banc_item = {
            "case_number": "2016다248998",
            "court": "대법원",
            "case_kind": "전원합의체 판결",
            "decision_date": "2018-10-30",
        }
        score_en_banc, tier_en_banc = _calculate_authority_score(en_banc_item)
        self.assertEqual(tier_en_banc, "SUPREME_COURT_EN_BANC")
        self.assertGreaterEqual(score_en_banc, 150.0)

        # 2. 대법원 일반 판결
        regular_item = {
            "case_number": "2020다99999",
            "court": "대법원",
            "case_kind": "판결",
            "decision_date": "2021-01-15",
        }
        score_reg, tier_reg = _calculate_authority_score(regular_item)
        self.assertEqual(tier_reg, "SUPREME_COURT")
        self.assertGreaterEqual(score_reg, 100.0)
        self.assertLess(score_reg, 150.0)

        # 3. 고등법원 판결
        high_item = {
            "case_number": "2021나1234",
            "court": "서울고등법원",
            "case_kind": "판결",
            "decision_date": "2022-03-01",
        }
        score_high, tier_high = _calculate_authority_score(high_item)
        self.assertEqual(tier_high, "HIGH_COURT")
        self.assertGreaterEqual(score_high, 50.0)
        self.assertLess(score_high, 100.0)

        # 4. 결정례 감산 (-10점)
        decision_item = {
            "case_number": "2020마5678",
            "court": "대법원",
            "case_kind": "결정",
            "decision_date": "2020-05-10",
        }
        score_dec, tier_dec = _calculate_authority_score(decision_item)
        self.assertLess(score_dec, 100.0)

        # 계층 위계 검증: 전원합의체 > 대법원 일반 > 고등법원
        self.assertGreater(score_en_banc, score_reg)
        self.assertGreater(score_reg, score_high)

    def test_p1_top_cases_fetch_summary_and_fallback(self):
        """P1: 최상위 판례에 대해 fetch_case로 판결요지 수집 및 폴백 검증."""
        adapter = MagicMock()
        adapter.name = "law_go_kr"
        adapter.settings.allow_network = True
        adapter.status.return_value = AdapterStatus.READY

        # 목록 응답
        item1 = {
            "case_number": "2016다248998",
            "court": "대법원",
            "case_kind": "전원합의체 판결",
            "decision_date": "2018-10-30",
            "case_name": "임금",
            "source_id": "99901",
            "summary": "",  # 목록에는 요지 없음
        }
        item2 = {
            "case_number": "2020다11111",
            "court": "대법원",
            "case_kind": "판결",
            "decision_date": "2021-02-01",
            "case_name": "손해배상",
            "source_id": "99902",
            "summary": "",
        }
        mock_resp = MagicMock(status=AdapterStatus.READY, records=[item1, item2])
        mock_resp.source_record.attributes = {"total_count": 2, "returned_count": 2}
        adapter.search_cases_by_query.return_value = mock_resp

        # 상세 응답 (item1은 성공, item2는 상세 실패 폴백)
        def mock_fetch(c):
            if c.get("source_id") == "99901":
                return MagicMock(status=AdapterStatus.READY, records=[{"summary": "대법원 전합 요지 본문 발췌"}])
            return MagicMock(status=AdapterStatus.ERROR, records=[])

        adapter.fetch_case.side_effect = mock_fetch

        verifier = MagicMock()
        verifier.registry.law = adapter

        cit = Citation.create(CitationType.STATUTE, "근로기준법 제23조", law_name="근로기준법", article="23")
        precedents, status = _discover_tk138_precedents([cit], verifier)

        self.assertEqual(status, "COMPLETED")
        self.assertEqual(len(precedents), 2)
        # item1은 요지 확보
        self.assertEqual(precedents[0]["case_number"], "2016다248998")
        self.assertEqual(precedents[0]["summary"], "대법원 전합 요지 본문 발췌")
        self.assertIn("검색 2건 중 2건", precedents[0]["search_scope"])
        # item2는 안전 폴백으로 메타데이터 보존
        self.assertEqual(precedents[1]["case_number"], "2020다11111")
        self.assertEqual(precedents[1]["summary"], "")

    def test_u3_and_p6_unprovided_case_filtering(self):
        """U3 & P6: 기존 정규식으로 사건번호 추출 후 제공 목록 밖 가공 인용 필터링."""
        # 1. 사건번호 추출 재사용 검증 (U3)
        mixed_text = "2024년3월 피고는 대법원 2020다12345 판결 및 94누4615 판결을 지어내어 주장하였다."
        extracted = extract_all_case_numbers(mixed_text)
        extracted_cases = {f"{y}{c}{s}" for y, c, s in extracted}
        self.assertIn("2020다12345", extracted_cases)
        self.assertIn("94누4615", extracted_cases)
        self.assertFalse(any("2024" in c and "월" in c for c in extracted_cases))

        # 2. 비인가 판례 인용 검출 및 필터링 (P6)
        result = ArgumentValidityResult()
        row = HallucinationTableRow(
            item_id=1,
            location="1p",
            claim_text="임의 주장",
            cited_authority="대법원 2019다00000 판결",
            authority_exists=False,
            ai_generation_basis="UNCONFIRMED",
            validity_verdict="검토필요",
            legal_reasoning="",
            recommended_counteraction="",
            basis="UNCONFIRMED",
        )
        result.rows.append(row)

        unverified_cases = [{
            "item_id": 1,
            "context": "원고의 청구는 부당하다",
            "citation": Citation.create(CitationType.CASE, "대법원 2019다00000 판결"),
        }]

        # 제공된 권위 판례: 2016다248998만 제공됨
        related_auth = {
            "precedents": [
                {"case_number": "2016다248998", "court": "대법원", "case_kind": "전원합의체 판결", "summary": "정당한 권위"}
            ]
        }

        # 모델 응답: 제공하지 않은 '2099다99999' 임의 판례를 인용함
        router = MagicMock()
        mock_reply = MagicMock()
        mock_reply.used = True
        mock_reply.parsed = {
            "overall_summary": "검토 요약",
            "rows": [
                {
                    "item_id": 1,
                    "claim_text": "임의 주장",
                    "validity_verdict": "타당",
                    "legal_reasoning": "대법원 2099다99999 판결에 따르면 타당합니다.",
                    "recommended_check": "확인 필요",
                }
            ],
        }
        mock_reply.executions = [MagicMock(provider="openai", model="gpt-4")]
        router.consult_all = unittest.mock.AsyncMock(return_value=[mock_reply])

        import asyncio
        asyncio.run(_attach_ai_opinions(result, unverified_cases, router, 0, None, related_authorities=related_auth))

        self.assertEqual(len(result.rows), 1)
        opinions = result.rows[0].ai_opinions
        self.assertEqual(len(opinions), 1)
        op = opinions[0]
        self.assertTrue(op.get("filtered_out_unprovided"))
        self.assertEqual(op.get("verdict"), "판단 불가")
        self.assertIn("[UNVERIFIED_INVENTED_IN_RESPONSE]", op.get("reasoning"))
        self.assertNotIn("2099다99999", op.get("reasoning"))
        self.assertIn("2099다99999", op.get("unprovided_case_numbers"))

    def test_u4_authority_budget_sharing_and_guards(self):
        """U4: 공용 예산 객체(15.0초)로 TK-137(8.0초 상한) 및 TK-138 가드 검증."""
        budget = AuthorityBudget(total_seconds=15.0, tk137_max_seconds=8.0, start_time=100.0)

        # 1. 시작 직후: TK-137 호출 가능
        with patch("time.monotonic", return_value=102.0):
            self.assertTrue(budget.tk137_can_call())
            self.assertEqual(budget.total_remaining(), 13.0)

        # 2. 8.5초 경과: TK-137 단계 상한 도달로 호출 차단
        with patch("time.monotonic", return_value=108.5):
            self.assertFalse(budget.tk137_can_call())
            # 하지만 전체 잔여는 6.5초 남아 있으므로 TK-138 목록 검색(>= 5.0초)은 가능
            self.assertTrue(budget.tk138_can_search(5.0))
            self.assertTrue(budget.tk138_can_fetch_detail(3.0))

        # 3. 11.5초 경과: 잔여 3.5초 (목록 검색 5초 미만이므로 검색 차단, 본문 상세 3초는 가능)
        with patch("time.monotonic", return_value=111.5):
            self.assertFalse(budget.tk138_can_search(5.0))
            self.assertTrue(budget.tk138_can_fetch_detail(3.0))

        # 4. 13.0초 경과: 잔여 2.0초 (본문 상세 3초 가드 미달로 상세 조회 차단)
        with patch("time.monotonic", return_value=113.0):
            self.assertFalse(budget.tk138_can_fetch_detail(3.0))

    def test_p5_offline_benchmark_zero_impact(self):
        """P5: allow_network False 환경에서 네트워크 미호출, 점수 변화 0 검증."""
        adapter = MagicMock()
        adapter.name = "law_go_kr"
        adapter.settings.allow_network = False
        adapter.status.return_value = AdapterStatus.READY

        verifier = MagicMock()
        verifier.registry.law = adapter

        cit = Citation.create(CitationType.STATUTE, "근로기준법 제23조", law_name="근로기준법", article="23")
        precedents, status = _discover_tk138_precedents([cit], verifier)

        self.assertEqual(status, "NETWORK_DISABLED")
        self.assertEqual(precedents, [])
        adapter.search_cases_by_query.assert_not_called()

    def test_report_lines_and_presentation(self):
        """P8 & U5: [관련 판례] 출력 및 긴 사건명 표기 검증."""
        doc = MagicMock()
        doc.filename = "test.pdf"
        doc.engine_data = {
            "related_authorities": {
                "status": "SOURCE_REVIEW_ONLY",
                "precedents": [
                    {
                        "case_number": "2016다248998",
                        "court": "대법원",
                        "decision_date": "2018-10-30",
                        "case_kind": "전원합의체 판결",
                        "case_name": "통상임금 산정 및 신의칙 위반 여부에 관한 청구사건",
                        "search_scope": "검색 1402건 중 100건 (대법원 한정)",
                    }
                ],
            }
        }

        lines = report_lines([doc])
        matched = [l for l in lines if "[관련 판례]" in l]
        self.assertEqual(len(matched), 1)  # 머리 줄 1개(범위 1회), 판례는 그 아래 줄(평가 측 보완 K1)
        start = lines.index(matched[0])
        line = " ".join(lines[start:start + 2])
        self.assertIn("2016다248998", line)
        self.assertIn("전원합의체 판결", line)
        self.assertIn("통상임금 산정 및 신의칙", line)
        self.assertIn("검색 1402건 중 100건 (대법원 한정)", line)
        self.assertIn("검토 자료", line)


    def test_p2_100_cases_selection_bias_free_sorting(self):
        """P2 & P3: 100건 전체에 대해 편향 없이 권위 가중치 정렬하여 전원합의체 우선 선별 검증."""
        adapter = MagicMock()
        adapter.name = "law_go_kr"
        adapter.settings.allow_network = True
        adapter.status.return_value = AdapterStatus.READY

        # 100건 모의 데이터 (하급심 다수 앞에 두고 전합을 50번째에 배치)
        records = []
        for i in range(1, 101):
            if i == 50:
                records.append({
                    "case_number": "2016다248998",
                    "court": "대법원",
                    "case_kind": "전원합의체 판결",
                    "decision_date": "2018-10-30",
                    "case_name": "임금",
                    "source_id": "5000",
                })
            elif i == 1:
                records.append({
                    "case_number": "2023나1001",
                    "court": "서울고등법원",
                    "case_kind": "판결",
                    "decision_date": "2024-01-01",
                    "case_name": "고등사건",
                    "source_id": "1001",
                })
            else:
                records.append({
                    "case_number": f"2020가합{i}",
                    "court": "서울중앙지방법원",
                    "case_kind": "판결",
                    "decision_date": "2020-05-01",
                    "case_name": "지방사건",
                    "source_id": str(i),
                })

        mock_resp = MagicMock(status=AdapterStatus.READY, records=records)
        mock_resp.source_record.attributes = {"total_count": 100, "returned_count": 100}
        adapter.search_cases_by_query.return_value = mock_resp
        adapter.fetch_case.return_value = MagicMock(status=AdapterStatus.READY, records=[{"summary": "요지"}])

        verifier = MagicMock()
        verifier.registry.law = adapter

        cit = Citation.create(CitationType.STATUTE, "민법 제750조", law_name="민법", article="750")
        precedents, status = _discover_tk138_precedents([cit], verifier)

        self.assertEqual(status, "COMPLETED")
        # 50번째에 있던 전원합의체가 1순위로 선별되어야 함 (선택 편향 없음)
        self.assertEqual(precedents[0]["case_number"], "2016다248998")
        self.assertEqual(precedents[0]["authority_tier"], "SUPREME_COURT_EN_BANC")
        # 2순위는 고등법원 판결
        self.assertEqual(precedents[1]["case_number"], "2023나1001")
        self.assertEqual(precedents[1]["authority_tier"], "HIGH_COURT")

    def test_review_related_authorities_integration_schema(self):
        """P8: review_related_authorities에서 delegations, explicit_references, precedents 단일 dict 결합 검증."""
        adapter = MagicMock()
        adapter.name = "law_go_kr"
        adapter.settings.allow_network = True
        adapter.status.return_value = AdapterStatus.READY

        # 판례 검색 응답 모의
        case_item = {
            "case_number": "2016다248998",
            "court": "대법원",
            "case_kind": "전원합의체 판결",
            "decision_date": "2018-10-30",
            "case_name": "임금",
            "source_id": "1001",
        }
        case_resp = MagicMock(status=AdapterStatus.READY, records=[case_item])
        case_resp.source_record.attributes = {"total_count": 1, "returned_count": 1}
        adapter.search_cases_by_query.return_value = case_resp
        adapter.fetch_case.return_value = MagicMock(status=AdapterStatus.READY, records=[{"summary": "요지"}])

        # 조문 resolve 및 3단 비교 모의
        adapter.resolve_statute.return_value = MagicMock(records=[{"version_id": "111", "law_name": "근로기준법"}])
        adapter.get_thd_cmp.return_value = {
            "LspttnThdCmpLawXService": {
                "기본정보": {"시행령명_한글": "근로기준법 시행령"},
                "위임조문삼단비교": {
                    "법률조문": [
                        {
                            "조번호": "0023", "조가지번호": "00", "조제목": "해고 등의 제한", "조내용": "본문",
                            "시행령조문": {"법령명": "근로기준법 시행령", "조번호": "0005", "조가지번호": "00", "조제목": "위임조문", "조내용": "위임내용"},
                        }
                    ]
                }
            }
        }

        verifier = MagicMock()
        verifier.registry.law = adapter
        verifier.verify_citations.return_value = MagicMock(source_records=[], data={"verdicts": []})

        doc = MagicMock()
        doc.visible_text = "서면 본문"
        cits = [Citation.create(CitationType.STATUTE, "근로기준법 제23조", law_name="근로기준법", article="23")]

        out, records = review_related_authorities(doc, cits, verifier)

        self.assertIsNotNone(out)
        self.assertEqual(out["status"], "SOURCE_REVIEW_ONLY")
        self.assertEqual(out["delegation_status"], "COMPLETED")
        self.assertEqual(out["precedent_status"], "COMPLETED")
        self.assertTrue(len(out["delegations"]) >= 1)
        self.assertTrue(len(out["precedents"]) >= 1)
        self.assertEqual(out["precedents"][0]["case_number"], "2016다248998")

    def test_c2_budget_exhaustion_on_search(self):
        """C2: TK-138 진입 전 남은 예산이 5초 미만일 때 BUDGET_EXHAUSTED 반환 검증."""
        adapter = MagicMock()
        adapter.name = "law_go_kr"
        adapter.settings.allow_network = True
        adapter.status.return_value = AdapterStatus.READY

        verifier = MagicMock()
        verifier.registry.law = adapter

        # 잔여 시간이 4.0초만 남은 예산 객체
        budget = AuthorityBudget(total_seconds=15.0, tk137_max_seconds=8.0, start_time=100.0)
        with patch("time.monotonic", return_value=111.0):  # 15초 중 11초 소진, 잔여 4초
            cit = Citation.create(CitationType.STATUTE, "근로기준법 제23조", law_name="근로기준법", article="23")
            precedents, status = _discover_tk138_precedents([cit], verifier, budget=budget)

        self.assertEqual(status, "BUDGET_EXHAUSTED")
        self.assertEqual(precedents, [])
        adapter.search_cases_by_query.assert_not_called()


class TestTK138EvaluatorSupplement(unittest.TestCase):
    """평가 측 보완 H1~H5·H7 시험(11-04)."""

    def _rows(self, n):
        res = ArgumentValidityResult()
        for i in range(1, n + 1):
            res.rows.append(HallucinationTableRow(
                item_id=i, location="1p", claim_text="주장", cited_authority=f"대법원 201{i}다1{i}{i}{i} 판결",
                authority_exists=False, ai_generation_basis="UNCONFIRMED", validity_verdict="검토필요",
                legal_reasoning="", recommended_counteraction="", basis="UNCONFIRMED"))
        cases = [{"item_id": i, "context": "주장 맥락",
                  "citation": Citation.create(CitationType.CASE, f"대법원 201{i}다1{i}{i}{i} 판결")} for i in range(1, n + 1)]
        return res, cases

    def _router(self, rows):
        router = MagicMock()
        reply = MagicMock()
        reply.used = True
        reply.parsed = {"overall_summary": "요약", "rows": rows}
        reply.executions = [MagicMock(provider="openai", model="m")]
        router.consult_all = unittest.mock.AsyncMock(return_value=[reply])
        return router

    def test_h1_request_with_precedents_passes_input_contract(self):
        import asyncio
        from packages.llm_router.input_contracts import valid_input_contract
        from packages.llm_router.privacy import inspect_request
        res, cases = self._rows(1)
        router = self._router([])
        related = {"precedents": [{"case_number": "2016다248998", "court": "대법원", "case_kind": "전원합의체 판결", "summary": "요지"}]}
        asyncio.run(_attach_ai_opinions(res, cases, router, 0, None, related_authorities=related))
        request = router.consult_all.call_args.args[1]
        self.assertIn("관련 권위 판례(참고)", request.user)
        self.assertTrue(valid_input_contract(request))
        self.assertEqual(inspect_request(request)["status"], "PASSED")

    def test_h2_h3_opinion_keeps_reasoning_key_and_item_own_case(self):
        import asyncio
        from packages.legal_engine.reasoning_format import reasoning_sections
        res, cases = self._rows(2)
        router = self._router([
            {"item_id": 1, "claim_text": "a", "validity_verdict": "타당", "legal_reasoning": "대법원 2011다1111 판결 취지", "recommended_check": "c"},
            {"item_id": 2, "claim_text": "b", "validity_verdict": "타당", "legal_reasoning": "대법원 2012다1222 판결 취지", "recommended_check": "c"},
        ])
        related = {"precedents": [{"case_number": "2016다248998", "court": "대법원"}]}
        asyncio.run(_attach_ai_opinions(res, cases, router, 0, None, related_authorities=related))
        for row in res.rows:
            op = row.ai_opinions[0]
            self.assertEqual(op["verdict"], "타당")
            self.assertFalse(op["filtered_out_unprovided"])
            self.assertTrue(reasoning_sections("검토", "AI", row.ai_opinions)["opinions"][0]["reasoning"])

    def test_h4_no_filter_without_provided_list(self):
        import asyncio
        res, cases = self._rows(1)
        router = self._router([{"item_id": 1, "claim_text": "a", "validity_verdict": "타당",
                                "legal_reasoning": "대법원 2016다248998 판결 취지", "recommended_check": "c"}])
        asyncio.run(_attach_ai_opinions(res, cases, router, 0, None, related_authorities=None))
        op = res.rows[0].ai_opinions[0]
        self.assertEqual(op["verdict"], "타당")
        self.assertFalse(op["filtered_out_unprovided"])

    def test_h5_unprovided_number_removed_from_shown_text(self):
        import asyncio
        res, cases = self._rows(1)
        router = self._router([{"item_id": 1, "claim_text": "a", "validity_verdict": "타당",
                                "legal_reasoning": "2016다248998 판결과 2099다 99999 판결 취지", "recommended_check": "c"}])
        related = {"precedents": [{"case_number": "2016다248998", "court": "대법원"}]}
        asyncio.run(_attach_ai_opinions(res, cases, router, 0, None, related_authorities=related))
        op = res.rows[0].ai_opinions[0]
        self.assertEqual(op["verdict"], "판단 불가")
        self.assertIn("2016다248998", op["reasoning"])
        self.assertNotIn("99999", op["reasoning"])
        self.assertEqual(op["unprovided_case_numbers"], ["2099다99999"])

    def test_h7_detail_fetch_capped_per_document(self):
        adapter = MagicMock()
        adapter.name = "law_go_kr"
        adapter.settings.allow_network = True
        adapter.status.return_value = AdapterStatus.READY
        def search(query, **kw):
            base = 1 if "23" in query else 5
            items = [{"case_number": f"20{base + i:02d}다{i + 1}", "court": "대법원", "decision_date": "2020-01-01",
                      "case_kind": "판결", "source_id": f"{base}{i}", "summary": ""} for i in range(3)]
            resp = MagicMock(status=AdapterStatus.READY, records=items)
            resp.source_record.attributes = {"total_count": 3, "returned_count": 3}
            return resp
        adapter.search_cases_by_query.side_effect = search
        adapter.fetch_case.return_value = MagicMock(status=AdapterStatus.READY, records=[{"summary": "요지"}])
        verifier = MagicMock()
        verifier.registry.law = adapter
        cits = [Citation.create(CitationType.STATUTE, "근로기준법 제23조", law_name="근로기준법", article="23"),
                Citation.create(CitationType.STATUTE, "민법 제750조", law_name="민법", article="750")]
        precedents, status = _discover_tk138_precedents(cits, verifier)
        self.assertEqual(len(precedents), 6)
        self.assertEqual(adapter.fetch_case.call_count, 3)


class TestTK138ScopeHeaderK1(unittest.TestCase):
    def test_k1_scope_per_query_in_header(self):
        from types import SimpleNamespace
        precedents = [
            {"case_number": "2010다1", "court": "대법원", "decision_date": "2020-01-01", "search_query": "가법 제1조",
             "search_scope": "검색 300건 중 100건 (대법원 한정)"},
            {"case_number": "2011다2", "court": "대법원", "decision_date": "2021-01-01", "search_query": "나법 제2조",
             "search_scope": "검색 50건 중 50건 (대법원 한정)"},
        ]
        doc = SimpleNamespace(filename="a.pdf", engine_data={"related_authorities": {"status": "SOURCE_REVIEW_ONLY", "precedents": precedents}})
        lines = report_lines([doc])
        header = [l for l in lines if l.startswith("[관련 판례]")]
        self.assertEqual(len(header), 1)
        self.assertIn("가법 제1조: 검색 300건 중 100건", header[0])
        self.assertIn("나법 제2조: 검색 50건 중 50건", header[0])
        self.assertIn("2건", header[0])


if __name__ == "__main__":
    unittest.main()

