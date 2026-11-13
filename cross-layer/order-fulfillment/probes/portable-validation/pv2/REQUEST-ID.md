# Fulfillment request ID limit (PV2)

Both `POST /fulfillment` and `POST /fulfillment/batch` require a nonblank
`requestId` of at most **64 UTF-16 code units**. A supplementary Unicode character
counts as two units: 32 emoji fit; 32 emoji plus one ASCII character do not.
Length 64 is allowed; 65 is rejected. Case and exact text remain significant.
Do not trim, normalize or truncate IDs. Order IDs, SKUs and read routes have no
new length limit.

This is application validation after standard typed binding. An overlength ID
returns single-item HTTP 400 or batch item admission 400 with null body and no
completion. It consumes no identity/capacity and produces no business effects.
Check it before identity lookup and capacity: even at capacity, invalid input
returns 400, a valid new ID returns 503, and a retained valid ID replays.

Valid siblings continue in order. Nonpositive quantities remain domain decisions.
All other PV1 behavior, including whole-request decoding failure, shared replay,
per-item domain outcomes and host-owned execution, remains unchanged. Each PV2
host starts fresh; no migration of previously admitted long IDs is implied.

Run `python3 tests/pv2_checks.py --url URL` against an ordinary seeded fixture for
public ASCII and Unicode boundary examples. The PV1 schema describes the canonical
request shape; a JSON Schema `maxLength` would count Unicode characters rather
than UTF-16 units and is not the length oracle for this rule.
