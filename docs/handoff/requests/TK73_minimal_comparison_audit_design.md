# TK-73: audit the evaluator's minimal comparison before product changes

Start: public Steve `aefd55ed4831d6aeda6d5b5ad7a01e8a59a135f7`. Follow [evaluation request](https://github.com/stevelee0119/verify_ACAS_LAW/pull/92#issuecomment-6226447328). This first commit is design only.

Measure exactly one proposed change inside `_numbering`: compare whitespace-stripped names only up to the first ASCII comma or colon. Keep extraction, rows, original names/evidence, section exclusion, party/parent/branch grouping, grades and other findings unchanged. A diagnostic compiles that one-expression change in isolation; it is never installed in product.

Use the unchanged public #92 `401d0988e0440a8db49b6e1c9f505b26d4fd587c` generators and semantic labels. Report original111 separately from all330 measured comparisons (the111 is already included, not additional). The three external-stream full comparisons remain unmeasured. Count true duplicates lost, retained true duplicates and removed false candidates per family; retain every individual public record. Existing public truth labels are not reclassified to favor this proposal. In particular a native title cell can contain a colon as part of its actual title.

If any true duplicate is lost, stop product activation and submit a one-page narrower protection design. The current permission to implement applies only when that loss count is zero. No new review status, score/grade changes, date/EOF expansion, protected asset edits or private corpus access. Use synthetic native title/date/document-identity counterexamples to inform that design, not private input reconstruction. Final reports cite their exact SHA and public commands.
