# Batch fulfillment

Start the service with `--batch-input FILE --batch-output FILE`. Both flags are
required together. Input must be readable; output must be a new, distinct file
in a writable directory. HTTP remains available after the batch completes.

Input is a JSON array of at most 100 items. Empty is valid. Malformed JSON, a
non-array or excess items produces `{"error":"InvalidBatch"}` without execution.
Otherwise items execute in order, awaiting completion individually. Invalid
items do not stop valid siblings. Successful items are not rolled back.

Fulfillment fields are exactly `requestId`, `orderId`, `sku`, `quantity`.
Identifiers must be nonblank strings. Quantity must be an exact signed 32-bit
integer JSON number (`1.0` and `1e0` are accepted). Numeric strings, booleans and
duplicate properties are invalid. Extra properties are ignored. These decoding
rules also apply to POST /fulfillment. Nonpositive quantities reach the domain.

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
