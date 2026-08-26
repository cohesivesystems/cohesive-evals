# Load Search Mapping — conventional C#

This is the conventional C# baseline for the Load Search Mapping evaluation
case. Joins, required-relationship validation, and projection are expressed
directly with ordinary .NET collections and types.

Equipment is required in this baseline. This repository intentionally contains
no implementation of the later Make Equipment Optional task.

## Build and test

The workspace requires the .NET SDK pinned by `global.json`.

```bash
dotnet restore LoadSearch.slnx --locked-mode
dotnet build LoadSearch.slnx --no-restore
dotnet test LoadSearch.slnx --no-build
```

## Projects

- `src/LoadSearch.Application` contains the public contract and implementation.
- `tests/LoadSearch.Application.Tests` contains visible baseline tests.
- `tools/LoadSearch.Probe` exposes deterministic scenarios used only by the
  maintainer baseline-equivalence suite.
