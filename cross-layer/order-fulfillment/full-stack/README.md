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
