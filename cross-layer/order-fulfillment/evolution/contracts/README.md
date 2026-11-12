# Shared contract supplements

COH-161 resolves the matrix's contract gaps. These are candidate contracts for
future reference implementations, not a claim that those implementations exist.
G0 application files remain unchanged.

`bundle.py` emits identical public artifacts for either condition: `CONTRACT.md`,
`schemas.json`, `seed.schema.json`, and `contract-examples.json`. It combines G0
with only the selected active supplements. H/L texts are identical at both ages.
The bundle contains no generator, future supplement, sibling probe or hidden test.

```sh
python3 bundle.py --checkpoint G1 --output /tmp/g1-contract
python3 bundle.py --checkpoint G3 --probe H --output /tmp/g3-h-contract
```

For a task, use its target contract with its starting source snapshot: E1 gets G1
contract + G0 source, E2 gets G2 + G1, E3 gets G3 + G2. H/L get G0 or G3 plus their
selected probe. The `--output` directory must not exist. Copy its four files into
the participant snapshot; never copy this directory. Full workspace/history audits
and visible HTTP behavior checks belong to reference/runner qualification.

| Decision | Contract |
|---|---|
| Hold conflicts | `OrderNotHoldable` / `OrderHoldNotReleasable` |
| Quantity-limit body | Required non-null integral JSON number, positive int32; extras ignored; invalid input precedes missing SKU |
| New bodyless commands | Body ignored; lookup then lifecycle rule |
| Seed compatibility | Versioned schema per active set; optional new facts with neutral defaults; no live migration |
| Persistence | Settled business state survives clean restart; request history need not |
| Read limits | Recompute actual serialized bytes including reviewMarked; unchanged limits |

Validate all eight contract profiles and public examples:

```sh
python3 -m pip install -r requirements-test.txt
python3 -B -m unittest discover -s . -p 'test_*.py'
```

`schemas.json` defines decoded JSON values. Raw malformed JSON, HTTP routing,
identity lookup, ignored extra fields and stateful precedence require HTTP tests
when the reference implementations are added. The examples are public schema
examples, not hidden fixtures or runtime qualification.

Read-boundary fixtures must use the actual default .NET web serializer. For each
active details shape, start with an existing order and one reservation whose SKU
is a long ASCII `a` string, then adjust its length until the response is exactly
1,000,000 bytes; seed matching inventory. Test one byte below, exactly at, and one
byte above separately for details and availability. Test both marker values.
For row limits use 999/1000/1001 short reservations, keeping byte size below the
limit. Excess returns 422 ReadResultTooLarge with no partial data. Keep these
synthetic read fixtures separate from generated invariant worlds. Do not reuse a
G0 byte count or substitute Python's JSON escaping for the .NET serializer.
