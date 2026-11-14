"""TK-163 원문 대조 보기 + TK-160 주장 3분류 배지(화면·보고서). 문장·사건번호는 모두 합성이다."""
from __future__ import annotations

import copy
import os
from types import SimpleNamespace

import pytest

from packages.common.schemas import Block, ReviewItem
from packages.legal_engine.evidence_basis import ALIGN_LIMIT, align_quote
from packages.report_engine.reference_opinions import compare_text
from packages.verification_engine.review_items import build_source_comparison, claim_verdict_of
from test_legal_engine import _verify  # noqa: F401  (시험용 내부 Mirror의 가상 판례)

OFFICIAL = "징계권자가 재량권의 행사로서 한 처분이 사회통념상 현저하게 타당성을 잃은 경우에 한하여 위법하다고 할 수 있다"


def _marks(alignment, side):
    return [(t, m) for t, m in alignment[side] if m != "same"]


# --- 엔진: 어절 정렬 ------------------------------------------------------------------------------------
def test_deleted_word_is_marked_removed_on_the_official_side():
    a = align_quote("재량권의 행사로서 한 처분이 사회통념상 타당성을 잃은 경우", OFFICIAL)
    assert a and a["changed"] and _marks(a, "official") == [("현저하게", "removed")] and _marks(a, "quoted") == []


def test_replaced_word_is_marked_on_both_sides():
    a = align_quote("재량권의 행사로서 한 처분이 사회통념상 다소 타당성을 잃은 경우", OFFICIAL)
    assert ("현저하게", "changed") in _marks(a, "official") and ("다소", "changed") in _marks(a, "quoted")


def test_added_word_is_marked_added_on_the_quoted_side():
    a = align_quote("재량권의 행사로서 한 처분이 사회통념상 현저하게 명백히 타당성을 잃은 경우", OFFICIAL)
    assert _marks(a, "quoted") == [("명백히", "added")] and _marks(a, "official") == []


def test_exact_quote_has_no_marks():
    a = align_quote("사회통념상 현저하게 타당성을 잃은 경우에 한하여", OFFICIAL)
    assert a and not a["changed"]


@pytest.mark.parametrize("quoted", ["", "전혀 다른 문장으로 원문과 겹치는 어절이 없는 인용문이다", "가나다"])
def test_no_alignment_when_not_comparable(quoted):
    assert align_quote(quoted, OFFICIAL) is None
    assert align_quote(OFFICIAL, "") is None


def test_long_quote_is_trimmed_without_false_tail_marks():
    base = " ".join(f"어절{i}" for i in range(400))
    a = align_quote(base, "앞말 " + base + " 뒷말")
    assert a["truncated"] and a["quoted"][-1][1] == "same" and a["official"][-1][1] == "same"
    assert len(" ".join(t for t, _ in a["quoted"])) <= ALIGN_LIMIT and not a["changed"]


def test_verifier_stores_alignment_from_full_official_text(registry):
    _, result = _verify(registry, '대법원 2099. 1. 15. 선고 2099도99999 판결은 "테스트를 위한 판시사항이다"라고 판시하였다.')
    verdict = result.data["verdicts"][0]
    alignment = verdict["review"]["quote_alignment"]
    assert alignment["changed"] and ("가상의", "removed") in _marks(alignment, "official")
    assert verdict["evidence_basis"]["basis_status"]  # TK-159 근거와 함께 실린다


# --- 검토 항목: 원문 대조 자료·3분류 ----------------------------------------------------------------------
BASIS = {"basis_status": "SOURCE_MISMATCHED",
         "source": {"kind": "OFFICIAL_CASE", "id": "1", "court": "대법원", "decision_date": "2099-01-15",
                    "case_number": "2099도99999", "detail_link": "https://www.law.go.kr/precInfoP.do?precSeq=1"},
         "passage": {"excerpt": "테스트를 위한 가상의 판시사항이다"}}


def _row(review=None, basis=BASIS):
    return {"citation_id": "c1", "evidence_basis": basis, "review": review or {}}


def test_comparison_carries_status_source_alignment_and_summary():
    alignment = align_quote("테스트를 위한 판시사항이다", "테스트를 위한 가상의 판시사항이다")
    c = build_source_comparison(_row({"quote_alignment": alignment}))
    assert c["status_label"] == "공식 원문과 다름" and c["source_label"] == "대법원 2099-01-15 2099도99999"
    assert c["alignment"] == alignment and c["official_excerpt"] is None and c["location_confidence"] == "TEXT"
    assert "인용에서 빠짐 1곳(1어절)" in c["summary"] and c["detail_link"].startswith("https://")


