# PV1 batch fulfillment references

Implementation of [#37](https://github.com/cohesivesystems/cohesive-evals/issues/37)
under the [portable-validation protocol](../protocol.md). Maintainer-only;
do not include this directory, its history or successors in participant workspaces.

Both references compose G3 with standard DTO deserialization, a thin CLI adapter, typed batch service and queue
refactor. HTTP and batch share admission identities, capacity, results and a
single worker. Conventional still calls its domain services; Cohesive still calls
its compiled process. No domain implementation is copied into the adapter.

The queue returns a transport-neutral admission and signals completion through
a task. HTTP maps responses to its existing routes; batch waits directly without
HTTP loopback or a second polling implementation. A batch is sequential and
partially successful. The CLI reads/writes JSON lines; the typed service owns
execution without JSON, console or file handling. A read-only observer checks
all physical business rows, including unrelated sentinels.

See [BATCH.md](BATCH.md) for public behavior and [sdk-audit.md](sdk-audit.md) for
pinned capabilities and limitations. Only application input validation is handwritten and shared
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
checks all G0–G3 obligations. Each condition has nine buildable defects: mismatched batch serializer options,
missing required-constructor checks, stop
on invalid input, oversized-envelope execution, lost cross-entry replay, changed
quantity, rejection of valid domain input, bypassed quarantine and skipped
compensation. Detection requires the exact named behavioral assertion;
build/setup failures, timeouts, 5xx and unrelated failures earn no credit.

## Evidence

[evidence.json](evidence.json) retains source/report hashes and compact results;
the adjacent build manifests bind application inputs to outputs. Each condition
runs 17 business items through each transport, 32 decoding items per transport,
five envelope cases with next-line recovery and clean EOF, and five public smoke
checks.
The capacity check fills all 1,000 host-local identities, checks CLI admission
at capacity and retains replay in both directions.
The separate cumulative run retains 52 G0 HTTP checks, 180 invariant commands,
118 E1, 92 E2 and 95 E3 commands, plus visible examples and clean restart.
These counts describe checks, not independent experimental samples.

## Review and scope

Conventional idiomaticity review: standard DTO deserialization handles transport decoding;
input-only predicates are shared; domain services remain authoritative; DI owns
one queue; its existing worker owns fulfillment; task completion replaces polling.
The CLI is called directly from the entry point, not a second background service.
No library ban or forced duplication is imposed. Independent PR review is still
required before admitting this parent to an experiment.

Capacity is filled through HTTP and tested through CLI and HTTP. Replays cover
both directions in the same host. File publication, live migration, durable
recovery, concurrent intents and scored campaigns are outside this probe.
Full participant packaging/history-isolation admission remains separate.
