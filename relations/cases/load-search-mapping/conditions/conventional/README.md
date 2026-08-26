# Load Search application

Load Search maps Loads to Customer and Equipment data using ordinary .NET
collections and types. Customer and Equipment relationships are required by the
current application behavior.

## Build and test

The workspace requires the .NET SDK pinned by `global.json`.

```bash
dotnet restore LoadSearch.slnx --locked-mode
dotnet build LoadSearch.slnx --no-restore
dotnet test LoadSearch.slnx --no-build
```

## Projects

- `src/LoadSearch.Application` contains the public contract and implementation.
- `tests/LoadSearch.Application.Tests` contains visible application tests.
- `tools/LoadSearch.Probe` exposes deterministic scenarios used only by the
  application behavior probe.

## Public compatibility surface

External consumers depend on the public types and members in
`src/LoadSearch.Application/Contracts.cs`, plus the concrete
`LoadSearchService` and `CustomerLoadSummaryService` adapters. Do not rename,
remove, replace, or change their CLR signatures. A change request may explicitly
authorize nullable-reference annotation changes for `Load.EquipmentId` and
`LoadSearchResult.EquipmentNumber`; no other contract encoding is compatible.
