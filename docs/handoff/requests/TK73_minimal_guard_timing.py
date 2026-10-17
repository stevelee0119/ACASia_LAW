"""Cold-process synthetic timing of the unapproved comparison guard only."""
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def sample(mode, length):
    spec = importlib.util.spec_from_file_location("public_guard", HERE / "TK73_minimal_comparison_audit.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    suffix = {"letters": "가" * length, "digits": "8" * length,
              "ascii": "x" * length, "spaced_location": "7" + " " * length + "쪽",
              "later_digits": "설명 " + "8" * length,
              "later_code": "설명 " + "REF-AA" * (length // 6),
              "wrapped": "[" + "8" * length + "]",
              "unclosed": "(" + "8" * length}[mode]
    rows = [{"name": "공개기록, " + suffix, "from_lines": True, "date": ""},
            {"name": "공개기록: 설명", "from_lines": True, "date": ""}]
    start = time.perf_counter()
    for _ in range(32):
        for row in rows:
            audit.guarded_comparison_name(row, rows)
    elapsed = time.perf_counter() - start
    return {"seconds": elapsed, "variable_characters": length, "calls": 64,
            "input_characters": sum(len(row["name"]) for row in rows)}


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--sample":
        print(json.dumps(sample(sys.argv[2], int(sys.argv[3]))))
        return
    result = {}
    for mode in ("letters", "digits", "ascii", "spaced_location",
                 "later_digits", "later_code", "wrapped", "unclosed"):
        groups = {}
        for label, length in (("1x", 4000), ("4x", 16000)):
            samples = [json.loads(subprocess.check_output(
                [sys.executable, str(Path(__file__).resolve()), "--sample", mode, str(length)], text=True))
                for _ in range(3)]
            groups[label] = {"samples": samples, "minimum_seconds": min(item["seconds"] for item in samples)}
        denominator = max(.0001, groups["1x"]["minimum_seconds"])
        ratio = groups["4x"]["minimum_seconds"] / denominator
        result[mode] = {"rows": groups, "denominator_seconds": denominator, "ratio": ratio,
                        "pass": ratio < 8 and groups["4x"]["minimum_seconds"] < 1}
    print(json.dumps({"python": platform.python_version(), "platform": platform.system(),
                      "cold_process_each_sample": True, "gc_changed": False,
                      "product_installed": False, "paths": result}, sort_keys=True))
    if not all(item["pass"] for item in result.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
