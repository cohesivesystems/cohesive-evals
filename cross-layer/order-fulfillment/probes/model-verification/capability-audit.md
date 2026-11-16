# Pinned capability audit

SDK source: `b0c442ab5645907968d6b605edeb1dd54550130d`. Application: merged AO1
`2e51498992ac1ac3cdd87a38d0e930e61932a77a`. The runnable witness uses the actual
production sources/types; it does not author a substitute reservation transition.
[Evidence](evidence/report.json) records source, package, lock and output hashes.

| Capability | Evidence type and observed result | Consequence |
| --- | --- | --- |
| Reuse conventional rules offline | Executed the original `Domain.cs` linked into a tiny runner; 10/10 independent examples pass | Conventional already has reusable pure logic; do not manufacture duplication |
| Reuse Cohesive reservation offline | Referenced the production application assembly; 10/10 examples pass through `TransitionReferenceInterpreter` | Int32 state/input, enums, JSON field names, rejection and accepted deltas work for these examples |
| Inspect authoritative guards | Exported the actual transition document: four ordered guards, fields/parameters, operators, rejection expressions and exact revision/fingerprint | Inputs for a potential case generator exist; generating a useful suite is separate work |
| Assurance batch evaluation | Four accepted reservation post-states satisfy independent `Available >= 0`; a synthetic negative-stock model observation violates it; serialized results re-evaluate identically | Evaluating claims is available; evidence is explicitly about reference-model observations, not production commits |
| Finite state-only admission | Actual order-submit guards satisfy an independent Draft-only claim over Draft/Submitted/Cancelled/Archived rows; 4 visited, enumeration complete, non-vacuity satisfied; artifact rechecks | Supported for this declared catalog; not a theorem over all entity states or transition effects |
| Finite reservation admission | Actual reservation binding throws `NotSupportedException`: `Admission 'fulfillment/reserve/body/auto/requires/1' uses unsupported expression 'ParameterExpr'.` | Quantity-dependent guard is outside the pinned profile; never erase it to obtain a successful check |
| Typed exact stock-delta claim | Ordinary `after.Available == before.Available - command.Quantity` fails with `authoring.expression.operatorUnsupported` at `body/right` | Int32 subtraction has different overflow semantics; retain independent exact-delta assertions rather than silently switching to decimal arithmetic |
| General automatic boundary/test generation | No such entry point identified in the inspected Assurance/transition-binding APIs | Must be authored, bounded and qualified; no out-of-box generation claim |
| Production observation/concurrency proof | Not exercised; the SDK reference evaluator does not supply a production observation adapter here | HTTP, persistence, replay and concurrency remain independent integration obligations |

The ten examples cover zero/negative quantity, overlapping quarantine/limit/stock
failures, exact limit/stock boundaries, ordinary success, Int32 min/max. They are
manually authored capability examples, not independent experimental samples or a
generated suite. Rejected transitions are checked by the Python expected results;
they are not mislabeled as commits for the Assurance transition claim.

The negative-stock observation is deliberately synthetic, not produced by the
correct reference. Its sole purpose is to show that the independently authored
claim can return Violated. No seeded application defect or held-out suite has been
qualified in this audit. The finite order catalog fixes ID/partition and enumerates
four statuses; complete enumeration means precisely those four rows.

## Source evidence

All links identify the inspected pin, not current main:

- [Reference interpreter](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/Cohesive.Transitions/Execution/TransitionReferenceInterpreter.cs): executes the compiled definition without a storage commit.
- [Transition admission bridge](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/Cohesive.Transitions.Assurance/TransitionAssurance.cs): preserves guard order/references; rejects command dependencies, creation and machine-bound transitions.
- [Finite checker](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/Cohesive.Assurance/FiniteGuardChecker.cs): evaluates supplied catalogs; does not construct an exhaustive input domain.
- [Assurance semantics](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/Cohesive.Assurance/README.md): claim forms, typed arithmetic restrictions and reference-observation boundary.

## Packaging and reproduction

The existing AO1 runtime package closure is unchanged. Two verification-only
packages, `Cohesive.Assurance` and `Cohesive.Transitions.Assurance`, were built from
an immutable Git archive of the same SDK commit. Their bytes are vendored under
`audit/packages`, with [hashes and source provenance](audit/package-manifest.json).
The audit restores both projects in locked mode. The conventional runner links
its exact production rule file; Cohesive references its exact application project.
Neither starts an HTTP server, worker or PostgreSQL instance.

```sh
python3 -B cross-layer/order-fulfillment/probes/model-verification/audit/run.py \
  --output /tmp/mv1-capability-audit
```

Use a fresh output directory and the pinned .NET 10.0.402 SDK. NuGet packages must
be cached or restorable; network failures are setup failures, not capability results.
`--prepare-locks` is only for deliberate maintainer lockfile changes, not normal runs.
The witness writes build logs, both result files, the transition document, the
finite-check artifact and a provenance report. The checked-in evidence retains
those files; production inputs are hashed before/after build to reject source drift.

To rebuild only the two added packages: archive the manifest's SDK revision,
then `dotnet pack` the listed projects with `-c Debug`,
`-p:Version=0.1.0-eval.b0c442a` and `-p:RepositoryCommit=<manifest revision>`.
Do not replace the production closure with rebuilt packages. A changed package
hash requires an explicit new audit pin, even if the source revision is unchanged.
