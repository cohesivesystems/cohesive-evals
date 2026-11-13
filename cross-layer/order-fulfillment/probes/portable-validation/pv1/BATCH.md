# Batch fulfillment CLI

Start the service with `--batch-cli true`. Send one JSON array per stdin line;
receive one JSON response per stdout line. Logs go to stderr. HTTP stays
available while stdin is open. EOF stops the host normally. Without this flag,
the service runs in its ordinary HTTP mode.

Arrays may contain 0–100 items. Malformed lines, non-arrays and excess items
return `{"error":"InvalidBatch"}` without admission or effects. The next line
still works. Invalid items get 400 while valid siblings execute in order. Each
admitted item settles before the next starts; successful siblings are not rolled
back. A typed batch application service uses the same queue as HTTP.

HTTP uses standard ASP.NET DTO binding; the CLI uses the same JSON options.
Canonical fields are `requestId`, `orderId`, `sku`, `quantity`. Property matching
is case-insensitive; unknown fields are ignored. Repeated properties whose values
deserialize use the last value. Identifiers must be nonblank strings and remain
case-sensitive values. The built-in Int32 converter accepts `1` and `"1"`, but
rejects `1.0`, `1e0`, their quoted forms, booleans, null and overflow. Nonpositive
quantities reach the domain. Schemas describe canonical typed values; wire checks
cover the serializer's accepted encodings.

A valid envelope returns `{"items":[...]}`. Each item has `index`,
`admission:{status,body}` and, when admitted, `completion:{status,body}`.
Status/body match HTTP; unspecified 400/503 bodies are null. Execution failures
are 500/ExecutionFailed; later items continue. Stream/host failures are operational
failures, not successful batch responses.

HTTP and all CLI lines share the host's 1000-identity registry. Exact typed-intent
duplicates replay; conflicting reuse is 409/RequestIdentityConflict. Replays work
in either direction and at capacity. Domain behavior remains G3. No automatic
retry, batch rollback or crash recovery is added.

## Public example

Seed `batch-seed.json` in a dedicated empty database using ordinary setup mode.
Start with `--batch-cli true > results.jsonl`, then paste the single line from
`batch-examples.json` into stdin. In another terminal, run
`python3 tests/pv1_checks.py --url URL --output results.jsonl` after the result
appears. It checks one success, one invalid item, duplicate replay, HTTP replay
and remaining stock. End the CLI session with EOF after checks finish.
