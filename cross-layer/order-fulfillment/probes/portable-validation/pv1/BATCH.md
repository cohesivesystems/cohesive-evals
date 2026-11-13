# Batch fulfillment

Start the service with `--batch-input FILE --batch-output FILE`. Both flags are
required together. Input must be readable; output must be a new, distinct file
in a writable directory. HTTP remains available after the batch completes.

Input is a JSON array of at most 100 items. Empty is valid. Malformed JSON, a
non-array or excess items produces `{"error":"InvalidBatch"}` without execution.
Otherwise items execute in order, awaiting completion individually. Invalid
items do not stop valid siblings. Successful items are not rolled back.

HTTP uses standard ASP.NET Core DTO binding. Batch deserializes each item with
those same configured JSON options, including required constructor fields.
Canonical fields are `requestId`, `orderId`, `sku`, `quantity`. Property matching
is case-insensitive; unknown fields are ignored. Repeated properties whose values
deserialize use the last value. Identifiers must be nonblank strings; their values
remain case-sensitive. Quantity uses the built-in signed 32-bit integer converter:
`1` and `"1"` work; `1.0`, `1e0`, their quoted forms, booleans, null and overflow
fail. Nonpositive quantities reach the domain. Equivalent deserialized intents
replay the same request. Schemas describe canonical typed values; wire checks
cover accepted encodings that JSON Schema cannot distinguish.

The output is published atomically as `{"items":[...]}`. Each item contains
`index`, `admission:{status,body}` and, when admitted,
`completion:{status,body}`. Status/body match HTTP; unspecified 400/503 bodies
are null. There is no completion for admission failures. Execution failures are
500/ExecutionFailed; later items continue. File/configuration failures stop the
host with nonzero exit, not a successful batch response.

Batch and HTTP share the same queue, request identities, retained results and
1000-identity capacity. Exact duplicates replay; conflicting reuse is 409
RequestIdentityConflict. Replay batch receipts through the ordinary result and
admission routes. State-dependent behavior and all other HTTP contracts remain
those of G3. There is no batch rollback, automatic retry or crash recovery.

## Public example

In a dedicated empty database, seed `batch-seed.json` using the ordinary setup
mode. Start with `--batch-input batch-examples.json --batch-output RESULT.json`.
After RESULT.json appears, run `python3 tests/pv1_checks.py --url URL --output
RESULT.json`. The example admits one success, rejects one malformed item and
replays the first item. It also checks replay through HTTP and remaining stock.
