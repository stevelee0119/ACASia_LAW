# TK44/49 Form inspection candidate receipt

Start `f84ccbabde2584e96204b74f8b668299220ee912`, design-first `28cd55f`. The final submission SHA is in the PR comment. All changes are public design/tests/probe only; `packages/`, existing expectations and protected paths have zero diff. This is ready for design review when evaluation resumes, not a product activation or ticket closure.

Linux/Python3.12.14 command and output:

```sh
/workspace/tk73-venv/bin/python -m pytest tests/test_tk44_form_inspection_candidate.py tests/test_tk44_named_actualtext_provider.py tests/test_tk44_actualtext_provider.py tests/test_boundary_signal_observations.py tests/test_boundary_candidates.py --tb=short
```
```text
259 passed in 8.59s
```

The33 new controls contain three fabricated instruction strings and three benign values, direct/indirect actual native Form resources, rotation, same-name PAGE/Form disagreement, unused/missing/unsupported sources and shared budget cases. Six indirect-instruction cases (three strings × two rotations) gain inspection; six direct-string counterparts were already inspected by the original raw collector and are not new gains. PAGE collision uses an indirect unselected value so it distinguishes selected lookup from the existing raw literal collector. Unused raw literals already seen by that collector remain intact. All controls preserve original reading/raw data and no Form boundary is certified; Form inspection completeness stays false. An initial related run lacked `apps/` in this sparse checkout (4 failures/251 passes); restoring the unchanged public application modules resolves those setup imports. No expectation was altered.

```sh
/workspace/tk73-venv/bin/python docs/handoff/requests/TK44_TK49_form_inspection_probe.py
```
```json
{"cold_process_each_sample": true, "denominator_seconds": 0.01119358699725126, "gc_changed": false, "pass": true, "path": "parse_document + Form inspection candidate", "platform": "Linux", "python": "3.12.14", "ratio": 1.066737499043935, "rows": {"1x": {"minimum_seconds": 0.01119358699725126, "samples": [{"decoded_form_content_bytes": 111, "logical_string_chars": 2000, "seconds": 0.01119358699725126, "selected_occurrences": 4, "source_bytes": 4989}, {"decoded_form_content_bytes": 111, "logical_string_chars": 2000, "seconds": 0.01583138199930545, "selected_occurrences": 4, "source_bytes": 4989}, {"decoded_form_content_bytes": 111, "logical_string_chars": 2000, "seconds": 0.014352251000673277, "selected_occurrences": 4, "source_bytes": 4989}]}, "4x": {"minimum_seconds": 0.011940618998778518, "samples": [{"decoded_form_content_bytes": 327, "logical_string_chars": 2000, "seconds": 0.011940618998778518, "selected_occurrences": 16, "source_bytes": 4991}, {"decoded_form_content_bytes": 327, "logical_string_chars": 2000, "seconds": 0.012834122997446684, "selected_occurrences": 16, "source_bytes": 4991}, {"decoded_form_content_bytes": 327, "logical_string_chars": 2000, "seconds": 0.012694143999397056, "selected_occurrences": 16, "source_bytes": 4991}]}}}
```

The variable operator sequence is4× (4→16 selections), not the compressed PDF file size. Observed decoded Form bytes are39 fixed +18 per selection:111→327. Capture reuses one2000-character string; the probe preserves real parse output and checks security outside the timed parse. It is a narrow measured workload, not a whole-parser bound or a certification of Form geometry/semantic roles.

Activation still requires evaluator-owned treatment of the existing explicit Form-inspection residual assertion. No approval to change it is inferred. Full TK44/49 untagged/UNKNOWN primary, floor, structure-tree and consumer residuals remain. No private/check/train/sealed inputs, scores or paid calls were used; no detector scores or acceptance are claimed for this test-only candidate.
