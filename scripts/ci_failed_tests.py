"""CI 실패 시험 목록 게시 (평가 에이전트 소관, 보호 경로). 2026-10-04 사용자 승인 '검증 실행 중복 줄이기'.

평가 측이 CI 로그 원문을 내려받지 못해도 실패 원인을 알 수 있도록, pytest `-rfE` 출력(tee로 남긴 파일)에서
`FAILED`·`ERROR` 줄을 모아 (1) 로그 끝에 목록으로 찍고 (2) GitHub 오류 주석(annotation)으로 남기고
(3) 작업 요약($GITHUB_STEP_SUMMARY)에 붙인다. 시험 결과를 바꾸지 않으며 항상 종료 코드 0이다.
사용: python scripts/ci_failed_tests.py <pytest 출력 파일>...
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.path_guard import contained_path  # noqa: E402

LINE = re.compile(r"^(FAILED|ERROR) (\S+)")
LIMIT = 60


def failures(paths: List[str]) -> List[Tuple[str, str]]:
    """(출력 파일 이름, 'FAILED 노드' 줄) 목록. 같은 줄은 한 번만."""
    out: List[Tuple[str, str]] = []
    seen = set()
    for p in paths:
        try:
            path = contained_path(p)  # TK-175: 저장소·임시 폴더 안의 pytest 출력만 읽는다
        except ValueError:
            continue
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = LINE.match(raw.strip())
            if m and (path.name, m.group(0)) not in seen:
                seen.add((path.name, m.group(0)))
                out.append((path.name, m.group(0)))
    return out


def _escape(text: str) -> str:
    """워크플로 명령 값의 예약 문자를 바꾼다(GitHub 문서의 규칙: % → %25, CR → %0D, LF → %0A)."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(text: str) -> str:
    """속성 값(title)은 ':'·','도 바꾼다."""
    return _escape(text).replace(":", "%3A").replace(",", "%2C")


def main(argv: List[str]) -> int:
    items = failures(argv)
    print(f"실패 시험 목록: {len(items)}건" + (f"(처음 {LIMIT}건만 표시)" if len(items) > LIMIT else ""))
    for name, line in items[:LIMIT]:
        print(f"  [{name}] {line}")
        print(f"::error title={_escape_property(name)}::{_escape(line[:300])}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:  # TK-175: 작업 요약 파일은 러너 임시 폴더 안만(밖이면 요약만 건너뛴다. 종료 코드는 늘 0)
            summary_path = contained_path(summary, os.environ.get("RUNNER_TEMP") or tempfile.gettempdir())
        except ValueError:
            return 0
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(f"### 실패 시험 {len(items)}건\n```\n")
            fh.writelines(f"[{name}] {line}\n" for name, line in items[:LIMIT])
            fh.write("```\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
