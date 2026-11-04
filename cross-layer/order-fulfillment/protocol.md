# Order fulfillment pilot protocol v0.1

Status: protocol defined on 2026-11-02; **not frozen for execution**. Fixture,
oracle, control-matching review, and execution-manifest admission remain open.
This protocol does not amend the frozen Relations protocol.

## Research question and decision boundary

Does a pinned coding agent preserve interacting behavioral obligations better
with Cohesive's persisted semantics than with an idiomatic conventional C#
implementation, and does that difference change after accumulated evolution?

The selected case is a one-item order-fulfillment service. The high-coupling
probe adds an order hold; the low-coupling probe adds an informational review
marker. Both probes run against fresh and aged versions of the same application.
They branch independently and never become prerequisites for the evolution chain.

This is a descriptive pilot of one manually authored case, two probe families,
and three repetitions. It can qualify the experiment, expose failure mechanisms,
and motivate a larger study. It cannot establish P1 coupling gradients, P2
long-term cost crossover, P3 superadditivity, or statistical equivalence. The
control differs in semantic responsibility as well as coupling; it is not a
perfect causal intervention on coupling alone.

The main comparison changes representation. A separate, small ablation probes
HTTP outcome-mapping completeness. Conventional code may share domain logic,
use typed outcomes and ordinary analyzers, and avoid unnecessary duplication.

## Application and treatment boundary

Use three baseline entity types: Order, InventoryItem, and Reservation. Each
fulfillment refers to one existing order, one SKU, and a positive integer quantity.
Use one fixed trusted partition and one PostgreSQL database, with entity state
as authority. No UI, Cosmos, event-authority comparison, broker, multi-tenant
policy change, or cross-entity ACID guarantee is included.

The starting model is adapted from the implemented Aspire fulfillment example,
not copied unchanged and assumed qualified. Its reference revision is
`b0af008d85871ad8866d7d4311707ecd926529de`. Notably, the pilot must define missing
order handling, duplicate-request behavior, and the common wire contract below
in both fixtures. That is baseline work, not work hidden in the agent's task.

| Condition | Authoritative implementation |
|---|---|
| `conventional` | ASP.NET Core, ordinary C# domain methods and typed outcomes, explicit orchestration, PostgreSQL persistence and receipts. No Cohesive dependency. |
| `cohesive` | Authored entity and Transition definitions; Process composition; API bindings; PostgreSQL storage; Relations-backed read views. Source is edited; canonical IR is derived. |
| `cohesive-custom-mapping` | The same Cohesive fixture with only automatic HTTP rejection-map completeness replaced by the existing custom mapping path. Used only in the mechanism substudy. |

Both main conditions expose identical behavior and development feedback. They
receive context-matched architecture and API documentation, ordinary tests,
static analysis, and the same shell/build tools. No dedicated semantic search
or impact-analysis tool is added in this version. Any inspectable derived model
must be generated from the current submitted source and contain no target answer.
Record package/framework release dates and familiarity differences; do not
claim that matching .NET versions equalizes training exposure.

## Shared public contract

Fixture implementation must supply a byte-identical `CONTRACT.md`, JSON schema,
and visible contract tests to both conditions before calibration. These are
participant-visible application material, without evaluation framing. The
following behavior is normative; schema files freeze exact field types,
nullability, enum spellings, and header encoding without introducing new behavior.

| Operation | Required public behavior |
|---|---|
| `POST /orders` | Create a Draft order, return 201 with `id`. Server-generated IDs are opaque. |
| `GET /orders/{id}` | 200 with `id` and `status`, or 404. |
| `GET /orders/{id}/details` | 200 with order identity/status and reservation facts, or 404. |
| `GET /orders/{id}/availability` | 200 with reservation quantities and currently available inventory; an existing order without reservations has an empty list. Unknown order is 404. |
| `POST /orders/{id}/submit` | Draft becomes Submitted and returns 200. Existing non-Draft order returns 409 with a stable domain code; unknown order returns 404. Direct submit never changes inventory or creates a reservation. |
| `POST /fulfillment` | Body contains `requestId`, `orderId`, `sku`, and integer `quantity`. Valid admission returns 202 with `operationId` and `resultUrl`. Admission is host-lifetime only. |
| `GET /fulfillment/results/{operationId}` | 202 while pending; 200 with terminal `{status, outcome}` when completed. Unknown ID is 404. A terminal domain rejection remains HTTP 200 with `status: Rejected`. |

