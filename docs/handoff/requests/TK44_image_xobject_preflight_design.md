# TK-44/49: subtype-only Form admission

Follow-up to #116 review6232639223 (conditional approval of ad848b1).
The preflight currently admits any nonempty XObject dictionary, causing a
second interpreter pass even when all XObjects are images. Admit this path
only when an XObject stream dictionary has `/Subtype /Form`. Keep PAGE
Properties admission and inline ActualText admission unchanged.

Resolve resource/XObject/subtype references with the existing bounded resolver
and shared document reference/cache budgets. Each inspected XObject uses one
existing shared capture context, bounding direct dictionaries as well as
references. Budget exhaustion remains sticky/incomplete and cannot certify
absence or boundaries. This conservative accounting can reduce later capture
capacity in large image-heavy documents; do not claim complete inspection.
Do not decode XObject content, recurse through uninvoked Form Resources, or
search for ActualText during preflight. Only the existing interpreter follows
actually invoked Forms; no change to primary text, named PAGE certification,
Form UNKNOWN/inspection-only, or lifecycle safeguards.

Validation: fabricated image-only PDFs through parse_document must never enter
the provider interpreter, while existing invoked-Form security findings remain.
Metadata-only controls cover image/Form/unsupported subtypes, indirect objects,
shared exhaustion and unopened stream bodies. Keep previous related controls.
Measure 5/20 pages, each with30 text lines and one small image, three fresh
processes per baseline/candidate/size, report minima and raw samples. Baseline
uses the preserved public b1e provider only on this no-ActualText/no-Properties
input; also time the original ad848b1 any-XObject predicate in isolation within
fresh parser processes to attribute the correction. GC unchanged, no whole-PDF
speed guarantee. Local OCR has tesseract5.5.0 eng/osd, no kor; default null.
Final-head outputs and new CI4 belong to the new SHA, not ad848b1's green CI.

Agent: implementer
