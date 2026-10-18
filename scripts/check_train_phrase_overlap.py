"""PR이 제품 코드에 새로 넣은 한글 문구가 개발 말뭉치(train) 원문을 그대로 옮긴 것인지 센다(평가 측 도구).

`check_hardcoding_diff.py`는 저장소 안 시험 입력만 본다. train 말뭉치는 저장소 밖에 있어 그 점검에 걸리지 않는다.
이 도구는 평가 측이 train 원문 텍스트(파서로 뽑은 읽기 텍스트, 문서당 .txt 1개)를 가진 곳에서 돌린다.

방법
- 기준 커밋 대비 제품 경로(`packages`·`apps`·`workers`)에 추가된 줄의 문자열에서 한글 낱말을 뽑는다.
  정규식 문법(`\\s*`·괄호·`|`·`?`·문자 묶음 등)은 낱말 경계로 본다. 선택(`|`)으로 갈린 낱말이 한 줄로 이어지므로,
  이어진 낱말 2~5개의 모든 연속 창을 공백 없이 붙여 후보로 만든다.
- 각 후보가 train 원문(공백 제거)에 몇 문서·몇 번 나오는지 센다.
- 낱말 2개 이상·공백 제거 LONG_CHARS자 이상인 후보가 train에 나오면 '원문 문구 의심'으로 표시한다.
  더 짧은 후보는 참고로만 센다. 더 긴 의심 후보에 포함된 짧은 후보는 출력하지 않는다.

평가 세트 모드(`--eval-sets`, 2026-10-18 사용자 승인): 저장소 안의 은퇴·고정 세트 정답지(`ground_truth.json`) 문자열과 대조한다.
은퇴·고정 세트는 일반화를 재는 평가 세트라 그 문장을 규칙에 옮기면 안 된다(#125 a536a02 사례). 저장소 안에 있으므로 CI에서 자동으로 돈다.
정답지 문장은 짧은 자리표시('별도 삽입 예정')도 결함 근거가 되므로 기준을 낮춘다: 낱말 2개 이상·공백 제거 EVAL_CHARS자 이상이고,
일반 법률 표현과 구별하려고 정답지 항목 EVAL_MAX_ITEMS개 이하에만 나오는 조각을 '평가 세트 문구 의심'으로 표시한다.
평가 측이 일반 표현으로 확인한 조각은 `docs/scorecards/approved_eval_phrases.json`(평가 측 커밋만)에 올리면 의심에서 뺀다.
한계: 정규식 선택(`|`)으로 갈린 문구('(?:삽입|첨부)\s*예정')는 원문 순서대로 이어지지 않아 놓칠 수 있다. 평가 측 검토를 대신하지 않는다.

판정 기준(평가 측, 2026-10-17): 원문 문구 의심이 1개라도 있으면 그 규칙이 같은 유형의 은퇴·고정 세트 항목에서
득점을 올렸는지(일반화) 함께 본다. train에서만 오르고 같은 유형 다른 세트에서 오르지 않으면 불수용한다.

사용:
  1) train 텍스트 만들기(1회, OCR 때문에 10분 넘게 걸릴 수 있다):
     python scripts/check_train_phrase_overlap.py --dump-from <train 폴더(set01..set04)> --corpus-text <출력 폴더>
  2) 대조: python scripts/check_train_phrase_overlap.py --base <기준 커밋> --corpus-text <train 텍스트 폴더> [--head HEAD]
  3) 평가 세트 대조(CI): python scripts/check_train_phrase_overlap.py --base <기준 커밋> --eval-sets
비공개 세트·check/ 텍스트에는 쓰지 않는다(집계만 다루는 규칙). 문구는 PR diff에서 온 것만 출력한다.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PRODUCT_PATHS = ("packages", "apps", "workers")
MIN_CHARS = 4
LONG_CHARS = 8
EVAL_CHARS = 6
EVAL_MAX_ITEMS = 3
EVAL_GT = ("tests/fixtures/retired_sealed/*/ground_truth.json", "tests/fixtures/legal_verifier_testset/ground_truth.json",
           "tests/fixtures/holdout/ground_truth.json")
# 정규식 문법 조각: 이스케이프 문자류, 반복, 묶음, 선택, 문자 묶음
REGEX_SYNTAX = re.compile(r"\\[sSdDwWbB]|\\.|\(\?[:=!<P][^)]*?>?|[()|?*+{}\[\]^$]|\d+")
HANGUL_RUN = re.compile(r"[가-힣][가-힣 ]*[가-힣]")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def added_lines(base: str, head: str) -> List[Tuple[str, str]]:
    diff = _git("diff", "-U0", f"{base}...{head}", "--", *PRODUCT_PATHS)
    out, path = [], ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
        elif line.startswith("+") and not line.startswith("+++") and path.endswith(".py"):
            out.append((path, line[1:]))
    return out


def phrases(line: str) -> List[str]:
    code = line.split("#", 1)[0]  # 주석 제외
    found = []
    for literal in re.findall(r"[rRfFbB]*(['\"])(.*?)(?<!\\)\1", code):
        text = REGEX_SYNTAX.sub(" ", literal[1])
        for run in HANGUL_RUN.findall(text):
            words = run.split()
            for n in range(1, 6):
                for i in range(len(words) - n + 1):
                    window = " ".join(words[i:i + n])
                    if len(window.replace(" ", "")) >= MIN_CHARS:
                        found.append(window)
    return found


def load_corpus(folder: Path) -> Dict[str, str]:
    return {p.name: re.sub(r"\s+", "", p.read_text(encoding="utf-8", errors="ignore")) for p in sorted(folder.glob("*.txt"))}


def load_eval_corpus(root: Path) -> Dict[str, str]:
    """정답지의 문자열 값 하나하나를 항목 하나로 본다(공백 제거)."""
    import json

    out: Dict[str, str] = {}

    def walk(node, name):
        if isinstance(node, str):
            if re.search(r"[가-힣]", node):
                out[f"{name}#{len(out)}"] = re.sub(r"\s+", "", node)
        elif isinstance(node, dict):
            for key, value in node.items():
                if not str(key).startswith("_"):
                    walk(value, name)
        elif isinstance(node, list):
            for value in node:
                walk(value, name)

    for pattern in EVAL_GT:
        for path in sorted(root.glob(pattern)):
            walk(json.loads(path.read_text(encoding="utf-8")), path.parent.name)
    return out


def dump_corpus(source: Path, out: Path) -> int:
    """train PDF를 제품 파서로 읽어 문서당 읽기 텍스트 .txt를 만든다."""
    import hashlib

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from packages.document_engine.reading_text import build_reading_text
    from packages.document_engine.registry import parse_document

    out.mkdir(parents=True, exist_ok=True)
    count = 0
    for pdf in sorted(source.glob("*/*.pdf")):
        data = pdf.read_bytes()
        doc = parse_document(str(pdf), document_id=pdf.stem, filename=pdf.name, mime_type="application/pdf",
                             sha256=hashlib.sha256(data).hexdigest())
        (out / f"{pdf.parent.name}_{pdf.stem}.txt").write_text(build_reading_text(doc).text, encoding="utf-8")
        count += 1
    print(f"train 텍스트 {count}개 → {out}")
    return 0 if count else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--corpus-text", type=Path)
    ap.add_argument("--eval-sets", action="store_true", help="저장소 안 은퇴·고정 세트 정답지와 대조한다(CI)")
    ap.add_argument("--dump-from", type=Path, help="train 폴더에서 텍스트를 만든다(대조는 하지 않음)")
    args = ap.parse_args(argv)
    if args.dump_from:
        if not args.corpus_text:
            ap.error("--corpus-text가 필요하다")
        return dump_corpus(args.dump_from, args.corpus_text)
    if not args.base:
        ap.error("--base가 필요하다")
    if args.eval_sets:
        return eval_main(args)
    if not args.corpus_text:
        ap.error("--corpus-text 또는 --eval-sets가 필요하다")
    corpus = load_corpus(args.corpus_text)
    if not corpus:
        print(f"train 텍스트가 없다: {args.corpus_text}")
        return 2
    rows, seen = [], set()
    for path, line in added_lines(args.base, args.head):
        for ph in phrases(line):
            key = ph.replace(" ", "")
            if key in seen:
                continue
            seen.add(key)
            docs = [n for n, t in corpus.items() if key in t]
            if docs:
                hits = sum(t.count(key) for t in corpus.values())
                rows.append((len(key) >= LONG_CHARS and " " in ph, ph, len(docs), hits, path))
    longest = [r for r in rows if not any(o is not r and r[1].replace(" ", "") in o[1].replace(" ", "") for o in rows)]
    rows = longest
    suspect = [r for r in rows if r[0]]
    print(f"train 원문 문구 대조 — 기준 {args.base[:7]} → {args.head}, train 문서 {len(corpus)}개, 새 한글 조각 {len(seen)}개")
    for flag, ph, ndoc, hits, path in sorted(rows, key=lambda r: (not r[0], -r[2])):
        mark = "[원문 문구 의심]" if flag else "[참고]"
        print(f"  {mark} '{ph}' — train {ndoc}문서·{hits}회 ({path})")
    print(f"원문 문구 의심 {len(suspect)}개" if suspect else "원문 문구 의심 없음")
    return 1 if suspect else 0


def load_approved(root: Path) -> set:
    import json

    path = root / "docs" / "scorecards" / "approved_eval_phrases.json"
    if not path.exists():
        return set()
    return {re.sub(r"\s+", "", e["phrase"]) for e in json.loads(path.read_text(encoding="utf-8")).get("phrases", [])}


def eval_main(args) -> int:
    root = Path(__file__).resolve().parents[1]
    corpus = load_eval_corpus(root)
    approved = load_approved(root)
    if not corpus:
        print("평가 세트 정답지가 없다")
        return 2
    rows, seen = [], set()
    for path, line in added_lines(args.base, args.head):
        for ph in phrases(line):
            key = ph.replace(" ", "")
            if key in seen or " " not in ph or len(key) < EVAL_CHARS or any(key in a for a in approved):
                continue
            seen.add(key)
            items = [n for n, t in corpus.items() if key in t]
            if items and len(items) <= EVAL_MAX_ITEMS:
                rows.append((ph, sorted({n.split("#")[0] for n in items}), len(items), path))
    rows = [r for r in rows if not any(o is not r and r[0].replace(" ", "") in o[0].replace(" ", "") for o in rows)]
    print(f"평가 세트 정답 문구 대조 — 기준 {args.base[:7]} → {args.head}, 정답지 문자열 {len(corpus)}개, 새 한글 조각 {len(seen)}개")
    for ph, sets, n, path in rows:
        print(f"  [평가 세트 문구 의심] '{ph}' — {', '.join(sets)} 정답지 {n}항목 ({path})")
    print(f"평가 세트 문구 의심 {len(rows)}개" if rows else "평가 세트 문구 의심 없음")
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
