"""Offline cold-process image-only PDF timing; no benchmark fixture inputs."""
import ast
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
PREVIOUS_HEAD = "ad848b16d8f6ffabeee760d445fe96c98bde0fa7"


def preflight_sample(mode, count):
    sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
    from pdfminer.pdftypes import PDFObjRef, PDFStream
    from pdfminer.psparser import LIT
    from packages.document_engine.actualtext_boundaries import _named_available
    from packages.document_engine.named_actualtext_capture import NamedActualTextCapture
    from test_tk44_image_xobject_preflight import page_with
    streams = {i: PDFStream({"Subtype": LIT("Form" if mode == "form_last" and
                       i == count - 1 else "Image")}, b"unopened") for i in range(count)}
    class ReferenceDocument:
        def getobj(self, objid):
            return streams[objid]
    document = ReferenceDocument()
    page = page_with({str(i): PDFObjRef(document, i, 0) if mode == "indirect_images"
                      else stream for i, stream in streams.items()})
    start = time.perf_counter()
    for _ in range(64):
        capture = NamedActualTextCapture()
        assert _named_available(page, capture) is (mode == "form_last")
        assert not capture.exceeded and capture.decode_calls == 0
    return {"seconds": time.perf_counter() - start, "xobject_entries": count, "calls": 64}


def sample(mode, count):
    sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
    from pytest import MonkeyPatch
    from packages.document_engine import actualtext_boundaries as provider
    from packages.document_engine.reading_text import build_reading_text
    from test_tk44_actualtext_provider import _parse
    from test_tk44_image_xobject_preflight import image_pdf
    from tk44_named_public_baseline import _parse as baseline_parse
    from pypdf import PdfReader
    with tempfile.TemporaryDirectory(prefix="tk44-images-") as folder:
        path = Path(folder) / "images.pdf"
        image_pdf(path, count)
        reader = PdfReader(str(path))
        assert all(not page["/Resources"].get("/Properties") and
                   all(obj.get_object()["/Subtype"] == "/Image"
                       for obj in page["/Resources"]["/XObject"].values())
                   for page in reader.pages)
        with MonkeyPatch.context() as patch:
            parse = baseline_parse if mode == "baseline_b1e" else _parse
            if mode == "previous_ad848b1":
                # Exact public pre-correction predicate, other parser code fixed.
                source = subprocess.check_output(["git", "show", PREVIOUS_HEAD +
                    ":packages/document_engine/actualtext_boundaries.py"], cwd=ROOT, text=True)
                tree = ast.parse(source)
                node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                            and n.name == "_named_available")
                namespace = dict(vars(provider))
                exec(compile(ast.Module(body=[node], type_ignores=[]), "previous_predicate", "exec"), namespace)
                patch.setattr(provider, "_named_available", namespace["_named_available"])
            start = time.perf_counter()
            doc = parse(path)
            seconds = time.perf_counter() - start
        assert len(doc.pages) == count
        assert all(any(f"line 29 on page {page}." in block.text for block in doc.blocks)
                   for page in range(count))
        primary = build_reading_text(doc).text
        assert primary.strip(), "synthetic body was removed as repeated headers"
        raw = json.dumps(doc.raw_layers, ensure_ascii=False, sort_keys=True)
        return {"seconds": seconds, "pages": count, "text_lines_per_page": 30,
                "images_per_page": 1, "source_bytes": path.stat().st_size,
                "reading_sha256": hashlib.sha256(primary.encode()).hexdigest(),
                "raw_sha256": hashlib.sha256(raw.encode()).hexdigest()}


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--sample":
        print(json.dumps(sample(sys.argv[2], int(sys.argv[3]))))
        return
    if len(sys.argv) == 4 and sys.argv[1] == "--preflight-sample":
        print(json.dumps(preflight_sample(sys.argv[2], int(sys.argv[3]))))
        return
    rows = {}
    for mode in ("baseline_b1e", "previous_ad848b1", "candidate"):
        rows[mode] = {}
        for pages in (5, 20):
            samples = [json.loads(subprocess.check_output(
                [sys.executable, str(Path(__file__).resolve()), "--sample", mode, str(pages)],
                cwd=ROOT, text=True)) for _ in range(3)]
            rows[mode][str(pages)] = {"samples": samples,
                "minimum_seconds": min(s["seconds"] for s in samples)}
    for pages in ("5", "20"):
        for key in ("reading_sha256", "raw_sha256"):
            assert len({s[key] for mode in rows for s in rows[mode][pages]["samples"]}) == 1
    ratios = {pages: rows["candidate"][pages]["minimum_seconds"] /
              rows["baseline_b1e"][pages]["minimum_seconds"] for pages in ("5", "20")}
    preflight = {}
    for mode in ("direct_images", "indirect_images", "form_last"):
        sizes = {}
        for label, count in (("1x", 8), ("4x", 32)):
            samples = [json.loads(subprocess.check_output(
                [sys.executable, str(Path(__file__).resolve()), "--preflight-sample", mode, str(count)],
                cwd=ROOT, text=True)) for _ in range(3)]
            sizes[label] = {"samples": samples, "minimum_seconds": min(s["seconds"] for s in samples)}
        denominator = max(sizes["1x"]["minimum_seconds"], .0001)
        ratio = sizes["4x"]["minimum_seconds"] / denominator
        passed = ratio < 8 and sizes["4x"]["minimum_seconds"] < 1
        assert passed, (mode, sizes, ratio)
        preflight[mode] = {"rows": sizes, "denominator_seconds": denominator, "ratio": ratio, "pass": passed}
    print(json.dumps({"python": platform.python_version(), "platform": platform.system(),
        "path": "parse_document image-only XObject pages", "rows": rows,
        "preflight": preflight,
        "candidate_over_baseline": ratios, "previous_predicate_sha": PREVIOUS_HEAD,
        "baseline_provider_sha": "b1e506f2eab2b830cb8fb7fd074d22dcdc3be589",
        "cold_process_each_sample": True, "gc_changed": False,
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))}, sort_keys=True))


if __name__ == "__main__":
    main()
