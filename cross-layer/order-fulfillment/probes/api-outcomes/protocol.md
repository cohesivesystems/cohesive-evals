# API outcome evolution and binding diagnostics

Specification for [#27](https://github.com/cohesivesystems/cohesive-evals/issues/27).
**AO1 = API Outcome probe, stage 1.** This is a development/qualification case,
not a scored campaign or a claim of Cohesive advantage. Implementation follows
in a separate PR after protocol review.

## Starting point and intended change

Both conditions start from the qualified typed-input stage in evals commit
`e9d79180bc230d4efa7c2cb3133bf6ad72cbd6f0` (PR #44). Keep its exact SDK package
closure, source `b0c442ab5645907968d6b605edeb1dd54550130d`, version
`0.1.0-eval.b0c442a`. SDK PR #569 subsequently merged as `ae546131`; do not rebuild
packages just to substitute the squash hash. Changed SDK/guidance is a new version.

Add `Archived` to the order lifecycle and one public submission rejection,
`OrderArchived`. Archived orders are supplied through matched seed data only;
there is no archive endpoint, new queue, or new authentication policy. Update
seed/schema validation and fresh-database status constraints in both conditions.
No live database migration or durable recovery is included. This leaves existing
state behavior intact and avoids changing the separate H/L hold/control tasks.

| Operation / state | Required outcome |
| --- | --- |
| Direct submit, Archived | HTTP 409, exactly `{ "code": "OrderArchived" }`; state remains Archived. |
| Direct submit, Draft / Submitted / Cancelled / missing | Retain 200 Submitted / 409 OrderNotDraft / 409 OrderCancelled / 404 respectively. |
| Cancel, Archived | HTTP 409 OrderNotCancellable; no state change. |
| Fulfillment, Archived, no reservation, eligible inventory | Admission 202; polling completion 200 with `{ "status": "Rejected", "outcome": "OrderArchived" }`. Release stock reserved by this attempt; create no reservation. |
| Batch fulfillment, same intent | Outer 200; the same per-item admission/completion. Valid siblings still execute. |
| Reads / restart | Existing read shapes remain unchanged; Archived is a new status value. Seeded state persists across clean restart. |

Preserve workflow precedence: input rejection before identity/capacity; then
OrderMissing, existing-reservation resolution, InventoryMissing, InvalidQuantity,
InventoryQuarantined, QuantityLimitExceeded, InsufficientStock, then submission.
An existing reservation on an Archived order yields ReservationConflict, including
matching SKU/quantity (successful existing-reservation replay requires Submitted).
An inventory rejection must not be replaced by OrderArchived. Only a successful
reserve followed by submission rejection requires compensation.

The new stage starts a fresh host/database. Within that host, unchanged requests
replay the original operation/result across single and batch entry points; changed
intent under the same request ID remains 409 RequestIdentityConflict. Retain
quantity limits, quarantine, cancellation, request-ID validation, array binding,
capacity and execution ownership. No state mutation may be used to manufacture
replay coverage. Run the independent PV2 + Required, PV1 and cumulative G0–G3 suites.

## Matched implementations and diagnostics

Cohesive uses its existing typed transitions/process and API bindings. Conventional
may use typed domain results, shared outcome maps, exhaustive registration checks,
OpenAPI tooling, analyzers and ordinary tests. Do not force repetitive switches
or forbid libraries to manufacture an advantage. Preserve ErrorResponse bodies
and standard ASP.NET binding in both conditions; a new Problem Details format is
not an acceptable substitute for the specified wire behavior.

The [SDK audit](sdk-audit.md) distinguishes implemented API checks from callback
semantics they cannot inspect. The new rejection must be exercised through direct
HTTP, process completion and batch results, not only an exported declaration.
An enum alias drift witness uses a CLR member such as `Archived` with wire alias
`OrderArchived`. The correct reference may use matching names; the defect must
show whether a branch/literal uses the wrong representation at the pinned revision.

Record earliest detection as compile/analyzer, registration, runtime HTTP, or
independent verifier. Capture diagnostics, locations and actionable context
verbatim with source/package hashes. **Early static rejection and running-defect
detection are separate evidence categories.** A build/startup failure earns early
credit only when its expected diagnostic and injected fault are verified; it is
never counted as a runtime assertion pass. Infrastructure, timeouts, absent
reports and unrelated failures remain unqualified. Unexpected execution 500 is
not a domain rejection. For invalid inputs, assert admission before polling work.

[The matrix](test-matrix.md) specifies witnesses and physical preservation checks.
Use the same task, budgets, feedback and tooling permissions in both conditions.
Report correctness, preservation, detection stage, edits, diagnostic usefulness
and preparation/execution effort separately. A source-only audit or successful
compile does not qualify the API behavior.

## Qualification and scope boundary

1. Materialize both correct references from the exact parent; qualify AO1 and all
   retained suites against an independent oracle. Shared source exceptions require
   reviewed exact hashes; schemas and verifier expectations cannot be exempted.
2. Add buildable behavioral mutants and separately identified static-negative
   fixtures. Each must fail its named assertion/diagnostic for the intended reason.
3. Publish source/build/package manifests, raw reports, the actual covered matrix
   and conventional idiomaticity review. Record unsupported detection as such.
4. Review before merging the implementation. Calibration/admission is separate.

If compatibility comparison is exercised, export only contracts derived from the
actual declarations and evaluate both directions under the pinned policy. Generic
string Code/Outcome fields may not expose the new vocabulary to the comparator;
Compatible is declaration-level evidence only, and Unknown is not success. Full
HTTP-surface migration belongs to #34. No automatic client/schema-generation or
exhaustive custom-body mapping advantage is assumed. Observed SDK friction may
motivate a separately pinned improvement; preserve the pre-improvement witness.
