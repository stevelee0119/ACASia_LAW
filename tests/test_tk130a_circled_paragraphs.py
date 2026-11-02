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


@pytest.mark.parametrize("first,second", [("㉑", "㉒"), ("㉟", "㊱")])
def test_content_comparison_scopes_by_paragraphs_beyond_twenty(first, second):
    # 내용 대조 경로(compare_claim_to_provision → _scoped_body)가 ㉑ 이후 항 경계로 주어별 구절을 나누는지.
    from packages.legal_engine.provision_content import compare_claim_to_provision
    body = f"{first} 갑은 30일 이내에 신고하여야 하고 {second} 을은 60일 이내에 신고하여야 하고"
    result = compare_claim_to_provision("갑은 60일 이내에 신고하여야 한다", body, subject="갑")
    assert result["status"] == "CONTRADICTED"
