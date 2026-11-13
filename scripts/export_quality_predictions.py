"""Bind actual product citation outputs to stable, gold-free evaluation items.

Identity and literal-quote decisions are separate; neither implies valid legal reasoning.
Missing outputs become ABSTAIN. No answer labels are read by this exporter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.evaluation import PredictionRecord
from scripts.evaluation_v2 import digest

DIMENSIONS = {"identity", "quote"}
ERROR_TYPES = {
    "identity": {"CASE_CITATION_ERROR", "CASE_NOT_FOUND", "CASE_METADATA_MISMATCH", "LAW_CITATION_ERROR", "STATUTE_NONEXISTENT"},
    "quote": {"CASE_QUOTE_MISMATCH", "QUOTE_MISMATCH", "STATUTE_TEXT_MISMATCH"},
}


def anchor(doc, citation, dimension):
    if not doc.get("sha256") or not citation.get("raw_text"):
        raise ValueError("Document hash and citation text required for stable binding")
    return {"document_sha256": doc["sha256"], "page": citation.get("page"),
            "span": citation.get("span"), "text_sha256": hashlib.sha256(citation["raw_text"].encode()).hexdigest(),
            "dimension": dimension}


def inventory(payload):
    rows, seen = [], set()
    for doc in payload.get("documents", []):
        for citation in doc.get("citations", []):
            for dimension in sorted(DIMENSIONS):
                if dimension == "quote" and not citation.get("quoted_text"):
                    continue
                binding = anchor(doc, citation, dimension)
                item = "citation-" + digest(binding)
                if item in seen:
                    raise ValueError("Ambiguous citation anchor: independent span/occurrence annotation required")
                seen.add(item)
                rows.append({"item_id": item, **binding})
    if not rows:
        raise ValueError("Empty citation inventory")
    return {"schema": 1, "scope": "CITATION_IDENTITY_AND_LITERAL_QUOTE_ONLY", "items": rows}


def decision(verdict, dimension):
    levels = verdict.get("levels") or {}
    if dimension == "identity":
        status = levels.get("level1", levels.get("existence"))
        if status == "VERIFIED":
            status = levels.get("level2", levels.get("article")) or "UNVERIFIED"
        if levels.get("format") == "INVALID" or levels.get("number_format") == "IMPOSSIBLE":
            status = "CONTRADICTED"
    else:
        status = levels.get("level3", levels.get("content"))
    mapping = {None: "ABSTAIN", "VERIFIED": "VERIFIED", "CONTRADICTED": "CONTRADICTED",
               "MODIFIED": "CONTRADICTED", "UNVERIFIED": "UNVERIFIED", "NOT_FOUND": "NOT_FOUND",
               "PARTIALLY_VERIFIED": "PARTIALLY_VERIFIED", "TRUNCATED": "PARTIALLY_VERIFIED",
               "SKIPPED": "SKIPPED", "PENDING_LLM": "UNVERIFIED"}
    if status not in mapping:
        raise ValueError("Unknown product decision state; update the explicit mapping contract")
    errors = sorted({str(f.get("type")) for f in verdict.get("findings") or []
                     if str(f.get("type")) in ERROR_TYPES[dimension] and not f.get("advisory_only")
                     and str(f.get("status")) not in {"UNVERIFIED", "VERIFIED", "SKIPPED"}})
    normalized = mapping[status]
    if normalized == "VERIFIED" and errors:
        raise ValueError("VERIFIED conflicts with a defect finding in the same dimension")
    return normalized, errors


def export(payload, index, system_version):
    if not payload.get("run_id") or payload.get("errors"):
        raise ValueError("Missing run identity or failed pipeline execution")
    if index.get("schema") != 1 or not index.get("items"):
        raise ValueError("Nonempty versioned inventory required")
    candidates, document_hashes = {}, set()
    for doc in payload.get("documents", []):
        document_hashes.add(doc.get("sha256"))
        verdicts = {}
        for v in (doc.get("engine_data") or {}).get("legal_verdicts") or []:
            if v["citation_id"] in verdicts:
                raise ValueError("Duplicate verdict identity")
            verdicts[v["citation_id"]] = v
        for citation in doc.get("citations") or []:
            for dimension in DIMENSIONS:
                key = digest(anchor(doc, citation, dimension))
                if key in candidates:
                    raise ValueError("Ambiguous citation anchor")
                candidates[key] = verdicts.get(citation["citation_id"])
    records, seen = [], set()
    for item in index["items"]:
        if item["item_id"] in seen or item["dimension"] not in DIMENSIONS:
            raise ValueError("Duplicate item or unsupported evaluation dimension")
        seen.add(item["item_id"])
        if item["document_sha256"] not in document_hashes:
            raise ValueError("Inventory document absent from this product run")
        binding = {k: item.get(k) for k in ("document_sha256", "page", "span", "text_sha256", "dimension")}
        verdict = candidates.get(digest(binding))
        status, errors = decision(verdict, item["dimension"]) if verdict else ("ABSTAIN", [])
        records.append(PredictionRecord(item_id=item["item_id"], run_id=payload["run_id"],
                                        system_version=system_version, status=status, error_types=errors))
    return records


def unbound_count(payload, index):
    """Unlabeled new outputs must remain visible rather than disappearing from precision claims."""
    bound = {digest({k: i.get(k) for k in ("document_sha256", "page", "span", "text_sha256", "dimension")})
             for i in index["items"]}
    candidates = {digest(anchor(doc, c, dim)) for doc in payload.get("documents", [])
                  for c in doc.get("citations", []) for dim in DIMENSIONS
                  if dim != "quote" or c.get("quoted_text")}
    return len(candidates - bound)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--result", type=Path, required=True)
    p.add_argument("--inventory", type=Path)
    p.add_argument("--make-inventory", action="store_true")
    p.add_argument("--system-version", help="exact product commit/model configuration ID")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        payload = json.loads(a.result.read_text(encoding="utf-8"))
        if a.make_inventory:
            output = json.dumps(inventory(payload), ensure_ascii=False, indent=2)
        else:
            if not a.inventory or not a.system_version:
                p.error("--inventory and --system-version required for prediction export")
            index = json.loads(a.inventory.read_text(encoding="utf-8"))
            rows = export(payload, index, a.system_version)
            output = "\n".join(r.model_dump_json() for r in rows)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(output + "\n", encoding="utf-8")
        metadata = {"scope": "CITATION_IDENTITY_AND_LITERAL_QUOTE_ONLY", "legal_reasoning_accuracy": "NOT_MEASURED",
                    "product_result_sha256": hashlib.sha256(a.result.read_bytes()).hexdigest(),
                    "inventory_sha256": hashlib.sha256(a.inventory.read_bytes()).hexdigest() if a.inventory else None,
                    "output_sha256": hashlib.sha256(a.out.read_bytes()).hexdigest(), "run_id": payload.get("run_id")}
        if not a.make_inventory:
            metadata["unbound_candidate_items"] = unbound_count(payload, index)
            metadata["precision_scope"] = "bound inventory only; unbound candidates need independent labels"
        a.out.with_suffix(a.out.suffix + ".manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
