from __future__ import annotations

import pytest

from packages.claim_engine.classification import assertion_mode


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        # Positive cases (>= 3): ClauseNormalizer handles expanded speaker/modality forms
        ("청구인 측은 이 사건 계약이 무효라는 취지로 항변한다.", "QUOTED_OTHER"),
        ("채무자는 변제가 완료되었다고 다툰다.", "QUOTED_OTHER"),
        ("예비적으로 부당이득 반환을 청구한다.", "ALTERNATIVE"),
        ("설령 통지가 지연되었다고 보더라도 손해는 없다.", "HYPOTHETICAL"),
    ],
)
def test_assertion_mode_delegation_positive(sentence: str, expected: str) -> None:
    assert assertion_mode(sentence) == expected


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        # Control cases (>= 3): author assertions / legal positions must not be misclassified
        ("당사자는 2026. 1. 10. 물품을 납품하였다.", "ASSERTED"),
        ("이 사건 처분은 재량권을 일탈·남용하여 위법하다.", "LEGAL_POSITION"),
        ("작성자는 계약서에 서명하고 원본을 보관하였다.", "ASSERTED"),
    ],
)
def test_assertion_mode_delegation_controls(sentence: str, expected: str) -> None:
    assert assertion_mode(sentence) == expected
