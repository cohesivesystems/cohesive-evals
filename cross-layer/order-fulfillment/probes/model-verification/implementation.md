# MV1 implementation and qualification

Tracked by [#50](https://github.com/cohesivesystems/cohesive-evals/issues/50), following
[#49](https://github.com/cohesivesystems/cohesive-evals/pull/49). This implements the
bounded reservation task in the [protocol](protocol.md); it does not run a development trial.

## What is compared

| | Conventional | Cohesive |
| --- | --- | --- |
| Production authority | Existing `InventoryRules.Reserve` and rejection mapping | Existing `InventoryTransitions.Reserve`, compiled and interpreted |
| Input proposals | Hand-authored threshold neighborhoods | Thresholds and boolean toggles inspected from actual guard IR |
| Expected behavior | Independent shared Python policy and state assertions | Same independent assertions |
| Offline adapter | [Program.cs](suites/conventional/Program.cs) | [Program.cs](suites/cohesive/Program.cs) |

Neither runner needs PostgreSQL or an HTTP server. The small [generator](suites/generate.py)
is new evaluation code, not a built-in SDK capability. It recognizes a narrow set of
predicates and refuses unsupported nodes; it does not implement an expression interpreter.
The shared state envelope, negative/zero/extreme quantities and independent assertions
remain available even when a faulty model loses a guard.

The [oracle](suites/oracle.py) checks exact domain and terminal outcomes, stock delta,
SKU, limit, quarantine and Cohesive partition preservation. Conventional has no partition
field. Its successful terminal label is an adapter constant; the separate HTTP checks
cover actual workflow projection. Offline rejection execution never establishes database,
concurrency or durable-recovery correctness.

## Results

| Check | Result |
| --- | --- |
| Correct original and revised references | 328 cases each, including 34 accepted, in each condition |
| Input parity | Identical generated inputs across conditions and policy versions |
| Maintenance negative control | Original assertions reject revised precedence in both conditions |
| Production defects | 10/10 detected per condition per policy version: 40/40 runs |
| Faulty-model regeneration | Changed quantity guard and omitted quarantine guard still fail independent assertions, under both versions |
| Authority / unsupported controls | Wrong definition, revision or fingerprint rejected; unsupported predicate reported explicitly |
| Versioned integration | Eight cases through single and batch APIs, cross-entry replay and full physical state, in both conditions and versions |
| Retained original integration | AO1, typed input/PV2/Required, PV1 and cumulative G0–G3 pass |
| Python tests | Five suite tests and eight evaluator tests pass; the three existing audit tests also pass |

The ten paired production faults cover zero admission, omitted quarantine/limit/stock
checks, strict stock/limit boundaries, omitted decrement, reject-all, corrupted configuration
and wrong terminal mapping. Each gets credit only for its named assertion. Build errors,
exceptions, timeouts and unrelated assertions receive no detection credit. Rejection-field
corruption is additionally checked as an oracle control, not counted as a production mutant.

The proposed precedence change is isolated in [patches with source hashes](suites/reference/):
positive over-limit requests precede quarantine; nonpositive quantity stays first.
Original AO1 production/package inputs are unchanged. The generator and input catalog need
no maintenance for this change; the independent oracle has explicit original/revised policies,
and the Cohesive transition's revision/fingerprint changes. This is one supplied evolution,
not a measured test-maintenance advantage.

## Feedback history and scope

The first suites were committed at `01676cc8c3fbe3fa184aa984b583b3992f59ee7f` before
fault execution. That attempt detected 32/40 runs and left eight unqualified: six mutation
anchors were ambiguous across reserve/release; two omitted-decrement runs produced
`NoChange`, which the adapter did not accept. No unqualified run received credit.

The adapter now accepts `NoChange` and inspects its outcome/state. Mutation anchors are
restricted to Reserve. The [initial freeze](evaluation/history/initial-suite-freeze.json),
[initial report](verification-evidence/initial-qualification.json) and
[repaired freeze](evaluation/suite-freeze.json) are retained. The 40/40 result is a rerun
after feedback, not the initial frozen result. No independent held-out result is claimed:
the same maintainer authored the suites and faults, and these materials are public.
Materialized candidate fixtures contain production inputs and adapters, not evaluator faults;
a future participant trial still requires genuinely separate workspaces and sealed cases.

This grid is finite, not an exhaustive Int32 proof. Assurance's audited quantity-dependent
finite-admission and typed subtraction limitations remain unchanged. We make no new
Assurance proof, performance, authoring-time or causal benefit claim. Raw authored source
counts are recorded [separately](verification-evidence/authored-work.json), with shared
files counted once; they are not a productivity score.

## Reproduce

From the repository root, with .NET 10 and Docker available:

```sh
MV1=cross-layer/order-fulfillment/probes/model-verification
python3 -B "$MV1/suites/run.py" --output /tmp/mv1-reference
python3 -B "$MV1/evaluation/qualify.py" --frozen /tmp/mv1-reference --output /tmp/mv1-qualification
python3 -B "$MV1/evaluation/integration.py" --fixtures /tmp/mv1-reference --output /tmp/mv1-http
python3 -B -m unittest discover -s "$MV1/suites" -p 'test_*.py'
python3 -B -m unittest discover -s "$MV1/evaluation" -p 'test_*.py'
python3 -B -m unittest discover -s "$MV1/audit" -p 'test_*.py'
```

Use fresh output directories. Restores are locked; original production packages remain
pinned to SDK `b0c442ab5645907968d6b605edeb1dd54550130d`. A reproduction records its own
build/output hashes while enforcing the committed suite source freeze. Re-run the existing
AO1, typed-input, PV1 and evolution E3 verifiers against `original/references`; their CLI
commands and expectations are unchanged. E3 requires AO1's `shared-source-pins.json`.
Do not run original precedence assertions against the separately revised production policy.

[Evidence manifest](verification-evidence/manifest.json) binds reports, inputs, source,
locks, package/build/output hashes, traces and logs. Its compressed archive contains a
per-file hash index and excludes packages, binaries and reproducible production source copies. HTTP checks used the production builds from before
the adapter-only repair; input equality and both build identities are retained explicitly.
