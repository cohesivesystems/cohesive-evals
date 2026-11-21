# Persisted order availability

Fulfilling B can change a reservation already shown on A. Both G0 references persist the full availability projection in PostgreSQL and refresh it on startup, after seed and creation, and before publishing a terminal fulfillment result. Direct submission changes only order status. A null reservation row represents a known empty order. The GET filters by order ID, sorts by UTF-16 ordinal ID and applies the existing row and serialized-byte limits. [Pilot contract and acceptance criteria](https://github.com/cohesivesystems/cohesive-evals/issues/57)

| Maintenance | Conventional | Cohesive |
|---|---|---|
| Define rows | SQL left joins from orders to reservations and inventory | Reuse the typed order → reservation traversal and inventory join across the existing per-order query and a new partition query |
| Persist and refresh | PostgreSQL stores the SELECT in a materialized view. One REFRESH command recomputes it. | A prepared PostgreSQL query reader hydrates the partition into typed rows. The application locks the target table, replaces its contents using binary COPY, and commits. |
| Read | Indexed order ID lookup against the persisted view | Same lookup against the persisted table |

[Conventional refresh](reference/conventional.cs) · [Cohesive refresh](reference/cohesive.cs) · [Typed query and maintenance boundaries](reference/cohesive.patch)

## SDK audit

The G0 SDK compiles and runs the relation as a parameterized PostgreSQL query. The compiled statement for this case contains bound parameters for the partition and presence tests. Embedding that statement verbatim in a PostgreSQL materialized-view definition would leave the parameters unresolved. The reference calls the prepared reader directly and hands its typed snapshot to Npgsql. Both apps retain the G0 lockfiles and the Cohesive package pin at b0af008. [Dependency manifest](../conditions/cohesive/dependency-manifest.json)

The newer SDK can declare a rooted relation materialization with an initial baseline, change capture, inverse impact traversal, checkpoints, and a generational index target. The published example binds PostgreSQL as the source and Elasticsearch as the target. The audited PostgreSQL adapter stores checkpoints and supplies source reads. I found no corresponding PostgreSQL output target that maintains the derived rows for this GET. The example also allows five minutes of lag. This pilot requires visibility by the first settled GET. [Example declaration](https://github.com/cohesivesystems/cohesive/blob/3fa9fad4/eng/examples/aspire-first/OrderWorker/FulfillmentMaterializations.cs) · [PostgreSQL infrastructure](https://github.com/cohesivesystems/cohesive/blob/3fa9fad4/src/adapters/Cohesive.Adapters.Postgres/PostgresMaterializationStorage.cs) · [Elasticsearch target](https://github.com/cohesivesystems/cohesive/blob/3fa9fad4/src/adapters/Cohesive.Adapters.Elastic/ElasticMaterializationTarget.cs)

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
python3 "$pilot/qualify.py" "$out/good" "$out/stale" "$out/live" "$out/results"
```

Scope is one host, one partition, sequential settled operations and clean restart. Both references recompute the full projection, and the Cohesive app buffers the snapshot in memory. Concurrent writes, incremental maintenance, latency and authoring effort remain unmeasured.
