"""Audit the exact one-expression proposal on unchanged, generated public data.

Inputs are the JSON and generated directory from the public #92 tree-support
probe at401d098. Never point this tool at private/evaluator corpus directories.
No source file or module function is patched in production.
"""
import argparse
from collections import Counter, defaultdict
import copy
from dataclasses import asdict
import inspect
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from packages.claim_engine import evidence_consistency as engine
from packages.document_engine.registry import parse_document


def minimal_numbering(*, guarded=False):
    source = inspect.getsource(engine._numbering)
    original = 're.sub(r"\\s", "", r.get("name") or "")'
    replacement = 're.sub(r"\\s", "", re.split(r"[,:]", r.get("name") or "", maxsplit=1)[0])'
    assert source.count(original) == 1, "The public baseline changed; review the exact proposal again."
    if guarded:
        replacement = "_guarded_comparison_name(r, same)"
    namespace = dict(vars(engine), _guarded_comparison_name=guarded_comparison_name)
    exec(compile(source.replace(original, replacement), "<TK73-minimal-diagnostic>", "exec"), namespace)
    return namespace["_numbering"]


def guarded_comparison_name(row, same):
    """Unapproved narrow design: retain native/GLOBAL/ambiguous identities."""
    import re
    original = re.sub(r"\s", "", row.get("name") or "")
    if len(same) != 2 or not all(item.get("from_lines") for item in same):
        return original
    pairs = [re.split(r"([,:])", item.get("name") or "", maxsplit=1) for item in same]
    if any(len(pair) != 3 or not pair[0].strip() for pair in pairs):
        return original
    if {pair[1] for pair in pairs} != {",", ":"}:
        return original
    if len({re.sub(r"\s", "", pair[0]) for pair in pairs}) != 1:
        return original
    # Dates are already extracted by the original producer, not inferred from
    # EOF or from untyped words here. Unequal observed dates preserve A.
    if len({re.sub(r"\s", "", item.get("date") or "") for item in same}) != 1:
        return original
    # Remove only explicit source-location units when looking for identity
    # numbers. Other numerals and alphanumeric IDs keep the old comparison.
    for pair in pairs:
        suffix = pair[2]
        for token in re.finditer(r"[0-9]+|[A-Za-z_-]+", suffix):
            value = token.group()
            if value[0].isdigit():
                if not re.compile(r"\s*(?:쪽|행|페이지)").match(suffix, token.end()):
                    return original
            elif '-' in value or '_' in value:
                return original
    return re.sub(r"\s", "", pairs[0][0])


def source_path(root, group, record):
    mode, extension, number = record["mode"], record["format"], record["example"]
    if group == "new_controls":
        return root / "tree_controls" / f"{mode}_{number}" / "public_caption.pdf"
    if group == "native21":
        return root / "frozen" / "native_controls" / f"{mode}_{number}" / "public_caption.pdf"
    base = root / "frozen" / "frozen"
    if group == "new54":
        base /= "new_controls"
    else:
        base = base / "frozen" / group
    if mode == "native_title":
        folder, filename = f"native_pdf_title_{number}", "public_title_role.pdf"
    elif mode == "native_date_title":
        folder, filename = f"native_date_title_{number}", "public_title_role.pdf"
    elif mode in ("native_source_reordered", "native_source_table"):
        folder, filename = f"{extension}_source_boundary_{number}", f"public_caption.{extension}"
    elif mode in ("image_only_final_page", "native_symbol_at_end"):
        folder, filename = f"{extension}_native_unsupported_{number}", f"public_caption.{extension}"
    elif mode == "foreign_namespace_at_end":
        folder, filename = f"docx_foreign_namespace_{number}", "public_caption.docx"
    else:
        folder, filename = f"{extension}_{number}_{mode}", f"public_caption.{extension}"
    return base / folder / filename


def duplicate(findings):
    return [f for f in findings if f.confidence_features.get("rule_id") == "EVI.EVIDENCE_NUMBER_DUPLICATE"]


def contract(findings):
    result = []
    for finding in findings:
        snapshot = asdict(finding)
        snapshot.pop('finding_id')
        snapshot.pop('created_at')
        for evidence in snapshot['evidence']:
            evidence.pop('evidence_id')
        result.append(snapshot)
    return result


def run(receipt, generated_root, *, guarded=False):
    candidate = minimal_numbering(guarded=guarded)
    counts = defaultdict(Counter)
    families = defaultdict(Counter)
    records = []
    groups = {"new_controls": receipt["new_controls"], **receipt["frozen"]}
    for group, population in groups.items():
        for record in population:
            if not record.get("comparison_measured", True):
                counts[group]["unmeasured"] += 1
                continue
            path = source_path(generated_root, group, record)
            doc = parse_document(str(path), document_id="public_caption", filename=path.name,
                                 mime_type={".txt": "text/plain", ".pdf": "application/pdf",
                                            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}[path.suffix],
                                 sha256="0" * 64)
            rows = engine.exhibit_rows(doc)
            before_rows = copy.deepcopy(rows)
            before = engine._numbering(doc, rows)
            after = candidate(doc, rows)
            baseline, proposed = duplicate(before), duplicate(after)
            assert len(baseline) == record["original_A"]
            assert rows == before_rows
            assert contract([f for f in before if f not in baseline]) == contract([f for f in after if f not in proposed])
            assert all(str(f.evidence_grade) == "A" for f in baseline + proposed)
            assert len(proposed) <= len(baseline)
            lost = len(baseline) - len(proposed)
            truth = record["public_true_duplicate"]
            values = {"documents": 1, "baseline_A": len(baseline), "minimal_A": len(proposed),
                      "true_lost": lost if truth else 0, "true_retained": len(proposed) if truth else 0,
                      "false_removed": 0 if truth else lost, "false_retained": 0 if truth else len(proposed)}
            counts[group].update(values)
            families[f"{group}/{record['mode']}"].update(values)
            records.append({"group": group, "mode": record["mode"], "format": record["format"],
                            "example": record["example"], "public_true_duplicate": truth,
                            "rows_and_other_numbering_findings_unchanged": True, **values})
    overall = Counter()
    for value in counts.values():
        overall.update(value)
    return {"python": platform.python_version(), "platform": platform.system(),
            "product_installed": False, "guarded_design_only": guarded, "counts": dict(counts), "all330": overall,
            "lost_families": {k: v for k, v in families.items() if v["true_lost"]}, "records": records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public_receipt", type=Path)
    parser.add_argument("generated_public_root", type=Path)
    parser.add_argument("--guarded", action="store_true", help="Measure the unapproved narrower design, never product.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(json.loads(args.public_receipt.read_text()), args.generated_public_root, guarded=args.guarded)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, ensure_ascii=False, sort_keys=True))
