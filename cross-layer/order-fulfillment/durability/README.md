# Durable reference qualification

Read the candidate [protocol supplement](protocol.md). This directory is
maintainer-only and must not enter participant workspaces.

```sh
python3 durability/build.py
python3 durability/verify.py
python3 durability/qualify.py
python3 durability/regression.py
python3 durability/check_diagnostics.py
python3 durability/test_verifier_errors.py
python3 durability/test_build_evidence.py
```

The builder materializes separate reference applications under ignored
`artifacts/durable-reference/`. It copies G0, adds the reviewed overlays and
Durable Task package references, and builds both with committed NuGet lockfiles.
Program, backend, registration and project overlays are committed source; the
builder copies them without source rewriting. Project files use `.csproj.overlay`
until materialization to prevent editor restores outside their fixture context. It never changes G0 fixtures.
The conventional overlay supplies an orchestrator with activities over the
existing store, with seven typed activities and typed call wrappers; the Cohesive overlay prepares the unchanged authored process
for its native Durable Task interpreter and calls `AdmitCohesiveProcessAsync`
for canonical start admission. Conventional schedules its typed orchestrator
directly with the SDK. Each condition owns its HTTP admission/dispatch code;
there is no shared execution interface or application execution-state wrapper.
Both retain a PostgreSQL HTTP admission record for the 1,000-identity capacity
limit, replay, and recovery before scheduler handoff. This product-level
plumbing counts as application integration in each condition.

Verification starts disposable PostgreSQL and pinned Durable Task emulator
containers, uses fresh databases for scenarios, kills/restarts API/worker
processes at named barriers, and checks recovery plus business invariants.
Only owned processes and containers are removed. Evidence stays under
`artifacts/durability/`; a successful report is written only when all scenarios
pass. The scheduler remains alive during these worker-failure tests.

Additional Cohesive adapter packages are built from the same baseline source
revision and checked against the local SHA-256 manifest. To rebuild their full
dependency closure without modifying baseline packages:

```sh
python3.13 packaging/build-packages.py /absolute/path/to/cohesive \
  --extra-root src/adapters/Cohesive.Adapters.DurableTask/Cohesive.Adapters.DurableTask.csproj \
  --output /tmp/order-durable-packages/packages
```

Only the three additional package IDs belong in `durability/packages`; existing
baseline dependency IDs stay pinned to the baseline artifacts. Review package
hash changes explicitly. No scored agent runs or production durability claims
follow from these reference tests.

Each build records source, project/configuration, lockfile, local package and
output-file hashes in a build manifest. Recovery, qualification and regression
check these before and after execution, rejecting stale source or binaries. Run
`python3 durability/test_build_evidence.py` to check these guards.

The recovery qualifier requires matching known-good source and build evidence,
then builds twelve mutants (six per condition): admission loss on restart,
resume only after POST, terminal failure left pending, missing reservation,
abandoned compensation and duplicate reservation. Only the named
behavioral assertion counts; failed builds or barrier/startup failures do not.
The regression command runs all 52 baseline checks and 180 invariant commands
per condition against the durable references. Public observations are still
compared across conditions; execution implementation bytes may differ.

Verified 2026-11-11: 20 known-good recovery scenarios, twelve detected durable
application mutants, and 52 contract checks plus 180 invariant commands per
condition. Compact evidence summaries are committed alongside this document;
full local logs and traces remain under ignored artifacts. Both reference builds
restore with locked dependencies and compile with zero warnings/errors.
Independent review and calibration/execution-manifest admission remain pending.

Focused diagnostic checks cover missing public results, exact repository lookup,
missing/ambiguous binding codes, unsupported realization, renamed barrier targets,
and early infrastructure assertions. Both execution paths reuse the Cohesive
completion mapper and repository resolver. `Canceled` is compatibility-only and
not emitted by SDK 1.25.0; it is defensively mapped to terminal failure alongside
Failed/Terminated, not claimed as an exercised cancellation workflow.
