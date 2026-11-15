"""비공개 탐침·봉인 문서 대비 하드코딩 점검(평가 에이전트·사용자 전용, 보호 경로).

저장소 밖에 둔 탐침 원문(평가 측 비공개 탐침, 사용자 봉인 문서의 텍스트)과 제품 코드를 대조한다. 구현 측 CI의
`check_case_literals`(저장소 안 사건 시험)·`check_train_phrase_overlap --eval-sets`(은퇴·고정 정답 문구)는 저장소 밖
문서를 볼 수 없다. 이 도구는 그 빈칸을 메운다(2026-11-14 평가 체계 감사).

    python scripts/check_private_probe_overlap.py --probe-dir <저장소 밖 폴더(.txt)>

찾는 것(check_case_literals와 같은 규칙)
- 사건번호·유효숫자 3자리 이상 쉼표 금액이 제품 코드 상수에 그대로 있는 경우
- 탐침 본문의 한글 열 글자 이상 연속 문구가 제품 코드의 정규식·메시지 상수에 그대로 있는 경우
출력에는 제품 코드 파일과 건수만 싣는다. 탐침 문구·값은 출력하지 않는다(탐침이 공개되지 않게).
종료 코드: 0 겹침 없음, 1 겹침 있음, 2 사용 오류.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import check_case_literals as literals  # noqa: E402


def probe_texts(probe_dir: Path) -> List[str]:
    return [p.read_text(encoding="utf-8", errors="ignore") for p in sorted(probe_dir.rglob("*.txt"))]


def overlaps(texts: List[str], root: Path = ROOT) -> Dict[str, Dict[str, int]]:
    """{제품 코드 파일: {"values": 건수, "phrases": 건수}} — 탐침 값·문구 자체는 돌려주지 않는다."""
    values: Dict[str, List[str]] = {}
    for text in texts:
        for value in literals.CASE_NUMBER.findall(text):
            values.setdefault(value, [])
        for value in literals.AMOUNT.findall(text):
            if literals.distinctive_amount(value):
                values.setdefault(value, [])
    value_hits = literals.scan(values, root, allow={}) if values else {}
    bodies = {literals.alnum(text): "probe" for text in texts}
    phrase_hits = literals.scan_phrases(bodies, root, allow={}) if bodies else {}
    out: Dict[str, Dict[str, int]] = {}
    for path, hits in value_hits.items():
        out.setdefault(path, {"values": 0, "phrases": 0})["values"] = len(hits)
    for path, hits in phrase_hits.items():
        out.setdefault(path, {"values": 0, "phrases": 0})["phrases"] = len(hits)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--probe-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    probe_dir = args.probe_dir.resolve()
    if probe_dir == ROOT or ROOT in probe_dir.parents:
        print("탐침 폴더는 저장소 밖에 있어야 한다", file=sys.stderr)
        return 2
    texts = probe_texts(probe_dir)
    if not texts:
        print(f"탐침 원문(.txt)이 없다: {probe_dir}", file=sys.stderr)
        return 2
    hits = overlaps(texts)
    print(f"비공개 탐침 대비 하드코딩 점검 — 탐침 {len(texts)}건, 겹친 제품 코드 파일 {len(hits)}개")
    for path, counts in sorted(hits.items()):
        print(f"  {path}: 사건 값 {counts['values']}건, 문구 {counts['phrases']}건")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
