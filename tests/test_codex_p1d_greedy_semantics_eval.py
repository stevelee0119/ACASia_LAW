"""Synthetic regex semantics tests; no private probe text."""
import pytest
from packages.claim_engine.date_verifier import _has_narrative_order_connective

@pytest.mark.parametrize("connector", ["뒤", "후", "다음"])
def test_last_greedy_connector_retains_baseline_verdict(connector):
    # Original greedy regex consumes through the last connector in this run.
    text = "한" + connector + "가" * 16 + "후"
    assert _has_narrative_order_connective(text) is False

@pytest.mark.parametrize("text", ["제출한 뒤", "기록을 남긴 후", "한 뒤다가"])
def test_existing_positive_order_markers_remain_true(text):
    assert _has_narrative_order_connective(text) is True

@pytest.mark.parametrize("text", ["가 뒤검토한후", "가 후작성한뒤", "가 다음제출한후"])
def test_scan_resumes_inside_run_after_previous_match(text):
    # A blanket negative lookbehind on Hangul would lose these later matches.
    assert _has_narrative_order_connective(text) is True
