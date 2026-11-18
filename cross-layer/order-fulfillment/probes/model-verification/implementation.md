# MV1 implementation and qualification

[PR #51](https://github.com/cohesivesystems/cohesive-evals/pull/51), tracked by
[#50](https://github.com/cohesivesystems/cohesive-evals/issues/50) and
[#52](https://github.com/cohesivesystems/cohesive-evals/issues/52), implements the bounded
reservation task in the [protocol](protocol.md). This is benchmark development, not a scored trial.

## Key code

| Responsibility | Conventional | Cohesive |
| --- | --- | --- |
| Generate states and quantities | Ordinary C# boundary values and threshold neighbors | `probe.GenerateCases(template, seed, options)` from actual transition guards |
| Execute production rules | `InventoryRules.Reserve(...)` | `probe.Execute(state, input, activationId)` |
| Source | [Program.cs](suites/conventional/Program.cs) | [Program.cs](suites/cohesive/Program.cs) |

The reusable Cohesive APIs are supplied by [SDK PR #587](https://github.com/cohesivesystems/cohesive/pull/587)
in `Cohesive.Transitions.Assurance` and the public `Cohesive.Transitions.Execution` layer. The SDK compiles once, generates typed inputs and returns
typed execution results with full decision evidence. No Python script parses expression IR.

Both adapters start from the same [template and bounds](suites/common/CaseCatalog.cs).
The conventional generator chooses stock and limit values at each endpoint, its inward
neighbor, and the template value. Cohesive inspects the reservation guards to choose
which fields to vary. The harness compares the sorted catalogs exactly before recording parity.

Two independently authored examples exercise zero quantity and a quarantined item
even when a defective model omits either guard. Both pass through the same oracle
as every generated pair. The earlier 328-case supplied-state run is preserved in
[the previous baseline](https://github.com/cohesivesystems/cohesive-evals/tree/f3a51a843751ee86c58e01b4135b38fb22a0d3f8/cross-layer/order-fulfillment/probes/model-verification).
The [independent Python oracle](../../../../cohesive_evals/mv1/oracle.py) checks domain/terminal outcomes, exact stock
delta and preservation of SKU, limit, quarantine and Cohesive partition. It imports neither
candidate model. The conventional success terminal label remains an adapter constant; actual
workflow projection is checked through HTTP separately.

## Qualification

- 388 matched cases, including 41 accepted, per condition and policy version.
- Ten paired production faults under both policies: 40 qualification runs.
- Original assertions detect the revised precedence. Wrong/omitted model guards remain detectable
  when cases are regenerated; generated outcomes never become expected answers.
- Exact model authority, unsupported-generation and build/runtime/timeout classification controls.
- Eight independent versioned HTTP witnesses through single/batch APIs, replay and physical state.
- Retained AO1, typed-input/PV2/Required, PV1 and cumulative G0–G3 checks.
- Nineteen package tests (oracle, evaluator and infrastructure) and three preserved audit tests.
  SDK validation includes 206 Assurance tests; full SDK CI passed.

The [current reports](verification-evidence/manifest.json) record actual results and bind raw
traces, diagnostics, locks, packages, source and build/output hashes. Fault detection gets credit
only for its expected named assertion; exceptions, unrelated assertions and unsupported results
never count as success. SDK packages are pinned to source `f9439d2bc6d4477636f3a03bb84c4a541d383caa`.

The only business-rule change is the separately hashed [precedence patch](suites/reference/):
positive over-limit rejection precedes quarantine; nonpositive quantity stays first. Original
business source is unchanged; Cohesive's package/lockfile upgrade is explicit in [sdk](sdk/).
Earlier AO1/PV checkpoints retain their original SDKs. The exact local-feed packages were
[published as an SDK prerelease](https://github.com/cohesivesystems/cohesive/releases/tag/eval-sdk-f9439d2)
before this upgrade; this is not a nuget.org release.

## Limits and development history

The SDK proposes neighbors for direct Int32 comparisons and handles direct/negated Boolean guards.
It records per-candidate motivating nodes, bounds, a versioned profile and coverage limits.
Callers supply a template and integer domains. The SDK varies guard-referenced fields to
construct synthetic pre-states. State-to-state comparisons sample around template values. Unsupported constructs and input-budget exhaustion fail explicitly.
`NoChange` remains an inspectable decision, so omitted effects can fail independent assertions.
No database commit, concurrency, durable-recovery or general Assurance proof follows from an
offline execution. Existing audit limitations describe its original SDK pin.

The earlier handwritten prototype and its initial 32 detected/eight unqualified runs remain in
[commit 5ead1e9](https://github.com/cohesivesystems/cohesive-evals/tree/5ead1e91bb3c9e61ca9490fe74aa4850e794385f/cross-layer/order-fulfillment/probes/model-verification).
This PR now uses the published SDK capability; it does not maintain two competing implementations.
The same maintainer authored suites and faults, with development feedback. No blinded/held-out
trial, performance, development-time advantage or exhaustive Int32 correctness is claimed.

## Reproduce

From the repository root, with .NET 10 and Docker available:

```sh
MV1=cross-layer/order-fulfillment/probes/model-verification
python3 -B -m cohesive_evals mv1-run --output /tmp/mv1-reference
python3 -B -m cohesive_evals mv1-qualify --frozen /tmp/mv1-reference --output /tmp/mv1-qualification
python3 -B -m cohesive_evals mv1-integration --fixtures /tmp/mv1-reference --output /tmp/mv1-http
python3 -B -m unittest discover -s tests
python3 -B -m unittest discover -s "$MV1/audit" -p 'test_*.py'
```

Use fresh output directories. Restores are locked; reproductions retain their own output hashes
while enforcing the suite source freeze. Existing AO1, typed-input, PV1 and evolution E3 verifiers
run against `original/references`; E3 uses AO1's `shared-source-pins.json`. Do not apply original
precedence expectations to the revised policy. See the [tooling map](tooling.md) for script roles.
