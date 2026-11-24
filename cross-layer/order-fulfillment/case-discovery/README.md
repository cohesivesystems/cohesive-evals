# Guarded shipping case discovery

Two fresh authors selected single-step Ship cases from the same five lifecycle statuses and shipping-hold flag. Each received eight minutes and at most ten distinct cases. This pilot measures case selection. The benchmark supplies the execution adapter and a shared contract oracle. HTTP, persistence and multi-command sequences are outside this experiment.

| Result | Conventional | Cohesive |
|---|---:|---:|
| Unique cases on the clean reference | 10/10 | 10/10 |
| Matched executable defects detected twice | 5/5 | 5/5 |
| Constant-false Ship guard | Detected twice at runtime | Rejected at model compilation |

The [conventional author](submissions/conventional.cs) enumerated the status enum and both Boolean values. The [Cohesive author](submissions/cohesive.cs) prepared the production Ship transition and projected the generated states to status and hold. Both submitted the entire finite input domain under the same ten-case ceiling. This establishes reuse of the machine definition for case selection; one session per condition and an exhaustive budget give no evidence of superior discovery or speed.

The [post-session Cohesive replay](replay/cohesive.cs) uses the parameterless overload from [SDK 3291ecf3](https://github.com/cohesivesystems/cohesive/releases/tag/eval-sdk-3291ecf3). The grader checks its ordered proposals against the frozen submission twice before running the panel.

```csharp
var cases = ship.GenerateCases(new Order("order-A", "partition-A"), new() { MaxCases = 10 });
```

Six defect pairs were pinned. Replacing the Ship guard with constant false made the Cohesive success return unreachable. After the first replay stopped at this setup failure, we added a classification for its exact model compiler diagnostic, kept the original control and both submissions, and reran the panel. Five pairs remained independently executable in both conditions. [Run evidence](evidence/results.json) · [Compiler diagnostic](evidence/reject-clear-diagnostic.txt) · [Session receipts](sessions.json)

The [brief](task.md), [paired defects](controls.json), production deltas and SDK lockfiles were frozen at `9291254` before dispatch. Each author received only their own materialized fixture, on a shared machine with directory isolation by instruction. The conventional author could use idiomatic .NET or Stateless; the Cohesive author was directed to use Assurance generation. Both could rehearse on their clean implementation. Generator setup and fixture preparation preceded the sessions.

The grader checks each clean implementation on the full ten-input domain. It runs the submitted generator twice on clean code, freezes its proposals, and replays them twice against each defect. Independently, it exhausts the domain on each broken implementation and requires exactly the pinned witness and identical observed results in both conditions. The grader records the known unreachable-return diagnostic separately and excludes that pair from the behavioral denominator. Other build, setup or execution errors abort grading. A detection requires an observed contract mismatch on a submitted case.

Run from the repository root with the pinned .NET SDK and Python 3.13.

```sh
PYTHONPATH=. python3 -B cross-layer/order-fulfillment/case-discovery/grade.py /tmp/ship-replay
```

Use a fresh output directory. The SDK package manifest pins the published artifacts. [SDK #598](https://github.com/cohesivesystems/cohesive/pull/598) · [Pilot #65](https://github.com/cohesivesystems/cohesive-evals/issues/65)
