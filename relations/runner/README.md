# Evaluation runner

This directory contains the candidate local runner/scorer foundation. It can
construct and score deterministic dry-run submissions, but it cannot launch an
agent, freeze artifacts, calibrate the task, or execute the pilot.

COH-59 remains the admission gate for those deferred actions.

## What the runner does

For one condition, `run.sh`:

1. verifies the condition and oracle Git tree IDs pinned by
   `config.v0.1.json`;
2. exports only the selected condition tree and initializes it as a fresh,
   standalone Git repository;
3. records a file manifest and rejects evaluation-material leakage;
4. optionally applies one or more patches to simulate a completed agent run;
5. preserves the final workspace, manifest, Git status, and binary-capable diff;
6. copies the submission to a separate scoring workspace;
7. restores and builds the application, runs visible tests, compiles the oracle
   adapter, and executes hidden checks; and
8. writes `run.json` plus raw logs and normalized obligation evidence.

The run directory is immutable by convention: the runner refuses to overwrite
an existing run ID. A correct invocation exits zero for both complete and
incomplete submissions because incompleteness is an experimental result.
Infrastructure failure writes an invalid record when possible and exits 2.

## Candidate configuration

`config.v0.1.json` pins candidate—not frozen—baseline and oracle revisions and
tree IDs. It also contains the exact task, obligation IDs, initial top-level
allowlists, and leakage indicators. If COH-59 changes a baseline, these pins and
the affected validation evidence must be revised before freeze.

`run-record.schema.json` defines the normalized record shape. Raw files remain
authoritative evidence; normalized records may be regenerated from them when a
parser changes.

## Run one dry submission

```bash
relations/runner/run.sh \
  --condition conventional \
  --run-id example-baseline \
  --output-root /private/tmp/cohesive-eval-runs
```

To replay a known patch, repeat `--patch` in application order:

```bash
relations/runner/run.sh \
  --condition cohesive \
  --run-id example-good \
  --output-root /private/tmp/cohesive-eval-runs \
  --patch relations/oracle/load-search-mapping/qualification/patches/cohesive/LSM-QUAL-GOOD-COH.patch
```

`DOTNET_CLI` may select a non-default .NET executable. Restore failures are
infrastructure failures; submission-authored build or contract failures are
valid incomplete outcomes.

## Validate the runner

```bash
relations/runner/validate.sh
```

The validation replays five cases: both untouched baselines, both known-correct
solutions, and one incompatible-contract submission. It checks the normalized
completion gates and obligation vectors without invoking a model.

Validation writes evidence under a new temporary directory and prints its path.
Pass an explicit unused directory as the first argument to retain evidence at a
known location.