Quantities and inventory counts are signed 32-bit integers. Valid stored inventory
is nonnegative. Order/reservation IDs and SKU values are case-sensitive opaque
strings. Read arrays use ascending ordinal reservation ID order. Summary is
`{id, status}`; details is `{id, status, reservations}` with reservation entries
`{id, sku, quantity, availableStock}`; availability entries are
`{reservationId, sku, quantity, availableStock}`. The review probe adds only the
specified `reviewMarked` field to summary and details. Conflict responses include
a string `code`; descriptive message text is not scored. Baseline direct-submit
conflict code is `OrderNotDraft`. Timestamps and opaque generated IDs are
normalized only where equality across fixtures would otherwise be meaningless.

Malformed bodies, empty required identifiers, and out-of-range integer encodings
return 400 before execution. Domain-invalid quantities are terminal domain
rejections, not malformed input. For fixed host lifetime, the same requestId and
identical canonical input return the original admission/result; a reused ID with
different input returns 409 and starts no work. Distinct request IDs are distinct
attempts. The result and admission paths retain equivalent baseline authorization.
Credentials and trusted scope come from the fixture host, not caller JSON.

The public fixture contract also provides read-only inventory inspection for
scoring and a maintainer-controlled seed/reset facility. Both use the same
condition-neutral schema. Participants see the application contract, not hidden
seed data or oracle code. Setup facilities are disabled on the evaluated public
listener and cannot be used by a submission to manufacture a score.

### Baseline outcomes and precedence

After admission, an exact completed request replay returns its retained result
without reevaluating newer state. For a new request, select the first applicable
outcome in this order:

1. Unknown order: `OrderMissing`.
2. Existing reservation: the same order/SKU/quantity with a Submitted order gives
   `ReservedAndSubmitted` without new writes; any other match gives
   `ReservationConflict` without writes.
3. Unknown SKU: `InventoryMissing`.
4. Nonpositive quantity: `InvalidQuantity`.
5. Insufficient available stock: `InsufficientStock`.
6. Non-Draft order: `OrderRejected`.
7. Otherwise reserve quantity, submit the order, and create exactly one matching
   reservation: `Submitted / ReservedAndSubmitted`.

All other listed outcomes are `Rejected`. A successfully completed domain
rejection leaves no new reservation and no net inventory change. In particular,
if stock was reserved before an order rejection, it is released. An implementation
may instead reject before reserving; the oracle judges final behavior, not an
internal sequence. Inventory cannot become negative. Unrelated records remain
unchanged. A fixed scope is not evidence of general tenant isolation.

v0.1 scores sequential operations and exact duplicate requests, including requests
whose predecessors have completed. It does not score races between independent
fulfillment intents, machine crashes, concurrent hold/submit races, or physical
failure after a partial commit. Such failures are not falsely classified as
successful rollback: they are execution failures. Crash recovery and adversarial
concurrency require a later protocol version and a qualified public control path.

## High-coupling probe H Add an order hold

Add `OnHold` to the order lifecycle, plus two commands:

* `POST /orders/{id}/hold`: Draft becomes OnHold; OnHold is an idempotent success.
* `POST /orders/{id}/release-hold`: OnHold becomes Draft; Draft is an idempotent
  success.

Both return 200 with the order summary on success. Unknown IDs return 404.
Existing terminal states, including Submitted and any terminal states added by
the evolution chain, return 409 and remain unchanged. There are no reason fields,
timestamps, users, or notification requirements in this task.

Direct submit of an OnHold order returns 409 with code `OrderOnHold`. In
fulfillment, replace step 6 with an OnHold-specific `OrderOnHold` outcome, followed
by the existing non-Draft `OrderRejected` outcome. Earlier failure precedence is
unchanged: for example, held plus insufficient stock gives `InsufficientStock`.
A terminal OnHold rejection leaves the order held, inventory unchanged, and no
new reservation. Release allows a later distinct request to fulfill normally.
An old completed rejected request still replays its original result after release.
Order summary and details show OnHold; availability remains a projection of
actual reservation/inventory facts, not hypothetical demand.

