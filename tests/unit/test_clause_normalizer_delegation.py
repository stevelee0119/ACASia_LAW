"""Unit tests for ClauseNormalizer delegation in polarity.py (P1 PR-06)."""
from __future__ import annotations

import pytest

from packages.legal_engine.polarity import (
    ASSERTED,
    CONDITIONAL,
    NEGATED,
    REPORTED,
    clause_normalizer_polarity,
    polarity,
)


def test_clause_normalizer_delegation_matches_core_cases(monkeypatch):
    monkeypatch.setenv("LV_CLAUSE_NORMALIZER_MODE", "default")

    # 3 negated / non-asserted controls
    s_neg = "이 조항이 언제나 무효인 것은 아니다."
    idx_neg = s_neg.index("무효") + 2
    assert polarity(s_neg, (s_neg.index("무효"), idx_neg)) == NEGATED

    s_rep = "피고는 이 사건 계약이 무효라고 주장하나 이유 없다."
    assert polarity(s_rep, (s_rep.index("무효"), s_rep.index("무효") + 2)) == REPORTED

    s_cond = "설령 이 사건 계약이 무효라 하더라도 청구는 기각되어야 한다."
    assert polarity(s_cond, (s_cond.index("무효"), s_cond.index("무효") + 2)) == CONDITIONAL

    # 3 asserted positives (including double negation)
    s_ass1 = "이 사건 계약은 당연히 무효이다."
    assert polarity(s_ass1, (s_ass1.index("무효"), s_ass1.index("무효") + 2)) == ASSERTED

    s_ass2 = "이 조항이 무효가 아니라고 볼 수 없다."
    assert polarity(s_ass2, (s_ass2.index("무효"), s_ass2.index("무효") + 2)) == ASSERTED

    s_ass3 = "피고의 책임이 인정된다."
    assert polarity(s_ass3, (s_ass3.index("책임"), s_ass3.index("책임") + 2)) == ASSERTED
