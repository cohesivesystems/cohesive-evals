# Load Search application

Load Search maps Loads to Customer and Equipment data. The canonical
Cohesive.Relations relation is the authority for required relationship traversal
and result projection; the application adapter supplies in-memory evidence and
translates canonical outcomes into the public contract.

## Build and test

The workspace requires the .NET SDK pinned by `global.json`. Immutable Cohesive
packages built from the source revision recorded below are stored in `packages/`.

```bash
dotnet restore LoadSearch.slnx --locked-mode
dotnet build LoadSearch.slnx --no-restore
dotnet test LoadSearch.slnx --no-build
```

## Pinned Cohesive dependency

- Package version: `0.1.0-alpha.1.8cf0242`
- Source commit: `8cf02424cfe9c097e90eebcc96118cf78e5e1fc0`
- Source date: 2026-08-23
- `Cohesive` SHA-256: `61e34836eb1f473c4e497ac2bda60124e800a825a52b9f0a1ccbf130a68cda16`
- `Cohesive.Relations` SHA-256: `483fa75d0d4ed4d30be5238ae6f04c60f0ae18802d265139f2c07dd994ca6993`

## Projects

- `src/LoadSearch.Application` contains the public contract, canonical relation,
  evidence adapter, and implementation.
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
