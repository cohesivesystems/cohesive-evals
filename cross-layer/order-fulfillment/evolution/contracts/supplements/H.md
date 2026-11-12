## Order hold

Add persistent status `OnHold` to order summary/details.

| Request | Current status | Response |
|---|---|---|
| POST /orders/{id}/hold | Draft or OnHold | 200 summary, OnHold |
| same | Any other existing status | 409 `{code:"OrderNotHoldable"}`, unchanged |
| POST /orders/{id}/release-hold | OnHold or Draft | 200 summary, Draft |
| same | Any other existing status | 409 `{code:"OrderHoldNotReleasable"}`, unchanged |
| Either command | Unknown order | 404 |

No request body is required or read; an optional body is ignored. Both commands
are idempotent and change only order status. Terminal states cannot be reopened.
Other lifecycle commands retain their existing allowed source states.

Direct submit of OnHold returns 409 `{code:"OrderOnHold"}`. Fulfillment returns
HTTP 200 `{status:"Rejected",outcome:"OrderOnHold"}` at the lifecycle decision,
after all active inventory restrictions. Other non-Draft states retain their
specified outcomes. Completed rejection leaves the order held with no new
reservation or net stock change. Availability still reports actual reservations.

Release permits a later distinct request to proceed subject to all other rules.
Old requests retain their original admission/result, including held rejections.
Unrelated orders, inventory and reservations remain unchanged.
