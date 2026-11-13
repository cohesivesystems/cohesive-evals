## Informational order review

Add a persistent order-review resource keyed by order ID with Boolean `marked`.
No record means false. This is independent of order lifecycle and fulfillment.

| Request | Success | Failure |
|---|---|---|
| POST /orders/{id}/mark-reviewed | 200 `{id,marked:true}` | 404 unknown order |
| POST /orders/{id}/clear-review | 200 `{id,marked:false}` | 404 unknown order |

Both commands are idempotent and accept every existing lifecycle state. No body
is required or read; an optional body is ignored. Add required Boolean
`reviewMarked` to summary and details, default false. The marker survives all
allowed lifecycle changes; no timestamps, notifications or reason fields exist.

Only review state changes. Submission, fulfillment and other lifecycle commands cannot read
it to make decisions. Inventory, reservations, lifecycle status, availability,
request identities/results and unrelated review records remain unchanged.

Existing details row/byte limits apply to the **current** response including
`reviewMarked`; availability has no new field. At equal reservation count, a
larger details response may exceed the byte limit while availability succeeds.
