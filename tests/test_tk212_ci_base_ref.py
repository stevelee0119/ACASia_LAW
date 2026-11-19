"""TK-212 — CI 게이트 비교 기준(BASE)이 이벤트 종류와 무관하게 하나로 정해지는지.

배경: 2026-11-19 같은 커밋 `832c439f`에서 `push` 실행과 `pull_request` 실행이 서로 다른
기준을 써 `점수 하락 게이트`가 한쪽 failure·한쪽 success였다. 기준 판정을
scripts/ci_base_ref.py로 빼고 여기서 축을 전수 시험한다.

축: (HEAD 부모 수 0·1·2) × (ref_name: 통합·배포·기능 브랜치·PR merge 꼴) × (통합 ref 조회 가능/불가)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ci_base_ref import EMPTY_TREE, select_base  # noqa: E402

INTEG = "Steve_ACASiaLAW"
DEPLOY = "main"

PREV = "a" * 40        # 직전 커밋 / 병합 커밋의 첫 부모
SIDE = "b" * 40        # 병합 커밋의 둘째 부모
TIP = "c" * 40         # origin/통합 브랜치 끝
ANCESTOR = "d" * 40    # 공통 조상


def _resolver(*, integration_tip=TIP, merge_base=ANCESTOR):
    """저장소 조회를 흉내낸다. integration_tip=None이면 통합 ref를 못 푼다."""

    def resolve(rev: str):
        if rev.startswith("merge-base:"):
            return merge_base
        if rev in (f"origin/{INTEG}", INTEG):
            return integration_tip
        return None

    return resolve


# --- 축 1: 병합 시험 커밋(PR 실행)은 ref_name과 무관하게 첫 부모 ---------------

@pytest.mark.parametrize("ref_name", ["343/merge", "346/merge", INTEG, DEPLOY, "feat/x", ""])
def test_merge_ref_checkout_always_uses_first_parent(ref_name):
    base = select_base([PREV, SIDE], ref_name, _resolver(), INTEG, DEPLOY)
    assert base == PREV


def test_octopus_merge_also_uses_first_parent():
    base = select_base([PREV, SIDE, "e" * 40], "343/merge", _resolver(), INTEG, DEPLOY)
    assert base == PREV


# --- 축 2: 통합·배포 브랜치 푸시는 직전 커밋 ---------------------------------

@pytest.mark.parametrize("ref_name", [INTEG, DEPLOY])
def test_integration_and_deploy_push_uses_previous_commit(ref_name):
    base = select_base([PREV], ref_name, _resolver(), INTEG, DEPLOY)
    assert base == PREV


@pytest.mark.parametrize("ref_name", [INTEG, DEPLOY])
def test_integration_push_does_not_consult_integration_tip(ref_name):
    """통합 브랜치에서 자기 자신과의 공통 조상(=자기 끝)을 기준으로 삼으면 diff가 빈다."""
    base = select_base([PREV], ref_name, _resolver(), INTEG, DEPLOY)
    assert base != TIP


# --- 축 3: 그 밖 브랜치는 공통 조상 -----------------------------------------

def test_feature_branch_push_uses_merge_base():
    base = select_base([PREV], "feat/tk208", _resolver(), INTEG, DEPLOY)
    assert base == ANCESTOR


def test_evaluator_branch_push_uses_merge_base():
    base = select_base([PREV], "evaluator/023-round2", _resolver(), INTEG, DEPLOY)
    assert base == ANCESTOR


def test_falls_back_to_previous_commit_when_integration_ref_missing():
    base = select_base(
        [PREV], "feat/x", _resolver(integration_tip=None), INTEG, DEPLOY
    )
    assert base == PREV


def test_falls_back_to_previous_commit_when_merge_base_missing():
    base = select_base(
        [PREV], "feat/x", _resolver(merge_base=None), INTEG, DEPLOY
    )
    assert base == PREV


def test_local_integration_ref_is_used_when_remote_missing():
    def resolve(rev: str):
        if rev.startswith("merge-base:"):
            return ANCESTOR
        if rev == f"origin/{INTEG}":
            return None
        if rev == INTEG:
            return TIP
        return None

    assert select_base([PREV], "feat/x", resolve, INTEG, DEPLOY) == ANCESTOR


# --- 축 4: 부모 없는 최초 커밋 ----------------------------------------------

@pytest.mark.parametrize("ref_name", [INTEG, DEPLOY, "feat/x"])
def test_root_commit_uses_empty_tree(ref_name):
    base = select_base(
        [], ref_name, _resolver(integration_tip=None), INTEG, DEPLOY
    )
    assert base == EMPTY_TREE


def test_empty_tree_hash_is_the_real_one():
    out = subprocess.run(
        ["git", "hash-object", "-t", "tree", "/dev/null"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert out == EMPTY_TREE


# --- 축 5: 같은 커밋에서 두 이벤트가 같은 값을 내는지 (TK-212의 본체) --------
# PR 실행은 병합 시험 커밋을, push 실행은 브랜치 끝을 꺼낸다. B-1(2026-11-19 사용자 승인)로
# 기능·평가 브랜치의 push 실행은 더 이상 생기지 않으므로 그 조합은 PR 실행 하나만 남는다.
# 통합 브랜치에서는 병합 커밋이 곧 브랜치 끝이어서 두 경로가 같은 값을 낸다.

def test_integration_merge_commit_same_base_for_both_events():
    as_push = select_base([PREV, SIDE], INTEG, _resolver(), INTEG, DEPLOY)
    as_pr = select_base([PREV, SIDE], "346/merge", _resolver(), INTEG, DEPLOY)
    assert as_push == as_pr == PREV


def test_no_event_field_is_consulted():
    """기준 판정이 github.event에 의존하지 않는 것을 코드에서 확인한다."""
    src = (Path(__file__).resolve().parents[1] / "scripts" / "ci_base_ref.py").read_text(
        encoding="utf-8"
    )
    body = src.split('"""', 2)[2]  # 모듈 설명(원인 기록)은 제외한다
    assert "pull_request.base.sha" not in body
    assert "event.before" not in body


