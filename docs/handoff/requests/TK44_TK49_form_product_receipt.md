# TK-44/49 selected Form product submission

Public start `aefd55ed4831d6aeda6d5b5ad7a01e8a59a135f7`; design-first `8fd97db`. Final SHA and same-SHA CI run IDs belong to the PR's three-line review request. [Approval](https://github.com/stevelee0119/verify_ACAS_LAW/pull/108#issuecomment-6226443498) permits the exact two residual assertion reversals; the third incompleteness assertion, all other existing expectations, protected paths, versions and workflows remain unchanged.

The actual parser now captures an invoked Form's exact selected named ActualText for the existing scanner under shared capture budgets. No Form boundary is certified. It preserves original reading/raw text, UNKNOWN and incomplete inspection. New43 controls execute the product parser (no candidate adapter); the existing b1e public baseline supplies historical reading/raw comparison. Six indirect malicious cases gain inspection; direct counterparts were already seen by the raw collector. No product imports test code.

The initial product `e072aec4d5b7d433940b828d4da51e7a18779fa8` passed362 related tests. An additional source-ownership audit then reproduced six PAGE-property capture counterexamples for absent/empty native Form Resources. The library inherits PAGE resources in those cases, so the correction keeps the actual invoked stream's own Resources operand separately. Ten added controls cover those six, three uninvoked Forms and one invoked Form with no selection. The latter's first fixture write used pypdf's unsupported encoded-stream mutation (one fixture error,371passes); rebuilding a decoded stream corrects the synthetic fixture without changing expectations. All earlier test bodies remain intact. Final verification covers372 related cases and is recorded at the final SHA in the PR; earlier CI/timing is not attributed to it.

Initial e072aec functional checks (Linux, Python3.12.14; historical):

```sh
/workspace/tk73-venv/bin/python -m pytest tests/test_tk44_selected_form_inspection.py tests/test_tk44_named_actualtext_provider.py tests/test_tk44_actualtext_provider.py tests/test_tk44_named_inspection_lifecycle_spike.py tests/test_tk44_named_actualtext_capture_budget_spike.py
# 198 passed in 9.20s
/workspace/tk73-venv/bin/python -m pytest tests/test_boundary_signal_observations.py tests/test_boundary_candidates.py tests/test_tk44_named_actualtext_activation_spike.py tests/test_tk44_named_actualtext_capability_spike.py --tb=short
# 164 passed in 5.09s
```

Cold product timing command:

```sh
/workspace/tk73-venv/bin/python docs/handoff/requests/TK44_TK49_form_product_timing.py
```

Three fresh processes per size, product parse first, baseline afterward, GC unchanged. 1x4/4x16 selected occurrences; decoded Form bytes111/327 (39 fixed+18 per selection), compressed PDFs4989/4991 bytes. One reused2000-character string. Initial measured minima .370611411/.396856723 seconds, ratio1.070816254, satisfying the measured-workload <1second/<8ratio limits. Startup/noise dominate; this does not prove whole-parser complexity or a0.1second full-parser bound. Final-SHA exact output is attached in the PR; initial measurements are not attributed to an untested later SHA.

Common checklist: (1) real entry point `test_actual_selected_form_source_reaches_security_only`, including scanner result and original outputs; (2) command above; (3) commands/output/environment here, final SHA/CI in PR; (4) retired4/fixed comparison and injection-defense verification are **pending independent evaluator measurement**, as required by the approval. No private/train/check/sealed inputs are accessed or self-evaluated. Train item5 is not applicable to this existing parser ticket. No local `verify_all` run.

The accompanying one-page closure plan solves only selected Form security inspection and proposes structure-tree, untagged UNKNOWN primary, confidence floor and alternative consumers as `known_open`. Neither entire ticket is claimed closed. Independent acceptance, integration/full verification, release evidence and main checks are still required. User has authorized sequential progress through main once those conditions are met.