def test_statute_without_quote_shows_official_excerpt_only():
    basis = {"basis_status": "SOURCE_MATCHED", "source": {"kind": "OFFICIAL_LAW", "id": "9", "effective_from": "2099-01-01"},
             "passage": {"excerpt": "합성 조문 본문"}}
    c = build_source_comparison(_row(basis=basis))
    assert c["alignment"] is None and c["official_excerpt"] == "합성 조문 본문"
    assert c["source_label"] == "공식 법령 원문 (시행 2099-01-01)" and "직접 인용문 없음" in c["summary"]


@pytest.mark.parametrize("row", [
    {"citation_id": "c1"},                                                                          # 근거 없음
    _row(basis={"basis_status": "RULE_BASED", "source": {"kind": "DETERMINISTIC_RULE"}, "passage": None}),  # 규칙 판정
    _row(basis={"basis_status": "LOOKUP_FAILED", "source": None, "passage": None}),                 # 조회 실패
])
def test_no_comparison_box_without_an_official_passage(row):
    assert build_source_comparison(row) is None


def test_scanned_citation_is_flagged_and_unsafe_link_dropped():
    doc = SimpleNamespace(block_by_id=lambda b: Block(block_id=b, text="x", page=1, source_layer="ocr_layer"))
    basis = copy.deepcopy(BASIS)
    basis["source"]["detail_link"] = "javascript:alert(1)"
    c = build_source_comparison(_row(basis=basis), SimpleNamespace(block_id="b1"), doc)
    assert c["location_confidence"] == "OCR" and c["detail_link"] is None


def test_claim_verdict_is_taken_from_the_claim_row():
    assert claim_verdict_of({}) is None
    v = claim_verdict_of({"claim_verdict": "INSUFFICIENT", "claim_verdict_label": "근거 부족", "claim_verdict_note": "합성 사유"})
    assert v == {"code": "INSUFFICIENT", "label": "근거 부족", "note": "합성 사유"}


def test_review_item_serializes_new_fields():
    item = ReviewItem(item_id="i", kind="CITATION", document_id="d", claim_text="c", official_status="OFFICIAL_CONFIRMED",
                      reference_status="NOT_CHECKED", verdict_label="v", severity="INFO",
                      source_comparison={"summary": "s"}, claim_verdict={"code": "SUPPORTED"})
    d = item.to_dict()
    assert d["source_comparison"] == {"summary": "s"} and d["claim_verdict"] == {"code": "SUPPORTED"}


# --- 보고서 요약 줄 ------------------------------------------------------------------------------------
def test_report_cell_gets_claim_verdict_and_comparison_summary():
    alignment = align_quote("테스트를 위한 판시사항이다", "테스트를 위한 가상의 판시사항이다")
    comparison = build_source_comparison(_row({"quote_alignment": alignment}))
    document = SimpleNamespace(review_items=[{"citation_id": "c1", "source_comparison": comparison}])
    row = {"citation_id": "c1", "claim_verdict_label": "근거와 모순", "claim_verdict_note": "합성 사유"}
    text = compare_text(document, row)
    assert "[근거 판정] 근거와 모순 — 합성 사유" in text
    assert "[원문 대조] 공식 원문과 다름 · 대법원 2099-01-15 2099도99999 · 공식 원문과 다른 곳: 인용에서 빠짐 1곳(1어절)" in text
    assert compare_text(SimpleNamespace(review_items=[]), {"citation_id": "c9"}) == ""


# --- 화면 -------------------------------------------------------------------------------------------
@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright
    options = {"headless": True}
    if os.getenv("LV_TEST_BROWSER_CHANNEL"):
        options["channel"] = os.environ["LV_TEST_BROWSER_CHANNEL"]
    with sync_playwright() as playwright:
        b = playwright.chromium.launch(**options)
        yield b
        b.close()


def _result_with_comparison():
    import test_tk155_ui_cleanup as ui
    result = copy.deepcopy(ui.RESULT)
    item = result["documents"][0]["review_items"][1]  # 합성 판례 인용 행(출처 미확인 탭)
    alignment = align_quote("테스트를 위한 판시사항이다", "이 사건에서 테스트를 위한 가상의 판시사항이다 라고 보았다")
    item["source_comparison"] = build_source_comparison(_row({"quote_alignment": alignment}))
    item["claim_verdict"] = {"code": "INSUFFICIENT", "label": "근거 부족", "note": "공식 원문의 근거 구간이 없어 모순으로 단정하지 않음"}
    return ui, result


