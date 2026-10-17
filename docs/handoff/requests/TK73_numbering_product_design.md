# TK-73 approved comparison-key implementation

Implement approved #117 head59b62fc, [review6233150342](https://github.com/stevelee0119/verify_ACAS_LAW/pull/117#issuecomment-6233150342),
from public Steve1d279d0 (#114/#118/#119 included), in a new product PR.
The asymmetric-date residual is explicitly known_open; keep its A finding.

Change only `_numbering`'s distinct-name comparison key. Local helpers within
that function implement the approved grammar: exactly2 line-derived rows,
one comma/one colon, equal nonempty whitespace-normalized prefixes, equal
original dates, and no immediately attached first-token identifier. Copy the
approved first-token character grammar/punctuation/wrapper behavior exactly.
All other groups use the original full-name keys. Never mutate rows, original
names, grouping, finding/evidence/grades, extraction, dates or statement/COPY
logic. No new dictionary or product import from tests/handoff.

Preserve the original public comparison baseline as test-only source frozen
verbatim from Steve1d279d0 `_numbering`; compile against unchanged engine globals.
Reuse #117's73 exact controls/expectations with that historical baseline and the
real installed product function. Re-run unchanged330 public inputs/labels using
real check_document for the candidate, compare non-duplicate findings/rows too.
No replacing old truth labels to match the product. Add an actual pipeline
entry-point test checking result count/content and A/CONTRADICTED preservation.
Run existing evidence/numbering/party/branch/parent/interval/date/amount/list/time
protections and #118 statement/COPY controls, related tests only locally.

Time each approved grammar path in actual `_numbering`, suffix4000/16000chars,
3fresh processes/size, unchangedGC, report raw samples/minima and ratio<8,
4x<1s. This is the numbered-comparison path, not whole-parser complexity.
Final-head commands/output/environment and checklist1-4 belong in the PR.
Retired4 baseline/candidate use evaluator-owned CI `은퇴 세트 비교`: expected
c25.2/A1, others unchanged relative to latest Steve; fixed results cite CI.
No private/fixed/corpus input or local fullverify_all. Normally merge any new
Steve commits before push; no force/rebase/direct integration-branch push.

Independent product acceptance is still required before Steve integration;
the release includes #116 plus this product change before authorized main merge.
