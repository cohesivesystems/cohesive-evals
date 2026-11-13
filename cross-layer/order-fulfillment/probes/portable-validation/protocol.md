# Portable validation across entry points

Specification candidate for [#26](https://github.com/cohesivesystems/cohesive-evals/issues/26).
No implementation, qualified result or Cohesive advantage is asserted here.
This is a separate probe on G3; it does not add E4, change H/L, or expand the
[pilot matrix](../../evolution/test-matrix.md).

## Two changes

| Stage | Parent | Task | Retained obligations |
|---|---|---|---|
| PV1 | Gold G3 | Add a non-HTTP batch entry point for fulfillment. | B + E1 + E2 + E3, plus PV1 below. |
| PV2 | Qualified PV1 | Limit new fulfillment request IDs to 64 UTF-16 code units, on both entry points. | All PV1 behavior except the explicitly narrowed input domain. |

Use the same parents and public requirements in both conditions. PV2 is a new
host, not a live upgrade: admission identities are host-local and do not survive
restart. No historical requests are imported. Within each stage, replay retains
its original result. Pre-task failures and new regressions are recorded separately.

## Batch contract (PV1)

Add `--batch-input FILE --batch-output FILE` to the service host. Input is a
UTF-8 JSON array of at most 100 fulfillment objects. An empty array is valid.
The host starts its ordinary HTTP interface and uses the same local identity,
admission registry, capacity and worker for both entry points. The batch path
calls application services directly; it must not loop back through HTTP.
The host stays available for HTTP reads and replay after batch completion.
Readiness means HTTP is listening; the completed output file signals batch completion.
Both flags must be supplied together. Input and output must be distinct files,
and output must not already exist. Invalid configuration fails before admission;
write output through a temporary sibling and rename it only when complete.

Parse and validate the entire envelope before any item is admitted. Invalid JSON,
a non-array or more than 100 elements yields `{ "error": "InvalidBatch" }` and
no effects. A syntactically valid array containing an invalid item still processes
its valid siblings. An unreadable input or unwritable output is an operational
failure, never a successful empty batch or a behavioral rejection.

Process items in array order. Wait for each admitted item's terminal result before
starting the next item, so shared-stock examples have deterministic outcomes.
There is no batch transaction, rollback of successful siblings, batch identity or
automatic retry. Duplicates within a batch and across HTTP/batch use the same
request identity rules. Tests await batch completion before issuing HTTP mutations;
concurrent independent intents and crash recovery remain out of scope.

Write one completed JSON object `{ "items": [...] }` atomically after processing.
Each item has its zero-based `index` and `admission: {status, body}` using the HTTP
contract's status numbers and JSON bodies. An admitted item additionally has
`completion: {status, body}` matching the result endpoint. Admission failures omit
`completion`. Normalize unspecified 400/503 bodies to `null` in the batch output;
409 retains `RequestIdentityConflict`. An execution failure records completion
500/`ExecutionFailed`, starts no automatic retry, and does not erase earlier
results. Later items continue; qualification treats any execution failure in a
correct-reference scenario as a failure, not an expected domain outcome.

Transport-specific operation IDs and absolute URLs need not match between
isolated runs. Replay within one host must return the same admission and result.
The verifier compares normalized admissions/completions and all settled business
facts, not timing or generated identifiers across hosts.

## Parsing, validation and domain decisions

| Layer | Required behavior |
|---|---|
| Transport | Decode JSON and required fields/types. Wrong root/item shape, missing/null fields, blank identifiers, fractional/overflow quantities and wrong JSON types fail before admission. Required names are exactly `requestId`, `orderId`, `sku`, `quantity`; extra properties are ignored. Identifiers are JSON strings. Quantity is a JSON number with an exact signed 32-bit integer value: `1`, `1.0` and `1e0` are equivalent; numeric strings and booleans are rejected. Duplicate property names are invalid. Apply these rules to HTTP and batch alike, aligning both with the published G3 schemas. |
| Input-only | PV1 retains G3 rules. PV2 adds `requestId.Length <= 64` in UTF-16 code units. Case and exact text remain significant; do not trim, normalize or truncate. HTTP returns 400 and batch item admission returns 400/null. Validate before identity lookup or capacity checks. Invalid input consumes no identity and has no business effects. |
| State-dependent | Both paths execute the same G3 domain contract: order/reservation lookup, missing inventory, nonpositive quantity, quarantine, quantity limit, stock and lifecycle precedence. Nonpositive quantity remains admissible input with domain outcome `InvalidQuantity`. |

The new rule applies only to fulfillment request IDs, not order IDs, SKUs or
read routes. Nonblank IDs of length 1 and 64 remain valid; 65 fails in PV2.
A supplementary Unicode character counts as two UTF-16 code units. Test valid
Unicode strings; unpaired-surrogate decoding is outside this rule's witness set.
At capacity, a valid retained identity replays, a valid new identity returns 503,
and a new overlength identity returns 400. Identity conflicts retain 409.
The startup batch admits at most 100 items. Capacity witnesses fill the remaining
registry through HTTP after batch completion, then replay batch identities through
HTTP. Batch-at-capacity and HTTP-to-batch replay are not independently reachable
in this single-startup-file interface and are not claimed as tested.

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
| PV1-02 | Batch has malformed item, success and stock rejection; valid siblings finish in order. | Empty/100/101 elements, malformed envelope, non-object items, shared-stock ordering, invalid first/middle/last items. | Whole-batch rollback, stop on item rejection or partial execution before envelope validation → ordered results/preservation assertion. |
| PV1-03 | Duplicate item admits once; conflicting payload returns 409. | Replay batch result through HTTP, HTTP retry after changed stock/configuration, rejection replay, capacity and distinct request IDs for the same order. | Separate registries or replay bypass → admission identity/effect-count assertion. |
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
Before implementing, audit the pinned SDK for transport-independent input
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
3. Implement PV2 as deltas from the qualified PV1 parent; qualify stale-validator,
   ordering, identity and preservation defects in both conditions.
4. Retain source/package/build hashes, traces, named detection results and scope
   limits. A separate reviewed execution plan must set budgets, feedback and
   scheduling before calibration or scored runs.
