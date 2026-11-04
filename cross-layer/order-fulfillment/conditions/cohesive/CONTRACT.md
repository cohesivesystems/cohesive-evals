# Fulfillment service contract

The service manages orders, inventory and one-item fulfillment in a fixed local
scope. IDs are case-sensitive opaque strings. Quantities are signed 32-bit
integers; stored available stock is nonnegative. JSON property names use camel
case. All calls use the same host-provided local identity; request JSON cannot
select a tenant or principal. This is a local application, not an authentication
example.

## Public HTTP interface

| Request | Response |
|---|---|
| POST /orders | 201 {id}; creates a Draft order. |
| GET /orders/{id} | 200 {id,status}, or 404. |
| GET /orders/{id}/details | 200 {id,status,reservations}, or 404. Each reservation is {id,sku,quantity,availableStock}. |
| GET /orders/{id}/availability | 200 array of {reservationId,sku,quantity,availableStock}, or 404 for an unknown order. |
| GET /inventory/{sku} | 200 {sku,available}, or 404. |
| POST /orders/{id}/submit | Draft becomes Submitted and returns 200 {id,status}; non-Draft returns 409 {code: "OrderNotDraft"}; unknown order returns 404. |
| POST /fulfillment | Body {requestId,orderId,sku,quantity}; 202 {operationId,resultUrl} on admission. |
| GET /fulfillment/results/{operationId} | 202 while pending, 200 {status,outcome} after domain completion, 500 {code: "ExecutionFailed"} after execution failure, or 404 for an unknown operation. |

An order with no reservations has empty arrays. Reservation arrays are ordered
by ordinal reservation ID. Direct submission does not reserve inventory or
create a reservation. Read views reflect current inventory, not historical stock.

Malformed JSON, absent fields, blank identifiers, and out-of-range integer
encodings return 400 before admission. A zero or negative quantity is valid JSON
input but causes a domain rejection. Descriptive error text is not a contract;
409 domain/identity codes are. JSON schemas are in schemas.json.

## Fulfillment behavior

Exact duplicate requestId and input return the original admission and retained
result for the lifetime of this host. A reused requestId with different input
returns 409 {code: "RequestIdentityConflict"} and starts no work. No failed
operation is retried under the same identity. The host retains at most 1000
admitted requests; additional new identities receive 503 without admission.
Existing identities remain replayable at capacity.

For a new request, the first applicable rule wins:

1. Unknown order: OrderMissing.
2. Existing reservation with the same order, SKU and quantity, with a Submitted
   order: ReservedAndSubmitted without writes. Other existing reservations:
   ReservationConflict without writes.
3. Unknown SKU: InventoryMissing.
4. Nonpositive quantity: InvalidQuantity.
5. Insufficient stock: InsufficientStock.
6. Non-Draft order: OrderRejected.
7. Otherwise decrement stock, submit the order, and create one reservation with
   ID equal to the order ID: ReservedAndSubmitted.

ReservedAndSubmitted returns {status: "Submitted", outcome: "ReservedAndSubmitted"}.
Every other listed outcome returns status Rejected. Completed domain rejections
leave inventory unchanged and create no reservation. Earlier stock changes must
be compensated if a later domain decision rejects. Physical failure is an
execution failure and does not assert rollback. Unrelated orders and stock are
preserved. Replayed results do not depend on later state changes.

## Execution and setup

Admission and result retention last only for this host. Client disconnection
cannot cancel admitted work. A single bounded host worker executes admitted
operations. Each mutation and its process-step receipt commit together in
PostgreSQL; the whole sequence is not one transaction. Independent-intent races
and crash recovery are outside this application's declared guarantees.

Inventory and preexisting records can be provisioned before the host starts with
--seed FILE and FULFILLMENT_SETUP=1, against a dedicated empty database. The file
is {orders:[{id,status}],inventory:[{sku,available}],reservations:[{id,orderId,sku,quantity}]}.
Orders may be Draft or Submitted. Quantities must be positive; referenced orders
and SKUs must exist. There is no seed/reset HTTP route. Failed setup requires a
fresh database; setup is not an application transaction guarantee.
