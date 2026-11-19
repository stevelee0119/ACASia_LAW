"""평가 도구가 여는 파일 경로를 허용 폴더 안으로 묶는다(CodeQL py/path-injection, 릴리스 PR #285).

평가 도구는 명령행 인자·환경변수(TESSDATA_PREFIX)·하위 프로세스 출력으로 경로를 받는다. 실제 경로로 펴서
(심볼릭 링크·'..' 해소) 허용 폴더 안인지 확인하고, 밖이면 ValueError를 낸다.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
# 저장소와 임시 폴더(시험 tmp_path·기준 커밋 worktree)만 평가 자료·출력 위치로 쓴다.
WORK_ROOTS = (ROOT, Path(tempfile.gettempdir()))


def _main_checkout() -> Optional[Path]:
    """이 파일이 속한 저장소의 주 작업 폴더. 없으면 None(TK-219).

    기준 커밋 worktree에서 돌 때 ROOT는 임시 폴더이고, 시험 명세·입력은 현재 저장소에 있다. 저장소가
    홈 밖에 있으면 그 입력이 어느 허용 폴더에도 들지 않아 전 항목이 '측정 못 함'이 됐다. 허용 폴더를
    환경변수가 아니라 git이 알려주는 공통 폴더에서 끌어내 같은 저장소의 주 작업 폴더만 받는다.
    """
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    line = out.stdout.strip()
    if out.returncode != 0 or not line:
        return None
    common = Path(os.path.realpath(line))  # <주 작업 폴더>/.git
    return common.parent if common.name == ".git" else None


# 평가 측이 받은 서면(사용자 업로드)을 탐침할 때: 저장소·임시 폴더에 더해 사용자 홈 아래(TK-175)와
# 같은 저장소의 주 작업 폴더(TK-219). 주 작업 폴더는 worktree가 아닐 때 이미 ROOT로 허용되던 곳이다.
MAIN_CHECKOUT = _main_checkout()
INPUT_ROOTS = tuple(r for r in (*WORK_ROOTS, Path.home(), MAIN_CHECKOUT) if r is not None)
# 한국어 OCR 모델(tessdata) 위치: 배포판 패키지·로컬 설치·저장소 안.
TESSDATA_ROOTS = ("/usr/share", "/usr/local/share", "/opt", ROOT)


def contained_path(path, *roots) -> Path:
    """path를 실제 경로로 펴서 roots(기본 WORK_ROOTS) 중 하나의 안(그 폴더 자신은 제외)이면 돌려준다. 밖이면 ValueError."""
    full = os.path.realpath(os.fspath(path))
    for root in roots or WORK_ROOTS:
        prefix = os.path.join(os.path.realpath(os.fspath(root)), "")  # 끝에 구분자 하나
        # 검사는 정규화한 full 자체에 대한 startswith 하나로만 한다. 다른 값을 검사하거나 'or'로 묶으면
        # CodeQL이 경로 검증으로 인정하지 않는다. 허용 폴더 자신이 아니라 그 안의 경로만 받는다.
        if full.startswith(prefix):
            return Path(full)
    raise ValueError(f"허용 폴더 밖의 경로: {path}")
