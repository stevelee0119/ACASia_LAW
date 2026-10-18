# TK55 generated claim-ID follow-up

Public start `f84ccbabde2584e96204b74f8b668299220ee912`; design-first `bf878705fc25ad2c10d06f5c94f4103cd138bc1b`. The final submitted SHA is recorded in PR #106 after committing this receipt. This is a producer alphabet change, not a detection/policy/threshold change. It addresses new generated claim IDs; existing contact-like identifiers keep the pre-budget block. TK55 unknown-role, opaque/unsupported and capture-budget residuals remain open. Evaluation is paused under the current remaining-ticket handoff; no acceptance/integration/release is claimed.

`Claim.create` now encodes each of the twelve UUID nibbles bijectively as `a`–`p`, preserving 48 random bits, one draw, `CLM_`, and sixteen total characters. Explicit/imported/persisted claims and `new_id` for all other entities are unchanged. No string is authenticated or exempted by its key, spelling, or generator; the privacy walker, typed capabilities and original source gates are unchanged.

Actual entry test: `tests/test_tk55_generated_claim_identifiers.py::test_generated_claim_reaches_real_review_router_without_pii_exemption` exercises Claim.create → review_document → LLMRouter.run → in-memory provider and durable SQLite budget ledger, both profiles. The first fabricated overlap seed failed before the product change (only document review reserved/sent: expected2/actual1). Afterward all43 new tests pass, including three original overlap seeds, three safe controls, real contact blocking in metadata/user/system, old unsafe-ID blocking, full per-position nibble distinction and identity preservation. No paid/network model executes.

Reproduction (Linux/Python3.12.14, isolated test environment):

```sh
/workspace/tk73-venv/bin/python -m pytest tests/test_tk55_generated_claim_identifiers.py tests/regression/test_post013_tk55_excerpt_source_product.py tests/regression/test_post013_tk55_cascade_source_product.py tests/regression/test_tk55_first_party_input_contracts.py tests/test_tk65_envelope_schema.py tests/test_tk56_structured_name_boundary.py tests/test_f3_claim_search.py
```

```text
1281 passed in 15.43s
```

Cold process per sample, unchanged GC and actual generation/output assertions:

```sh
/workspace/tk73-venv/bin/python docs/handoff/requests/TK55_generated_claim_identifier_probe.py
```

```json
{"cold_process_each_sample": true, "denominator_seconds": 0.006854205999843543, "gc_changed": false, "pass": true, "path": "Claim.create", "platform": "Linux", "python": "3.12.14", "ratio": 4.458213540951728, "rows": {"1x": {"claims": 1000, "id_chars": 16, "minimum_seconds": 0.006854205999843543, "prefix_chars": 4, "samples_seconds": [0.008641380001790822, 0.006854205999843543, 0.008644988000014564]}, "4x": {"claims": 4000, "id_chars": 16, "minimum_seconds": 0.03055751400097506, "prefix_chars": 4, "samples_seconds": [0.03055751400097506, 0.04304695700193406, 0.03904853099811589]}}}
```

The cardinality comparison measures fixed-size identifier generation batches, not a variable-length parser or the full pipeline. No new regex/analysis path is added. Detectors and scoring are unchanged, so no new retired/train scoring is claimed for this source-only change. No development corpus was received or accessed. Same-SHA required CI, including CodeQL new warnings, is reported in the PR separately from these local results. Existing expectations, protected assets, versions, defaults and budget policies are unchanged.
