# E2 cancellation references and qualification

Matched G2 implementations for [#24](https://github.com/cohesivesystems/cohesive-evals/issues/24),
following [E1](../e1/README.md). The [E2 supplement](../contracts/supplements/E2.md)
is the public contract. G0 and G1 remain unchanged.

`build.py` composes G1 with reviewable unified source deltas and the active G2
contract bundle. Each delta records exact before/after file hashes; parent drift,
unlisted files and unexpected outputs fail before writing the snapshot. Full
standalone C# sources are materialized for builds and participant packaging. Conventional uses a domain rule within an explicit Npgsql
transaction; Cohesive uses a native order transition and API binding. Both persist
Cancelled, permit repeated cancellation, reject cancellation of Submitted orders,
and enforce cancellation at the lifecycle step after existing inventory rules.

## Run

From the repository root, with .NET 10 and Docker available:

```sh
python3 -B cross-layer/order-fulfillment/evolution/e2/build.py --output /tmp/e2-reference
python3 -B cross-layer/order-fulfillment/evolution/verify.py --generation e2 --fixtures /tmp/e2-reference --output /tmp/e2-verification
python3 -B cross-layer/order-fulfillment/evolution/qualify.py --generation e2 --output /tmp/e2-qualification
python3 -B -m unittest discover -s cross-layer/order-fulfillment/evolution/e2 -p 'test_*.py'
```

Output directories must be unused. PostgreSQL image `postgres:17.10-alpine3.24`
must already be available locally. Containers are disposable and removed after
execution. Builds use locked dependencies and source/package/output manifests.

## Coverage

One shared verifier/qualifier selects generation profiles. G2 activates the
unchanged G0/E1 expectations plus E2 in the same host: 52 G0 HTTP checks, 180 G0
invariant commands, five visible E1 examples and 118 E1 commands per condition,
then five visible E2 examples and 92 E2 model commands,
including 60 mixed operations with fixed seed 162 and a clean restart.

The independent Python model checks cancellation, direct submission, fulfillment,
configuration and request replay. Read-only physical observations compare all
orders, inventory settings and reservation rows in the test world after each
command. Targeted witnesses cover ignored bodies, missing orders, seeded Cancelled
orders, idempotency, rejection precedence, compensation, summary/details views,
replay after cancellation and unrelated-state preservation.

Eight buildable defects per condition must fail their exact named assertion:

| Defect | Obligation | Required assertion |
|---|---|---|
| Cancel Submitted | E2-01 | cancellation state table |
| Reject repeated cancellation | E2-01 | idempotent cancellation |
| Wrong direct-submit code | E2-02 | direct submit outcome |
| Wrong stock-outcome projection | E2-02 | limit before cancellation |
| Generic fulfillment rejection | E2-02 | cancelled fulfillment |
| Check cancellation before inventory | E2-02 | missing inventory before cancellation |
| Skip compensation | E2-02 | cancelled fulfillment (physical facts) |
| Lose retained admission | E2-03 | retained admission |

Known-good qualification runs the cumulative checks; mutants run only E2 checks
so earlier suites cannot accidentally earn detection credit. Build/setup errors,
HTTP 5xx, timeouts and unrelated assertions do not qualify detection. The E1 mutation suite is separately rerun through the shared harness as a
regression check; G0 mutation qualification remains separate. Detailed traces and logs stay in run
outputs; [evidence.json](evidence.json) retains compact results and build provenance.

## Review changes

Submit and cancel both use the simple native rejection callback and return the
application's `ErrorResponse` directly. No problem-response filter or code-prefix
slicing remains in G2. The direct-submit defect targets the explicit outcome map.

Conventional orchestration uses typed stock/submission projection helpers.
Cohesive transition results carry their typed fulfillment projection; the process
propagates it after the appropriate reserve/compensate step. Adding a rejection
updates its decision/projection, without adding another process branch. The pinned
syntax-only process cannot call arbitrary C# mapping helpers. This change does not
add custom-body support to the SDK's classified rejection API.

The generation-local verifier/qualifier files are compatibility entry points;
shared execution lives in `../harness.py`. Check modules and mutation definitions
remain generation-specific and independent of reference mappings.

## Pinned SDK observation

With Cohesive `0.1.0-eval.b0af008`, declaring `SubmissionOutcome.Cancelled` with
JSON alias `OrderCancelled` let direct HTTP submission return the expected code,
but the process comparison selected generic `OrderRejected`. The pinned process
generator emits enum constants using `enumMember.Name`
(`ProcessComputationSourceGenerator.cs:6287` at source revision
`b0af008d85871ad8866d7d4311707ecd926529de`). The final reference names the outcome
`OrderCancelled` in both conditions, matching its serialized value. The new
cancellation enum also explicitly declares its string serializer.

These are reference-authoring findings, not evidence that the SDK diagnoses such
mismatches. Retain this example for the [API diagnostics probe #27](https://github.com/cohesivesystems/cohesive-evals/issues/27).

## Limits and isolation

This tests settled sequential behavior, not concurrent cancellation or crash
recovery. Clean restart preserves business facts; host-lifetime request history
need not survive. No live schema migration is provided. E3, H/L and campaign
admission remain separate. Keep this directory, reference answers, hidden checks,
mutation recipes and evidence outside participant workspaces and their history.
