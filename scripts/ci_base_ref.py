#!/usr/bin/env python3
"""CI 게이트의 비교 기준(BASE) 커밋을 하나의 규칙으로 정한다 (TK-212).

왜 스크립트인가
---------------
기준을 `github.event.pull_request.base.sha || github.event.before`로 적으면 **같은 커밋에
대해 이벤트 종류에 따라 다른 기준**이 나온다. 실제로 2026-11-19 `832c439f`에서
`push` 실행은 직전 head(`1d27895f`)를, `pull_request` 실행은 PR base(`556dac84`)를 기준으로
삼아 `점수 하락 게이트`가 한쪽은 failure, 한쪽은 success였다. 같은 코드의 게이트 결론이
갈리면 판정 자체를 믿을 수 없다.

워크플로 YAML 안의 셸 분기는 시험할 수 없으므로 판정을 여기로 빼고 단위 시험을 붙인다.

규칙 (순서대로)
---------------
1. HEAD가 병합 커밋이면(부모 2개 이상) **첫 부모**가 기준이다.
   `pull_request` 실행은 `refs/pull/<N>/merge`를 꺼내므로 HEAD가 '기준 브랜치 끝 + 이 PR'의
   병합 커밋이고, 그 첫 부모가 **지금의** 기준 브랜치 끝이다. `base.sha`는 PR이 마지막으로
   갱신된 시점의 값이라 그 뒤 병합된 다른 PR의 효과가 이 PR 몫으로 섞인다(#120에서 확인).
2. 통합·배포 브랜치 푸시면 직전 커밋(`HEAD~1`)이 기준이다. 그 브랜치에서는 '이 푸시가 더한 것'이
   곧 평가 대상이다.
3. 그 밖(열린 PR 없는 브랜치의 수동 실행 등)은 통합 브랜치와의 공통 조상이 기준이다.
4. 어느 것도 풀리지 않으면 `HEAD~1`로 내려간다. 그마저 없으면(최초 커밋) 빈 트리 해시를 쓴다.

출력은 커밋 해시 한 줄이다. 워크플로는 `BASE=$(python scripts/ci_base_ref.py)`로 쓴다.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Callable, List, Optional, Sequence

# `git hash-object -t tree /dev/null` — 모든 저장소에서 같은 빈 트리 해시다.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

INTEGRATION_BRANCH = "Steve_ACASiaLAW"
DEPLOY_BRANCH = "main"


def _git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return r.returncode, r.stdout.strip()


def _resolve(rev: str) -> Optional[str]:
    """rev가 실제 커밋이면 그 해시, 아니면 None."""
    code, out = _git("rev-parse", "-q", "--verify", f"{rev}^{{commit}}")
    return out if code == 0 and out else None


def _head_parents() -> List[str]:
    code, out = _git("rev-list", "--parents", "-n", "1", "HEAD")
    if code != 0 or not out:
        return []
    return out.split()[1:]


def select_base_with_reason(
    parents: Sequence[str],
    ref_name: str,
    resolve: Callable[[str], Optional[str]],
    integration: str = INTEGRATION_BRANCH,
    deploy: str = DEPLOY_BRANCH,
) -> tuple[str, str]:
    """기준 커밋과 그것을 고른 이유를 돌려준다. 순수 함수이므로 단위 시험이 가능하다.

    parents: HEAD의 부모 해시 목록(0개 = 최초 커밋)
    ref_name: GITHUB_REF_NAME. PR 실행에서는 '<번호>/merge' 꼴이다
    resolve: rev -> 해시 또는 None (저장소 조회를 주입한다)

    이유를 값으로 돌려주는 까닭: 밖에서 되짚으면 공통 조상이 직전 커밋과 같을 때
    '내려감'으로 잘못 적는다(2026-11-19 사전 검증에서 확인).
    """
    # 1. 병합 시험 커밋(PR 실행): 첫 부모가 지금의 기준 브랜치 끝이다.
    if len(parents) >= 2:
        return parents[0], "PR 병합 시험 커밋의 첫 부모(지금의 기준 브랜치 끝)"

    # 2. 통합·배포 브랜치 푸시: 직전 커밋.
    if ref_name in (integration, deploy):
        if parents:
            return parents[0], f"{ref_name} 푸시의 직전 커밋"
        return EMPTY_TREE, "최초 커밋이라 빈 트리"

    # 3. 그 밖: 통합 브랜치와의 공통 조상.
    for candidate in (f"origin/{integration}", integration):
        tip = resolve(candidate)
        if tip is None:
            continue
        merge_base = resolve(f"merge-base:{tip}")
        if merge_base:
            return merge_base, f"{candidate}와의 공통 조상"

    # 4. 내려감.
    if parents:
        return parents[0], "공통 조상을 풀 수 없어 직전 커밋으로 내려감"
    return EMPTY_TREE, "기준을 풀 수 없고 부모도 없어 빈 트리"


def select_base(
    parents: Sequence[str],
    ref_name: str,
    resolve: Callable[[str], Optional[str]],
    integration: str = INTEGRATION_BRANCH,
    deploy: str = DEPLOY_BRANCH,
) -> str:
    """기준 커밋만 돌려준다."""
    return select_base_with_reason(parents, ref_name, resolve, integration, deploy)[0]


def _resolver_with_merge_base() -> Callable[[str], Optional[str]]:
    """select_base가 쓰는 조회기. 'merge-base:<tip>'는 공통 조상 조회로 번역한다."""

    def resolve(rev: str) -> Optional[str]:
        if rev.startswith("merge-base:"):
            tip = rev.split(":", 1)[1]
            code, out = _git("merge-base", tip, "HEAD")
            return out if code == 0 and out else None
        return _resolve(rev)

    return resolve


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="CI 게이트 비교 기준 커밋을 출력한다")
    p.add_argument("--ref-name", default=os.environ.get("GITHUB_REF_NAME", ""))
    p.add_argument("--integration", default=INTEGRATION_BRANCH)
    p.add_argument("--deploy", default=DEPLOY_BRANCH)
    p.add_argument("--explain", action="store_true", help="고른 이유를 stderr에 적는다")
    a = p.parse_args(argv)

    parents = _head_parents()
    base, why = select_base_with_reason(
        parents, a.ref_name, _resolver_with_merge_base(), a.integration, a.deploy
    )
    if a.explain:
        print(f"기준 {base} — {why}", file=sys.stderr)
    print(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
