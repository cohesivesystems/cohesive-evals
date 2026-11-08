# Durable reference qualification

Read the candidate [protocol supplement](protocol.md). This directory is
maintainer-only and must not enter participant workspaces.

```sh
python3 durability/build.py
python3 durability/verify.py
python3 durability/qualify.py
python3 durability/regression.py
```

The builder materializes separate reference applications under ignored
`artifacts/durable-reference/`. It copies G0, adds the reviewed overlays and
Durable Task package references, and builds both with committed NuGet lockfiles. It never changes G0 fixtures.
The conventional overlay supplies an orchestrator with activities over the
existing store, with seven typed activities and typed call wrappers; the Cohesive overlay prepares the unchanged authored process
for its native Durable Task interpreter. Both use identical persisted admission
and result retention.

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
per condition against the durable references.

Verified 2026-11-07: 20 known-good recovery scenarios, twelve detected durable
application mutants, and 52 contract checks plus 180 invariant commands per
condition. Compact evidence summaries are committed alongside this document;
full local logs and traces remain under ignored artifacts. Both reference builds
restore with locked dependencies and compile with zero warnings/errors.
Independent review and calibration/execution-manifest admission remain pending.
