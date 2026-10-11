# TK73 confirmation-tier public counterpart receipt

Review only; no product, grade, status, existing test, scorer, baseline or gate changes. Base product is `2a85aa0e043cb6d13993742c2a053a8b048c48d5`. This receipt concerns the adjacent review memo and parallel diagnostic, not acceptance or a completed TK73 fix. No private inputs were accessed.

Reproduce the fixed public counterpart with Python and the repository's public dependencies:

```sh
PYTHONPATH=. python docs/handoff/requests/TK-73_post013_confirmation_tier_spike.py /tmp/tk73-confirmation-public > /tmp/tk73-confirmation-public.json
```

The script generates 108 actual TXT/PDF/DOCX documents (12 modes × three complete-title variants × three formats) and three actual native ruled-PDF TITLE documents. Mode/tier, original row counts and other-rule counts are fixed assertions. All 111 original row dictionaries remain unchanged. A second unchanged engine call verifies every original finding field except automatically generated finding/evidence IDs and creation timestamps. Original duplicate evidence grades remain A.

| Public measurement | Count |
|---|---:|
| Original duplicate A findings | 93 |
| Independent native TITLE-A conflicts | 3 |
| Legacy A retained, without a new TITLE certificate | 72 |
| Proposed pending candidates, original A still present | 18 |
| Public author-intended genuine duplicates detected | 66 |
| Genuine duplicates proposed for pending | 9 |
| Genuine duplicates retaining A presentation | 57 (3 independently certified; 54 legacy) |
| Original false candidates under public author intent | 27 |
| False candidates proposed for pending | 9 |
| False candidates retaining legacy A presentation | 18 |

The public semantic labels are assigned **after** the source-only triage. They express the generator author's intention, not an input to the classifier and not an independently inferred role. Both same-title/different-description and genuinely different untyped mixed-format titles enter pending (nine each). This exposes a genuine confirmation loss. Retaining all 66 original detections is not preserving independently confirmed recall. Under the original measure all 27 false candidates remain; pending does not produce original AFP0.

Each mode has nine actual documents. `same_description` and `true_unknown_mixed` propose pending. Plain different names, two complete noninventory propositions, two complete inventory alternatives, another parent, protected literal, source-owner uncertainty, original recognized-list population and invalid-date differences retain legacy A. Unregistered branch and party controls retain their original duplicate0; they supply no certificate. Three native PDF complete sentence-title differences retain independently certified A. Every ordinary unrecognized-list mode retains its original numbering-gap finding; all nine date controls retain their original invalid-date A and gap findings. Recognized-list controls retain their original no-gap population.

The missing-owner controls are explicitly a **diagnostic source-producer fault simulation**: the original file/document is unchanged, and one source-owner entry is removed before certification. They are not claimed as actual malformed parser inputs. The program abstains. Global alternative, parent and protected controls are actual generated-file inputs.

## What is proved by the diagnostic

For line controls the existing public source provider reads decoded native TXT characters, DOCX XML runs and PDF character occurrences separately from parser `attrs.lines`/reading strings. It checks ordered lexical ownership, native contiguous heading/reference/colon occurrences, actual peer/ancestor close positions and exact original occurrence/key correspondence. All original same-key rows participate before triage; two distinct complete alternatives in either role veto pending. Complete captions, propositions, dates and literal punctuation are preserved. Whitespace-only application comparison is declared as such: ignored or inserted reading whitespace is not certified as a physical glyph or used to manufacture heading/reference/colon grammar. These generated ordinary cases exercise exact source correspondence; they do not establish coverage for arbitrary NFKC, PUA, Cf, reordered or missing-owner inputs.

For native TITLE controls, `native_title_certificates` takes **no expected-title input**. It reopens the actual PDF, finds the actual ruled table, reads actual header cells using existing header aliases and locates title/reference/header characters inside their actual cell geometry. The receipt records original page character indices and bounding boxes. It verifies every native table/reference occurrence against original producer order, exact party/number/branch and complete original name/reference. Fixture expected names are checked separately for generator fidelity; they do not create a TITLE certificate. The three native examples each have two source-proved title cells.

These mechanical checks differ from **reviewed role-contract assumptions**: an explicit native TITLE header declares a title field, and a generic inventory heading with two unprotected reference-colon entries and an independent close defines a bounded inventory context. Native ownership proves the inscription, not arbitrary author intent. Outside colon formatting is expressly not a predicate, NON_TITLE or equal-title certificate. Pending communicates that remaining role uncertainty. Manual public author-intent labels are separate from both mechanical checks and the proposed role contract.

The geometric diagnostic reopens source files and is not a production linear-runtime certificate. No new source field, cache, log/export payload or LLM wire change is introduced. No full936 or 0.1-second implementation pass is claimed. Earlier native DOCX table cases with original exhibit_rows0 remain separate coverage residuals; this receipt certifies native TITLE only for its three actual PDF cases.

## Original expectations and approvals still required

The original936 expectations are unchanged and are not rerun as proof of this unimplemented proposal. Public test-family inspection identifies the relevant boundaries:

- `test_synthetic_genuine_different_titles`, `test_synthetic_unanchored_sentence_subtitles_remain_genuine` and `test_synthetic_reflow_opposites_preserve_genuine_duplicate` require original duplicate1/A. Plain/unanchored/protected counterparts here retain legacy A. A differently structured genuine mixed-format case can propose pending, as the nine explicit losses demonstrate; its assertion/confirmation contract would need approval.
- `test_synthetic_conflicting_prose_identities_remain_ambiguous` requires genuine full-proposition A. The diagnostic's all-origin competing-proposition and inventory-alternative guards retain A; no parent-local subset can certify away such alternatives.
- `test_synthetic_same_title_descriptions` expects duplicate0 under the prior C comparison. The proposed triage applies only to existing findings and cannot alter a resolved original duplicate0. Fresh 0.13 outputs and previously rejected C outputs must not be conflated.
- Original TK64 section populations, source UNKNOWN fallback, date/gap rules and genuine A grades remain. The nine recognized-section and nine invalid-date counterparts preserve those original paths.

A future implementation would require a separately approved meaning for user-facing “확인 필요”, an explicit impact inventory for genuine A confirmation expectations, and evaluator-approved confirmation metrics alongside unchanged original metrics. Original A evidence would remain traceable even if its user-facing assertion changes. No existing confirmation/AFP0 requirement is treated as satisfied by this receipt. Independent safety and counts-only target-applicability review must precede any user approval request or product implementation.
