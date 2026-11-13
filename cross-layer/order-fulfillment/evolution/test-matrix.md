# Hold/control and evolution milestone-to-test matrix

Status: maintainer plan with E1 implementation, 2026-11-12. This matrix translates the
[protocol v0.1](../protocol.md) into implementation and qualification work for
[issue #8](https://github.com/cohesivesystems/cohesive-evals/issues/8). It does not freeze new
requirements, claim unimplemented checks pass, or authorize agent runs.

Keep this directory, reference implementations, hidden fixtures, mutation recipes,
and evidence outside participant workspaces and their Git history. Durability is
[a separate G0 probe](../durability/protocol.md); its crash tests and durable
admission guarantees do not enter this matrix.

## Checkpoints and cumulative activation

G1, G2 and G3 are the snapshots produced by E1, E2 and E3 respectively. H and L
are independent probe branches, never trunk features or prerequisites for one
another. The same activation rules apply to gold and agent-produced snapshots.

| Snapshot/task | Starting snapshot | Obligations to grade after the task | Reference work still needed |
|---|---|---|---|
| G0 | Existing baseline | B | Existing implementations and G0 qualification are available. |
| E1 → G1 | G0 | B + E1 | [Matched references, checks and defect qualification](e1/README.md) available; campaign admission remains separate. |
| E2 → G2 | G1 | B + E1 + E2 | Both gold implementations and cumulative checks. |
| E3 → G3 | G2 | B + E1 + E2 + E3 | Both gold implementations and cumulative checks. |
| Fresh H | G0 | B + H | Both isolated hold references and checks. |
| Fresh L | The same G0 snapshot as fresh H | B + L | Both isolated review-marker references and checks. |
| Aged H | G3 | B + E1 + E2 + E3 + H | Both isolated aged hold references and interaction checks. |
| Aged L | The same G3 snapshot as aged H | B + E1 + E2 + E3 + L | Both isolated aged marker references and interaction checks. |

H/L are not scheduled at G1 or G2. H+L together is not a treatment. Independent
mode uses gold parents; continuous and fresh-context modes use their own prior
outputs as specified by the protocol. Privately score each actual starting
snapshot before its task, retaining inherited failures rather than repairing them.

## Reading the matrix

Each row identifies a public obligation, an ordinary participant-visible example,
a maintainer-only extension, expected correct reference behavior, and a running
application defect that should fail the named obligation. Hidden checks vary data
and sequences, not the contract. All proposed checks must be implemented and
qualified in both conditions before admission.

`q` is requested quantity, `S` available stock, `M` the per-order limit, and `Q`
quarantine. Unless a row says otherwise, use a fresh Draft order, known SKU,
`S=10`, `q=3`, `M=2147483647` when present, and `Q=false` when present. Use separate
worlds for independent examples. Retain unrelated order/SKU sentinels in every
stateful world. Missing entity and boundary fixtures are explicit exceptions.

Every terminal fulfillment outcome except `ReservedAndSubmitted` has
`status: Rejected` and HTTP 200. Admission remains 202; direct command conflicts
remain 409. A completion must be polled before comparing settled state. Exact
replay returns the same admission/result; conflicting reuse returns 409
`RequestIdentityConflict` without execution. HTTP error message prose is not scored.

The B rows below group existing G0 requirements for coverage; they are local
matrix labels, not new protocol obligations or extra scoring weight. E/H/L IDs
are the protocol's obligation IDs. Multiple assertions under one ID do not become
independent experimental samples or inflate its score.

## Baseline retention B — active everywhere

| Group | Visible check | Hidden extension | Expected reference behavior | Deliberate defect / expected failure |
|---|---|---|---|---|
| B-lifecycle | Create Draft; direct submit; submit again; missing order. | Direct submit with inventory/reservation sentinels; all active non-Draft states. | 201 creation; 200 Draft→Submitted; proper 404/409; direct submit has no inventory/reservation effects. State-specific E2/H codes supersede G0's generic conflict only where specified. | Direct submission decrements stock; incomplete status guard → lifecycle/effect assertion. |
| B-fulfillment | Successful q=3; nonpositive q; insufficient stock; missing order/SKU; Submitted rejection. | Full precedence witnesses, signed integer edges, reservation match/conflict, distinct IDs after completion. | First applicable outcome wins; success makes one matching reservation with ID=order ID and decrements exactly q; completed rejection preserves state and net stock. | Extra decrement, skipped release, missing/duplicate reservation, reversed precedence → exact outcome or settled-fact assertion. |
| B-identity | Exact replay; different payload under the same ID. | Duplicate admission while pending; replay after later state/configuration changes; capacity=1000 and replay at capacity. | One admission/result per request identity for host lifetime; conflict starts no work; new ID at capacity returns 503; retained identity remains usable. | Reexecute duplicate; accept changed payload; evict old result at capacity → replay/identity assertion. |
| B-reads | Summary, details, availability, inventory; empty and missing cases. | Multi-reservation seeded read fixtures; U+E000/U+10000 ordinal order; case-sensitive IDs; exact 1000-row and 1,000,000-byte boundaries per endpoint. Recompute byte-bound fixtures when L adds a field. | Exact current projections, UTF-16 ordinal ordering, endpoint-specific limits; excess yields 422 `ReadResultTooLarge`, never partial results. | Stale stock enrichment, wrong ordering, truncate instead of reject → read assertion. |
| B-input | Malformed body, missing/blank IDs, integer overflow. | Type/null/boundary variants under frozen schemas; input and admission failures leave business facts unchanged. | 400 before execution for malformed input; valid nonpositive q is a domain rejection. New command ambiguities below must be frozen first. | Parse overflow as a valid quantity; mutate before validation → input/effect assertion. |
| B-invariants | Deplete stock; reject one more; verify unrelated records. | Extend existing independent model and read-only observer across deterministic/generated sequences. Check all physical reservation rows in each world. | Nonnegative stock; settled conservation; positive quantities and valid references; at most one workflow-created reservation/order; no collateral effects. Direct submit may legitimately have no reservation. | Hidden extra row, dangling reference, wrong-order mutation → physical invariant assertion. |

Existing evidence: [G0 verifier](../verification/README.md) and
[application-defect qualification](../qualification/README.md). Their 52 visible
checks and 180 generated commands per condition are the current baseline, not an
assumed final cumulative test count. Multi-reservation read fixtures are distinct
from invariant worlds that require unique workflow-created reservations.

## Evolution trunk

| ID | Visible check | Hidden extension | Expected reference behavior | Deliberate defect / expected failure |
|---|---|---|---|---|
| E1-01 | Read default M; PUT M=2; read it; reject M=0/-1; unknown SKU. | M=1 and int.MaxValue; repeated update; malformed encodings once schema is frozen; compare S and unrelated inventory before/after. | Default int.MaxValue; positive updates return 200 inventory view; nonpositive returns 400, missing SKU 404; rejected update writes nothing; valid update changes only M. | Default limit too small, accepts zero, updates S too → configuration/read/preservation assertion. |
| E1-02 | M=2: q=2 succeeds, q=3 gives `QuantityLimitExceeded`. | q=0 plus S=0; q>M plus q>S; missing entity/reservation precedence; int.MaxValue without arithmetic overflow. | Invalid quantity precedes limit; limit precedes insufficient stock; earlier G0 rules survive; rejection has no net stock/reservation effect. | Limit checked only in direct submit or after stock shortage; off-by-one → limit/precedence assertion. |
| E1-03 | Complete q=3, lower M to 2, replay original request; use a new order/request to show the new limit applies. | Replay both success and rejection after raising/lowering M; Submitted lifecycle rejection with q≤M and sufficient stock; verify settled stock. | Retained result ignores new M. Completed lifecycle rejection restores any earlier reservation effect; stock release, if used, must not apply M. See release coverage boundary below. | Reevaluate retained requests using new M; stock leak on lifecycle rejection → replay/conservation assertion. |
| E2-01 | Cancel Draft; cancel again; cancel Submitted; missing order; read summary/details. | Terminal-state persistence across later commands; cancellation preserves inventory/reservations and unrelated orders. | Draft→Cancelled and Cancelled→Cancelled return 200 summary; Submitted returns 409 `OrderNotCancellable`; missing returns 404; no terminal reopening. | Cancel permits Submitted or toggles Cancelled back to Draft → state-table assertion. |
| E2-02 | Direct submit Cancelled: 409 `OrderCancelled`; valid fulfillment of Cancelled: Rejected/`OrderCancelled`. | Cancelled combined with missing SKU, invalid q, limit excess, insufficient stock; physical checks after completed rejection. | Cancellation-specific outcome occurs at the lifecycle decision, after earlier failures; order remains Cancelled, no new reservation or net stock change. | Fix direct route only, use generic `OrderRejected`, or check lifecycle too early → entry-path/precedence/preservation assertion. |
| E2-03 | Complete a request, cancel when legal, replay it; verify E1 still works on another order. | Reject for stock/limit on a Draft order, cancel it, then replay the original request unchanged; repeated cancellation; generated mixed histories. | Request replay stays original; cancellation neither repairs nor invalidates an earlier result; all E1 and unrelated-state obligations remain. | Cancel clears request identities or drops M on an inventory rewrite → replay/retention assertion. |
| E3-01 | Quarantine/clear twice; inspect inventory; unknown SKU. | Alternate Q while M is nondefault; check S/M and other SKUs remain unchanged; initial Q=false. | Commands return 200 current inventory view and are idempotent; unknown SKU 404; only Q changes. | Quarantine resets M or replenishes S; stale view → configuration/preservation assertion. |
| E3-02 | Q=true gives `InventoryQuarantined`; clear then use a distinct request to succeed. | q=0 with Q=true; Q=true with q>M and q>S; Cancelled with Q=true; missing inventory/reservation precedence. | Invalid quantity precedes Q; Q precedes limit, shortage and lifecycle; all completed rejections preserve stock/reservations. | Quarantine enforced only in reads, or after limit/lifecycle → enforcement/precedence assertion. |
| E3-03 | Complete a request, quarantine SKU, replay unchanged; complete a quarantine rejection, clear Q, replay unchanged. | New identity after clear observes current rules; Submitted/Cancelled lifecycle rejection with Q=false and q≤M; cumulative B/E1/E2 generated histories. | Old results remain stable; prior obligations survive; any compensation release is exempt from Q. Do not invent a new release endpoint or claim unreachable release coverage. | Replay reevaluates Q; clear resets M; rejection leaks stock → replay/retention/conservation assertion. |

## High-coupling hold probe H — G0 and G3 only

| ID | Visible check | Hidden extension | Expected reference behavior | Deliberate defect / expected failure |
|---|---|---|---|---|
| H-01 | Draft→hold→hold→release→release; missing order; try both commands on Submitted. | At G3 test both commands on Cancelled; cancel OnHold; cycle holds repeatedly and inspect sentinels. | Hold/release are idempotent 200 summaries for their allowed states; missing 404; terminal states 409 unchanged. At G3 cancel OnHold is 409 `OrderNotCancellable`. Conflict codes: `OrderNotHoldable` / `OrderHoldNotReleasable` (shared supplement). | Release reopens Submitted/Cancelled; hold replaces terminal state → state-table assertion. |
| H-02 | Direct submit OnHold returns 409 `OrderOnHold`; release then direct submit succeeds. | Repeated rejected submissions; compare inventory/reservations and both read views. | Held state and all business facts unchanged; released Draft uses existing submit behavior. | Guard only fulfillment, or generic direct-submit code → direct-entry assertion. |
| H-03 | Valid fulfillment while held returns Rejected/`OrderOnHold`; held plus stock shortage returns `InsufficientStock`. | Missing SKU, invalid q, and at G3 Q/limit/shortage conflicts; compare fresh and aged lifecycle outcomes. | Hold is enforced at the lifecycle decision, never before earlier rules; Cancelled retains its distinct aged outcome. | Guard only direct submit; move hold ahead of stock rules → process-entry/precedence assertion. |
| H-04 | Hold, fulfill with otherwise valid input, poll completion, compare stock and reservations. | Repeat with distinct request IDs and quantities; read physical rows; untouched order/SKU; then fulfill a different order using all stock. | No new reservation, no net stock change, order remains OnHold; no hidden leaks or duplicate rows. | Return `OrderOnHold` after decrement without release → outcome passes but preservation fails. |
| H-05 | Retain a held rejection, release, replay old ID, then fulfill using a new ID. | Multiple hold/release cycles; old successful/rejected results; at G3 release with Q=true or q>M followed by clearing the appropriate restriction. | Old result remains `OrderOnHold`; a new valid request succeeds after release, but release does not bypass independent inventory rules. | Reuse/rewrite old result; release grants unconditional fulfillment eligibility → replay/interaction assertion. |
| H-06 | Summary/details show OnHold, then Draft after release; availability stays factual. | Unrelated read records, empty reservations, repeated reads and current-stock enrichment. | Status agrees across views; availability shows only actual reservation facts; no hypothetical held demand. | Write status but omit read projection; synthesize a reservation for hold → view assertion. |
| H-07 | Ordinary nonheld fulfillment still succeeds; sentinels unchanged. | Run the complete active B/E1/E2/E3 suite and model sequences with holds/releases. | Existing obligations retain their specified behavior; new OnHold paths do not erase Cancelled or weaken inventory restrictions. | Replace lifecycle enum/guard and lose cancellation; reset inventory settings → cumulative retention assertion. |

## Low-coupling review-marker control L — G0 and G3 only

| ID | Visible check | Hidden extension | Expected reference behavior | Deliberate defect / expected failure |
|---|---|---|---|---|
| L-01 | Default false; mark twice; clear twice; missing order. | Mark/clear Submitted and, at G3, Cancelled; independent markers on two orders. | 200 `{id,marked}` for any existing state; missing 404; no-review-record means false. | Restrict marking to Draft, default true, or share a global flag → state/default/isolation assertion. |
| L-02 | Compare `reviewMarked` in summary and details after each command. | Absent review record versus explicit cleared record; schema/serialized-byte boundary cases. | Both views agree; marker adds only the declared fields and respects existing read limits. | Update one projection only; serialize a missing record as null → view/schema assertion. |
| L-03 | Snapshot lifecycle, inventory, reservations and availability; mark/clear; compare. | Existing reservations, terminal orders, nondefault M/Q, unrelated sentinels. | Only review state changes; lifecycle, stock, reservation facts, settings and request identity do not. | Store marker in status or overwrite inventory/order fields → preservation assertion. |
| L-04 | Paired worlds differing only in marker: direct submit and ordinary fulfillment. | Pair each applicable rejection class and precedence collision at fixed other state; compare normalized responses and non-review facts. | Outcomes and effects are invariant to marker. Neither marked nor unmarked is a prerequisite for submit/fulfill/cancel. | Require review before submit, bypass limit when marked, or block marked orders → metamorphic equivalence assertion. |
| L-05 | Mark Draft, submit or fulfill, read marker; at G3 mark then cancel. | Clear terminal orders; repeated transitions, old/default records and generated histories. | Marker persists through allowed lifecycle operations; terminal state does not prevent mark/clear. | Recreate order on submit/cancel and lose marker → persistence assertion. |
| L-06 | Complete success/rejection, toggle marker, replay exact request. | Pending duplicate admission where supported by existing G0 contract; payload conflicts after marker changes; repeated toggles. | Same admission/result regardless of marker; conflicting input still 409 without effects. | Include marker in fulfillment identity or invalidate cache on mark → replay assertion. |
| L-07 | Ordinary behavior and unrelated markers survive. | Complete active B/E1/E2/E3 suites and mixed marker/configuration histories. | Control remains informational at both ages; older requirements and unrelated records remain intact. | Marker endpoint resets M/Q, or lifecycle changes clear another marker → cumulative retention/isolation assertion. |

## Required interacting-pair witnesses

These are assertion groupings under the obligation IDs above, not additional
scoring weight. Use fresh identities for changed-state attempts; exact replay is
always tested separately before new-request precedence.

| Pair / activation | Witness | Expected result |
|---|---|---|
| H-03 × H-04, fresh/aged H | Held order, S=10, q=3. | `OrderOnHold` **and** unchanged stock/no reservation/held status. |
| H-01 × H-05, fresh/aged H | Hold rejection → release → old ID replay → new ID. | Old rejection retained; new valid attempt succeeds. |
| H × E1, aged H | Held, M=2, q=3; repeat with q=2. | `QuantityLimitExceeded`, then `OrderOnHold`; no effects for either. |
| H × E2, aged H | Hold/release Cancelled; cancel OnHold; submit each state. | No terminal reopening; cancel OnHold rejects; distinct `OrderCancelled`/`OrderOnHold` mappings. |
| H × E3, aged H | Held and Q=true; clear Q; later release hold. | `InventoryQuarantined`, then `OrderOnHold`, then success with valid input/new IDs. |
| E1 × E3, G3 and aged probes | Q=true, M=2, S=1, q=3; clear Q; raise M. | `InventoryQuarantined`, `QuantityLimitExceeded`, `InsufficientStock` on successive new requests. |
| E2 × inventory rules, G2 onward | Cancelled with invalid q, limit excess, shortage; add Q at G3. | Inventory/input failures precede `OrderCancelled`; lifecycle outcome only when earlier rules pass. |
| L-04 × each active rule, fresh/aged L | Paired worlds differing only in marker for each outcome above. | Same fulfillment/direct-command outcomes and non-review effects. |
| Replay × E/H/L, whenever active | Retain a completed result, change allowed settings/status/marker, replay exact ID. | Original admission/result wins over all current-state rules. |
| Existing reservation × E1/E3, whenever active | Successfully fulfill; lower M/quarantine; repeat same order/SKU/q under a new request ID. | Existing matching Submitted reservation still yields success without new writes. Changed SKU/q gives `ReservationConflict` before current inventory restrictions. |

Precedence fixtures must make both competing predicates true. Merely testing each
outcome independently cannot detect a swapped decision order. Generate adjacent
and relevant nonadjacent collisions from the active ordered decision list, retaining
explicit examples for each interacting pair above.

## State model, observation and coverage limits

Extend the independent Python model with `maxPerOrder`, Cancelled, `quarantined`,
and the selected probe state only when active. Keep request-result history
separate from current business state. Model expected outcomes from the published
decision order, not from either reference implementation or its process steps.

Use public reads plus a read-only physical observer mapping each schema to common
business facts. Extend mappings for inventory configuration and review resources;
do not require identical tables, receipt representations, or workflow architecture.
Persist the seed, command prefix, expected/observed responses and facts, parent
snapshot, evaluator version and source/build hashes for each check. Choose and
freeze evolution seeds before qualification; the G0 seeds are not evidence of
coverage of new commands by themselves.

Check settled conservation in initially unreserved invariant worlds:
`available + sum(reserved quantities) = initial stock`, per SKU. Configuration,
hold, review and cancellation commands do not replenish or consume inventory.
Do not apply uniqueness assertions to deliberately multi-reservation read fixtures.
Sampled settled checks do not prove continuous safety, independent-intent
concurrency, or crash recovery. Storage persistence can be inspected directly;
any optional clean-restart check must use settled business data and must not
require host-lifetime admission/results to survive a restart.

**Release coverage:** E1/E3 require compensation release to remain permitted, but
there is no public release command and a correct implementation may reject before
reserving. Score reachable completed rejections by their net effects. A release
under a newly restrictive limit/quarantine may not be reachable in this sequential
public model: record that limitation explicitly. Optional reference-level unit
checks can inspect such release behavior, but cannot count as a black-box pass
for every participant or force a particular internal sequence. A new interleaving
schedule or endpoint requires an openly revised contract and qualification.

## Shared contracts before scored assertions

[Contract supplements and schema bundles](contracts/README.md) resolve the
preparation gaps below. They specify target behavior. [E1 references and runtime qualification](e1/README.md)
are implemented; E2/E3 and H/L remain to be written and qualified. Only active bundles
enter participant workspaces. This is not the campaign release freeze.

| Detail | Shared decision |
|---|---|
| H conflict codes | Hold: `OrderNotHoldable`; release: `OrderHoldNotReleasable`. |
| New command parsing | Quantity-limit input is required positive int32; invalid body/value precedes missing SKU. Bodyless commands ignore bodies. |
| E2 states/outcomes | Cancelled is terminal; direct submit `OrderCancelled`; cancel conflict `OrderNotCancellable`. |
| Seed compatibility | Per-profile versioned schemas; neutral defaults for optional new facts; inactive fields excluded; no live migration. |
| Persistence | Clean restart preserves settled business facts; host-lifetime request history need not survive. |
| L read bounds | Rebuild exact byte fixtures with the current serializer/shape and both review-marker values; limits unchanged. |

## Qualification and delivery sequence

1. Review the common participant-facing E1/E2/E3/H/L supplements and schemas
   in [contracts](contracts/README.md). Only the current task and prior active material
   enter a workspace; future supplements and sibling probes stay private.
2. Build isolated gold G1, G2 and G3 in both conditions, retaining G0. Implement
   visible examples and hidden cumulative checks alongside each milestone.
3. Build fresh H/L from G0 and aged H/L from G3 independently. Check paired public
   observations and physical facts; review conventional idiomaticity and measure
   control/reference task effort under the protocol's matching screen.
4. Qualify all gold snapshots and the running defects named in the matrix. Each
   defect must build/start and fail its intended behavioral assertion. Record the
   actual obligation detected and any collateral failures; build, setup or barrier
   failures do not qualify business-defect detection. Explicit setup-diagnostic
   tests remain a separate category, as in the durability work.
5. Exercise acceptance breadth: at least reject-before-reserve and
   reserve-then-compensate correct references must receive equivalent settled
   judgments where those strategies are applicable. Read-only facts, not a
   prescribed implementation, decide acceptance. Keep task-size review separate
   from correctness and do not pad the control.
6. Emit per-obligation and per-assertion passed/failed/not-evaluated results for
   pre-task and submitted snapshots; compute retention/regression/healing from
   paired vectors. Build/startup failure blocks semantic checks and fails strict
   completion, without inventing semantic assertion results.
7. Audit packaged workspaces, source-derived artifacts, history isolation and
   prompt–verifier alignment. Then complete runner/manifest admission and the
   separately authorized calibration phase. This matrix does not change run counts,
   budgets, or the protocol's admission-before-calibration ordering.

Definition of done for this document: every B/E/H/L obligation has a visible
example, hidden extension, correct behavior and defect witness; activation and
interaction coverage are explicit; gaps are disclosed. Implementation, runtime
qualification and calibration remain separate deliverables, not checked off by
writing this matrix.
