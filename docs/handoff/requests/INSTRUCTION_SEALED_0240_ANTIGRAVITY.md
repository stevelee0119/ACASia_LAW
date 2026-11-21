# 0.24.0 후보 봉인 세트 짝 비교 실행 지시 (Antigravity 전달용)

Agent: evaluator. 2026-11-21. 이 문서는 **시험 실행만** 요청한다. 제품 코드·채점기·정답지 수정, 커밋, 병합, 배포를 요청하지 않는다.

## 대상과 조건

- 직전 운영 `main`: `f7a7f49056fa4fc6239ffdad803eed53443d9045` (0.23.0).
- 후보 `Steve_ACASiaLAW`: `0055fa728202c2d4b500099fa2b6c29d8258c07e` (버전 판정 전 코드).
- 동일한 **사용자 보관 봉인 폴더 한 벌**, 동일한 Python 환경·Tesseract `kor+eng`·채점기를 두 SHA에서 각 1회만 쓴다. 두 실행은 한 번의 짝 비교이며, 점수를 본 뒤 제품을 고쳐 같은 봉인 세트를 다시 돌리지 않는다.
- 봉인 원본 폴더는 저장소·PR·대화·에이전트 첨부에 올리지 않는다. 원문 PDF, `ground_truth.json`, `match_spec.json` 및 `.sealed_out/` 상세는 열람·전송·인용하지 않는다. 구현 세션에서 실행하므로 이 평가 후 해당 세트는 개발에 재사용하지 않고 교체한다.
- **2026-11-21 운영본 첫 실행 오류 정정:** `scripts/evaluation_v2.py`는 봉인 폴더가 저장소·시스템 임시 폴더 밖에 있으면 `scripts/path_guard.py:57`에서 `ValueError`를 낸다. 기존 지시의 원본 경로 직접 전달은 동작하지 않았다. 아래 명령은 원본을 변경하지 않고 **같은 Python의 시스템 임시 폴더 안에 일회용 사본**을 만든 뒤 두 SHA에 같은 사본을 전달한다. 두 실행의 상세 출력은 일회용 사본 안에만 생기며, 성공·실패와 관계없이 종료 시 그 사본을 지운다. 첫 시도는 집계 JSON 없이 중단됐으므로 점수 확인 뒤 재시험에 해당하지 않는다.

## 실행

저장소 루트에서 아래를 실행한다. 첫 줄의 경로는 사용자 PC의 **저장소 밖** 봉인 폴더로 바꾼다. 모든 명령은 두 기준의 SHA가 정확할 때만 진행한다. 로컬 venv의 Python 경로를 `ACAS_PYTHON`으로 지정하며, **같은 실행 파일**을 두 worktree에서 사용한다.

