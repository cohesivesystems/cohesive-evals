# Persisted order availability

Fulfilling B can change a reservation already shown on A. Both G0 references persist the full availability projection in PostgreSQL and refresh it on startup, after seed and creation, and before publishing a terminal fulfillment result. Direct submission changes only order status. A null reservation row represents a known empty order. The GET filters by order ID, sorts by UTF-16 ordinal ID and applies the existing row and serialized-byte limits. [Pilot contract and acceptance criteria](https://github.com/cohesivesystems/cohesive-evals/issues/57)

| Maintenance | Conventional | Cohesive |
|---|---|---|
| Define rows | SQL left joins from orders to reservations and inventory | Reuse the typed order → reservation traversal and inventory join across the existing per-order query and a new partition query |
| Persist and refresh | PostgreSQL stores the SELECT in a materialized view. One REFRESH command recomputes it. | The app binds the partition query with `MaterializeRows` and awaits `ResyncAsync()`. The SDK executes the bound SELECT and publishes all rows in one PostgreSQL transaction. |
| Read | Indexed order ID lookup against the persisted view | Same lookup against the persisted table |

[Conventional refresh](reference/conventional.cs) · [Cohesive refresh](reference/cohesive.cs) · [Typed query and maintenance boundaries](reference/cohesive.patch)

## SDK audit

The Aspire example uses PostgreSQL for source rows, CDC and checkpoint storage. Its destination is an Elasticsearch shadow generation. The pilot now uses the published synchronous PostgreSQL row target. The app supplies the typed relation, partition and target name. The adapter owns parameter binding, serialized replacement and rollback. The previous revision hydrated the whole partition and copied it back through Npgsql in application code. [Aspire example](https://github.com/cohesivesystems/cohesive/tree/3fa9fad4/eng/examples/aspire-first/OrderMaterialization) · [Published eval SDK](https://github.com/cohesivesystems/cohesive/releases/tag/eval-sdk-62c8a5f3) · [Package pins](sdk/dependency-manifest.json)

## Operator resync

Run `dotnet Fulfillment.Application.dll --resync-availability` with the same Orders connection string as the running app. The command returns after the refreshed rows commit. Both conditions use the same refresh operation for ordinary maintenance and explicit repair.

The verifier leaves A and B showing 5 while authoritative stock remains 3. It observes stale data through the running host, invokes the command twice, and checks persisted rows and immediate GETs after each invocation. A no-op operator command must fail the named explicit-resync assertion.

## Qualification

The independent oracle joins seed facts with acknowledged command effects. A separate inspector reads persisted rows before the GET and while the host is stopped. PostgreSQL auto_explain records the actual application queries for a populated, empty and unknown order. Each control must fail its named assertion. Missing plans, build failures and unavailable infrastructure earn no detection credit. The retained paired G0 verifier covers Unicode ordering, multiple reservations, row and byte limits, and seeded invariant sequences. [Recorded results and plans](evidence/qualification.json)

From the repository root with Docker, Python and the pinned .NET SDK available, choose a new output directory for every run.

```sh
export PYTHONPATH=.
pilot=cross-layer/order-fulfillment/materialized-availability
out=$(mktemp -d)
python3 "$pilot/build.py" "$out/good"
python3 "$pilot/build.py" "$out/stale" --defect stale-stock
python3 "$pilot/build.py" "$out/live" --defect live-read
python3 "$pilot/build.py" "$out/noop" --defect resync-noop
python3 "$pilot/qualify.py" "$out/good" "$out/stale" "$out/live" "$out/noop" "$out/results"
```

Scope is one host, one partition, sequential settled operations and clean restart. Both references recompute the full projection inside PostgreSQL. Latency and authoring effort remain unmeasured.

**Next evolution.** Move maintenance to an asynchronous worker. Specify the freshness promise at fulfillment completion and test a reservation committed during resync, including catch-up after worker restart.
