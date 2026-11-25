# Partial-shipping case discovery

This offline pilot extends the merged guarded-Ship baseline at `2b1741c` with a shipment quantity and a remaining quantity. Both conditions use the same public single-step contract. The SDK pin is `0.1.0-eval.3291ecf3` and the conventional machine uses Stateless 5.21.0. The adapters execute the actual order domain. Transport, storage and reachability of synthetic seed states are outside the experiment.

Each author gets a fresh context, its own clean fixture, eight minutes and eight distinct submitted cases. There are 280 legal inputs. Authors can screen larger candidate pools during generation; the eight-case ceiling applies to executed test cases. Both receive the same brief. The Cohesive author uses Assurance; the conventional author can use idiomatic .NET or Stateless. Each sees only its own fixture by instruction on a shared machine. Authors do not see the oracle or controls.

The grader checks all 280 inputs on each clean reference before scoring. For every mutant it independently confirms the pinned witness and requires the full set of incorrect inputs **and their observed outcomes** to match across implementations. The author’s generator runs twice on clean code. The same frozen cases then run twice against every mutant. Only reproducible, observed mismatches earn credit. Build, execution, protocol and unmatched-control errors abort the run. This measures case selection with a supplied oracle and executor, not the cost of writing assertions.

[Author brief](task.md) · [Mutation panel](controls.json) · [Starting baseline](../case-discovery/README.md) · [Tracking issue](https://github.com/cohesivesystems/cohesive-evals/issues/67)

From the repository root, use a fresh output directory and the pinned .NET SDK.

```sh
PYTHONPATH=. python3 -B cross-layer/order-fulfillment/partial-shipping/qualify.py /tmp/partial-shipping-replay
```
