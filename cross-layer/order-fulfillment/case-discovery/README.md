# Guarded shipping case discovery

Two fresh authors selected single-step Ship cases from the same five lifecycle statuses and shipping-hold flag. Each received eight minutes and at most ten distinct cases. This pilot measures case selection. The benchmark supplies the execution adapter and a shared contract oracle. HTTP, persistence and multi-command sequences are outside this experiment.

The [brief](task.md), [paired defects](controls.json), production deltas and SDK lockfiles were frozen at `9291254` before dispatch. Each author received only their own materialized fixture, on a shared machine with directory isolation by instruction. The conventional author could use idiomatic .NET or Stateless; the Cohesive author was directed to use Assurance generation. Both could rehearse on their clean implementation. Generator setup and fixture preparation preceded the sessions.

The grader checks each clean implementation on the full ten-input domain. It runs the submitted generator twice on clean code, freezes its proposals, and replays them twice against each defect. Independently, it exhausts the domain on each broken implementation and requires exactly the pinned witness and identical observed results in both conditions. A build, setup or execution error aborts grading. A detection requires an observed contract mismatch on a submitted case.

Run from the repository root with the pinned .NET SDK and Python 3.13.

```sh
PYTHONPATH=. python3 -B cross-layer/order-fulfillment/case-discovery/grade.py /tmp/ship-replay
```

Use a fresh output directory. The SDK package manifest pins the published artifacts. [SDK #598](https://github.com/cohesivesystems/cohesive/pull/598) · [Pilot #65](https://github.com/cohesivesystems/cohesive-evals/issues/65)