| ID | Public obligation |
|---|---|
| `H-01` | Hold/release state table, idempotence, not-found behavior, and protection of every existing terminal state. |
| `H-02` | Direct submit rejects OnHold with the declared conflict and no mutation. |
| `H-03` | Fulfillment rejects OnHold with the declared outcome and precedence. |
| `H-04` | Completed hold rejection preserves net stock and creates no reservation. |
| `H-05` | Release enables a new valid fulfillment; completed old requests retain their original result. |
| `H-06` | Summary/details expose the state; availability agrees with persisted facts. |
| `H-07` | Baseline and all active evolution obligations survive, including ordinary fulfillment and unrelated records. |

The hold couples one lifecycle decision to two entry paths, stock consequences,
outcome mapping, and read views. Score interacting pairs explicitly, especially
H-03 × H-04, H-01 × H-05, and H-03 × each active evolution restriction.

## Low-coupling probe L Add an informational review marker

Add a separate order-review resource keyed by order ID with Boolean `marked`,
default false when no review record exists. It is not an Order lifecycle state
and is not read by submission, stock decisions, or fulfillment. Physical table
layout is an implementation choice; its semantic writes must not change order
status, inventory, reservations, or fulfillment request identity.

* `POST /orders/{id}/mark-reviewed`: set marked to true; repetition succeeds.
* `POST /orders/{id}/clear-review`: set marked to false; repetition succeeds.

Both return 200 with `{id, marked}`; unknown order IDs return 404. Review can be
marked or cleared for any existing order, including terminal states. Add
`reviewMarked` to summary and details, defaulting to false. No timestamps,
notifications, or workflow decisions are introduced. A marker survives submit,
fulfillment and lifecycle changes. Mark/clear operations never turn a previously
failed fulfillment into success or invalidate a completed request replay.

| ID | Public obligation |
|---|---|
| `L-01` | Set/clear state table, idempotence, default false, and not-found behavior. |
| `L-02` | Summary/details expose the same marker for the same order. |
| `L-03` | Marker changes preserve lifecycle, stock, reservations and availability. |
| `L-04` | Submission and fulfillment outcomes are invariant to the marker at fixed other inputs. |
| `L-05` | Marker persists through existing lifecycle/fulfillment operations, including terminal states. |
| `L-06` | Duplicate fulfillment requests retain their result regardless of later marker changes. |
| `L-07` | Baseline and every active evolution obligation survive; unrelated orders are unchanged. |

This is low coupling, not zero coupling: identity, persistence and read projections
are shared. Its business behavior factors from fulfillment decisions. Both probes
add two commands, one binary distinction, persistent state, two read projections,
idempotent operations and not-found handling. They differ in lifecycle and failure
interactions, which is the intended contrast, but their implementation effort is
not assumed equal. Do not pad the control with meaningless requirements.

Before calibration, independent reviewers compare known-good implementations for
required decisions, active work time, files/semantic nodes touched, and reference
patch size. Reference patches never enter agent workspaces. If one probe requires
more than twice the reference active implementation time, revise the pair or
declare it unmatched before evidence freeze. This is a feasibility screen, not
proof of equal difficulty; retain all task-size measurements as covariates.

## Participant prompts

Each prompt is byte-identical across representations and ages. The repository
contains the current application contract and all active obligations; the prompt
does not reveal hidden tests, the other probe, hypotheses, or future milestones.

**H:**

> Add an order hold and release operation as specified in CONTRACT.md. Held
> orders must not be submitted through either public entry path. Preserve the
> specified rejection precedence, inventory and reservation behavior, completed
> request replay, read views, and all existing lifecycle rules. Keep the public
> contract, build, and visible tests correct.

**L:**

> Add an informational order-review marker and clear operation as specified in
> CONTRACT.md. Expose the marker in both order read views. It must persist
> without changing submission, fulfillment, inventory, reservation, or completed
> request replay behavior. Preserve all existing lifecycle rules. Keep the
> public contract, build, and visible tests correct.