# --- 축 6: 고른 이유를 값으로 돌려준다 (2026-11-19 사전 검증에서 찾은 결함) ----
# 밖에서 '기준 == 직전 커밋'으로 이유를 되짚으면, 공통 조상이 직전 커밋과 같은 경우(브랜치에
# 커밋이 하나뿐일 때)를 '내려감'으로 잘못 적는다. 이유는 판정 쪽에서 돌려준다.

def test_reason_is_merge_base_even_when_it_equals_previous_commit():
    from scripts.ci_base_ref import select_base_with_reason

    base, why = select_base_with_reason(
        [PREV], "feat/x", _resolver(merge_base=PREV), INTEG, DEPLOY
    )
    assert base == PREV
    assert "공통 조상" in why
    assert "내려감" not in why


def test_reason_says_fallback_only_when_integration_ref_unresolvable():
    from scripts.ci_base_ref import select_base_with_reason

    base, why = select_base_with_reason(
        [PREV], "feat/x", _resolver(integration_tip=None), INTEG, DEPLOY
    )
    assert base == PREV
    assert "내려감" in why


@pytest.mark.parametrize(
    "parents,ref_name,expect",
    [
        ([PREV, SIDE], "343/merge", "첫 부모"),
        ([PREV], INTEG, "직전 커밋"),
        ([PREV], DEPLOY, "직전 커밋"),
        ([PREV], "feat/x", "공통 조상"),
        ([], INTEG, "최초 커밋"),
    ],
)
def test_every_branch_reports_a_reason(parents, ref_name, expect):
    from scripts.ci_base_ref import select_base_with_reason

    _, why = select_base_with_reason(parents, ref_name, _resolver(), INTEG, DEPLOY)
    assert expect in why
