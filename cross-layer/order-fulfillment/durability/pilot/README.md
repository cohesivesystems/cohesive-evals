# G0 durability authoring pilot

[#55](https://github.com/cohesivesystems/cohesive-evals/issues/55) records the freeze before either author started. This is one calibration pair. The author task and exact starting trees are in [task.md](task.md) and [pins.json](pins.json).

## Results

| One session per condition | Conventional | Cohesive |
|---|---:|---:|
| Elapsed to first passing implementation build (author reported) | 2m 05s | 3m 11s |
| Elapsed to submission | 8m 35s | 8m 52s |
| Independent recovery scenarios passed | 10/10 | 10/10 |
| Retained HTTP checks passed | 52/52 | 52/52 |
| Invariant sequences passed (60 commands each) | 3/3 | 3/3 |
| Persistent capacity, replay and conflict | Passed | Passed |
| Application C# lines added / removed, including evaluator hooks | +310 / −84 | +246 / −61 |

Both submissions built with locked dependencies. Their retained HTTP observations and invariant-sequence results matched exactly. The ten scenarios cover eight abrupt termination points, uninterrupted completion and terminal engine failure. The scheduler and database remained available throughout host restarts.

| Responsibility in the frozen patch | Conventional | Cohesive |
|---|---|---|
| Fulfillment decisions | Moved inspection, reserve, submit, record and compensation into an orchestrator and five named activities | Retained the entire `FulfillmentProcess` definition |
| Effect replay | Reused the store and its receipts, adding a transaction-scoped lock before receipt lookup | Bound PostgreSQL transition receipts to the order, inventory and reservation repositories |
| Admission and retained results | Authored PostgreSQL operations table, replay/conflict and capacity checks, dispatch and result persistence | Authored the same responsibilities in `OperationQueue`. It serializes admission, counts rows, and polls every 100 ms when idle |
| Crash instrumentation | Activities call the evaluator after store operations | Activity host matches four transition IDs and inspects typed outcomes before signaling an applied effect |

These observations describe two submitted patches. The pilot did not measure throughput, multi-host contention or the distribution of authoring effort. Estimating typical differences would require additional independent pairs on a frozen SDK and rubric.

### Cohesive API follow-ups

The submission used `ScheduleCohesiveProcessAsync`. The pinned SDK also exposes `AdmitCohesiveProcessAsync` for accepted, replayed and conflicting starts. A follow-up should run that API against the same public contract, especially atomic capacity across distinct identities, replay at capacity, and retained results after restart. That would establish which pieces need a typed admission API and which already exist. [Pinned admission implementation](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/adapters/Cohesive.Adapters.DurableTask/DurableTaskProcessStartAdmission.cs)

Two smaller API candidates come from the host code. A typed post-commit callback for applied transitions could replace the evaluator's ID switch and result decoding. A registration helper could share the data converter between the Durable Task client and worker. Evaluate these changes in a subsequent SDK run against the same crash boundaries.

The [conventional submission](conventional/submission.patch) and [Cohesive submission](cohesive/submission.patch) preserve the exact authored changes. Each condition's evidence directory contains the build manifest, recovery observations, G0 report, HTTP observations and capacity result. Neither session tested a hosted scheduler.

## Reproduction

Each author received a fresh session with no parent conversation, a separate working directory and an identical instruction to read its task and implement it there. To reconstruct either starting tree, copy the corresponding G0 condition at the pinned commit, add the three packages in `durability/packages` to the Cohesive feed, and copy `task.md` to `TASK.md`. Initialize a fresh Git repository and stage all starting files, including pinned packages. Compare the Git tree hash with the freeze. Apply the condition's submission patch to this tree to reproduce its authored changes.

The 60-minute limit is an elapsed-time ceiling with early submission allowed. Both authors could use their installed SDK, NuGet cache, public package XML docs, visible tests, and local builds. They ran on the same machine. Workspace boundaries and use of allowed materials were instructed, without OS-level read isolation. Local tool permissions and warm caches are part of the calibration environment. No evaluator results were sent back to the authors. Token use and cost were not separately capped.

For grading, use `durability/build.py::build_candidate` on the frozen submissions, then use `durability/verify.py --condition CONDITION --point POINT --references FROZEN_PARENT --output FRESH_DIR` for each of its ten points. Use `verification/verify.py --condition CONDITION --fixtures FROZEN_PARENT --output FRESH_DIR` with a fresh scheduler for the original G0 contracts and invariant sequences. The verifier owns the PostgreSQL service; the public app targets .NET SDK 10.0.402 and the scheduler package version is 1.25.0. [Dependency pins](../dependency-manifest.json) identify the Cohesive source, extra packages and scheduler image. PostgreSQL is `postgres:17.10-alpine3.24`, local image ID `sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193`.

[Control results](control.json) record the existing known-good applications passing the same ten recovery scenarios per condition.

A supplemental capacity check was specified while the authors worked, before grading either submission. It admits 1,000 distinct requests through HTTP, checks the first overflow, replay and conflict, kills the host, and repeats those three observations after restart. Run `PYTHONPATH=. python3 -B cross-layer/order-fulfillment/durability/pilot/capacity.py ABSOLUTE_APP_DLL FRESH_OUTPUT CONDITION` from the repo root. Both known-good controls passed. The [control record](control.json) identifies their build manifests and capacity outcomes. This check is reported separately from the ten pre-existing recovery scenarios.
