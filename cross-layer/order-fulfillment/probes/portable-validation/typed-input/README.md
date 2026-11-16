# Model-authored request ID validation

Implements [#42](https://github.com/cohesivesystems/cohesive-evals/issues/42) as a
separate stage after qualified PV2. PV2 and the old-package audit PR #43 remain
unchanged. Maintainer-only references and hidden checks must stay outside
participant workspaces.

The public contract is unchanged: [PV2 request IDs](../pv2/REQUEST-ID.md).
The conventional reference is byte-identical to PV2. Cohesive declares
`[Required, MaxLength(64)]` on the request ID and `[Required]` on order ID and SKU.
It registers `AddCohesiveInputValidation(options => options.UseDataAnnotations()
.For<FulfillmentRequest>())` once at startup and injects `IInputValidator` into
`OperationQueue`. Admission calls `inputs.Validate(request).IsValid`; the dedicated
`FulfillmentInput` wrapper and handwritten nonblank/length predicates are removed.

The registered contract is prepared at startup and shared by single/batch calls.
Validation still precedes identity lookup, retention and capacity. Standard array
binding, per-item domain outcomes and host-owned execution are preserved. Quantity
remains a domain rule. No endpoint or public error format changes.

## SDK and consumer boundary

Cohesive SDK source: `b0c442ab5645907968d6b605edeb1dd54550130d` ([SDK PR #569](https://github.com/cohesivesystems/cohesive/pull/569), pending review; builds on merged #548).
Package version: `0.1.0-eval.b0c442a`. The dependency manifest pins all vendored
packages; the source delta includes the updated lockfile. New packages are built
from an immutable Git archive, not the maintainer's working tree:

```sh
python3.13 cross-layer/order-fulfillment/packaging/build-packages.py /path/to/cohesive \
  --revision b0c442ab5645907968d6b605edeb1dd54550130d --version 0.1.0-eval.b0c442a \
  --output cross-layer/order-fulfillment/probes/portable-validation/typed-input/packages
```

This JIT-hosted application receives a CLR DTO and has no portable value at queue
admission, so it uses the shared SDK validator with typed projection. This includes projection
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

Conventional retains PV2's nine defects. Cohesive has fourteen: declaration removal,
63/65 limits, disabled projection, bypassed validation, stale validated input,
single/batch truncation, capacity-before-validation, identity trimming/reset, and removal of each Required rule.
Removing or weakening the declaration must change observable admission, proving
that a leftover handwritten check does not hide absent model enforcement.

```sh
BASE=cross-layer/order-fulfillment/probes/portable-validation
python3 -B "$BASE/typed-input/build.py" --output /tmp/typed-input-build
python3 -B "$BASE/typed-input/verify.py" --fixtures /tmp/typed-input-build --output /tmp/typed-input-pv2
python3 -B "$BASE/pv1/verify.py" --fixtures /tmp/typed-input-build --output /tmp/typed-input-pv1
python3 -B cross-layer/order-fulfillment/evolution/verify.py --generation e3 --fixtures /tmp/typed-input-build --shared-source-pins "$BASE/typed-input/shared-source-pins.json" --output /tmp/typed-input-g0-g3
python3 -B "$BASE/typed-input/qualify.py" --output /tmp/typed-input-qualified
python3 -B -m unittest discover -s "$BASE/typed-input" -p test_harness.py
```

This qualifies rule-driven admission in the upgraded SDK. It does not isolate the
length feature from other SDK changes, measure development effectiveness or
performance, prove arbitrary validation portability, or admit a scored campaign.
No live migration or durable-recovery scope. The independent verifier remains
Python and does not derive expected results from Cohesive declarations.

The retained evolution harness normally requires identical shared source files.
`--shared-source-pins` permits only the reviewed hashes for DTO declarations,
startup registration and queue injection. Other shared source drift still fails;
schema and verifier files cannot receive exceptions. Behavioral expectations stay
independent, and the report records the exact pins.

Application review: record declarations, registration and queue validation change;
`FulfillmentInput.cs` is deleted on the Cohesive side. Each condition has one
source of input rules. The conventional predicate remains idiomatic and unchanged.
Both conditions expose the same 400 response, so this probe does not measure
richer diagnostics, initial line-count advantage or execution performance.

Required-policy migration adds 30 independent cases per condition (three fields,
five invalid values, both entry points), with valid retries and physical
preservation checks. Values include empty, null, ASCII and Unicode whitespace.
The inherited PV2/PV1/G0–G3 expectations remain unchanged.

## Recorded result (2026-11-15)

Both references pass PV2 plus 30 nonblank-policy cases each, retained PV1 and
cumulative G0–G3. All 23 deliberately broken applications fail named assertions
(9 conventional, 14 Cohesive); the two known-good controls pass. Harness tests:
4 typed-input, 2 PV2, 7 shared/PV1, 6 evolution. [Evidence index](evidence.json)
hashes reports, build manifests, source deltas, packages and shared verifier inputs.
Counts describe checks, not independent experimental samples. SDK #569 and eval
#44 remain reviewable changes; the SDK feature branch is pinned explicitly.
