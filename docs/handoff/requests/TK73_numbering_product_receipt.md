# TK-73 approved product comparison

Approval: [#11759b62fc](https://github.com/stevelee0119/verify_ACAS_LAW/pull/117#issuecomment-6233150342).
Start public Steve1d279d0a785dfcc5099daef530dde5006ea1c7c4 (#114/#118/#119),
new branch/product PR, design-first4a2234b. Final SHA/results/CI run IDs go in
the PR after clean-head verification. Design PR stays open until evaluator
cleans it up after product acceptance.

Production changes only `_numbering`'s comparison-key decision. Two local
helpers reproduce approved first-token grammar and pair guards. All original
numbering statements other than the comparison-key expression have identical
AST; all other top-level product nodes, including extraction and #118 COPY,
are unchanged. No original row/name/date/group/finding/evidence/grade mutation.
The asymmetric-date A finding remains known_open, as explicitly accepted.

The approved73 controls keep their semantic expectations. Historical before
uses a test-only verbatim original `_numbering` from public Steve1d279d0,
compiled with the unchanged engine globals; after uses actual installed
product. No prototype candidate is installed or imported by product. Four
helper-only boundary controls now test full product outputs with the same
tails. The native unguarded-loss diagnostic assertion is preserved separately.
Three new full offline pipeline cases use actual TXT parsing (no parser/engine
mock) and assert exact duplicate count1, retained original names/evidence and
A/CONTRADICTED for a different immediate identifier, while excluding the
repeated mention. Related existing exhibit/party/branch/parent/interval/date/
amount/list/time and #118 COPY controls remain. No old test edits or protected
path changes.

Public330 uses the unchanged #92 generator/labels at401d098 and the same
generated inputs. Both comparisons now execute check_document; candidate is
the normal product, baseline temporarily swaps only the frozen old numbering
within a restoring context. Check original baseline counts, untouched rows,
all non-duplicate findings, A grades and existing semantic labels. Expected
true120 retained/loss0, false183 removed; original111 included,3 external-stream
full comparisons still unmeasured. No claim of independent generalization.

Commands (Linux/Python3.12.14, defaultOCRnull: tesseract5.5.0eng/osd, no kor):

```sh
/workspace/tk73-venv/bin/python -m pytest tests/test_tk73_numbering_product.py tests/test_tk73_numbering_pipeline.py tests/test_v5_exhibit_grammar.py tests/test_tk64_exhibit_prose_rows.py tests/test_tk67_numbering_gap_scope.py tests/test_copy_statement_heading.py tests/test_v3_d5_consistency.py tests/test_evidence_hardening.py --tb=short
/workspace/tk73-venv/bin/python docs/handoff/requests/TK73_numbering_product_public330.py /tmp/tk73-final401-20261016.json /tmp/tk73-final401-20261016 --output /tmp/tk73-numbering-final330.json
/workspace/tk73-venv/bin/python docs/handoff/requests/TK73_numbering_product_timing.py
```

Timing uses actual installed `_numbering` for eight approved grammar paths,
4000/16000variable chars,32two-row calls/sample,3fresh processes/size, GC
unchanged, denominator floor.0001s. Check result counts and original names.
Report samples/minima/ratios and <8/<1s4x; no whole-parser guarantee.

Checklist1 actual pipeline test above;2/3 commands and final-head exact outputs
in PR;4 fixed dev/holdout and public retired4 from same-head CI, including new
`은퇴 세트 비교`. Approval expects last25.2/A1/.302 and other3unchanged. These
CI results are pending until completed; design evaluator scores are historical,
not product remeasurement. No local fullverify_all/private/fixed/corpus input.
Independent product acceptance, Steve integration and release validation still
precede user-authorized main merge; neither entire ticket nor deployment is
claimed by this implementation submission.
