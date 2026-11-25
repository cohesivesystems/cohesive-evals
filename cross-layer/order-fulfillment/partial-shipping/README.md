# Partial-shipping case discovery

This offline pilot extends the merged guarded-Ship baseline at `2b1741c` with a shipment quantity and a remaining quantity. Both conditions use the same public single-step contract. The SDK pin is `0.1.0-eval.3291ecf3` and the conventional machine uses Stateless 5.21.0. The adapters execute the actual order domain. Transport, storage and reachability of synthetic seed states are outside the experiment.

**Stateless caught 6/6 held-out defects; Cohesive caught 5/6.** Each author submitted eight cases. Both suites caught acceptance of zero and excessive quantities, subtracting one instead of the amount shipped, bypassing the hold for a partial shipment, and shipping a Submitted order. The difference was the last-unit defect: the order incorrectly rejected shipping exactly one unit when one remained.

| Selected exact shipment on a clear Packed order | Result |
|---|---|
| Conventional: 1 remaining, ship 1 | Exposed the defect |
| Cohesive: 2 remaining, ship 2 | Passed even on the defective implementation |

The [conventional author](submissions/conventional.cs) chose representatives directly from the two Stateless transitions. The [Cohesive author](submissions/cohesive.cs) flattened the generated groups to state/command pairs and explicitly required `Remaining > 1` for the exact-shipment representative. The clean model proposed the missing 1/1 input; selection discarded it.

With the author's template and ranges, `MaxCases = 8` raised a state-exploration budget error. With a ceiling of 1,024, Assurance returned 290 pairs across 40 pre-states; 210 pairs were in the pilot domain. This run illustrates two distinct SDK needs: accessing pairs directly, and selecting a small suite while retaining important intersections of boundaries. The observed score describes one author per condition and one six-defect panel.

[Graded proposals and witnesses](evidence/results.json) · [Budget audit](evidence/budget.json) · [Frozen submissions and pins](sessions.json)

Each author gets a fresh context, its own clean fixture, eight minutes and eight distinct submitted cases. There are 280 legal inputs. Authors can screen larger candidate pools during generation; the eight-case ceiling applies to executed test cases. Both receive the same brief. The Cohesive author uses Assurance; the conventional author can use idiomatic .NET or Stateless. Each sees only its own fixture by instruction on a shared machine. Authors do not see the oracle or controls.

The grader checks all 280 inputs on each clean reference before scoring. For every mutant it independently confirms the pinned witness and requires the full set of incorrect inputs **and their observed outcomes** to match across implementations. The author’s generator runs twice on clean code. The same frozen cases then run twice against every mutant. Only reproducible, observed mismatches earn credit. Build, execution, protocol and unmatched-control errors abort the run. This measures case selection with a supplied oracle and executor, not the cost of writing assertions.

[Author brief](task.md) · [Mutation panel](controls.json) · [Starting baseline](../case-discovery/README.md) · [Tracking issue](https://github.com/cohesivesystems/cohesive-evals/issues/67)

From the repository root, use a fresh output directory and the pinned .NET SDK.

```sh
PYTHONPATH=. python3 -B cross-layer/order-fulfillment/partial-shipping/qualify.py /tmp/partial-shipping-replay
```

## Post-session Assurance selection

The [SDK replay](selection/Program.cs) supplies only the clean Ship transition, the original template and seed, quantity ranges and budgets. With `MaxCandidates = 1024` and `MaxCases = 8`, Assurance selected eight distinct pairs from 240 bounded candidates. It selected clear Packed **1 remaining / ship 1** as the intersection of quantity one above zero and equality with remaining on the observed full-shipment edge. This was a post-session development replay using [SDK dac729ee](https://github.com/cohesivesystems/cohesive/releases/tag/eval-sdk-dac729ee). The frozen authors' original score and session receipts are retained above.

| Precommitted defect | SDK-selected cases, two runs |
|---|---|
| Reject the last unit | Detected twice |
| Accept zero | Missed |
| Accept excessive quantity | Missed |
| Subtract one regardless of shipped quantity | Missed |
| Ignore the hold on partial shipments | Missed |
| Allow a partial shipment from Submitted | Missed |

The selector covered its observed goals in six cases. The initial SDK stopped there; the published revision fills two remaining slots in stable candidate order. Its one accepted partial shipment requested a single unit, which masks the subtract-one defect. Its zero-quantity and held inputs used states already ineligible to ship. These cases illustrate how model-derived goal coverage and independent defect detection can diverge.

The replay generated the cases and explanations twice on clean code and graded those fixed inputs twice per defect. Both frozen authors also reproduced their original results on the replay SDK, byte for byte. The evidence lists all eight inputs, their coverage goals, residual goals and independent defect witnesses. [Replay evidence](evidence/select-cases.json) · [SDK PR #599](https://github.com/cohesivesystems/cohesive/pull/599)

```sh
PYTHONPATH=. python3 -B cross-layer/order-fulfillment/partial-shipping/qualify.py /tmp/partial-select-replay --select
```
