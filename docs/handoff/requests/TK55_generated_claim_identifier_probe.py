"""Cold-process, offline batch timing of actual Claim.create; public output only."""
from __future__ import annotations

import json
import platform
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[3]


def sample(rows):
    sys.path.insert(0, str(ROOT))
    from packages.common.enums import ClaimType
    from packages.common.schemas import Claim
    start = time.perf_counter()
    claims = [Claim.create(ClaimType.LEGAL_ARGUMENT, "합성 주장") for _ in range(rows)]
    elapsed = time.perf_counter() - start
    assert all(c.claim_id.startswith("CLM_") and len(c.claim_id) == 16
               and set(c.claim_id[4:]) <= set("abcdefghijklmnop") for c in claims)
    return elapsed


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--sample":
        print(json.dumps({"seconds": sample(int(sys.argv[2]))}))
        return
    rows = {}
    for label, count in (("1x", 1000), ("4x", 4000)):
        samples = []
        for _ in range(3):
            output = subprocess.check_output([sys.executable, str(Path(__file__).resolve()),
                                              "--sample", str(count)], text=True, cwd=ROOT)
            samples.append(json.loads(output)["seconds"])
        rows[label] = {"claims": count, "id_chars": 16, "prefix_chars": 4,
                       "samples_seconds": samples, "minimum_seconds": min(samples)}
    denominator = max(rows["1x"]["minimum_seconds"], 0.0001)
    ratio = rows["4x"]["minimum_seconds"] / denominator
    passed = ratio < 8 and rows["4x"]["minimum_seconds"] < 1
    print(json.dumps({"python": platform.python_version(), "platform": platform.system(),
                      "path": "Claim.create", "cold_process_each_sample": True,
                      "gc_changed": False, "rows": rows, "denominator_seconds": denominator,
                      "ratio": ratio, "pass": passed}, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