```bash
set -euo pipefail
export ACAS_SEALED_DIR='/absolute/path/to/private/sealed-set'
export ACAS_PYTHON='/absolute/path/to/project-venv/bin/python'
export LV_ALLOW_NETWORK=0

git fetch origin main Steve_ACASiaLAW
ACAS_MAIN_SHA=f7a7f49056fa4fc6239ffdad803eed53443d9045
ACAS_CANDIDATE_SHA=0055fa728202c2d4b500099fa2b6c29d8258c07e
ACAS_RUN_DIR=$(mktemp -d)
ACAS_STAGE_DIR=$("$ACAS_PYTHON" - <<'PY'
from pathlib import Path
import tempfile
print(Path(tempfile.mkdtemp(prefix="acas_sealed_stage_")) / "sealed")
PY
)
cleanup_stage() {
  "$ACAS_PYTHON" - "$ACAS_STAGE_DIR" <<'PY'
from pathlib import Path
import shutil
import sys
import tempfile

stage = Path(sys.argv[1]).resolve()
if (stage.name == "sealed" and stage.parent.name.startswith("acas_sealed_stage_")
        and stage.parent.parent == Path(tempfile.gettempdir()).resolve()):
    shutil.rmtree(stage.parent)
    assert not stage.parent.exists(), "임시 봉인 사본 삭제를 확인하지 못함"
else:
    raise ValueError("임시 봉인 사본 삭제 경로 확인 실패")
PY
}
trap cleanup_stage EXIT
git worktree add --detach "$ACAS_RUN_DIR/main" "$ACAS_MAIN_SHA"
git worktree add --detach "$ACAS_RUN_DIR/candidate" "$ACAS_CANDIDATE_SHA"
test "$(git -C "$ACAS_RUN_DIR/main" rev-parse HEAD)" = "$ACAS_MAIN_SHA"
test "$(git -C "$ACAS_RUN_DIR/candidate" rev-parse HEAD)" = "$ACAS_CANDIDATE_SHA"
"$ACAS_PYTHON" --version
tesseract --version
tesseract --list-langs
tesseract --list-langs | rg -x kor
tesseract --list-langs | rg -x eng

"$ACAS_PYTHON" - "$ACAS_SEALED_DIR" "$ACAS_STAGE_DIR" <<'PY'
from hashlib import sha256
from pathlib import Path
import shutil
import sys
import tempfile

source, stage = (Path(p).resolve() for p in sys.argv[1:])
temp_root = Path(tempfile.gettempdir()).resolve()
if temp_root not in stage.parents or source == stage or not source.is_dir():
    raise ValueError("봉인 원본·임시 사본 경로 조건 불충족")

def digest(root):
    h = sha256()
    for p in sorted(root.rglob("*")):
        if ".sealed_out" in p.relative_to(root).parts:
            continue
        if p.is_symlink():
            raise ValueError("봉인 폴더에 심볼릭 링크가 있음")
        if not p.is_file():
            continue
        h.update(p.relative_to(root).as_posix().encode("utf-8"))
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.digest()

before = digest(source)
shutil.copytree(source, stage, ignore=shutil.ignore_patterns(".sealed_out"))
if before != digest(stage) or before != digest(source):
    raise ValueError("봉인 원본·임시 사본 무결성 불일치")
print("봉인 임시 사본 무결성 확인")
PY

(cd "$ACAS_RUN_DIR/main" && "$ACAS_PYTHON" scripts/scorecard.py --sets dev --sealed-dir "$ACAS_STAGE_DIR" --out "$ACAS_RUN_DIR/main_scorecard.json")
(cd "$ACAS_RUN_DIR/candidate" && "$ACAS_PYTHON" scripts/scorecard.py --sets dev --sealed-dir "$ACAS_STAGE_DIR" --out "$ACAS_RUN_DIR/candidate_scorecard.json")

"$ACAS_PYTHON" - "$ACAS_RUN_DIR/main_scorecard.json" "$ACAS_RUN_DIR/candidate_scorecard.json" <<'PY'
import json
import sys

rows = []
for label, path in zip(("main", "candidate"), sys.argv[1:]):
    card = json.load(open(path, encoding="utf-8"))
    sealed = card["sets"]["sealed"]
    proxy = sealed["regression_v2"]
    rows.append({
        "side": label,
        "sha": card["git"]["sha"],
        "dataset_sha256": proxy["dataset_sha256"],
        "documents": sealed["documents"],
        "overall": sealed["overall"],
        "weighted_recall": sealed["weighted_recall"],
        "false_positives": sealed["false_positives"],
        "a_grade_false_positives": sealed["a_grade_fp"],
        "regression_v2_items": proxy["items"],
        "regression_v2_hits": proxy["hits"],
        "regression_v2_recall": proxy["recall"],
        "engine_error_count": sum(sealed["engine_errors"].values()),
    })
assert rows[0]["dataset_sha256"] == rows[1]["dataset_sha256"], "봉인 세트가 달라 비교 불가"
print(json.dumps(rows, ensure_ascii=False, indent=2))
PY
```

## 평가 세션에 전달할 결과

위 마지막 명령의 **집계 JSON만** 전달한다. 함께 Python·Tesseract 버전, `kor`·`eng` 언어 확인 여부, 두 실행의 종료 코드, 실행 중 오류 여부를 알려 준다. 봉인 원문·문서별 결과·유형별 문구·`.sealed_out/` 내용은 전달하지 않는다. 어느 실행이든 실패하거나 SHA·데이터셋 해시가 다르면 점수 비교를 멈추고 오류의 종류만 알린다.

고정 비공개 벤치마크는 봉인 세트와 별개다. 보관 자료가 있다면 평가 세션에 집계 결과만 별도로 알려 주며, 없으면 `NOT_MEASURED`로 둔다. 이 결과를 평가자가 릴리스 판정서에 기록하기 전까지 릴리스 승인·버전 확정으로 보지 않는다.