The target contract supplement is identical across ages for its probe. Preserve
the baseline's active contract alongside it. No condition receives an additional
implementation recipe. The two different probes need not have identical prompts.

## Evolution sequence and checkpoints

Build gold implementations in both conditions and prove equivalence at every
milestone. The trunk is the dependency chain `G0 → E1 → E2 → E3`; its linear
shape is a bounded special case of the evaluation DAG. Depth and scheduled
change index are 0–3. Neither H nor L appears on the trunk.

| Milestone | Requested change | New cumulative obligations |
|---|---|---|
| `G0` | Matched baseline defined above. | `B`: baseline public contract, stock safety, rejection preservation, replay and reads. |
| `E1` | Add an inventory-owned positive integer `maxPerOrder` limit, configurable through a documented inventory command. Defaults preserve existing behavior. | `E1-01`: configure/read a positive limit; invalid configuration is rejected without writes. `E1-02`: quantity above the limit yields `QuantityLimitExceeded`, after invalid quantity but before insufficient stock, without net stock/reservation change. `E1-03`: releases are not blocked by this limit; existing requests replay unchanged. |
| `E2` | Add Cancelled as a terminal order state and `POST /orders/{id}/cancel`. Draft may cancel; Cancelled is an idempotent success; Submitted conflicts. | `E2-01`: cancellation state table and read visibility. `E2-02`: direct submit gives `OrderCancelled`; fulfillment gives `OrderCancelled` at the lifecycle decision, without net stock/reservation change. `E2-03`: completed request replay remains stable; unrelated orders and E1 behavior survive. |
| `E3` | Add an inventory-owned `quarantined` Boolean, initially false, with quarantine/clear commands and read visibility. | `E3-01`: command idempotence and state visibility. `E3-02`: quarantined stock rejects new fulfillment with `InventoryQuarantined`, after invalid quantity and before quantity-limit/insufficient-stock checks. `E3-03`: release of previously reserved stock remains permitted; completed requests replay unchanged. E1/E2 and baseline behavior survive. |

After E3, the ordered terminal checks are: completed-request replay; missing order;
existing reservation match/conflict; missing inventory; invalid quantity;
quarantine; quantity limit; insufficient stock; lifecycle restriction; success.
After H is added, lifecycle restriction distinguishes OnHold, Cancelled when
present, and other non-Draft states. H does not enable cancelling an OnHold
order: cancel accepts Draft or an already Cancelled order only. Marking review
does not alter any of these checks.

Inventory inspection is `GET /inventory/{sku}`, returning 200 with `{sku,
available}` or 404. E1 adds `maxPerOrder`, initially 2147483647, to this response
and `PUT /inventory/{sku}/quantity-limit` with `{maxPerOrder}`. Valid updates return
200 with the inventory view, nonpositive values return 400 without writes, and
unknown SKUs return 404. E3 adds `quarantined` to the same view and introduces
`POST /inventory/{sku}/quarantine` and `POST /inventory/{sku}/clear-quarantine`;
both are idempotent, return 200 with that view, or 404 for an unknown SKU. These
commands cannot modify `available` or other inventory settings. E2 cancel returns
200 with the order summary, 404 if missing, or 409 with `OrderNotCancellable`.
Both conditions receive the same fixed operator authorization for inventory
commands. This is not a study of adding authorization policy.

Each evolution task receives the complete public contract supplement above and
one of these identical-across-condition requests:

* E1: "Add the per-order quantity limit specified in CONTRACT.md. Enforce its
  documented precedence in fulfillment, expose and update it through the inventory
  API, and preserve completed-request replay and all existing behavior."
* E2: "Add cancellation as specified in CONTRACT.md. Preserve terminal-state
  protection, direct submission and fulfillment outcomes, stock and reservations,
  read views, completed-request replay, and existing quantity-limit behavior."
* E3: "Add inventory quarantine and clearing as specified in CONTRACT.md.
  Enforce its documented precedence for new fulfillment, preserve compensation
  when used, and retain lifecycle, quantity-limit, read-view and replay behavior."

A release is the existing compensation operation, not a new public customer
endpoint. Its preservation is scored through net stock after reachable completed
rejections. The oracle cannot mandate a reserve-before-reject implementation or
claim coverage of a compensation branch that the implementation never executes.

