# Asynchronous availability maintenance

Fulfillment completion acknowledges the source writes. The availability GET reads the latest committed projection. After a command completes, read `GET /availability/checkpoint` and save its `requested` revision. Once `applied` reaches that revision, the projection includes the command. Revisions are local to each database and count source statements. [Pilot issue and authoring budget](https://github.com/cohesivesystems/cohesive-evals/issues/59)

| | Conventional | Cohesive |
|---|---|---|
| Detect committed changes | PostgreSQL statement triggers on orders, reservations and inventory | Same triggers on the three mapped entity tables |
| Publish | PostgreSQL refreshes its materialized view | The SDK runs the compiled typed relation through `ResyncAsync()` |
| Read | Indexed SQL on the view | Typed lookup on the persisted target |

Both reference implementations use the [same worker](reference/AvailabilityMaintenance.cs). Each source transaction advances a durable request counter. A worker serializes refreshes, captures the current revision, publishes the projection, then acknowledges only the captured revision. Source writers can advance the request counter during publication. A crash between publication and acknowledgement leaves work pending and a full refresh can be replayed. The shared counter serializes source writers at the trigger. The pilot uses one host and one partition.

## Run

Use the [synchronous pilot builder](../materialized-availability/README.md) to produce the pinned base fixtures. The async builder checks each baseline's full input digest before applying the [host changes](reference/host.patch). From the repo root:

```sh
export PYTHONPATH=.
sync=cross-layer/order-fulfillment/materialized-availability
pilot=cross-layer/order-fulfillment/async-availability
out=$(mktemp -d)
python3 "$sync/build.py" "$out/base"
python3 "$pilot/build_async.py" "$out/base" "$out/good"
for defect in eager late-publication over-acknowledge; do
  python3 "$pilot/build_async.py" "$out/base" "$out/controls/$defect" --defect "$defect"
done
python3 "$pilot/qualify_async.py" "$out/good" "$out/controls" "$out/results"
```

Seed or start the HTTP host before launching the separate worker with `--availability-worker`. The operator command `--resync-availability` now queues a rebuild and prints its requested revision. `--availability-worker-once` processes one captured revision for batch operation and deterministic recovery checks. Initial bootstrap builds the first readable snapshot.

## Comparison

With the worker stopped, B reserved two units of X and completed. A still showed 5. After publication, A and B both showed 3. The verifier killed the worker while its checkpoint write was blocked in PostgreSQL. Restarting replayed that refresh without introducing duplicate rows. A second reservation committed during an operator rebuild. The first acknowledgement stopped at the captured revision, and the next worker caught up through the new write.

The unrelated order U was physically rewritten in both conditions. PostgreSQL row versions changed for all five seeded orders after B settled. Both strategies refresh the full projection. This pair demonstrates freshness and recovery behavior and leaves selective impact discovery untested. It provides no comparative authoring-time or latency result. The implementations were developed together under the same per-condition ceiling.

The verifier also checks actual GET plans, UTF-16 ordering, and the inherited row and byte limits. Eager HTTP refresh, delayed publication, and acknowledgement beyond the processed revision must each fail a named assertion in both conditions. [Qualification evidence](evidence.json)
