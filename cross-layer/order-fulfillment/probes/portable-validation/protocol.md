# Validation reuse across single and batch API operations

Protocol for [#26](https://github.com/cohesivesystems/cohesive-evals/issues/26).
No implementation, qualified result or Cohesive advantage is asserted here.
This tests validation reuse across API operations, not transport portability.
A non-HTTP transport would be a separate probe. This is a separate probe on G3; it does not add E4, change H/L, or expand the
[pilot matrix](../../evolution/test-matrix.md).

## Two changes

| Stage | Parent | Task | Retained obligations |
|---|---|---|---|
| PV1 | Gold G3 | Add `POST /fulfillment/batch` for multiple fulfillment intents. | B + E1 + E2 + E3, plus PV1 below. |
| PV2 | Qualified PV1 | Limit new fulfillment request IDs to 64 UTF-16 code units, on both entry points. | All PV1 behavior except the explicitly narrowed input domain. |

Use the same parents and public requirements in both conditions. PV2 is a new
host, not a live upgrade: admission identities are host-local and do not survive
restart. No historical requests are imported. Within each stage, replay retains
its original result. Pre-task failures and new regressions are recorded separately.

## Batch contract (PV1)

`POST /fulfillment/batch` accepts an `application/json` array containing 0–100
fulfillment items. The existing `POST /fulfillment` remains the single-item API.
ASP.NET Core binds the whole request to a typed array using the configured JSON
options; a thin endpoint calls a typed batch application service. Each item uses the same queue,
request identities, capacity, host-provided caller identity and domain workflow
as a single-item request. No CLI, file protocol or JSON-RPC layer is added.

Malformed JSON, a non-array, any item decoding failure or more than 100 items
returns HTTP 400 without admission or effects, including for valid preceding
items. Oversized arrays return `{ "error": "InvalidBatch" }`; binding failures
use the framework's 400 response with unspecified body. Successfully decoded
null items or items with null/blank identifiers receive per-item 400 while valid
siblings continue. Empty arrays succeed with an empty result.

Valid envelopes return HTTP 200 with `{ "items": [...] }`, including partial or
all-item rejection. Items execute in array order; each admitted item settles
before the next starts. Each result has a zero-based `index` and
`admission: {status, body}` using the single-item API's status numbers/bodies.
Admitted items additionally have `completion: {status, body}` matching the result
endpoint. Admission failures omit `completion`; unspecified 400/503 bodies are
`null`, while 409 retains `RequestIdentityConflict`. An execution failure records
completion 500/`ExecutionFailed` and later items continue. Qualification treats an
unexpected execution failure as a failure, not a domain rejection.

There is no batch transaction, rollback of successful siblings, batch identity
or automatic retry. The batch service uses the host lifetime, so disconnecting
a caller does not cancel accepted work. This adds no crash-recovery guarantee.
Tests alternate settled single-item and batch requests; concurrent independent
intents remain outside this probe. HTTP/host failures are operational failures,
never successful empty batches or defect-detection credit.

Generated operation IDs and absolute URLs need not match between
isolated runs. Replay within one host must return the same admission and result.
The verifier compares normalized admissions/completions and all settled business
facts, not timing or generated identifiers across hosts.

## Parsing, validation and domain decisions

| Layer | Required behavior |
|---|---|
| Transport | The matched references use ASP.NET Core DTO binding for the single request and typed array binding for the batch, with the same configured HTTP JSON options. Keep .NET web defaults and `RespectRequiredConstructorParameters = true`. Malformed JSON, incompatible types, missing constructor fields and out-of-range quantities reject the entire request before any admission, including all siblings in a batch. JSON null array elements decode successfully and receive per-item input rejection. No custom token parser is needed. |
| Input-only | Reject null/blank identifiers after deserialization. PV1 retains G3 application rules. PV2 adds `requestId.Length <= 64` in UTF-16 code units. Case and exact text remain significant; do not trim, normalize or truncate. HTTP returns 400 and batch item admission returns 400/null. Validate before identity lookup or capacity checks. Invalid input consumes no identity and has no business effects. |
| State-dependent | Both paths execute the same G3 domain contract: order/reservation lookup, missing inventory, nonpositive quantity, quarantine, quantity limit, stock and lifecycle precedence. Nonpositive quantity remains admissible input with domain outcome `InvalidQuantity`. |

Equivalent idiomatic deserialization is allowed; grading checks behavior rather
than requiring these exact calls. The pinned serializer's accepted encodings are
part of the probe contract:
property matching is case-insensitive, unknown properties are ignored, and
repeated properties whose values deserialize use the last value. Quantity uses
the built-in `Int32` converter: `1` and the numeric string `"1"` are accepted;
`1.0`, `1e0`, their quoted forms, booleans, null and overflow are rejected.
Identifiers remain strings with case-sensitive values. Replay identity compares
the deserialized intent, so equivalent encodings must retain the same receipt.
Schemas describe the canonical typed form, not every accepted JSON spelling;
JSON Schema cannot distinguish integer-valued tokens `1` and `1.0`. Independent
wire examples/checks pin these differences rather than adding custom converters.
This revises the earlier custom-decoder requirements; original G0–G3 snapshots
are unchanged. Deserializer behavior is infrastructure, not portability credit.

The new rule applies only to fulfillment request IDs, not order IDs, SKUs or
read routes. Nonblank IDs of length 1 and 64 remain valid; 65 fails in PV2.
A supplementary Unicode character counts as two UTF-16 code units. Test valid
Unicode strings; unpaired-surrogate decoding is outside this rule's witness set.
At capacity, a valid retained identity replays, a valid new identity returns 503,
and a new overlength identity returns 400. Identity conflicts retain 409.
Single-item and batch calls share the host registry. Test replay in both
directions and fill the registry through single-item calls before checking batch
admission/replay at capacity.

Rejected input must not invoke domain work. A well-formed domain rejection is
admitted and retained, so replay after inventory/lifecycle changes remains stable.
There is no new public validation endpoint or requirement to use a particular
validator library, class layout or generator.

## Independent test matrix

All rows run in both conditions. PV2 runs PV1 with compliant IDs, plus its own
boundaries. All ordinary scenarios retain unrelated order/inventory sentinels.

| ID | Visible example | Maintainer extension | Defect and required witness |
|---|---|---|---|
| PV1-01 | One valid HTTP intent and the same batch intent in identical fresh worlds produce the same outcome/facts. | Every G3 completion outcome, including reservation match/conflict and competing rejection conditions. | Batch bypasses quarantine or lifecycle guard → exact outcome and physical-state assertion. |
| PV1-02 | Batch has a decoded invalid input, success and stock rejection; valid siblings finish in order. | Empty/100/101 elements, malformed requests followed by valid requests, incompatible item types reject the entire batch before effects or identity retention; shared-stock ordering and decoded invalid first/middle/last items. | Whole-batch rollback, stop on item rejection or partial execution before envelope validation → ordered results/preservation assertion. |
| PV1-03 | Duplicate item admits once; conflicting payload returns 409. | Replay in both directions, retries after changed stock/configuration, rejection replay, single-item and batch capacity, and distinct request IDs for the same order. | Separate registries or replay bypass → admission identity/effect-count assertion. |
| PV1-04 | Invalid input leaves stock and reservations unchanged. | Observe all physical rows, sentinels and retained outcomes after each settled scenario; run cumulative G0–G3 checks. | Validation after effects, extra reservation or unrelated update → preservation/retention assertion. |
| PV2-01 | IDs of length 64 pass, 65 fail on HTTP and batch. | Length 1, empty/blank, 63/64/65, supplementary Unicode boundaries, case differences and long order/SKU IDs unaffected. | HTTP-only or batch-only stale validator, off-by-one or scalar-count length → entry-point boundary assertion. |
| PV2-02 | Mixed valid/overlength batch preserves valid siblings; rejected ID consumes no capacity. | Invalid input combined with missing entity, quarantine, shortage and full admission registry; valid zero/negative quantity still reaches domain rejection. | Rule implemented as domain guard, truncated identity or capacity checked first → admission classification/no-effects assertion. |
| PV2-03 | Replay valid success and rejection across entry points after configuration changes. | Corrected short-ID submission after an invalid long-ID attempt; all retained PV1/G3 obligations. | Validator resets identity registry or drops retained fields → replay/retention assertion. |

The Python oracle owns expected decisions and physical observations. It must not
import production validators, generated model assertions or application schemas
as its source of expected outcomes. Shared verifier-owned fixture/default metadata
is allowed. Visible examples disclose semantics; hidden cases vary only data and
sequences. Defect qualification requires the named assertion, not just a nonzero
exit. Build errors, startup failures, timeouts and HTTP 5xx earn no defect-detection
credit. Classify application execution failures separately from harness/setup faults.

## Fair implementation and evidence

Conventional may share input validators, DTOs and domain/application services and
use idiomatic libraries. Cohesive may use supported input models/adapters, with
handwritten glue where needed. Do not force duplicate validation in conventional
or give Cohesive extra repair feedback. Both receive the same public cases, task
budget and dependency policy; any extra library must be pinned before execution.

The existing handwritten HTTP filter does not establish model-driven portability.
Before implementing, audit the pinned SDK for reusable input
validation and record which checks are generated, shared manually or unsupported.
If portability needs an SDK change, scope and qualify that upgrade separately;
do not silently switch packages in one condition. Keep runtime behavioral parity
separate from authoring convenience and diagnostic quality.

Record correctness and retained obligations first, then validation-rule edits,
changed files, duplicated semantic rules, authoring/repair effort, regressions and
diagnostic stage/usefulness. Initial line count is descriptive only. Reference
maintenance time is not agent effort. Match budgets/feedback before any scored
experiment; this specification sets no repetition count and authorizes no runs.

## Follow-through

1. [PV1 implementation issue #37](https://github.com/cohesivesystems/cohesive-evals/issues/37):
   audit the pinned SDK and freeze identical batch/input schemas and examples;
   implement matched PV1 references and the independent verifier in one child issue.
2. Qualify PV1 against running defects; review conventional idiomaticity, acceptance
   breadth and package/history isolation before calling it an admissible parent.
3. [PV2 implementation issue #40](https://github.com/cohesivesystems/cohesive-evals/issues/40):
   implement PV2 as deltas from the qualified PV1 parent; qualify stale-validator,
   ordering, identity and preservation defects in both conditions.
4. Retain source/package/build hashes, traces, named detection results and scope
   limits. A separate reviewed execution plan must set budgets, feedback and
   scheduling before calibration or scored runs.