The measured checkpoints are **fresh G0** and **aged G3**. E1 and E2 still receive
full cumulative scoring but no H/L probes. At each measured checkpoint, fork H
and L from exactly the same pre-probe repository snapshot. Probe outputs are
discarded from the trunk after evidence capture. A probe never sees its sibling's
patch, conversation, or score.

## Execution modes

| Mode | Trunk starts | Aged probe starts | Conversation |
|---|---|---|---|
| `independent` | E1 from G0, E2 from gold G1, E3 from gold G2; outputs do not propagate. | Gold G3. | New agent for every task/probe. |
| `continuous` | E1 from G0, then E2/E3 on the agent's own output. | That repetition's own post-E3 snapshot. | Continuing trunk session; each aged probe gets an isolated clone of the trunk conversation. |
| `fresh-context` | Same own-output chain as continuous. | That repetition's own post-E3 snapshot. | New agent at every step and each probe; repository knowledge persists. |

Fresh H/L probes always start from G0 with a new agent. Reuse this fresh
measurement as the common reference for all three modes; do not count copies
as additional samples. Never inject gold repairs into a continuous chain. Later
tasks may repair earlier defects within their ordinary budget. Continue even
after an agent-produced build failure; record inherited failures and blocked
checks. A harness outage instead pauses the chain under the invalid-run rules.

Scheduled age is assigned depth, not successful feature count. Record both depth
and the obligations actually satisfied, including pre-probe scores. Gold-depth
comparisons isolate accumulated requirements; own-output comparisons additionally
include accumulated implementation defects. Neither conflates age with task size.

## Repetitions, budgets and scheduling

Use three preregistered repetitions per main condition. For each condition and
repetition, execute 17 tasks:

* 3 independent evolution tasks plus 2 fresh and 2 gold-aged probes: 7.
* 3 continuous evolution steps plus 2 own-aged probes: 5.
* 3 fresh-context evolution steps plus 2 own-aged probes: 5.

That is **102 main task executions**. Each step/probe has a fresh 30-minute active
agent wall-time budget, excluding harness setup and scoring. Continuing-session
cost is attributed per step, including context input. Timeouts remain valid
incomplete outcomes. Do not allow one condition extra repair attempts. No arbitrary
token cap is inferred from a product that cannot enforce it; record that limitation.

Freeze one agent product/version, requested model and served-model policy,
reasoning setting, context/compaction policy, inference parameters exposed by the
product, tool permissions, SDK/package lockfiles, host image and PostgreSQL version
in an execution manifest. Set a numeric campaign monetary cap and usage accounting
policy before launch. These operational selections are still admission blockers;
this document does not authorize launching a paid campaign.

Generate the full schedule before execution from a retained seed. Pair conditions
within repetition/mode; randomize condition and H/L order while preserving trunk
dependencies. Use the same fixed concurrency limit and resource allocation in
both conditions. Execute the campaign within a 72-hour start window with no
outcome-driven delays; retain actual timestamps and any provider version changes.
If the configuration changes or the window cannot be met, retain the partial
campaign as exploratory and begin a new versioned campaign rather than pooling it
as the planned complete set. Do not assume controllable model sampling seeds.

## Calibration and admission

Admission precedes calibration: matched gold baselines at every depth; independent
conventional review; exact public contracts; qualified hidden oracle; leakage audit;
control-matching review; functional runner; and a complete execution manifest.

Run **4 calibration repetitions of each probe at each gold checkpoint in each
main condition**: 2 probes × 2 ages × 2 conditions × 4 = **32 runs**. Calibration
uses the same 30-minute budget and is permanently excluded from main evidence.
Also run one non-evidence E1→E3 chain per condition and continuous mode to validate
snapshotting and context handling: 2 conditions × 2 modes × 3 steps = **12 steps**.

For each conventional probe/age cell, require 1–3 failures out of 4 runs
(provisional 25–75% failure). Four passes is a ceiling; four failures is a floor.
This coarse gate is task admission, not a failure-rate estimate. Cohesive scores
do not select favorable cases. Changes after calibration require a new candidate
version and all affected qualification/calibration, with the full revision history
retained. Do not selectively alter checks or discard difficult obligations.

