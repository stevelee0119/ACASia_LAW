"""Evaluator-owned regression proxy. This is not an estimate of legal accuracy."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from scripts import eval_testset as legacy

PROTOCOL = "regression-proxy-v2.0"
POSITIVE = {"NOT_FOUND", "CONTRADICTED", "SUSPICIOUS", "INVALID_FORMAT", "INVALID", "MODIFIED"}
UNCERTAIN = {"CIT-NX-DB", "SRC-UNV"}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def dataset_identity(folder):
    folder = Path(folder).resolve()
    gold = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))
    files = ["ground_truth.json", "match_spec.json"] + [d["file"] for d in gold["documents"].values()]
    hashes = {}
    for name in files:
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file():
            raise ValueError("Evaluation input missing or outside dataset")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest(hashes)


def maximum_matching(edges):
    owners = {}
    def visit(item, seen):
        for finding in edges[item]:
            if finding in seen:
                continue
            seen.add(finding)
            if finding not in owners or visit(owners[finding], seen):
                owners[finding] = item
                return True
        return False
    for item in edges:
        visit(item, set())
    return set(owners.values())


def finding_text(finding):
    parts = [str(finding.get(k) or "") for k in ("title", "detail")]
    parts += [str(e.get(k) or "") for e in finding.get("evidence") or []
              for k in ("excerpt", "description")]
    return legacy._norm(" ".join(parts))


def category(kind):
    if kind in UNCERTAIN:
        return "source_uncertainty"
    if kind.startswith(("CIT", "LAW", "OVR")) or kind == "EVI-FAKECIT":
        return "legal"
    if kind.startswith("INJ"):
        return "security_detection"
    return "authorship_signals" if kind == "AIGEN" else "document_consistency"


def aggregate(rows):
    count, hits = len(rows), sum(r[1] for r in rows)
    return {"items": count, "hits": hits, "recall": hits / count if count else None}


def score(result, folder, legacy_report=None):
    folder = Path(folder)
    gold = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))["documents"]
    tokens = json.loads((folder / "match_spec.json").read_text(encoding="utf-8"))["tokens"]
    if result.get("errors"):
        raise ValueError("Pipeline errors: regression measurement is incomplete")
    documents, ids = {}, {}
    for doc in result.get("documents", []):
        key = legacy.doc_key(doc.get("filename") or doc.get("document_id") or "")
        if not key or key in documents or not doc.get("document_id") or doc["document_id"] in ids:
            raise ValueError("Missing or duplicate document identity")
        # Quarantining adversarial fixtures is an intended product decision, not a runner failure.
        documents[key] = list(doc.get("findings") or [])
        ids[doc["document_id"]] = key
    if set(documents) != set(gold) or set(tokens) != set(gold):
        raise ValueError("Document/answer/token inventory mismatch")
    for finding in result.get("project_findings") or []:
        owner = ids.get(finding.get("document_id"))
        if owner:
            documents[owner].append(finding)
    rows, by_type, by_group = [], defaultdict(list), defaultdict(list)
    advisory = 0
    for doc, meta in gold.items():
        items, groups = meta["items"], tokens[doc]
        if len(items) != len(groups):
            raise ValueError("Item/token count mismatch")
        findings, seen = [], set()
        for finding in documents[doc]:
            fid = finding.get("finding_id")
            if fid and fid in seen:
                continue
            if fid:
                seen.add(fid)
            findings.append(finding)
        advisory += sum(bool(f.get("advisory_only")) for f in findings)
        texts = [finding_text(f) for f in findings]
        edges = {}
        for i, item in enumerate(items):
            kind = item[0]
            if kind == "FP-TRAP":
                continue
            if not groups[i] or any(not group or any(not str(t).strip() for t in group) for group in groups[i]):
                raise ValueError("Empty match tokens cannot earn credit")
            candidates = [j for j, f in enumerate(findings) if legacy.type_allowed(kind, f)
                          and legacy.matches(texts[j], groups[i]) == len(groups[i])]
            veto = kind in UNCERTAIN and any(str(findings[j].get("status")) == "VERIFIED" for j in candidates)
            allowed = {"UNVERIFIED"} if kind in UNCERTAIN else POSITIVE
            edges[i] = [] if veto else [j for j in candidates if not findings[j].get("advisory_only")
                                       and str(findings[j].get("status")) in allowed]
        hits = maximum_matching(edges)
        for i in edges:
            row = (items[i][0], int(i in hits))
            rows.append(row)
            by_type[row[0]].append(row)
            by_group[category(row[0])].append(row)
    old = legacy_report if legacy_report is not None else legacy.score(result, folder, db_available=False)
    types = {k: aggregate(v) for k, v in sorted(by_type.items())}
    return {"protocol": PROTOCOL, "scope": "REUSED_REGRESSION_PROXY", "status": "MEASURED",
            "dataset_sha256": dataset_identity(folder), "documents": len(gold),
            **aggregate(rows), "macro_recall": sum(v["recall"] for v in types.values()) / len(types) if types else None,
            "by_type": types, "by_group": {k: aggregate(v) for k, v in sorted(by_group.items())},
            "known_false_positive_findings": old["false_positives_total"],
            "unadjudicated_alerts": len(old["unmatched_defect_findings"]), "advisory_findings": advisory,
            "precision": None, "legal_accuracy": None, "injection_defense_success_rate": None,
            "limitations": ["lexical_matching_not_semantic_or_span_verified", "reused_not_blind",
                            "unadjudicated_alerts_not_false_positives", "no_official_db_or_llm"]}


def compare_sets(current, baseline):
    """Fail closed; only regression counts are gated, never clinical/legal quality."""
    failures = []
    for name, base in baseline.items():
        now = current.get(name)
        if not isinstance(now, dict) or now.get("status") != "MEASURED":
            failures.append(f"[{name}] v2 measurement missing/failed")
            continue
        for key in ("protocol", "dataset_sha256", "documents", "items"):
            if now.get(key) != base.get(key):
                failures.append(f"[{name}] v2 incomparable {key}")
        if set(now.get("by_type", {})) != set(base.get("by_type", {})):
            failures.append(f"[{name}] v2 type inventory changed")
        for kind, expected in base.get("by_type", {}).items():
            value = now.get("by_type", {}).get(kind, {})
            hits, count = value.get("hits"), value.get("items")
            if type(hits) is not int or type(count) is not int or count != expected["items"] or not 0 <= hits <= count:
                failures.append(f"[{name}] v2 invalid denominator/count: {kind}")
            elif hits < expected["hits"]:
                failures.append(f"[{name}] v2 regression {kind}: {expected['hits']} → {hits}")
        if type(now.get("hits")) is not int or now["hits"] != sum(v.get("hits", 0) for v in now.get("by_type", {}).values() if type(v.get("hits")) is int):
            failures.append(f"[{name}] v2 inconsistent hit total")
    if set(current) != set(baseline):
        failures.append("v2 set inventory mismatch")
    return failures
