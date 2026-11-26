# Full-stack order fulfillment development pilot

Carry one Cohesive application and its database forward. Start from cohesive-evals `fa7d21af204308f0e4594d5fbf5bda6c78596a35` (#70), its Cohesive lifecycle reference and published SDK `0.1.0-eval.439aa6a9` (locks and package digests under `../lifecycle-sequences/replay`). The checkpoint overlay exposes and persists the existing offline shipping and hold rules. PostgreSQL image: `postgres:17.10-alpine3.24`. This is a development pass; record SDK changes and rerun the whole path on one released stack before freezing.

| Step | Change | Checks retained at every later checkpoint |
|---|---|---|
| 0 | Persist the existing lifecycle | Pack a three-unit order, hold it, reject shipping, preserve identity, status and remaining quantity across restart. Retain the existing lifecycle sequence contract. |
| 1 | Release a quantity under hold | Upgrade that same row. A legacy held order starts with zero released units. Release adds a positive allowance up to the remaining held units. Shipping consumes both remaining quantity and allowance; rejects preserve both. Full release clears the hold; setting a hold revokes the allowance. |
| 2 | Materialize shippable quantity | The persisted view equals the order after release, shipment, rejection, restart and resync. Unrelated orders retain their values. |
| 3 | Expose actions via API and MCP | Both surfaces advertise the same feasible actions and quantity bounds; execution independently enforces them. |
| 4 | Plan fulfillment with an agent | Given a held order and a fulfillment goal, discover actions and ship only the permitted quantity. Record tool calls and verify actual order state. |
| 5 | Interrupt and resume | Recover an acknowledged operation without duplicating shipment. The held remainder, view and discovery agree after recovery. |

The Step 1 allowance counts unshipped units approved while a hold remains active. Unpack/repack preserves it. A whole-order release makes all remaining units shippable. Shipping the final unit moves the order to Shipped. Each step inherits the previous working application; fresh grading checks all earlier obligations. Future steps have their own implementation PRs.

## Running the first evolution

[Path tracker #71](https://github.com/cohesivesystems/cohesive-evals/issues/71) · [Partial release #72](https://github.com/cohesivesystems/cohesive-evals/issues/72)

Step 0 is checkpoint commit `6232419`. Its host delta binds shipping commands and maps the existing hold and remaining quantity fields to PostgreSQL. The setup seed can supply a multi-unit order. The original public create route still creates a one-unit order.

From the repository root, run the live migration check in a fresh directory with Python 3.13, .NET 10, and the pinned PostgreSQL Docker image available locally.

```sh
PYTHONPATH=. python3.13 -B cross-layer/order-fulfillment/full-stack/verify.py /tmp/full-stack-release-run
```

The verifier seeds a Submitted three-unit order through the old application, packs and holds it over HTTP, and restarts the old host. It checks the old schema, runs the migration twice on the same database, and starts the new application without reseeding. It also starts the evolved application against a separate empty database and creates an order through the public API. The clean lifecycle oracle runs 130 paths against each version. A previously applied full release and repeated hold retain their original semantics.

To materialize the carry-forward Step 1 application separately:

```sh
PYTHONPATH=. python3.13 -B cross-layer/order-fulfillment/full-stack/build.py /tmp/full-stack-step1 --partial-release
```

The runnable host project is under `cohesive/src/Fulfillment.Application` in the output. For an existing Step 0 database, stop that host and apply [migrate.sql](partial-release/migrate.sql) before launching Step 1. A new empty database initializes directly. `POST /orders/{id}/release-quantity` and `POST /orders/{id}/ship` accept a JSON body such as `{"quantity":1}`. `GET /orders/{id}/shipping` returns the committed state. The hold flag remains set after a quantity grant, even when the allowance covers all remaining units; only the whole-order release command clears it.
