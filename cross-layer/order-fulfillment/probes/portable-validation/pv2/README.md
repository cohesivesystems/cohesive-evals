# PV2 request ID length limit

Implements [#40](https://github.com/cohesivesystems/cohesive-evals/issues/40) under
[the PV2 protocol](../protocol.md), from qualified PV1 (`1494986`, PR #39).
Maintainer-only: exclude this directory and its history from participant workspaces.

Both conditions add `request.RequestId.Length <= 64` to the existing shared
application predicate. The checked patch changes only `FulfillmentInput.cs`.
Standard binding, queue ownership and domain implementations are unchanged.
This is manual validation reuse in both conditions, not evidence of a generated
Cohesive validation advantage. SDK packages remain pinned.

[REQUEST-ID.md](REQUEST-ID.md) is the public contract. A new host starts each
stage; this probe does not migrate retained identities from PV1.

## Checks

The verifier reuses PV1's HTTP host and physical observer. Independent expectations
cover ASCII and supplementary Unicode boundaries, combining characters, exact
identity text, long order/SKU IDs, domain precedence, mixed outcomes, replay after
configuration changes and invalid input at the 1,000-identity capacity limit.
Separate retained suites run all PV1 and G0–G3 checks.

The shared PV1 qualification runner accepts a builder and defect catalog; its
existing CLI defaults are unchanged. Nine defects per condition cover stale
validation, rejecting 64, accepting 65, counting graphemes, single/batch truncation,
capacity before validation, trimming identities and resetting the registry.
Only the specified behavioral assertion earns detection credit. Build, setup,
timeout and execution failures remain unqualified.

```sh
python3 -B cross-layer/order-fulfillment/probes/portable-validation/pv2/build.py --output /tmp/pv2-build
python3 -B cross-layer/order-fulfillment/probes/portable-validation/pv2/verify.py --fixtures /tmp/pv2-build --output /tmp/pv2-verify
python3 -B cross-layer/order-fulfillment/probes/portable-validation/pv1/verify.py --fixtures /tmp/pv2-build --output /tmp/pv2-retained-pv1
python3 -B cross-layer/order-fulfillment/evolution/verify.py --generation e3 --fixtures /tmp/pv2-build --output /tmp/pv2-retained-e3
python3 -B cross-layer/order-fulfillment/probes/portable-validation/pv2/qualify.py --output /tmp/pv2-qualified
python3 -B -m unittest discover -s cross-layer/order-fulfillment/probes/portable-validation/pv2 -p test_harness.py
```

Both references pass PV2, retained PV1 and cumulative G0–G3 checks. All 18
deliberate defects fail their named assertions; ten harness tests pass.

[evidence.json](evidence.json) records reports and source hashes; adjacent manifests
bind tested application inputs to outputs. Counts describe checks, not independent
experimental samples. Concurrent intents, crash recovery, live migration and
scored campaigns remain separate.
