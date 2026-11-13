# Evaluation glossary

Quick reference for this repository. Pilot-specific meanings are marked below; the
[protocol](cross-layer/order-fulfillment/protocol.md) defines the actual rules.

## Shared terms

| Term | Brief meaning and example |
|---|---|
| **Condition / treatment** | Configuration being compared. These terms overlap; we use **condition** for conventional versus Cohesive. A complete run configuration also specifies task, checkpoint and execution mode. |
| **Task** | One requested change with defined inputs and success criteria, such as adding cancellation. |
| **Trial / run** | One attempt at a task under a recorded configuration. Repeated attempts are separate runs. |
| **Solver** | The model plus its agent harness, instructions and tools that attempts the task. |
| **Agent harness** | Runs the model's action loop and manages its tools and context. |
| **Evaluation harness / runner** | Prepares environments, runs trials, invokes graders and retains evidence. Distinct from the agent harness. |
| **Specification / contract** | Required application behavior. An **obligation** is one requirement within it, such as preserving stock on rejection. |
| **Oracle** | Source or procedure for determining expected results, such as an independent state model. The expected result itself is **ground truth**. |
| **Verifier / grader** | Checks an attempt against the criteria. Our scripts can combine oracle and verifier roles, but the roles differ. |
| **Hidden tests** | Checks withheld from the solver. Visibility is separate from whether a check tests new behavior or preserves old behavior. |
| **Fail-to-pass / pass-to-pass** | A check changes from failing to passing, or is expected to keep passing. A **pass-to-fail** change signals a regression. |
| **Control** | A comparison that helps interpret an effect; our review-marker task provides the low-coupling comparison. |
| **Ablation** | Remove or change one mechanism while keeping other settings matched, to investigate its contribution. |
| **Admission** | Readiness criteria for including a task/configuration in an evaluation. Our protocol requires admission before calibration. |
| **Contamination / leakage** | Exposure to answers or evaluation material that compromises the comparison, including through repository history. |

## Pilot vocabulary and local meanings

| Term | Meaning here |
|---|---|
| **Case / fixture** | The application scenario / its runnable code and setup. Order Fulfillment is our cross-layer case. |
| **Baseline / G0** | **Starting application** before evolution. In experimental comparisons, baseline also means a reference condition; say “comparison baseline” when that is intended. Both conditions have a G0. |
| **Evolution / E1–E3** | Successive changes: quantity limit, cancellation, quarantine. |
| **Application checkpoint / G1–G3** | Saved application after an evolution step. E2 is the change; G2 is its resulting snapshot. This contains application code, not trained weights as in a model checkpoint. |
| **Age** | Scheduled evolution depth: fresh G0 versus aged G3. It does not imply that every earlier change succeeded. |
| **Probe task / H or L** | A targeted coding task: H adds hold; L adds review marking. A diagnostic probe is a narrower test. Ours are complete tasks with multiple obligations, scored for full correctness. |
| **Coupling** | Interaction with existing behavior. Hold affects lifecycle and fulfillment; review marking must remain informational. |
| **Gold reference** | Maintainer-built, verified correct solution; used for controlled starting snapshots and test qualification, never supplied as the target answer. |
| **Qualification** | Check that the evaluator accepts correct applications and detects deliberate defects for the intended reasons. |
| **Calibration** | Broadly, checking the measurement process. Here: separate preliminary agent runs to assess task difficulty and workflow readiness; excluded from main evidence. |
| **Matrix / test coverage table** | Maps obligations to checks, expected behavior and defect witnesses. “Matrix” is a table label here, not a special algorithm or a prescribed standard format. |
| **Cumulative scoring** | Check all active earlier obligations as well as the new task; record regressions and repairs. |

Example: a solver receives **G3 application source** in the **Cohesive condition**,
performs the **H probe task**, and is checked against hold requirements **plus all
prior active obligations**. H and L start on separate branches of the same snapshot.
