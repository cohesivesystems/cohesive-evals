# E1 quantity-limit references and qualification

Maintainer-only G1 implementations for [#21](https://github.com/cohesivesystems/cohesive-evals/issues/21),
under [#8](https://github.com/cohesivesystems/cohesive-evals/issues/8).
The [E1 supplement](../contracts/supplements/E1.md) defines the public behavior.
G0 participant fixtures remain unchanged. Do not distribute this directory,
reference answers, mutation recipes or evidence in participant workspaces/history.

## Implementation

`build.py` copies G0 into an isolated directory, overlays the complete committed
C# files in `reference/`, and emits the active G1 contracts and visible examples.
It does not patch source strings. Both conditions receive identical transport
parsing, contracts, schemas and examples.

The conventional application uses a domain guard and explicit Npgsql reads/updates.
The Cohesive application uses an inventory transition, native entity API binding,
persisted shape mapping and process outcome mapping. Both persist `maxPerOrder`,
default it to int.MaxValue, check it before stock shortage, and retain original
host-lifetime admissions/results after configuration changes. Configuration changes
only the limit; compensation does not apply the limit.

## Run

From the repository root, with .NET 10 and Docker available:

```sh
python3 -B cross-layer/order-fulfillment/evolution/e1/build.py --output /tmp/e1-reference
python3 -B cross-layer/order-fulfillment/evolution/e1/verify.py --fixtures /tmp/e1-reference --output /tmp/e1-verification
python3 -B cross-layer/order-fulfillment/evolution/e1/qualify.py --output /tmp/e1-qualification
python3 -B -m unittest discover -s cross-layer/order-fulfillment/evolution/e1 -p 'test_*.py'
```

Use unused output directories. PostgreSQL image `postgres:17.10-alpine3.24` must
already be available locally. Each run creates disposable databases and removes
its container. Qualification rebuilds each candidate with locked dependencies;
source/package and executable hashes are checked before and after execution.
The reusable build/provenance helpers come from `durability/build.py`; these
applications do not use the durable runtime.

## Checks and evidence

The verifier and qualifier now delegate to the shared `../harness.py`; the old
commands remain valid. `../verify.py --generation e1` and
`../qualify.py --generation e1` select the same G1 profile. Generation-specific
expectations and mutation definitions remain separate.

`visible_checks.py` supplies five ordinary G1 examples. `checks.py` is an independent
Python model of the published decision order, with read-only SQL observation of
all business facts in each test world. Its 118 recorded commands include parsing,
integer boundaries, precedence collisions, reservation match/conflict, success and
rejection replay, configuration preservation, 60 generated mixed commands (seed
161), and clean restart persistence. It checks physical reservations and untouched
sentinels, not only HTTP responses. Expected behavior does not come from either
application or the contract generator.

The paired verifier also retains all 52 G0 HTTP observations and 180 invariant
commands per condition, adapting only the newly required inventory response field.
It compares normalized results and final business facts between conditions.
Detailed seeds, command traces, expected/observed facts, host/build logs and build
manifests remain in the output directories. [evidence.json](evidence.json) retains
compact results and fingerprints for the checked run.

Qualification requires both correct references to pass and all seven defects per
condition to build and fail the exact named behavioral assertion:

| Defect | Obligation | Required assertion |
|---|---|---|
| Restrictive seed default | E1-01 | seed/default/read |
| Configuration changes stock | E1-01 | integral input |
| Missing limit guard | E1-02 | limit enforcement |
| Exclusive boundary | E1-02 | inclusive boundary |
| Shortage precedes limit | E1-02 | limit before shortage |
| Skipped compensation | E1-02 | lifecycle rejection preserves stock |
| Lost replay admission | E1-03 | retained admission |

Build/setup failures, HTTP 5xx, timeouts, missing reports and unrelated assertions
never earn detection credit. Harness tests exercise this classification and require
exactly one mutation anchor. A failed qualification run produces no success report.

## Scope

This qualifies sequential, settled, host-lifetime behavior. Clean restart preserves
business facts; admission history need not survive. There is no live schema migration.
The reachable lifecycle-rejection checks verify compensation effects, but cannot
exercise release after an interleaved limit reduction through this sequential public
API. They do not establish concurrency or crash-recovery correctness. E2/E3, H/L,
acceptance-breadth review and campaign admission remain separate work.
