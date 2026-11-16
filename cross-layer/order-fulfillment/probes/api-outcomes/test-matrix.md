# AO1 milestone-to-test matrix

Planned checks, **not executed qualification**. Parent/source pins and exact wire
outcomes are in [the protocol](protocol.md). Assertions below must have stable
names in the independent verifier. Mutant names are planned, not detection claims.

| Obligation | Named assertion / witness | Required observation | Planned defect |
| --- | --- | --- | --- |
| AO1-01 | `archived direct submission` | Archived → 409 OrderArchived; order/inventory/reservations unchanged. | Missing guard; stale generic OrderNotDraft mapping; wrong HTTP category/body. |
| AO1-01 | `existing direct outcomes` | Draft, Submitted, Cancelled and missing retain their outcomes; Archived cancellation remains OrderNotCancellable. | Broad catch-all maps existing rejections to OrderArchived. |
| AO1-02 | `archived fulfillment outcome` | Single and batch: admission 202, completion 200 Rejected/OrderArchived. | Missing terminal mapping; generic OrderRejected fallback; enum alias/literal drift. |
| AO1-02 | `archived compensation` | Net inventory unchanged, no new reservation, Archived retained; unrelated facts identical. | Skip release, release twice, create reservation after rejection. |
| AO1-03 | `rejection precedence` | Inventory missing/invalid/quarantined/over-limit/insufficient takes precedence; existing Archived reservation yields ReservationConflict. | Check Archived before inventory or existing-reservation resolution. |
| AO1-04 | `bound entity identity` | Route selects intended entity; case-sensitive IDs and an unrelated sentinel detect cross-entity effects. | Bind route ID to a constant/sibling entity or wrong parameter. |
| AO1-04 | `bound input meaning` | SKU and quantity reach their existing domain guards unchanged. | Constant/swapped input field; default quantity; wrong typed input contract. |
| AO1-04 | `declared binding consistency` | Capture exact diagnostic for a wrong canonical transition reference/revision, response body contract or missing required binding. | Deliberate declaration/binding mismatch; evaluate conventional static checks fairly. |
| AO1-05 | `shared replay and identity` | Single↔batch same intent returns original operation/result; changed intent conflicts; no extra effects. | Recompute/re-admit rejected intent; reset identity registry; per-endpoint registry. |
| AO1-05 | `mixed batch preservation` | Archived rejection does not abort a following valid sibling; decoding failure still rejects whole batch before effects. | Stop batch at domain rejection; bypass shared admission. |
| AO1-06 | `archived read and restart` | Views retain shape and report Archived; fresh-database constraints/seed validation accept it; clean restart preserves it. | Stale enum/schema/status constraint; read mapping erases new status. |
| AO1-07 | `retained behavior` | Independent PV2 + Required, PV1 and G0–G3 suites all pass. | Existing seeded defects remain isolated from the AO1 task. |

For every behavioral mutant, record successful build/startup, assertion identity,
observed failure and source/build hashes. Static-negative fixtures instead record
the expected compiler/registration diagnostic and successful setup controls;
never mix those counts with runtime detection. Prefer one fault per fixture and
retain negative/inconclusive results. Test wrong named assertions and injected
infrastructure failures so neither can receive detection credit.

Use independent fixtures for direct submit, successful-reserve/compensation,
existing reservations, each inventory precedence case and clean restart. Snapshot
physical order/inventory/reservation facts before and after; include unrelated
sentinels. Keep known-good controls for both conditions, even when a mutant is
caught before the runtime verifier can execute.

## Implemented coverage

See [results and reproduction](README.md) and [evidence](evidence.json). AO1-01–06
run in `verify.py`; AO1-07 runs the unchanged retained suites separately. Physical
snapshots cover the full fixture, including unrelated sentinels. Clean restart
uses the same database without reseeding; admission identities are only replayed
within the original host lifetime.

`mutations.py` qualifies 29 running defects across guard/mapping, compensation,
precedence, identity/input binding, replay, batch continuation and read projection.
`diagnostics.py` separately records wrong-type compiler errors and declaration
reference/response/input registration failures. `alias_witness.py` supplies the
paired enum-alias comparison witness. All have known-good controls.

The planned defect list is a design space, not a claim that every example was
seeded. No stale schema/seed-validator mutant, distinct revision-only mismatch,
separate per-endpoint registry mutant or compatibility export is qualified here.
Correct schema/seeding/restart behavior is exercised by both references. The
conventional reference has no standalone API declaration to mismatch; its typed
argument controls and behavioral binding defects are exercised instead.
