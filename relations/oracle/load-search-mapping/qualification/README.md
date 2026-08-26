# Load Search Mapping oracle qualification

This package proves that the candidate oracle distinguishes correct solutions,
known defects, completion-gate failures, and treatment-integrity bypasses in
both conditions. It is maintainer-only material and must never be copied into an
agent workspace.

## Contents

- `cases.json` declares 28 immutable qualification submissions derived from the
  baseline revision. A non-baseline submission applies its condition's
  known-correct patch followed by at most one seeded mutation patch.
- `patches/` contains separate conventional and Cohesive known-correct patches,
  per-check seeded defects, contract and visible-test gate defects, and the two
  treatment-integrity defects.
- `expectations.json` freezes the complete expected gate, check, obligation, and
  treatment-integrity vectors for all submissions.
- `observed.json` records the complete oracle evidence and SHA-256 hash of every
  applied patch from the successful qualification run.
- `run-qualification.sh` reconstructs every submission in an isolated temporary
  directory, builds the application and oracle adapter, executes visible tests
  and the private oracle, and rejects any difference from `expectations.json`.

## Run

The script requires the pinned .NET 10 SDK, `git`, and `jq`:

```bash
relations/oracle/load-search-mapping/qualification/run-qualification.sh
```

An optional first argument selects the observed-output path. Dependency restore
failure aborts qualification and is never classified as a submission build
failure. Application or oracle-adapter compilation failure is recorded as the
contract/build result.

## Qualified result

The recorded run establishes:

- both known-correct submissions pass every behavioral and integrity check;
- both untouched required-Equipment baselines fail the optionality obligations;
- every `LSM-BHV-*` check fails for a targeted seeded defect in each condition;
- contract-breaking submissions fail the build gate and do not execute runtime
  obligations;
- visible-test defects fail that independent gate while the hidden oracle still
  passes; and
- the conventional dependency and Cohesive parallel-mapper defects fail only
  their applicable treatment-integrity checks.

These artifacts qualify the candidate oracle but do not freeze it. COH-59 must
complete the independent conventional baseline review first. If that review
changes a baseline, all patches and vectors must be regenerated and requalified.
