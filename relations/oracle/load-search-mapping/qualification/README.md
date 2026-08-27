# Load Search Mapping oracle qualification

This package smoke-tests the candidate oracle against ten representative
submissions. It is maintainer-only material and must never be copied into an
agent workspace.

## Contents

- `cases.json` declares the patches and compact expected result for each case.
- `patches/` contains two known-correct solutions, two combined behavioral
  regressions, and four representative gate or integrity failures.
- `observed.json` records the compact result and SHA-256 hash of each applied
  patch from the last successful run.
- `run-qualification.sh` reconstructs each submission in a temporary directory,
  builds it, runs visible tests and the private oracle, and compares the observed
  summaries with `cases.json`.

The patch runner and gate classification are reusable mechanics. The small case
list is intentionally not an exhaustive mutation suite: the six direct
behavioral scenarios are easier to inspect than dozens of task-specific seeded
programs.

## Run

The script requires the pinned .NET 10 SDK, `git`, and `jq`:

```bash
relations/oracle/load-search-mapping/qualification/run-qualification.sh
```

An optional first argument selects the observed-output path. Dependency restore
failure aborts qualification and is never classified as a submission failure.
Application or oracle-adapter compilation failure is recorded as the
contract/build result.

These artifacts qualify the candidate oracle but do not freeze it. COH-59 must
complete the independent conventional baseline review first. If that review
changes a baseline, the applicable patches and observations must be regenerated.
