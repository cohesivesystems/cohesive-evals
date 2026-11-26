# Reservation availability on PostgreSQL

[Issue #76](https://github.com/cohesivesystems/cohesive-evals/issues/76) asks for the first 50 pickable orders at a warehouse. An order qualifies when packed, unheld and every reserved SKU has enough physical stock for that order at that location. Orders share stock independently on this planning screen. A pick-list read does not allocate inventory.

[Measured results across both scales](RESULTS.md) · [Per-run evidence](evidence)

## Implementations

| | Conventional | Cohesive |
|---|---|---|
| Starting point | ASP.NET, Npgsql and the G0 order store | Same host and Npgsql, with G0 Cohesive entities, transitions and repository mappings |
| Warehouse fields | Add columns to orders with SQL | Extend the typed Order and its PostgreSQL mapping. The SDK creates and checks the mapped columns. |
| Pick-list calculation | Indexed query on read | Same indexed query on read, scoped to the model's local partition |
| Maintenance and restart | PostgreSQL maintains the indexes in the source transaction | Same. Schema admission also checks the Cohesive model at startup. |

[The query](candidate/pick-list.sql) reads packed, unheld orders in queue order, sums reservation lines by SKU within each candidate, and compares those totals with location-specific stock. SQL `bool_and` on zero groups returns NULL, excluding an order with no reservations. Missing stock contributes zero units. Limit applies after eligibility. Ordinary views give the shared Npgsql endpoint the same logical column names on the two physical schemas. The endpoint performs one parameterized SQL statement per GET.

- [Cohesive model and mapping](candidate/cohesive.patch)
- [Conventional PostgreSQL binding](candidate/conventional.sql) and [Cohesive PostgreSQL binding](candidate/cohesive.sql)
- [Shared HTTP endpoint](candidate/PickList.cs) and [stock table](candidate/stock.sql)

This implementation compares two PostgreSQL-backed G0 applications using their shared native SQL option. It does not exercise Cohesive's relation compiler or async materialization worker. The first smoke run tried to add undeclared columns directly to Cohesive's entity table; its schema check rejected them on restart. The measured version declares those fields on the model.

## Reproduce

Use .NET 10.0.402, Python 3.13 and Docker with enough resources for the capped app and database. From the repository root:

```sh
pilot=cross-layer/order-fulfillment/pick-list
python3.13 -m venv /tmp/pick-venv
/tmp/pick-venv/bin/pip install -r "$pilot/requirements.txt"
python3.13 -B "$pilot/workload.py"
python3.13 -B "$pilot/build.py" /tmp/pick-build
PYTHONPATH=. /tmp/pick-venv/bin/python -B "$pilot/qualify.py" /tmp/pick-build /tmp/pick-runs
python3.13 -B "$pilot/summarize.py" /tmp/pick-runs
```

Use fresh output directories. A short plumbing check can use `--smoke --scales 4000 --repetitions 1`. Only the default run qualifies the issue workload. The harness commits mutations directly to source tables, allowing it to measure from PostgreSQL commit acknowledgment and isolate the read path. Logs record scheduler lag separately from request latency. Anonymous resident bytes are end-of-run snapshots, not peak RSS. Database block counters include foreground reads, visibility probes and write-related activity. Work per write divides whole-workload cost by the number of source commits.

[Protocol](protocol.md) · [Frozen fixture and independent oracle](workload.py) · [Expected hashes](golden.json)
