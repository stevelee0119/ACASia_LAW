"""평가 도구가 여는 파일 경로를 허용 폴더 안으로 묶는다(CodeQL py/path-injection, 릴리스 PR #285).

평가 도구는 명령행 인자·환경변수(TESSDATA_PREFIX)·하위 프로세스 출력으로 경로를 받는다. 실제 경로로 펴서
(심볼릭 링크·'..' 해소) 허용 폴더 안인지 확인하고, 밖이면 ValueError를 낸다.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 저장소와 임시 폴더(시험 tmp_path·기준 커밋 worktree)만 평가 자료·출력 위치로 쓴다.
WORK_ROOTS = (ROOT, Path(tempfile.gettempdir()))
# 한국어 OCR 모델(tessdata) 위치: 배포판 패키지·로컬 설치·저장소 안.
TESSDATA_ROOTS = ("/usr/share", "/usr/local/share", "/opt", ROOT)


def contained_path(path, *roots) -> Path:
    """path를 실제 경로로 펴서 roots(기본 WORK_ROOTS) 중 하나의 안이면 돌려준다. 밖이면 ValueError."""
    full = os.path.realpath(os.fspath(path))
    for root in roots or WORK_ROOTS:
        base = os.path.realpath(os.fspath(root))
        if full == base or full.startswith(base.rstrip(os.sep) + os.sep):
            return Path(full)
    raise ValueError(f"허용 폴더 밖의 경로: {path}")
