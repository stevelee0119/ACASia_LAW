"""Cold public nonmatching-source probe of the existing test-only admission."""
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
PREFIX = "가사 "
UNIT = "합성 입력의 근거 연결을 확인한다 "


def sample(repeats):
    sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
    from packages.common.schemas import NormalizedDocument, Page, Block
    from tk45_norm_binding_capability import proposal_admission
    text = PREFIX + UNIT * repeats
    doc = NormalizedDocument("public", "public.txt", "text/plain", "synthetic",
                             pages=[Page(1, blocks=[Block("body", text, 1)])])
    start = time.perf_counter()
    result = proposal_admission(doc)
    elapsed = time.perf_counter() - start
    assert result is None
    return {"seconds": elapsed, "characters": len(text), "prefix_chars": len(PREFIX), "repeats": repeats}


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--sample":
        print(json.dumps(sample(int(sys.argv[2]))))
        return
    rows = {}
    for label, repeats in (("1x", 500), ("4x", 2000)):
        samples = [json.loads(subprocess.check_output(
            [sys.executable, str(Path(__file__).resolve()), "--sample", str(repeats)],
            text=True, cwd=ROOT)) for _ in range(3)]
        rows[label] = {"samples": samples, "minimum_seconds": min(r["seconds"] for r in samples)}
    denominator = max(rows["1x"]["minimum_seconds"], .0001)
    ratio = rows["4x"]["minimum_seconds"] / denominator
    passed = ratio < 8 and rows["4x"]["minimum_seconds"] < 1
    print(json.dumps({"path": "existing test-only proposal_admission", "python": platform.python_version(),
                      "platform": platform.system(), "cold_process_each_sample": True, "gc_changed": False,
                      "rows": rows, "denominator_seconds": denominator, "ratio": ratio, "pass": passed}, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