If the hold is too easy because the baseline already shares its Draft guard,
retain that sharing. Revise the behavioral task openly or report the ceiling;
never weaken the comparator. If either control checkpoint cannot meet headroom,
the intended coupling contrast is not admitted. A separately labeled feasibility
report may still describe the results without making a coupling claim.

## Mechanism substudy

The implemented HTTP `TransitionRejectionResponses<TCode>` checks that each enum
member has a declared mapping. The custom `OnRejected` overload allows the same
correct baseline mapping without that automatic coverage check. Qualify a third
fixture differing only in this mechanism, with identical normal responses and
all other facilities unchanged. Use a seeded missing-outcome mapping to verify
the intended contrast before running agents.

Run H at gold G0 and gold G3, three repetitions each: **6 additional executions**.
Compare with the corresponding existing independent Cohesive runs. Total main
plus substudy is **108 task executions**, excluding 32 calibration runs and 12
chain-calibration steps. Run a non-agent smoke qualification for the ablation;
do not use its results to retune the task or disable unrelated compiler checks.

The endpoint is correct outcome handling and the distribution of handled cases,
explicit setup rejection, and silent omission. An explicit setup rejection is
safer detection, but is still an incomplete implementation. Do not label this
global typestate completeness or claim a mechanism effect from six runs. If the
ablation cannot be isolated while preserving the baseline, report it unavailable
and defer it rather than substituting a different treatment mid-campaign.

## Oracle, scoring and analysis

The oracle runs outside participant workspaces through the same public contracts
and fixed setup boundary. It cannot demand Cohesive internals, exact files, a
particular orchestration order, or a handwritten copy of the Cohesive graph.
Known-good implementations must pass; seeded defects must include missed direct
or process paths, wrong rejection precedence, lost review markers, stock leaks,
duplicate effects, terminal-state reopening, and collateral E1/E2/E3 regressions.

Before each task, score its starting snapshot privately; never feed those results
to the agent. After submission, save the patch and grade it in a clean environment
with dependencies and derived IR rebuilt from source. Run all baseline and active
milestone obligations plus the current probe obligations. New hidden fixtures may
vary data and operation sequences, but cannot add undisclosed behavior.

Per obligation report passed, failed, or not-evaluated; also retain assertion-level
results. Strict completion requires build/public-contract compatibility, all
visible tests, all active obligations, and treatment integrity. A participant-caused
build/startup failure is incomplete, not a harness exclusion. Not-evaluated checks
are reported separately rather than counted as semantic passes or invented failures.

Report distinct measures:

* New-obligation success and strict all-pass rate, with raw counts.
* Retention of previously passing obligations; new regressions and healing since
  the pre-task snapshot. Report preexisting failures separately.
* Progress precision = newly passing obligations / (newly passing obligations +
  newly failing obligations), undefined when the denominator is zero. New-feature
  recall = passed obligations introduced by this task / all obligations introduced
  by this task. A new obligation that passes counts as newly passing; existing
  obligations count only on an observed fail-to-pass or pass-to-fail transition.
  Keep build-blocked counts visible and do not hide them in the ratio.
* Interacting-pair results and failure classes: incomplete enforcement, interaction
  violation, unsupported invention, data/persistence, lifecycle/business logic,
  API classification, and harness/task ambiguity.
* Survival and error propagation by scheduled depth: originating, inherited,
  induced, masked, or healed. Chain steps are dependent observations.
* Wall time, tokens, tool calls and cost when measured; initial baseline-authoring
  cost separately from agent evolution cost. Reference-maintainer time is not
  interchangeable with agent cost, so no combined crossover estimate is made.
* Task size, semantic decisions, diagnostic churn and changed files as explanatory
  covariates, never correctness credit.

For each mode, report the Cohesive-minus-conventional success difference for H
and L at each age, then the descriptive contrast
`(delta_H_aged - delta_H_fresh) - (delta_L_aged - delta_L_fresh)`.
Reuse of the fresh reference must remain explicit. Do not pool assertions,
milestones, or repeated runs as independent worlds, attach confirmatory p-values,
or interpret a nonsignificant result as equivalence. Record reviewer uncertainty
and keep correction decisions independent of which condition benefits.

