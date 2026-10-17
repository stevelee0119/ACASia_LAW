# TK-73 numeric/identifier scope follow-up

Follows user handoff(2) and [review6232562505](https://github.com/stevelee0119/verify_ACAS_LAW/pull/117#issuecomment-6232562505). Original submitted head `a9f90c2556be24ecfe239d284ca740f966ba681c` and its CI/failure/retry history remain separate. Latest public Steve `097c7dc` was merged normally before this design follow-up. Design-first829085e and boundary clarification24c0212 precede prototype changes. Final SHA/exact output/CI run IDs are attached in the PR, not inferred from an uncommitted tree.

Only the first whitespace-delimited token after comma/colon can supply numeric/ASCII identifier evidence. Later narrative numbers, exhibit references and codes do not veto the pair. No title/description vocabulary or retired-set values are in the rule/tests. Existing two-line/comma-colon/equal-prefix/date/native/third-occurrence protections remain unchanged. The candidate is test/design-only; no product function/file is installed or modified.

| Public retired set | Baseline score / recall / FP / A | First-token candidate | Injection |
|---|---|---|---|
| 20261008 |19.0 / .190 /0/0|unchanged|defended both|
| 20261008b |29.6 / .296 /0/0|unchanged|defended both|
| 20261009 |36.2 / .362 /0/0|unchanged|defended both|
| 20261010 |15.2 / .302 /3/3|**25.2 / .302 /1/1**|defended both|

**A0 target remains unmet.** The remaining pair has exactly2line rows, comma/colon, equal normalized prefixes and **zero identifier vetoes**. Its original date fields have unequal availability: one absent, the other observed in later prose. The unchanged date guard retains the full original A finding. This metadata-only trace does not require a case-name exception. Three additional fabricated asymmetric-date controls fix that current protection as a visible residual; no expected-value replacement, grade/status change or date expansion is used to force A0. Request an explicit evaluator decision about this separate residual after reviewing the scoped numeric fix.

Public330: same original labels/documents, original111 included (not additional), true120 retained/loss0, false183 removed. Three external-stream full comparisons stay unmeasured. Native title/GLOBAL/unequal-date findings remain protected. Added controls cover three distinct fabricated titles with later numeric/code prose, differing immediate numeric/ASCII/bracket IDs, malformed identifier wrappers, first-token boundaries and asymmetric dates; original27 controls unchanged.

Commands, Linux/Python3.12.14 (final-head exact outputs in PR):

```sh
/workspace/tk73-venv/bin/python -m pytest tests/test_tk73_minimal_comparison_design.py --tb=short
/workspace/tk73-venv/bin/python docs/handoff/requests/TK73_minimal_comparison_audit.py /tmp/tk73-final401-20261016.json /tmp/tk73-final401-20261016 --guarded --output /tmp/tk73-first-token-final330.json
/workspace/tk73-venv/bin/python docs/handoff/requests/TK73_public_retired_compare.py --mode baseline --output /tmp/tk73-first-token-final-baseline.json
/workspace/tk73-venv/bin/python docs/handoff/requests/TK73_public_retired_compare.py --mode guarded --output /tmp/tk73-first-token-final-guarded.json
/workspace/tk73-venv/bin/python docs/handoff/requests/TK73_minimal_guard_timing.py
```

The aggregate-only public runner uses unchanged evaluator/scorer code and four hard-selected now-public retired directories, network0, temporary local data and no private/fixed/corpus input. Candidate patch is in-memory in that process only, restored afterward. Protected scorecard's existing OCR-language-list formatting is retained verbatim; the separate adapter probe gives the actual languages/readiness. No protected file is changed. This is implementation-side reproduction, not independent acceptance, new sealed testing or product activation.

Timing expands the previous four paths with later narrative digits/codes and closed/unclosed wrapper tokens, each4000/16000variable characters,64calls/sample, three fresh processes/size and unchanged GC. Report measured<8ratio/<1s4x conditions, no whole-parser/0.1s guarantee. Preliminary measurements are superseded by final-head output without deleting their history.

OCR clarification for #116: local tesseract5.5.0 has eng/osd but no kor, so default adapter is null/LANGUAGES_MISSING. The unchanged ad848b1 Form-only native parse confirms ocr_engine=null and attempted/recognized pages empty. The earlier372passed/11.38s is not a Korean-OCR-capable full-runtime claim. This was also posted to #116; that branch remains frozen while the evaluator measures real-PDF XObject-path performance.

Product implementation still requires independent design approval and a new `_numbering`-only PR. User release scope includes #116 plus the eventual TK73 implementation; no main deployment, entire ticket completion, A0 or new review status is claimed by this design follow-up.
