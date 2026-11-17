# MV1: model-assisted verification

Specification approved in [#28](https://github.com/cohesivesystems/cohesive-evals/issues/28).

Development update: the [current implementation](implementation.md) upgrades the Cohesive
SDK through [Cohesive #584](https://github.com/cohesivesystems/cohesive/pull/584) and uses
its typed generation/execution APIs. The original capability audit remains pinned; the
implementation prototype is superseded, not a separate scored condition.

The original #49 supplied a capability audit and protocol, not a generated test suite,
held-out defect qualification, development trial or scored campaign.

## Question and starting point

Can an executable, inspectable model reduce the work of authoring and maintaining
useful tests without sacrificing independent defect detection?

The preserved audit starts from merged AO1 (`2e51498992ac1ac3cdd87a38d0e930e61932a77a`),
SDK source `b0c442ab5645907968d6b605edeb1dd54550130d`, package `0.1.0-eval.b0c442a`;
its [manifest](audit/package-manifest.json) remains unchanged. The current implementation
uses published SDK `0.1.0-eval.90eefde`, pinned in [sdk](sdk/dependency-manifest.json).
The original business source is preserved; package/lockfile changes are separately checked.
Each SDK/guidance change creates a development version; do not pool scored trial results.

The task is to build an offline reservation test suite, then maintain it through
one supplied policy evolution. Both conditions reuse the actual production model:

| Condition | Reused authority | Permitted verification tools |
| --- | --- | --- |
| Conventional | `InventoryRules.Reserve`, original record/enum types | Ordinary unit/property-based tests, generators, shrinkers, analyzers and reusable helpers |
| Cohesive | `InventoryTransitions.Reserve`, its canonical definition and interpreter | Same tools, plus model inspection and supported Assurance APIs |

Do not force conventional to duplicate its rules. Do not copy a simplified
Cohesive transition into the verifier. Independent requirements/assertions are
separate from either candidate's implementation; that separation is intentional.
The audit's ten manually selected examples are visible setup controls, not a
model-generated suite or hidden evaluation set.

## Scope and task sequence

1. **Reuse control.** Invoke production reservation logic in a fresh offline runner.
   Check accepted deltas and unchanged rejection state against independent examples.
   Record the exact source and transition fingerprints, and show no database/server
   is needed. Model execution alone is not model-assisted test generation.
2. **Author tests.** Produce cases for quantity, availability, maximum-per-order,
   quarantine and overlapping failures. Inspecting a model may propose inputs or
   coverage obligations; expected outcomes must be justified by the supplied policy.
   A generator that merely evaluates the candidate to produce expected results is
   a consistency check and cannot count as independent correctness evidence.
3. **Maintain tests.** Supply a separately qualified production revision in both
   conditions: positive over-limit quantities take precedence over quarantine when
   both apply; nonpositive quantity remains first. No other outcome/state changes.
   This is an explicit experimental policy evolution, not a change to AO1. Give both
   authors the same revised requirements and production patch; measure test work
   separately from preparing that patch. Keep the initial suite and its failures.
4. **Evaluate frozen suites.** Run correct controls and sealed requirement-targeted
   defects independently. Recheck concrete model counterexamples against the actual
   operation where applicable. Retain the external Python HTTP/physical-state oracle
   and AO1/PV2/Required/PV1/G0–G3 regressions for the unchanged application checkpoint;
   the experimental precedence revision needs separately versioned expectations.

The [matrix](test-matrix.md) fixes obligations and fault families. Check outcomes
and state, not just `Available >= 0`: an implementation that rejects everything
can satisfy that invariant. Include success/non-vacuity and false-alarm controls.
No persistence, concurrent overselling, reservation uniqueness, durable recovery,
or public HTTP mapping guarantee follows from an offline reservation check.
Those remain the responsibility of the existing independent integration verifier.

## Supported path and capability boundary

Use the reference interpreter for input-dependent reservation decisions. Assurance
may evaluate independently authored claims over explicitly labeled model observations.
Do not present these observations as production commits. The finite admission bridge
supports only state-dependent predicates; it rejects command-dependent reservation
guards. The original audit found no general automatic boundary generator. The current SDK
adds bounded Int32/Boolean proposals with caller-supplied states and per-input provenance;
this does not imply arbitrary predicate solving or exhaustive coverage.
Added generator/adapter work is recorded and qualified separately.
The audited typed Int32 subtraction claim is unsupported; do not silently replace
its arithmetic semantics. Use independent exact-delta assertions and report the
Assurance coverage limit.
Unsupported nodes and Unknown/incomplete results must be reported, not silently
removed or treated as success. Do not reimplement an SDK expression interpreter.

## Matching, feedback and isolation

This is one bounded supplementary experiment; it does not extend the pilot matrix
or settle the authorship/representation design in #10/#13. Before any trial, freeze
an implementation manifest with tool/library versions, instructions, visible examples,
feedback access, author identity/model, and budget settings in coordination with #17.

Proposed preparation-trial envelope: 60 active minutes for initial authoring and
30 for maintenance, equal within each matched pair; unrestricted visible build/test
iterations within that time. Record elapsed active time, iterations, tokens where
available and external dependencies. Log infrastructure interruptions separately;
retain timed-out/unsuccessful attempts as censored, never discard them. These are
protocol settings for later admission, not authorization to run a campaign now.

The independent evaluator owns requirements, expected outcomes and a held-out defect
set, outside participant workspaces. Freeze suite/source hashes before exposing any
held-out feedback. The public audit examples and already disclosed AO1 mutations
are development material, never relabeled held-out. Include a wrong shared-model
rule and misleading generated assertions to detect correlated mistakes. Specify
concrete held-out fixtures in an evaluator-only manifest before implementation
qualification; do not publish their locations/patches with participant artifacts.

## Measurements and admission

Report separately: correct-reference pass, paired requirement defects caught,
false alarms, unqualified/unsupported runs, concrete failing inputs, diagnostic
location/cause/actionability, authored test/generator lines and maintained rule sites,
active time and repair iterations. Record initial setup/SDK work separately from
per-task and maintenance effort. Use paired fault families and denominators; no
weighted detection-stage score or unequal-fixture headline percentages.

The comparison estimates the complete stack/tooling condition for this task; it
does not isolate model inspection causally. That requires a separately matched
inspection-on/off design. A finite catalog is complete only for its declared rows;
sampled success is not a universal proof. SDK source audits are not execution evidence.

Next deliverable after review: a PR-sized implementation/qualification issue covering
the offline adapters, generated suites, evaluator-only defect manifest and reporting.
Admit no trial until correct controls pass, planted defects and classification controls
are qualified, unsupported coverage is explicit, and both implementations receive
an idiomaticity/information-leakage review.
