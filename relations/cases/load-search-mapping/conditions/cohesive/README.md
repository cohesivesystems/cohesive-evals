# Load Search Mapping — Cohesive.Relations

This is the Cohesive.Relations baseline for the Load Search Mapping evaluation
case. The canonical relation is the authority for required relationship
traversal and result projection; the application adapter supplies in-memory
evidence and translates canonical outcomes into the shared public contract.

Equipment is required in this baseline. This repository intentionally contains
no implementation of the later Make Equipment Optional task.

## Build and test

The workspace requires the .NET SDK pinned by `global.json`. Immutable Cohesive
packages built from the source revision recorded below are stored in `packages/`.

```bash
dotnet restore LoadSearch.slnx --locked-mode
dotnet build LoadSearch.slnx --no-restore
dotnet test LoadSearch.slnx --no-build
```

## Pinned Cohesive dependency

- Package version: `0.1.0-eval.coh56.8cf0242`
- Source commit: `8cf02424cfe9c097e90eebcc96118cf78e5e1fc0`
- Source date: 2026-08-23
- `Cohesive` SHA-256: `b22dc6e0533437a2d518265b6651091057f7f1cde1b7ab5019ab554d28ab53c1`
- `Cohesive.Relations` SHA-256: `ac0fe7ee9d38b8135263798d220319a8cf57d8b8a00e47d699b7085fc90389b5`

## Projects

- `src/LoadSearch.Application` contains the public contract, canonical relation,
  evidence adapter, and implementation.
- `tests/LoadSearch.Application.Tests` contains visible baseline tests.
- `tools/LoadSearch.Probe` exposes deterministic scenarios used only by the
  maintainer baseline-equivalence suite.
