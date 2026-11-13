# E3 quarantine references and qualification

Matched G3 implementations for [#25](https://github.com/cohesivesystems/cohesive-evals/issues/25).
The [E3 supplement](../contracts/supplements/E3.md) defines the public contract.
G0/G1/G2 applications remain unchanged; `build.py` applies exact-parent source
deltas to G2 and emits the active G3 contracts.

Conventional uses a domain guard, typed outcome projection and Npgsql updates.
Cohesive uses a quarantine transition and native API bindings; its fulfillment
process propagates the new typed outcome without a new rejection branch.
Quarantine and clear change only the Boolean setting. Invalid quantity precedes
quarantine; quarantine precedes limit, shortage and lifecycle restrictions.

## Run

From the repository root, with .NET 10, Git and Docker available:

```sh
python3 -B cross-layer/order-fulfillment/evolution/e3/build.py --output /tmp/e3-reference
python3 -B cross-layer/order-fulfillment/evolution/verify.py --generation e3 --fixtures /tmp/e3-reference --output /tmp/e3-verification
python3 -B cross-layer/order-fulfillment/evolution/qualify.py --generation e3 --output /tmp/e3-qualification
python3 -B -m unittest discover -s cross-layer/order-fulfillment/evolution -p 'test_harness.py'
```

Use unused output directories. PostgreSQL image `postgres:17.10-alpine3.24` must
already be available locally. The shared harness owns disposable databases,
locked builds, manifests and failure classification.

## Coverage

Each condition runs 52 G0 HTTP checks, 180 G0 invariant commands, 118 E1 commands,
92 E2 commands and 95 E3 commands, plus five visible examples for each evolution.
E3 includes 60 mixed operations (seed 163), explicit precedence collisions,
matching/conflicting reservations, replay across quarantine changes, preservation
of stock/limits, direct submission independence, cancellation interactions and
clean restart persistence of both Boolean values.

The independent E3 model inherits E2's initialization, trace writer, decision
chain, polling, replay and existing command assertions. It declares its fixture,
request/trace prefix and obligation IDs, then overrides one inventory-rejection
hook to insert quarantine before the inherited limit/stock checks. E3 owns only
its new command and scenario sequences. No expectations come from either app.

Each generation's `profile.json` declares the inventory fields it adds, their
physical columns and neutral values. The harness selects columns and projects
HTTP/physical observations generically. Before hiding a newer field from older
checks (including G0), it verifies presence, exact JSON type and neutral value.
There are no E3 branches or hard-coded field defaults in the shared harness.

Eight buildable defects per condition must fail the named assertion:

| Defect | Obligation | Assertion |
|---|---|---|
| Wrong default | E3-01 | seed/default/read |
| Quarantine resets limit | E3-01 | quarantine response |
| Clear does not clear | E3-01 | quarantine response |
| Missing quarantine guard | E3-02 | quarantine enforcement |
| Limit before quarantine | E3-02 | quarantine before limit |
| Quarantine before invalid quantity | E3-02 | invalid quantity before quarantine |
| Skipped compensation | E3-02 | cancelled compensation (physical facts) |
| Lost replay | E3-03 | retained admission |

Build/setup failures, HTTP 5xx, timeouts and unrelated assertions earn no detection
credit. Known-good candidates run cumulative checks; mutants isolate E3. The E2 mutation suite is also rerun after the shared check refactor; the G0/E1
mutation suites are not rerun in this revision. [evidence.json](evidence.json)
retains compact results and source/build fingerprints; run directories contain
full seeds, traces, expected/observed facts and logs.

## SDK follow-up

Inventory reads and both command responses share one `ToInventoryView` mapper.
The dummy rejection handler remains necessary for the pinned SDK: only
`OnRejected` completes the typed binding, even for a Set/Return transition.
[Cohesive #513](https://github.com/cohesivesystems/cohesive/issues/513) tracks
completion without a dummy handler, with admission/domain rejection and
concurrency contracts preserved. An SDK fix and separately qualified package
upgrade are required before removing it from this reference.

## Scope

Sequential settled behavior only: no concurrent quarantine/clear, crash recovery
or live migration. Release after quarantine changes during an in-flight operation
is not reachable in this public sequential model; the suite verifies reachable
compensation after clearing quarantine. Host-lifetime request history need not
survive restart. H/L references and campaign admission remain separate.

Keep references, hidden checks, mutation recipes and evidence outside participant
workspaces/history. Participant bundles receive only the active contracts and
visible examples with their prescribed starting source snapshot.
