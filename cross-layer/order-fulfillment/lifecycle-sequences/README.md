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

## Post-session SDK replay

Assurance selected four paths totaling 24 commands within the original four-sequence, eight-steps-per-sequence limits. The required six-command scenario occupied one slot. The generator registered the public command vocabulary and executed the clean typed model from the same Submitted seed. The bounded search explored 1,916 steps and covered 36 of 266 observed decision and adjacent-decision goals. Beam pruning limited exploration. [Selector](replay/Program.cs) · [Evaluation SDK release](https://github.com/cohesivesystems/cohesive/releases/tag/eval-sdk-439aa6a9)

| Sequence | Commands | Defects detected |
|---|---|---|
| 1 (required) | `Pack Ship:1 Hold Ship:2 Release Ship:2` | Multi-unit shipment debits one |
| 2 | `Hold Pack Hold Hold Pack Ship:-1 Ship:0 Ship:1` | None |
| 3 | `Hold Release Ship:3 Ship:4` | None |
| 4 | `Hold Pack Pack Release Hold Unpack` | Release toggles a clear hold, unpack clears a hold, unpack rejects a held order |

Both original executors reproduced the same four detections. The SDK missed the final-single-unit rejection and the repeat Pack quantity reset. The two frozen authors scored 5/6 (Stateless) and 4/6 (Cohesive). The SDK traded the Cohesive author's final-unit detection for the release defect. In sequence 3 all four commands are rejected in Submitted. The selector rewards distinct named decisions and adjacent pairs, which can use budget on paths that never advance the order. This is a post-session replay on a previously seen panel. [Full evidence](evidence/replay.json)

Append `--replay` to the qualification command above. Only the clean selector project uses the newer SDK. Both frozen submissions, executors and graded models use their original dependencies. The replay requires repeatable clean selection and equal first failures across both executors on every paired defect.

The clean replay also uses the registered commands to execute 130 qualification paths and the four selected paths against the independent oracle. Setup resolves the required command names before search.

Warm selection cost on an Apple M5 Max (1,916 steps: 64.6 ms, 31.3 MiB; 4,096 steps: 124.3 ms, 65.2 MiB). Figures are medians of five calls and current-thread managed allocations for the whole selector, including offline execution. The 4,096-step run increases beam width to 128 and depth to 16 to reach the default candidate ceiling. [Measurement samples](evidence/selection-cost.json)

To reproduce after qualification, build the generated Cohesive Suite project in Release mode and pass the same required scenario to the measurement entry point:

```sh
cd /tmp/lifecycle-sequence-run/generator/cohesive
dotnet build Suite/Suite.csproj -c Release --no-restore
echo '{"Required":["Pack","Ship:1","Hold","Ship:2","Release","Ship:2"],"Qualification":[]}' | DOTNET_TieredCompilation=0 dotnet Suite/bin/Release/net10.0/Suite.dll --measure
```
