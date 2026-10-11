# TK73 native page-tree/source-stream comparison receipt

Review-only diagnostic after the f87e636 design memo. Original 5c8/464 HOLD findings remain historical results. No product, grades/status, original936, fixed prior diagnostic inputs/expectations, scorer/gates/version or acceptance criteria change is made. No original AFP0, target completion or CI success is claimed.

```sh
PYTHONPATH=. python docs/handoff/requests/TK-73_post013_pdf_tree_support_spike.py /tmp/tk73-pdf-tree > /tmp/tk73-pdf-tree.json
```

The final comparison generates 30 new actual PDFs and invokes the unchanged frozen native21/source54/original111/dated117 diagnostics on their actual files (303 existing documents). **330 complete document comparisons assert original rows/finding semantics unchanged; three additional external-stream PDFs reject isolated native support but remain full-EOF unmeasured.** Fresh IDs/timestamps alone are excluded from finding comparison. Parser failures are not counted as original A, confirmed/pending success or complete comparison passes. Assertion failures are never swallowed into the parser-failure category.

| Separate population | Fully measured docs | Original A | Pending | Legacy A | Native TITLE-A | Tier changes vs 464 |
|---|---:|---:|---:|---:|---:|---:|
| New tree/stream controls | 27 | 27 | 6 | 21 | 0 | 12 |
| Frozen native21 | 21 | 21 | 3 | 18 | 0 | 0 |
| Frozen source54 | 54 | 54 | 27 | 27 | 0 | 0 |
| Frozen original111 (expanded review) | 111 | 93 | 27 | 63 | 3 | 0 |
| Frozen dated117 | 117 | 108 | 54 | 51 | 3 | 0 |

**Actual source-tree contrasts.** Three titles each have ordinary, valid nested Pages, wrong Parent pointing to an unrelated empty Pages, inconsistent Count, duplicate child, root Parent cycle, dangling child, external `/F` stream, unknown stream capability and genuine complete-date alternatives. Ordinary3 and correctly connected nested3 preserve pending with supported native extent. Parent/count/duplicate/unknown-stream3 each lose previously proposed pending and retain original A (12 changes). Root-cycle3 and dangling3 already abstained under the prior native helper and stay legacy; they are not additional gains. Genuine GLOBAL full-date alternatives3 retain original A despite supported extent. All27 fully measured controls exhaust decoded lexical occurrences, but only nine have supported source EOF; source extent9 is distinct from pending6. External-stream3 produce `PdfminerException` before original full comparison: isolated support rejects `/F`, full EOF remains unmeasured and no original finding retention is asserted for them.

**Membership and occurrence proof.** An iterative catalog-root DFS follows original Kids references in declared order, requiring root/no-parent, exact bidirectional child/Parent links, file-local reference ownership/resolution, typed Kids/Count, no duplicate/cyclic nodes, Count equal to visited descendant leaves and supported node capabilities. Leaf-reference order/cardinality must agree with the reader page view. Native PDFMiner page-object ids also must match those leaf occurrences in the same order; flattened reading segment indices are not substituted for these native identities. The PDFMiner occurrence mapping does not expose generation, so this bounded tree/content reference domain requires generation0 and rejects uncertain other generations rather than discarding that distinction. Original indirect content-stream references are preserved while decoding; a resolved StreamObject is not mistaken for its source-reference witness.

Native content streams accept only embedded stream metadata Length/Filter/DecodeParms and a proved owned indirect stream object. External `/F`, `/FFilter`, `/FDecodeParms`, unknown capabilities and uncertain/non-stream values reject before content decoding. No external source is fetched, declared empty or replaced with an inline fallback. The previous operator/resource/text-state checks remain necessary and are invoked only after this tree/stream domain proof. Graph membership, decoded character exhaustion, native extraction owner mapping, protection closure, inventory role and formal TITLE identity remain separate conditions. This is declared page/source extent under the explicit native grammar, not whole-file metadata semantics, raw byte authenticity, arbitrary font-glyph meaning or OCR completeness.

Frozen native21/source54/111/117 have zero tier changes. Original111 remains false pending9/true pending18/calendar A9; dated117 remains false pending45/true pending9/calendar A36/native whole-date TITLE-A3, with nine original parser misses separately retained. Compared with narrow5cd, date expansion still adds no false-candidate benefit and nine genuine confirmation losses. This source-tree rejection closes a public safety gap, not the target's missing native-to-reading coverage or full TK73 acceptance.

No production sidecar/cache/export/log/masking/LLM-wire change or production linear/0.1-second claim is made. The new tree walk uses forward visits plus Count offsets, without inventory×citation pairing; the whole diagnostic also retains the prior parsers/helpers and is not a runtime gate. Independent safety and counts-only target-applicability review are pending; later user criteria/implementation approval is still required.
