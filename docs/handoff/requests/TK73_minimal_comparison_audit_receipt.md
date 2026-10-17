# TK-73 public minimal-comparison audit

Public Steve baseline `aefd55ed4831d6aeda6d5b5ad7a01e8a59a135f7`; original `_numbering` is unchanged from the generator submission `401d0988e0440a8db49b6e1c9f505b26d4fd587c`. Design-first `df0c336`, narrower-design memo `76cfec8`. Final submission SHA, final-head output and CI run IDs are recorded in the PR. Product files, original expectations, grades, statuses and protected assets have zero diff.

## Exact unguarded proposal

The diagnostic changes just the distinct-name expression in a separately compiled copy of the current `_numbering`, using the first ASCII comma/colon prefix. It never replaces the module's production function. It reparses each unchanged public generated document with the current parser, preserves rows and compares the complete remaining numbering findings (excluding random IDs/timestamps). Baseline A counts match every original public record. Original semantic labels remain fixed.

| Population | Documents | Baseline A | Minimal A | True lost | True retained | False removed |
|---|---:|---:|---:|---:|---:|---:|
| original111 | 111 | 93 | 45 | **21** | 45 | 27 |
| dated117 | 117 | 108 | 18 | 12 | 18 | 78 |
| new54 | 54 | 54 | 9 | 9 | 9 | 36 |
| native21 | 21 | 21 | 0 | 3 | 0 | 18 |
| new tree controls, measured | 27 | 27 | 0 | 3 | 0 | 24 |
| All measured (includes111) | **330** | **303** | **72** | **48** | **72** | **183** |

Three external-stream full comparisons remain unmeasured, not passes. These are repeated synthetic families across related populations, not330 independently sampled legal documents. Losses: original111 GLOBAL inventory/prose18 + native title3; dated117 GLOBAL date9 + native date title3; other three populations GLOBAL date15. All original public labels are retained, including conservative GLOBAL truth labels. The evaluator's minimal patch result on target aggregates and this public loss audit measure different things; neither overwrites the other.

## Narrower unapproved design

The accompanying one-page memo restricts suppression to two line-derived rows with comma/colon shape agreement and equal prefixes, preserving native cells, third occurrences, unequal dates and ambiguous numeric/ID suffixes. Its separate diagnostic currently retains all120 true A findings/loss0 and removes183 public false candidates; original111 retains66/loss0/removes27. This is **not approval or installation**. Unsupported identity/title grammar remains a design risk; no complete semantic title proof is claimed. The guard preserves original complete names/evidence whenever a finding remains.

New synthetic controls:27 passed (initial local run0.29seconds). These include three distinct names, differing dates/document IDs, third occurrences, same-delimiter ambiguity, native table titles and repeated source-location mentions through the real TXT parser or native-row consumer. The existing engine remains unchanged before/after each design-only comparison. Existing111/330 generators and expectations are unchanged.

## Reproduction and measured path

Use a separate **public-only** checkout at `401d0988e0440a8db49b6e1c9f505b26d4fd587c` for the original probe. Its script imports only its adjacent public design scripts and public product/audit generators. Keep private fixtures/corpus outside this process. With `/workspace/tk73-readiness` at that SHA:

```sh
cd /workspace/tk73-readiness
PYTHONPATH=. /workspace/tk73-venv/bin/python docs/handoff/requests/TK-73_post013_pdf_tree_support_spike.py /tmp/tk73-public-regenerated > /tmp/tk73-public-regenerated.json
cd /workspace/tk73-minimal
/workspace/tk73-venv/bin/python docs/handoff/requests/TK73_minimal_comparison_audit.py /tmp/tk73-public-regenerated.json /tmp/tk73-public-regenerated --output /tmp/tk73-minimal-audit.json
/workspace/tk73-venv/bin/python docs/handoff/requests/TK73_minimal_comparison_audit.py /tmp/tk73-public-regenerated.json /tmp/tk73-public-regenerated --guarded --output /tmp/tk73-guarded-audit.json
/workspace/tk73-venv/bin/python -m pytest tests/test_tk73_minimal_comparison_design.py --tb=short
/workspace/tk73-venv/bin/python docs/handoff/requests/TK73_minimal_guard_timing.py
```

The actual initial run reused unchanged generated files `/tmp/tk73-final401-20261016` and their public receipt `.json`, with full current-parser re-comparison. Literal `Object999999` diagnostics are expected from existing generated dangling-reference controls; exit0 is preserved. No private target set or original four-set scoring is run by this implementer.

Timing: four proposed guard paths (non-Latin letters, long numeral, ASCII letters, spaced source-location token), variable suffix4000/16000characters,64calls/sample, three fresh processes/size, unchanged GC. Initial4x minima .038707/.007324/.005423/.084515seconds, ratios3.414573/3.813380/2.604558/4.466588. All pass measured<1second/<8ratio. This is helper timing, not parser or product timing. Final-head JSON is attached separately in the PR.

Common checklist1/4/5: no new product entry point, scoring behavior or train assignment; not applicable to this design-only PR.27 synthetic controls and the current-parser330 audit are supplied for design review. Actual product entry-point tests, independent aggregate acceptance and full verification are required after design approval. User has authorized progress through main, but that does not substitute for the required independent design approval or release evidence.
