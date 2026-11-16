# AO1: API outcome evolution

Implementation of [#46](https://github.com/cohesivesystems/cohesive-evals/issues/46),
following the approved [protocol](protocol.md) and [matrix](test-matrix.md).
Maintainer-only references and checks; do not expose them to participants.

Both conditions accept seeded `Archived` orders. Direct submission returns
409 `{"code":"OrderArchived"}`; fulfillment and batch completion return
200 `{"status":"Rejected","outcome":"OrderArchived"}` after releasing stock.
No reservation is created. Cancellation, inventory precedence, replay and existing
outcomes remain unchanged. No archive endpoint, SDK upgrade or migration.

The conventional change extends its enum, domain switch and existing typed outcome
maps. Cohesive adds one transition guard and its outcome values/direct API mapping;
the process already carries the typed fulfillment outcome and needs no new branch.
Both update seed validation and public schemas. PostgreSQL status constraints are
explicit SQL in conventional and inferred from the enum mapping in Cohesive.
Exact parent/output hashes protect the small source patches. Shared source pins
cover reviewed DTO differences; schema equality remains mandatory.

[AO1 measurements](MEASUREMENTS.md) compare application change counts, semantic
edit sites and paired fault detection stages; development effort remains unmeasured.

## Results

- Both references pass AO1, retained PV2 + Required, PV1 and G0–G3.
- 29 behavioral defects fail their named checks: 15 conventional, 14 Cohesive.
  Both known-good controls pass. A 500, timeout or unrelated failure earns no credit.
- Six separate static-negative cases: three compiler errors (two conventional,
  one Cohesive) and three Cohesive registration errors. Known-good startup controls
  pass. These are capability witnesses, not equal-sized treatment samples.
- Four enum-name/alias runs reproduce a pinned SDK limitation, described below.
- Original qualification: 25 harness tests pass (6 AO1 and 19 retained tests).
  The measurement follow-up adds 3 passing tests for evidence integrity and pairing.

[Evidence index](evidence.json) hashes reports, build/source inputs and the compressed
raw logs/traces. Counts are checks, not independent samples. This is maintainer
preparation, with no matched development-time measurement, performance claim,
Cohesive advantage claim or scored-campaign admission.

## What the diagnostic evidence shows

Wrong argument types fail compilation in both stacks. Cohesive also rejects a
wrong canonical transition reference, mismatched declared response, and missing
input binding at registration. Diagnostics retain their exact text and location;
the response-contract diagnostic lists several possible mismatches, while the
transition/input diagnostics are more specific.

Well-typed wrong IDs, wrong input values and stale custom error-body maps start
successfully in both conditions and require independent runtime checks. The
conventional endpoints use ordinary C# results and have no separate declaration
consistency check to exercise. Libraries/analyzers remain permitted; no inference
about their best achievable diagnostics follows from this reference.

The alias witness first introduces an explicit outcome comparison with matching
CLR/wire names, then renames the member to `Archived` with JSON name `OrderArchived`.
Both controls and the conventional alias variant pass. The Cohesive alias variant
builds and starts but returns `OrderRejected`: its generated comparison uses the
CLR name, while the transition supplies the wire name. AO1-02 catches this.
This is a separately authored comparison witness, **not a defect in the correct
reference**, which passes through the typed outcome instead. Preserve this pin
before any SDK improvement. Contract compatibility/export was not exercised.

## Reproduce

Use fresh output directories. The existing Docker PostgreSQL image and pinned .NET
SDK/packages are required. All scripts operate on materialized copies.

```sh
AO=cross-layer/order-fulfillment/probes/api-outcomes
PV=cross-layer/order-fulfillment/probes/portable-validation
python3 -B "$AO/build.py" --output /tmp/ao1-build
python3 -B "$AO/verify.py" --fixtures /tmp/ao1-build --output /tmp/ao1-verify
python3 -B "$AO/qualify.py" --output /tmp/ao1-qualified
python3 -B "$AO/diagnostics.py" --output /tmp/ao1-diagnostics
python3 -B "$AO/alias_witness.py" --output /tmp/ao1-alias
python3 -B "$PV/typed-input/verify.py" --fixtures /tmp/ao1-build --output /tmp/ao1-typed
python3 -B "$PV/pv1/verify.py" --fixtures /tmp/ao1-build --output /tmp/ao1-pv1
python3 -B cross-layer/order-fulfillment/evolution/verify.py --generation e3 \
  --fixtures /tmp/ao1-build --shared-source-pins "$AO/shared-source-pins.json" --output /tmp/ao1-evolution
python3 -B -m unittest discover -s "$AO" -p 'test_*.py'
```

The verifier reuses the existing PostgreSQL/host lifecycle and read-only physical
observer. AO1 expectations are independently authored and do not import application
schemas or SDK declarations. Qualification reuses the existing named-assertion
runner. Static negatives and alias comparisons have separate reports.
