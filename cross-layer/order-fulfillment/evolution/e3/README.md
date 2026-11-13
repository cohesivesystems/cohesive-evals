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

The independent E3 model reuses E2's cancel/submit/configure assertions and adds
its own quarantine decision order, replay witnesses and physical-fact checks.
It never derives expectations from either implementation. For earlier profiles,
the harness asserts the new `quarantined` field is exactly false before adapting
their inventory views/facts to unchanged expectations. Missing, true or non-Boolean
values fail; the new field is never silently ignored.

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
credit. Known-good candidates run cumulative checks; mutants isolate E3. Earlier
mutation suites are not rerun in this milestone. [evidence.json](evidence.json)
retains compact results and source/build fingerprints; run directories contain
full seeds, traces, expected/observed facts and logs.

## Scope

Sequential settled behavior only: no concurrent quarantine/clear, crash recovery
or live migration. Release after quarantine changes during an in-flight operation
is not reachable in this public sequential model; the suite verifies reachable
compensation after clearing quarantine. Host-lifetime request history need not
survive restart. H/L references and campaign admission remain separate.

Keep references, hidden checks, mutation recipes and evidence outside participant
workspaces/history. Participant bundles receive only the active contracts and
visible examples with their prescribed starting source snapshot.
