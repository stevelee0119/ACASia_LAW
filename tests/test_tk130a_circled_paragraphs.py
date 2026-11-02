"""TK-130a: 제21항 이상 원숫자(㉑~㊿) 항 경계. ㉑(U+3251)은 ⑳(U+2473)와 코드 범위가 이어지지 않는다."""
import pytest

# --- TK-130 2: 제21항 이상 원숫자 -------------------------------------------------------------------------------
from packages.legal_engine.temporal_review import paragraph_text

ALL_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"
ARTICLE = "제9조(시험) " + " ".join(f"{c} 제{i}항 본문." for i, c in enumerate(ALL_CIRCLED, start=1))


@pytest.mark.parametrize("n", ["20", "21", "22", "35", "36", "49"])
def test_paragraphs_beyond_twenty_are_sliced(n):
    text = paragraph_text(ARTICLE, n)
    assert f"제{n}항 본문" in text
    assert f"제{int(n) + 1}항" not in text and f"제{int(n) - 1}항 본문" not in text


@pytest.mark.parametrize("n", ["1", "2", "19"])
def test_paragraphs_below_twenty_unchanged(n):
    assert paragraph_text(ARTICLE, n).strip() == f"{'①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲'[int(n) - 1]} 제{n}항 본문."


def test_last_paragraph_fifty():
    assert paragraph_text(ARTICLE, "50").strip() == "㊿ 제50항 본문."


@pytest.mark.parametrize("before,first,second", [("⑳", "㉑", "㉒"), ("㉞", "㉟", "㊱"), ("㊽", "㊾", "㊿")])
def test_content_comparison_scopes_by_paragraphs_beyond_twenty(before, first, second):
    # 내용 대조 경로(compare_claim_to_provision → _scoped_body). 주장한 기간(60일)이 앞 항과 뒤 항에만 있으므로,
    # first·second 어느 경계 하나라도 나누지 못하면 60일이 같은 구절에 섞여 '일치'로 잘못 판정된다.
    from packages.legal_engine.provision_content import compare_claim_to_provision
    body = (f"{before} 병은 60일 이내에 신고하여야 하고 {first} 갑은 30일 이내에 신고하여야 하고 "
            f"{second} 을은 60일 이내에 신고하여야 하고")
    result = compare_claim_to_provision("갑은 60일 이내에 신고하여야 한다", body, subject="갑")
    assert result["status"] == "CONTRADICTED"


# --- 값·문장이 다른 조문 3꼴(AGENTS.md: 새 규칙은 값·문장이 다른 양성 3건 이상) -------------------------------------
from packages.rag_engine.provision_quotes import _paragraph  # noqa: E402

ARTICLE_ITEMS = ("제7조(보고) ⑳ 기관은 보고서를 작성한다.\n㉑ 보고서는 서면으로 제출한다.\n"
                 "㉒ 제21항의 보고서에는 다음 각 호의 사항을 적어야 한다.\n1. 일시\n2. 장소\n㉓ 보고 기한은 30일로 한다.")
ARTICLE_GLUED = "제12조(회의) ⑳위원회는 재적위원 과반수로 의결한다.㉑위원장은 회의를 소집한다.㉒회의는 공개한다."
ARTICLE_HIGH = ("제3조(정의) ㊲ \"시설\"이란 건축물을 말한다. ㊳ \"설비\"란 기계를 말한다(2024. 1. 1. 개정). "
                "㊴ \"장비\"란 이동 가능한 기구를 말한다. ㊵ 그 밖의 용어는 대통령령으로 정한다.")
CASES = [
    (ARTICLE_ITEMS, "22", "제21항의 보고서에는", ("보고 기한은", "서면으로 제출한다")),
    (ARTICLE_GLUED, "21", "위원장은 회의를 소집한다", ("공개한다", "과반수로")),
    (ARTICLE_HIGH, "39", "이동 가능한 기구", ("대통령령으로", "기계를 말한다")),
]


@pytest.mark.parametrize("article,n,inside,outside", CASES)
def test_varied_articles_both_paragraph_helpers(article, n, inside, outside):
    # 법령 시점 대조(temporal_review.paragraph_text)와 Drive 인용 대조(rag_engine.provision_quotes._paragraph)가
    # 같은 항 범위를 돌려주는지. 둘 중 하나라도 ⑳에서 멈추면 실패한다.
    for helper in (paragraph_text, _paragraph):
        text = helper(article, n)
        assert text is not None and inside in text
        assert all(word not in text for word in outside)


@pytest.mark.parametrize("article,n", [(ARTICLE_ITEMS, "51"), (ARTICLE_GLUED, "0")])
def test_out_of_range_paragraph_controls(article, n):
    # 대조: ㊿를 넘거나 0인 항 번호는 항을 고르지 않는다(시점 대조는 조문 전체, Drive 인용 대조는 None — 기존 동작).
    assert paragraph_text(article, n) == article
    assert _paragraph(article, n) is None