Correctness leads interpretation. A favorable result requires better obligation
delivery/retention or lower cost among equally correct outcomes without hiding
regressions. Worse correctness, extra reconstruction or diagnostic effort, or
conventional reconstruction being sufficient are negative evidence. Ceiling,
floor, unmatched task size, treatment leakage and unresolved oracle ambiguity make
the relevant comparison inconclusive. No result obliges a larger study.

## Isolation, provenance and stop rules

Participant workspaces contain only their condition, current task contract,
ordinary documentation/tests, and source-derived build outputs. Exclude parent
Git history, oracle/qualification code, gold successors, hidden fixtures, future
task supplements, other conditions and earlier scores. Each step uses the same
repository-history policy; continuing conversations contain only that trunk's
participant-visible interactions. Branch conversations must be independently
clonable; otherwise the continuous-mode runner is not admitted.

Pre-provision dependencies; agent-phase network access is restricted to the model
endpoint. Check workspace manifests before and after execution. Keep scoring
credentials and test-control privileges outside the agent workspace. Oracle
results must not be substituted for normal visible developer feedback.

Retain protocol/case/oracle and source hashes; exact gold and own-output snapshot
IDs; condition/mode/repetition/depth/probe identity; parent lineage; canonical
definition and tool/package versions; prompts and available context; transcript
or trace; compaction events; patch; logs; pre/post obligation vectors; timing and
usage; scheduling seed; deviations and exclusions. Score records remain bound to
their original evaluator version. Participant artifacts may not directly edit
derived canonical IR or bypass the assigned authoritative semantics.

Stop for leakage, wrong condition/model, configuration drift, missing evidence,
or a harness fault. Agent errors, budget exhaustion and unfavorable results do
not stop or invalidate a run. A harness-invalid step with descendants invalidates
the dependent suffix; restart that suffix from the last valid snapshot and its
matching conversation state, retaining all invalid attempts. If that exact state
cannot be restored, restart the chain. A disconnected probe can be replaced alone.

Oracle defects pause scoring for all affected submissions. Version and requalify
the oracle, then rescore every preserved affected snapshot; never repair only an
unfavorable result. Changed participant requirements require a new case version
and new runs. A campaign cost cap stops scheduling new work, retains all evidence,
and yields an explicitly incomplete campaign rather than adaptive early success.

## Freeze checklist and follow-through

- [ ] COH-130: matched G0–G3 fixtures, ordinary visible tests, and independent
  conventional review; implemented PostgreSQL checks pass on a disposable fixture.
- [ ] Exact common CONTRACT.md/JSON schemas, milestone supplements, request/replay
  encoding, and all prompt hashes are recorded without changing the semantics above.
- [ ] Reviewer task-size screen and hidden oracle qualification pass, including
  interaction checks and prompt–verifier alignment.
- [ ] Runner proves branch isolation, continuing-session cloning, fresh context,
  cumulative clean scoring, budget enforcement and exact provenance.
- [ ] Model/agent/tool/provider pins, schedule seed, concurrency and monetary cap
  are written to an execution manifest.
- [ ] Calibration gates pass with no subsequent unversioned changes.
- [ ] The exact protocol, fixtures, manifest and oracle are content-addressed
  together as the evidence-run release.

COH-129 defines this protocol; COH-130 implements and qualifies it. No evaluation
run or runtime qualification is asserted by authoring this document.

## References

- [Evaluation vision](https://app.notion.com/p/3b88cf7881f9812a9263d9949a808600)
- [Case selection COH-128](https://linear.app/cohesive-ari/issue/COH-128)
- [Protocol COH-129](https://linear.app/cohesive-ari/issue/COH-129)
- [Fixture and oracle COH-130](https://linear.app/cohesive-ari/issue/COH-130)
- [Implemented fulfillment model](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/eng/examples/aspire-first/Orders.Model/FulfillmentDomain.cs)
- [Integration test source](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive.Adapters.Aspire.Tests/FulfillmentProcessIntegrationTests.cs)
- [HTTP outcome completeness implementation](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/adapters/Cohesive.Adapters.AspNet/Entities/TransitionRejectionResponses.cs)