def test_review_row_shows_badge_and_side_by_side_comparison(browser, monkeypatch):
    from playwright.sync_api import expect
    ui, result = _result_with_comparison()
    monkeypatch.setattr(ui, "RESULT", result)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    ui._serve(page, ui.BASE_PROJECT)
    page.locator('.tabs button[data-tab="review"]').click()
    box = page.locator("#reviewTable details.source-compare").first
    expect(box).to_contain_text("원문 대조 보기 · 공식 원문과 다름")
    expect(page.locator("#reviewTable .claim-verdict").first).to_have_text("근거 부족")
    box.locator(":scope > summary").click()
    expect(box.locator(":scope > .compare-hunks del.diff-removed")).to_have_text("가상의")  # 칸 요약(다른 곳만)
    expect(box.locator(":scope > .compare-hunks .compare-quoted")).to_contain_text("테스트를 위한 판시사항이다")
    expect(box.locator(":scope > .compare-hunks .compare-head")).to_have_count(2)  # 머리글은 한 번만
    full = box.locator("details.compare-full")
    expect(full.locator(".compare-grid")).to_be_hidden()  # 전문은 접혀 있다
    full.locator("summary").click()
    expect(full.locator("del.diff-removed")).to_have_text("가상의")
    expect(box.locator("a", has_text="원문 열기")).to_have_attribute("rel", "noopener noreferrer")
    assert ui._codes(box.text_content()) == []
    if os.getenv("TK163_SHOT"):
        box.locator("xpath=ancestor::tr[1]").screenshot(path=os.environ["TK163_SHOT"])


def test_comparison_stacks_on_narrow_screens(browser, monkeypatch):
    from playwright.sync_api import expect
    ui, result = _result_with_comparison()
    monkeypatch.setattr(ui, "RESULT", result)
    page = browser.new_page(viewport={"width": 390, "height": 900})
    ui._serve(page, ui.BASE_PROJECT)
    page.locator('.tabs button[data-tab="review"]').click()
    box = page.locator("#reviewTable details.source-compare").first
    expect(box).to_be_attached()
    page.evaluate("document.querySelectorAll('details.source-compare').forEach(d => d.open = true)")
    columns = box.locator(":scope > .compare-grid").first.evaluate("g => getComputedStyle(g).gridTemplateColumns.split(' ').length")
    assert columns == 1


def test_summary_counts_change_groups_not_only_words():
    official = "가 나 다 라 마 바 사 아 자 차 카 타 파"
    a = align_quote("가 나 다 마 바 사 아 자 거 카 타 파", official)  # '라' 빠짐 1곳, '차'→'거' 바뀜 1곳
    c = build_source_comparison(_row({"quote_alignment": a}))
    assert c["summary"] == "공식 원문과 다른 곳: 인용에서 빠짐 1곳(1어절) · 바뀜 1곳"


LONG = ("공무원에 대한 징계처분이 사회통념상 현저하게 타당성을 잃었다고 하려면 구체적인 사례에 따라 징계의 원인이 된 비위사실의 내용과 성질, "
        "징계에 의하여 달성하려고 하는 행정목적, 징계 양정의 기준 등 여러 요소를 종합하여 판단할 때에 그 징계 내용이 객관적으로 명백히 "
        "부당하다고 인정할 수 있는 경우라야 하고, 징계권자가 내부적인 징계양정기준을 정하고 그에 따라 징계처분을 하였을 경우에는 정해진 "
        "징계양정기준이 합리성이 없다는 등의 특별한 사정이 없는 한 당해 징계처분이 재량권의 범위를 일탈하였다거나 재량권을 남용하였다고 할 수 없다")


def test_compact_hunks_show_only_changed_places_with_short_context():
    quoted = LONG.replace("현저하게 ", "").replace("객관적으로 명백히", "다소")  # 합성 변형
    a = align_quote(quoted, LONG)
    hunks = a["hunks"]
    assert len(hunks) == 2
    first, second = hunks
    assert [t for t, m in first["official"] if m == "removed"] == ["현저하게"] and len(first["official"]) <= 5
    assert [t for t, m in second["quoted"] if m == "changed"] == ["다소"] and second["lead"] and second["tail"]
    assert sum(len(h["quoted"]) for h in hunks) < len(a["quoted"]) // 3  # 칸 요약은 전문보다 훨씬 짧다
    assert align_quote(LONG[:80], LONG)["hunks"] == []  # 같으면 요약할 곳이 없다


def test_long_quote_cell_shows_at_most_three_places(browser, monkeypatch):
    from playwright.sync_api import expect
    ui, result = _result_with_comparison()
    official = LONG
    quoted = (LONG.replace("현저하게 ", "").replace("행정목적, ", "").replace("객관적으로 ", "")
              .replace("내부적인 ", "").replace("특별한 ", ""))  # 서로 떨어진 5곳 삭제(합성)
    item = result["documents"][0]["review_items"][1]
    item["source_comparison"] = build_source_comparison(_row({"quote_alignment": align_quote(quoted, official)}))
    monkeypatch.setattr(ui, "RESULT", result)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    ui._serve(page, ui.BASE_PROJECT)
    page.locator('.tabs button[data-tab="review"]').click()
    box = page.locator("#reviewTable details.source-compare").first
    box.locator(":scope > summary").click()
    expect(box.locator(":scope > .compare-hunks .compare-quoted")).to_have_count(3)
    expect(box).to_contain_text("외 2곳은 전문 대조에서 확인하세요.")
