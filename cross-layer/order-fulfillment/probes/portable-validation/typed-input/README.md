# Model-authored request ID validation

Implements [#42](https://github.com/cohesivesystems/cohesive-evals/issues/42) as a
separate stage after qualified PV2. PV2 and the old-package audit PR #43 remain
unchanged. Maintainer-only references and hidden checks must stay outside
participant workspaces.

The public contract is unchanged: [PV2 request IDs](../pv2/REQUEST-ID.md).
The conventional reference is byte-identical to PV2. Cohesive declares
`[property: MaxLength(64)]` on `FulfillmentRequest.RequestId`, builds its input
shape once with `UseDataAnnotations()`, and calls `ValidateInput` through the
existing shared `FulfillmentInput.IsValid` admission path. No handwritten length
predicate remains on that side. Nonblank checks remain shared application policy.

`OperationQueue.Submit` validates before identity lookup, retention and capacity.
Single and batch endpoints share that path; standard array binding, per-item
domain outcomes and host-owned execution are preserved. Quantity remains a domain
rule, not an input-only constraint. No new endpoint or error format is introduced.

## SDK and consumer boundary

Cohesive SDK source: `5fd1f0df8c9b1438b8be3300cb2772c0fa27e3c2` (merged SDK PR #548).
Package version: `0.1.0-eval.5fd1f0d`. The dependency manifest pins all vendored
packages; the source delta includes the updated lockfile. New packages are built
from an immutable Git archive, not the maintainer's working tree:

```sh
python3.13 cross-layer/order-fulfillment/packaging/build-packages.py /path/to/cohesive \
  --revision 5fd1f0df8c9b1438b8be3300cb2772c0fa27e3c2 --version 0.1.0-eval.5fd1f0d \
  --output cross-layer/order-fulfillment/probes/portable-validation/typed-input/packages
```

This JIT-hosted application receives a CLR DTO and has no portable value at queue
admission, so it uses the typed SDK convenience overload. This includes projection
cost; it is not zero-allocation validation. No trimming/NativeAOT support is claimed
and no analyzer warnings are suppressed. A consumer already holding an
`ObservationValue` should validate that value directly against the prebuilt shape.
Creating it manually just to bypass the typed overload's annotations would not
remove the projection requirements.

## Qualification

Unchanged independent PV2 checks cover UTF-16 boundaries, null/nonblank inputs,
whole-batch decoding failures versus item outcomes, identity/capacity precedence,
replay and physical preservation. Retained PV1 and cumulative G0–G3 run separately.
The shared qualifier gives credit only for the named behavioral failure; build,
startup, transport and unrelated assertion failures do not qualify a defect.

Conventional retains PV2's nine defects. Cohesive has eleven: declaration removal,
63/65 limits, disabled projection, bypassed validation, stale validated input,
single/batch truncation, capacity-before-validation, identity trimming and reset.
Removing or weakening the declaration must change observable admission, proving
that a leftover handwritten check does not hide absent model enforcement.

```sh
BASE=cross-layer/order-fulfillment/probes/portable-validation
python3 -B "$BASE/typed-input/build.py" --output /tmp/typed-input-build
python3 -B "$BASE/typed-input/verify.py" --fixtures /tmp/typed-input-build --output /tmp/typed-input-pv2
python3 -B "$BASE/pv1/verify.py" --fixtures /tmp/typed-input-build --output /tmp/typed-input-pv1
python3 -B cross-layer/order-fulfillment/evolution/verify.py --generation e3 --fixtures /tmp/typed-input-build --contract-sources "$BASE/typed-input/contract-sources.json" --output /tmp/typed-input-g0-g3
python3 -B "$BASE/typed-input/qualify.py" --output /tmp/typed-input-qualified
python3 -B -m unittest discover -s "$BASE/typed-input" -p test_harness.py
```

This qualifies rule-driven admission in the upgraded SDK. It does not isolate the
length feature from other SDK changes, measure development effectiveness or
performance, prove arbitrary validation portability, or admit a scored campaign.
No live migration or durable-recovery scope. The independent verifier remains
Python and does not derive expected results from Cohesive declarations.

The retained evolution harness normally requires byte-identical DTO source.
`--contract-sources` permits only the two reviewed, hash-pinned `Contracts.cs`
versions (the sole difference is the attribute). Missing/wrong pins and drift in
other shared artifacts still fail setup. All wire schemas and behavioral checks
remain independent and unchanged; the report records the source pins.

Application review: only `Contracts.cs` and `FulfillmentInput.cs` change on the
Cohesive side (plus SDK references and lockfile). Each condition has one authored
length rule; conventional remains a direct shared predicate, Cohesive lowers an
attribute into a reusable shape. Both return the same public 400 outcome, so this
probe does not measure richer SDK diagnostics. No line-count or speed advantage
is inferred from those differences.

## Recorded result (2026-11-15)

Both references pass PV2, retained PV1 and cumulative G0–G3. All 20 deliberately
broken applications fail their named assertions (9 conventional, 11 Cohesive);
the two known-good controls pass. Harness tests: 3 typed-input, 2 PV2, 7 shared/PV1,
6 evolution. [Evidence index](evidence.json) hashes the retained reports, build
manifests, source delta, packages and shared verifier inputs. These counts are
checks, not independent experimental samples.
