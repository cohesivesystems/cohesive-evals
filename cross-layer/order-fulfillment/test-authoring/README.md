# Order lifecycle test-authoring pilot

**Both suites caught all six held-out defects.** Each passed twice on its clean reference. Each mutant produced the same relevant named assertion failure on both runs. The pair reached the detection ceiling for this panel. It gives no ranking of the two stacks for defect discovery. [Issue #63](https://github.com/cohesivesystems/cohesive-evals/issues/63)

| Planted behavior | Conventional first observation | Cohesive first observation |
|---|---|---|
| Reject repeat pack | Domain returned no order for Packed + Pack | Compiled transition rejected Packed + Pack |
| Reopen a cancelled order on unpack | Domain returned Submitted | Compiled transition accepted the command |
| Dispatch the unpack route to pack | Draft unpack returned the pack conflict code | Submitted unpack returned Packed |
| Return the wrong pack conflict code | HTTP returned OrderNotDraft | HTTP returned OrderNotDraft |
| Read Packed as Submitted in details | Seeded order details returned Submitted | Seeded order details returned Submitted |
| Drop inventory compensation after rejected fulfillment | 15 units remained available after reserving 5 of 20 | 0 units remained available after reserving all 20 |

The first two defects surfaced offline in each suite. The other four surfaced through the public HTTP application on PostgreSQL. For the compensation defect, the independent grader reserved two units on each implementation and confirmed both returned the expected rejection but left 18 units. The authors independently chose different quantities to expose the same fault. The [run evidence](evidence/results.json) includes exact assertions, expected and actual values, and independent witness observations.

## Authoring conditions

| | Conventional | Cohesive |
|---|---|---|
| Starting point | Packed fixture, Stateless 5.21.0 | Packed fixture, SDK 0.1.0-eval.54e9910b |
| Wall-clock ceiling | 8 minutes | 8 minutes |
| Time to frozen submission | 2m 29s | 4m 09s |
| Offline technique | Enumerate state and command pairs and call the production aggregate’s Apply method | Compile the production entity transitions, execute them with the reference interpreter and project the resulting state |

Both authors wrote their own contract-based oracle, covered all 16 state/command pairs, and exercised fulfillment and concurrency through HTTP. The Cohesive author reported that the typed offline preparation helper refused machine-bound entities, then used the lower-level interpreter successfully. This is a concrete ergonomics difference. The elapsed times are individual session observations. [Stateless suite](submissions/conventional/Program.cs) · [Cohesive suite](submissions/cohesive/Program.cs) · [Pinned SDK helper](https://github.com/cohesivesystems/cohesive/blob/54e9910b/src/Cohesive.Transitions/Execution/OfflineTransition.cs)

## Protocol and reproduction

- The starting application is the merged lifecycle at `adf73a0`. Complete G2 and Packed fixture input fingerprints, the package locks and the [fixture pins](pins.json) guard against source drift.
- The [author brief](task.md), scaffold and six matched [defects](controls.json) were committed before dispatch. Authors ran in fresh contexts with the same inherited model settings. Each received its own fixture directory and rehearsal host. The supplied fixtures excluded earlier suites, graders and defects. Directory isolation was by instruction on a shared machine.
- Both authors could build freely and rehearse on their own clean host, then submit early. Only their single submitted source file was retained. The [session receipts](sessions.json) record dispatch time, submission time and hash. Both sources were frozen in commit `5258a89` before grading.
- Each suite must first pass twice on its clean implementation. The grader makes one source change at a time, builds the candidate, and independently demonstrates the intended fault via HTTP on a separate seeded database. It runs the frozen suite twice, each time against a fresh database with a 90-second ceiling. A named assertion earns detection credit after its observed mismatch is attributable to the planted behavior. Build failures, unconfirmed mutants, exceptions and timeouts earn no credit.
- The published panel is suitable for replay. A future blind discovery trial needs a fresh panel. One author per condition and six contract-derived defects limit the conclusions. Restart behavior and detection of concurrency-specific defects were outside this panel.

From the repository root, with Docker and the pinned .NET SDK available, run:

```sh
PYTHONPATH=. python3 -B cross-layer/order-fulfillment/test-authoring/grade.py /tmp/lifecycle-authoring-replay
```

Use a fresh output directory. The grader writes results, environment metadata, and per-candidate build and execution logs.
