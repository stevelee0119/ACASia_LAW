"""Offline cold-process timing; selected Form design only, not product behavior."""
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]


def sample(count):
    sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
    from pytest import MonkeyPatch
    from test_tk44_actualtext_provider import _parse
    from test_tk44_named_actualtext_capture_budget_spike import repeated
    from tk44_form_inspection_candidate import parse_candidate
    from packages.document_engine.reading_text import build_reading_text
    from packages.adversarial_engine.scanner import scan_document
    from pypdf import PdfReader
    with tempfile.TemporaryDirectory(prefix="tk44-public-") as folder:
        path = Path(folder) / "form.pdf"
        repeated(path, count, 2000, True, form_only=True)
        page = PdfReader(str(path)).pages[0]
        form = next(iter(page["/Resources"]["/XObject"].values())).get_object()
        content_bytes = len(form.get_data())
        before = _parse(path)
        with MonkeyPatch.context() as patch:
            start = time.perf_counter()
            after = parse_candidate(path, patch)
            elapsed = time.perf_counter() - start
        assert build_reading_text(before).text == build_reading_text(after).text
        assert before.raw_layers == after.raw_layers
        assert any("ACTUAL_TEXT" in f.tags for f in scan_document(after).findings)
        assert not any(p.attributes["actualtext_boundary_provider"].get("certified_edges", 0) for p in after.pages)
        return {"seconds": elapsed, "source_bytes": path.stat().st_size,
                "decoded_form_content_bytes": content_bytes,
                "selected_occurrences": count, "logical_string_chars": 2000}


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--sample":
        print(json.dumps(sample(int(sys.argv[2]))))
        return
    rows = {}
    for label, count in (("1x", 4), ("4x", 16)):
        samples = [json.loads(subprocess.check_output(
            [sys.executable, str(Path(__file__).resolve()), "--sample", str(count)],
            text=True, cwd=ROOT)) for _ in range(3)]
        rows[label] = {"samples": samples, "minimum_seconds": min(r["seconds"] for r in samples)}
    denominator = max(rows["1x"]["minimum_seconds"], .0001)
    ratio = rows["4x"]["minimum_seconds"] / denominator
    passed = ratio < 8 and rows["4x"]["minimum_seconds"] < 1
    print(json.dumps({"path": "parse_document + Form inspection candidate", "python": platform.python_version(),
                      "platform": platform.system(), "cold_process_each_sample": True, "gc_changed": False,
                      "rows": rows, "denominator_seconds": denominator, "ratio": ratio, "pass": passed}, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
