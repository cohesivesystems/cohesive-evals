# PV1 batch fulfillment references

Implementation of [#37](https://github.com/cohesivesystems/cohesive-evals/issues/37)
under the [portable-validation protocol](../protocol.md). Maintainer-only;
do not include this directory, its history or successors in participant workspaces.

Both references compose G3 with the same input decoder, file adapter and queue
refactor. HTTP and batch share admission identities, capacity, results and a
single worker. Conventional still calls its domain services; Cohesive still calls
its compiled process. No domain implementation is copied into the adapter.

The queue returns a transport-neutral admission and signals completion through
a task. HTTP maps responses to its existing routes; batch waits directly without
HTTP loopback or a second polling implementation. A batch is sequential and
partially successful, with one atomic output file. A read-only observer checks
all physical business rows, including unrelated sentinels.

See [BATCH.md](BATCH.md) for public behavior and [sdk-audit.md](sdk-audit.md) for
pinned capabilities and limitations. Input validation is handwritten and shared
in both conditions; this is not evidence of a model-driven portability advantage.
PV2 and any SDK upgrades remain separate.

## Run

Use unused absolute output directories and the pinned .NET/Docker environment:

```sh
python3 -B cross-layer/order-fulfillment/probes/portable-validation/pv1/build.py --output /tmp/pv1-build
python3 -B cross-layer/order-fulfillment/probes/portable-validation/pv1/verify.py --fixtures /tmp/pv1-build --output /tmp/pv1-verify
python3 -B cross-layer/order-fulfillment/evolution/verify.py --generation e3 --fixtures /tmp/pv1-build --output /tmp/pv1-retained
python3 -B cross-layer/order-fulfillment/probes/portable-validation/pv1/qualify.py --output /tmp/pv1-qualified
python3 -B -m unittest discover -s cross-layer/order-fulfillment/probes/portable-validation/pv1 -p test_harness.py
```

Known-good qualification runs the PV1 suite; the separate cumulative command
checks all G0–G3 obligations. Each condition has seven buildable defects: stop
on invalid input, oversized-envelope execution, lost cross-entry replay, changed
quantity, rejection of valid domain input, bypassed quarantine and skipped
compensation. Detection requires the exact named behavioral assertion;
build/setup failures, timeouts, 5xx and unrelated failures earn no credit.

## Evidence

[evidence.json](evidence.json) retains source/report hashes and compact results;
the adjacent build manifests bind application inputs to outputs. Each condition
runs 17 business items through each transport, 26 decoding items per transport,
five envelope cases, six operational-failure cases and five public smoke checks.
The capacity check fills all 1,000 host-local identities and retains batch replay.
The separate cumulative run retains 52 G0 HTTP checks, 180 invariant commands,
118 E1, 92 E2 and 95 E3 commands, plus visible examples and clean restart.
These counts describe checks, not independent experimental samples.

## Review and scope

Conventional idiomaticity review: input decoding lives at the transport boundary;
input-only predicates are shared; domain services remain authoritative; DI owns
one queue; `BackgroundService` owns work; task completion replaces adapter polling.
No library ban or forced duplication is imposed. Independent PR review is still
required before admitting this parent to an experiment.

Capacity is filled through HTTP after the startup batch, then batch identities
are replayed at capacity. The file interface cannot independently exercise a
batch arriving at capacity or replay HTTP-originated requests back into batch.
There is no live migration, durable recovery, concurrent-intent claim or scored
campaign. Full participant packaging/history-isolation admission remains separate.
