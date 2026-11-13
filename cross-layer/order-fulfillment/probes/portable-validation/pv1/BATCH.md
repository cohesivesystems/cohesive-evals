# Batch fulfillment API

`POST /fulfillment/batch` accepts an `application/json` array of 0–100 fulfillment
items. A valid envelope returns HTTP 200 with per-item results, including partial
or all-item rejection. Malformed JSON, a non-array, any item decoding failure or excess items returns
HTTP 400 without any admission or effects. Oversized arrays return
`{"error":"InvalidBatch"}`; binding failures use the framework's unspecified 400
body. Empty arrays return `{"items":[]}`.

Each item executes through the same queue as `POST /fulfillment`. Items settle in
array order. A decoded null item or an item with null/blank identifiers gets per-item 400
while valid siblings continue. Successful
siblings are not rolled back. There is no batch-level identity or automatic retry.

Both endpoints use standard ASP.NET Core typed binding with the same JSON
options. The entire array must decode before the batch service runs. Missing
required fields or incompatible field types reject all siblings, even valid
items preceding the failure. Canonical
fields are `requestId`, `orderId`, `sku`, `quantity`. Property matching is
case-insensitive; unknown fields are ignored. Repeated properties whose values
deserialize use the last value. Identifiers must be nonblank strings with
case-sensitive values. The built-in Int32 converter accepts `1` and `"1"`, but
rejects `1.0`, `1e0`, their quoted forms, booleans, null and overflow. Nonpositive
quantities reach the domain. Schemas describe canonical typed values; wire checks
cover the serializer's accepted encodings.

The response is `{"items":[...]}`. Each item has `index`, `admission:{status,body}`
and, when admitted, `completion:{status,body}`. Nested status/body match the
single-item API; unspecified 400/503 bodies are null. Execution failures are
500/ExecutionFailed within the item; later items continue.

Both operations share the host's 1000-identity registry. Exact typed-intent
replays retain admission/result; conflicting reuse is 409/RequestIdentityConflict.
Replay works in either direction and at capacity. The host owns accepted work,
so a client disconnect does not cancel it. G3 domain behavior and host-lifetime
retention remain unchanged; there is no added durability guarantee.

## Public example

Seed `batch-seed.json` in a dedicated empty database using ordinary setup mode,
then start the ordinary HTTP host. POST `batch-examples.json` to
`/fulfillment/batch`, or run `python3 tests/pv1_checks.py --url URL`. The smoke
check posts the batch itself and verifies one success, one invalid item,
duplicate replay, single-item replay and remaining stock.
