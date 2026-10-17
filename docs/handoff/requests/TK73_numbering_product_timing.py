"""Cold-process timing of the actual installed numbered-comparison path."""
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]


def sample(mode, length):
    sys.path.insert(0, str(ROOT))
    from packages.claim_engine.evidence_consistency import _numbering
    from packages.common.schemas import Block, NormalizedDocument, Page
    suffix = {"letters": "가" * length, "digits": "8" * length,
              "ascii": "x" * length, "spaced_location": "7" + " " * length + "쪽",
              "later_digits": "설명 " + "8" * length,
              "later_code": "설명 " + "REF-AA" * (length // 6),
              "wrapped": "[" + "8" * length + "]",
              "unclosed": "(" + "8" * length}[mode]
    rows = [{"party": "갑", "number": 1, "name": "공개기록, " + suffix,
             "from_lines": True, "date": ""},
            {"party": "갑", "number": 1, "name": "공개기록: 설명",
             "from_lines": True, "date": ""}]
    doc = NormalizedDocument("public-timing", "timing.txt", "text/plain", "0" * 64,
                            pages=[Page(1, blocks=[Block("body", "Synthetic note.", 1)])])
    names = [row["name"] for row in rows]
    expected = int(mode in ("digits", "spaced_location", "wrapped", "unclosed"))
    start = time.perf_counter()
    for _ in range(32):
        findings = _numbering(doc, rows)
        assert len(findings) == expected
        assert all(str(f.evidence_grade) == "A" for f in findings)
    elapsed = time.perf_counter() - start
    assert [row["name"] for row in rows] == names
    return {"seconds": elapsed, "variable_characters": length, "numbering_calls": 32,
            "input_characters": sum(len(row["name"]) for row in rows)}


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--sample":
        print(json.dumps(sample(sys.argv[2], int(sys.argv[3]))))
        return
    paths = {}
    for mode in ("letters", "digits", "ascii", "spaced_location",
                 "later_digits", "later_code", "wrapped", "unclosed"):
        groups = {}
        for label, length in (("1x", 4000), ("4x", 16000)):
            samples = [json.loads(subprocess.check_output(
                [sys.executable, str(Path(__file__).resolve()), "--sample", mode, str(length)],
                cwd=ROOT, text=True)) for _ in range(3)]
            groups[label] = {"samples": samples, "minimum_seconds": min(s["seconds"] for s in samples)}
        denominator = max(.0001, groups["1x"]["minimum_seconds"])
        ratio = groups["4x"]["minimum_seconds"] / denominator
        paths[mode] = {"rows": groups, "denominator_seconds": denominator, "ratio": ratio,
                       "pass": ratio < 8 and groups["4x"]["minimum_seconds"] < 1}
    result = {"python": platform.python_version(), "platform": platform.system(),
              "cold_process_each_sample": True, "gc_changed": False, "product_installed": True,
              "path": "actual evidence_consistency._numbering", "paths": paths,
              "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))}
    print(json.dumps(result, sort_keys=True))
    if not all(row["pass"] for row in paths.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
