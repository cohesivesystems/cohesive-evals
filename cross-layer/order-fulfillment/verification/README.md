# Baseline invariant verification

Run `python3 verification/verify.py` from the case directory after building both
conditions. The verifier runs the 52 visible HTTP checks and then three isolated
small worlds (seeds 17, 83, 251), each with 60 sequential commands. A fixed prefix
covers last-unit depletion, one-too-many rejection, same-intent/new-identity
replay, replay after later state changes, identity conflicts and compensation.
Generated commands mix submission, fulfillment, invalid quantities, unknown
entities and replays. Order 7 and the `untouched` SKU are isolation sentinels.

The independent model represents settled business state, not process steps or
receipt internals. After each completed command, assertions check:

- Nonnegative stock and conservation: available plus reserved equals initial stock.
- Unique reservation identity and at most one workflow-created reservation per order.
- Positive reservation quantities and existing order/SKU references.
- Exact model agreement for successful completion, rejection preservation and isolation.
- Public order/details projections and live stock enrichment.
- Stable request identity/results and conflict rejection without effects.

A test-only observer maps each schema to the same inventory/reservation facts in
one read-only PostgreSQL transaction. It inspects all reservation rows touching
that world's IDs, so extra rows cannot be hidden by the public projection.
Assertions apply to freshly seeded invariant worlds, not the separate contract
fixtures that deliberately permit multiple preexisting reservations per order.
The observer does not inspect or require identical runtime receipt tables.

Evidence is saved to `artifacts/verification/<condition>/invariants-<seed>.json`
before each command and after each check, including failure details. Repeat the
verifier with the same source revision to reproduce each deterministic sequence.
Automatic failing-sequence reduction is not implemented yet.

The checker is qualified against one good snapshot and six mutated snapshots:
negative stock, double decrement, duplicate reservation under a different ID,
dangling reference, missing reservation and unrelated stock mutation. This is
checker-level qualification, not qualification against mutated application builds.
Keep this directory outside participant workspaces.

## Guarantee boundaries and next qualification

These checks observe settled sequential behavior. They cannot prove that no
transient violation occurred between observations. They do not assert concurrent
independent-intent safety or crash recovery. Direct submission legitimately
produces a Submitted order without a reservation; stock may legitimately be
reserved before a reservation row exists during fulfillment.

COH-131's separate durability supplement must add deterministic external crash
barriers around admission acknowledgement and persisted stock/submission/
reservation/compensation effects. Restart the worker without resetting storage,
replay requests, and check settled invariants within a frozen recovery deadline.
Successful acknowledgement must imply durable admission and stable identity;
activity retries may occur, but business effects must not be duplicated. Qualify
this oracle with application-level seeded defects in both implementations before
scored runs. Transient-state assertions require committed-effect observation,
not polling presented as proof. Database loss and unrelated concurrent requests
need separate explicit failure models.

Hold, cancellation, quantity-limit and quarantine invariants enter the cumulative
oracle only at their declared milestones. A concurrent last-unit contention
scenario is a separately admitted extension, not a new hidden G0 requirement.
