# Cohesive evaluations

This repository contains controlled evaluations of whether Cohesive's semantic
representations help a coding agent make correct software changes. It keeps the
experimental protocol, matched application fixtures, private scoring oracles,
runner, and run evidence together without making any one evaluation a general
claim about Cohesive.

**Status (November 2026):** fixtures, reference solutions, and evaluator
qualification are in progress. No scored agent runs have been performed yet, so
this repository contains no results about Cohesive's efficacy.

New to the terminology? See the [evaluation glossary](GLOSSARY.md) for short
definitions and how these pilots use them.

See the [benchmark landscape](BENCHMARKS.md) for a classification of related
benchmarks and studies, their implications for this project's goals, and
candidate evaluation measures.

## Pilots

| Pilot | Question | Status |
|---|---|---|
| [Relations](relations/protocol.md) | Can a single small change be compared fairly between idiomatic C# and `Cohesive.Relations`? | Protocol v0.1 and oracle approved; oracle qualified; runner validated without an agent. Baseline/oracle freeze, agent driving, calibration, and runs pending. |
| [Order fulfillment](cross-layer/order-fulfillment/protocol.md) | Does Cohesive help preserve interacting obligations, and does that change after accumulated evolution? | Protocol defined, not frozen. G0 fixtures and E1–E3 references (G1–G3) implemented and qualified in both conditions. Independent conventional review, hold/review-marker references and oracle qualification, acceptance-breadth review, campaign admission, calibration, and runs pending. |

### Relations

The first pilot compares idiomatic conventional C# with `Cohesive.Relations` on
one small application change. Its purpose is to prove that the comparison can be
fair, repeatable, and independently scored before we automate or broaden it.

It has one case, **Load Search Mapping**, and one task, **Make Equipment
Optional**, with five independent runs scheduled per condition. The results will
be descriptive evidence about this configuration only; they will not establish
general developer productivity or Cohesive efficacy. Frozen v0 remains preserved
in Git history. The Python runner foundation keeps Relations as its regression
fixture; cross-layer runner integration follows separately.

### Order fulfillment

The broader pilot compares an order-hold change (H) with an informational
review-marker control (L) at fresh (G0) and aged (G3) checkpoints, using quantity
limits (E1), cancellation (E2), and inventory quarantine (E3) as the evolution
sequence. The [matched G0 fixtures](cross-layer/order-fulfillment/README.md) pass
52 shared HTTP checks per condition. Each evolution step has reference solutions
in both conditions, cumulative checks of earlier obligations, and application-defect
qualification.

Supporting work, outside the scored matrix:

- [Durability qualification](cross-layer/order-fulfillment/durability/README.md):
  recovery and invariant checks under controlled worker crashes.
- [Portable-validation probes](cross-layer/order-fulfillment/probes/portable-validation/protocol.md):
  single-item/batch validation reuse (PV1) followed by a shared request ID length
  rule (PV2), each with references and qualification.
- [Typed input constraint audit](cross-layer/order-fulfillment/probes/portable-validation/typed-input-audit/README.md):
  the pinned Cohesive SDK can declare a length constraint but does not enforce it,
  tracked in [cohesivesystems/cohesive#529](https://github.com/cohesivesystems/cohesive/issues/529).

Shared MV1 tooling and adapter contracts are documented in
[`cohesive_evals`](cohesive_evals/README.md). Run `python3 -m cohesive_evals --help`.

## Repository layout

```text
relations/
├── protocol.md
├── cases/load-search-mapping/   # case spec, conventional/cohesive conditions, equivalence checks
├── oracle/                      # maintainer-only
├── runner/
└── results/
cross-layer/order-fulfillment/
├── protocol.md
├── conditions/                  # G0 conventional and cohesive starting applications
├── verification/                # shared HTTP checks and invariant sequences
├── qualification/               # deliberately broken applications
├── evolution/                   # test matrix, contracts, E1–E3 references
├── durability/
├── probes/portable-validation/  # PV1, PV2, typed-input audit
└── packaging/                   # vendored Cohesive package build
```

- `conditions/` contains the independently buildable conventional and Cohesive
  starting repositories. Only a selected condition directory is given to an agent.
- `equivalence/` and `verification/` contain maintainer checks that enforce
  matching public surfaces and normalized behavior.
- Oracle, qualification, evolution, and reference material is maintainer-only. It
  must never be copied into an agent workspace.
- `relations/runner/` contains the candidate dry-run orchestration and scoring
  foundation.
- `relations/results/` will contain immutable evidence from evaluation runs.

## Working principles

1. Compare equivalent starting behavior, not identical source code.
2. Change only the software representation between conditions.
3. Give the agent the same task, feedback, permissions, and resource limits.
4. Judge correctness at a shared public application boundary.
5. Keep hidden checks outside the agent's workspace.
6. Treat a harness defect as an invalid experiment, not an agent failure.
7. Preserve obligation-level evidence instead of reducing a run to one score.
