# Asynchronous availability maintenance

Fulfillment completion acknowledges the source writes. The availability GET reads the latest committed projection. After a command completes, read `GET /availability/checkpoint` and save its `requested` revision. Once `applied` reaches that revision, the projection includes the command. Revisions are local to each database and count source statements. [Pilot issue and authoring budget](https://github.com/cohesivesystems/cohesive-evals/issues/59)

| | Conventional | Cohesive |
|---|---|---|
| Detect committed changes | PostgreSQL statement triggers on orders, reservations and inventory | The availability projection determines the PostgreSQL publication, replication slots and wake-up triggers |
| Publish | PostgreSQL refreshes its materialized view | The SDK resolves affected order IDs from logical changes and replaces their rows with the typed projection |
| Read | Indexed SQL on the view | Typed lookup on the persisted target |

The conventional worker captures the request revision and refreshes the entire view. The Cohesive hosted worker follows Aspire’s direct and inverse impact routes, including inventory → reservations → orders. It commits affected row groups before saving each input’s checkpoint and acknowledging its replication slot. Both workers expose requested/applied watermarks and acknowledge only their captured revision. Explicit resync repairs the full target.

Cohesive runs with PostgreSQL logical replication enabled, a stable position-authentication key, and one slot per relation input. The fixture generates a key per isolated database and shares it across that run’s processes. The app declares the reservation fields and order key once with `RowsByRoot`. `MaterializeAsyncRows` uses that projection for SQL publication, typed lookup and change-impact planning. The app supplies its local partition, target table and the existing schedule name used by the crash gate. The SDK supplies the remaining PostgreSQL defaults. Deployment is single-partition. Readers can observe committed intermediate pages during catch-up.

## Run

Use the [synchronous pilot builder](../materialized-availability/README.md) to produce the pinned base fixtures. The async builder checks each baseline's full input digest before applying the [conventional host changes](reference/host.patch) or the [Cohesive worker binding](reference/rooted.patch). From the repo root:

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

After B reserved two units of X, Cohesive rewrote A and B. Conventional rewrote A, B, C, R and U. Both served 3 available for A and B. The verifier records PostgreSQL `xmin` for every persisted reservation row per order, checks physical contents before the worker acknowledges, and checks U again after restart. The earlier development attempt used a shared full-refresh worker and rewrote all five orders in both conditions. This iteration includes SDK development outside the original authoring budget. The comparison concerns behavior and physical rewrites for this fixture.

The verifier also checks actual GET plans, UTF-16 ordering, and the inherited row and byte limits. Eager HTTP refresh, delayed publication, and acknowledgement beyond the processed revision must each fail a named assertion in both conditions. [Qualification evidence](evidence.json)
