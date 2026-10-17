# TK-44/49 conditional-review correction

Review6232639223 requested subtype-only admission after evaluator approval of
ad848b1's selected Form security behavior. Latest public Stevead8ac0f (#118)
was merged normally; design-first1c067b3 precedes this correction. No conflict
or TK76 product edits. Final SHA, exact measurements and CI IDs belong to the
PR report, not to uncommitted-tree measurements or prior ad848b1 CI.

Only the XObject admission fallback changes: stream dictionary `/Subtype
/Form` admits interpretation; image-only/unsupported objects do not. No
uninvoked XObject content or nested Resources is decoded or traversed. Shared
reference/cache budgets still apply and each metadata entry consumes a shared
context, including direct streams. Exhaustion is sticky/incomplete; this can
reduce later capacity in large image-heavy documents. PAGE/inline paths and
invoked Form source ownership, primary reading/raw, UNKNOWN, no certified Form
edges, selected-only capture and incomplete lifecycle stay as before.

15 new controls: actual image-only parser3 and invoked Form/scanner3,
direct/indirect image/Form/unsupported stream metadata6, direct-dictionary
budget exhaustion, malformed dictionary and indirect-subtype/reference-budget
controls. Existing372 controls retained, including the originally authorized
two residual assertion reversals and unchanged incompleteness assertion.
Test-edit/protected-path checks against origin/Steve_ACASiaLAW pass. Initial
fixture smoke run used a nonexistent document.text accessor (3 failed/11
passed); fixed to the document's real blocks, no behavioral expectation changed.

```sh
/workspace/tk73-venv/bin/python -m pytest tests/test_tk44_image_xobject_preflight.py tests/test_tk44_selected_form_inspection.py tests/test_tk44_named_actualtext_provider.py tests/test_tk44_actualtext_provider.py tests/test_tk44_named_inspection_lifecycle_spike.py tests/test_tk44_named_actualtext_capture_budget_spike.py tests/test_boundary_signal_observations.py tests/test_boundary_candidates.py tests/test_tk44_named_actualtext_activation_spike.py tests/test_tk44_named_actualtext_capability_spike.py --tb=short
/workspace/tk73-venv/bin/python docs/handoff/requests/TK44_image_xobject_preflight_timing.py
/workspace/tk73-venv/bin/python docs/handoff/requests/TK44_TK49_form_product_timing.py
```

Image workload:5/20pages,30fabricated lines and one8x8image/page; alphabetic
page variation avoids repeated-header stripping of the whole synthetic body.
PDF generation uses invariant metadata so independently generated samples have
the same raw metadata text. Initial cross-process hash assertion at9ac9056
failed because creation timestamps differed; same-file baseline/candidate
reading/raw were equal. No product behavior or expected result was changed.
Three fresh processes/mode/size; time parse_document, exclude PDF generation
and imports, unchanged GC. Compare preserved b1e provider on this input without
ActualText/Properties, exact ad848b1 any-XObject predicate with all other current
parser code fixed, and current candidate. Compare reading/raw hashes across
all samples. This measures the predicate's effect; it is not a full historical
checkout/evaluator-environment comparison. Also time direct image, indirect
image and Form-last metadata paths with8/32entries,64calls/sample, fresh3each,
report raw times/denominator/ratio and <8/<1s criteria for the new path itself.
Existing selected-Form4/16occurrence timing is preserved separately.

Environment Linux/Python3.12.14, tesseract5.5.0 eng/osd, missingkor, defaultnull.
The earlier372passed11.38s was this no-Korean-OCR environment; OCR binary was
present. Synthetic body text does not need OCR. No whole-parser time guarantee.
Scores/injection at ad848b1 are evaluator results (fixed81.7/79.2/0; retired
19.0/29.6/36.2/15.2 withFP0/0/0/3); new-head CI supplies current fixed results.
Evaluator requested changed-scope/time-only recheck; fullverify_all is deferred
to one release-candidate run. No local full run or private/corpus access.

Checklist1 actual parser/scanner tests above;2/3 new timing harness/commands and
final-head exact PR outputs;4 prior evaluator scores explicitly tied toad848b1,
new fixed results from new CI;5train not assigned to this existing ticket.
Known_open closure proposals accepted in conditional review; evaluator owns
registry updates after acceptance. Neither release nor full-ticket closure is
claimed by this correction; release still includes eventual TK73 product.
