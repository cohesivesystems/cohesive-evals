# Offline order lifecycle sequences

Two fresh authors each had eight minutes to write four sequences of up to eight commands and an executor for their condition. Every sequence starts from the same Submitted order with three units. The required scenario crosses partial shipping, a hold, a rejected shipment, release and completion. Both authors used all 32 steps and carried the actual order returned by the domain into the next step. [Author brief](task.md) · [Issue #69](https://github.com/cohesivesystems/cohesive-evals/issues/69)

The conventional author called `Order.Apply` on each command, retaining the previous order when it returned null. The Cohesive author prepared four typed transitions once, dispatched each command to its transition, and advanced to `result.State`. Both authors chose their sequences by hand. [Conventional suite](submissions/conventional.cs) · [Cohesive suite](submissions/cohesive.cs)

## Results

| Held-out defect | Stateless | Cohesive |
|---|---|---|
| Unpacking clears an active hold | Caught | Caught |
| Unpacking a held order is rejected | Caught | Caught |
| Shipping multiple units debits only one | Caught | Caught |
| Shipping the final single unit is rejected | Caught | Caught |
| Releasing an already-clear order sets a hold | Caught | Missed |
| Packing again restores the original quantity | Missed | Missed |
| **Total** | **5/6** | **4/6** |

The conventional author tried Release immediately after Pack on an unheld order. Both authors repeated Pack, but neither did so after a partial shipment. On the clean reference, `Pack → Ship:1 → Pack` leaves two units. The defective Pack restores three. [Per-sequence observations at the first failing step](evidence/results.json)

There was one author per condition and a supplied oracle. Four controls target hold or packing behavior, and two revisit shipping defects from the prior single-step panel. The score describes these particular sequence choices. It does not estimate a framework effect.

## Qualification

The contract, clean fixture patches, mutation pairs and their witnesses were committed before author dispatch. Each fresh context saw only its own clean fixture by instruction on a shared machine. Both submissions were hash-frozen before grading. The SDK and Stateless locks come from the merged partial-shipping pilot at `9f40af4`. [Session receipts](sessions.json) · [Panel](panel.json)

An independent Python oracle checks every step's acceptance, order ID, status, hold and remaining quantity. Qualification visits every reachable clean state by a shortest command prefix and appends each legal next command (13 states × 10 commands, plus six pinned witness paths). Both implementations must match the oracle on clean qualification paths and their own authored sequences. For every paired defect, the named witness must fail and all qualification paths must produce identical mismatches across conditions. The grader runs the clean proposals twice and replays the resulting sequences twice per defect. Build, protocol or execution errors abort grading.

Run from the repository root with .NET 10 and Python 3.10 or later, using a fresh output directory.

```sh
PYTHONPATH=. python3.13 -B cross-layer/order-fulfillment/lifecycle-sequences/grade.py /tmp/lifecycle-sequence-run
```
