# Cohesive package preparation

The Cohesive condition vendors two local packages so a run does not depend on a
mutable checkout or package feed. Protocol v0.1 uses source commit
`8cf02424cfe9c097e90eebcc96118cf78e5e1fc0` and package version
`0.1.0-alpha.1.8cf0242`.

Before packing, apply [`remove-task-specific-guide.patch`](remove-task-specific-guide.patch)
to a clean archive of that source revision. The patch changes documentation
packaging only: it omits `docs/GETTING_STARTED.md`, whose optional-Equipment
example is a task-specific hint, and removes the resulting dead README link. It
does not change library source or XML API documentation.

```bash
git apply --unidiff-zero remove-task-specific-guide.patch
```

Pack `src/Cohesive/Cohesive.csproj` and
`src/Cohesive.Relations/Cohesive.Relations.csproj` in Release configuration with:

```text
Version=0.1.0-alpha.1.8cf0242
RepositoryCommit=8cf02424cfe9c097e90eebcc96118cf78e5e1fc0
ContinuousIntegrationBuild=true
```

Committed package hashes (used to verify the vendored artifacts, not to claim
bit-for-bit deterministic NuGet archive metadata):

| Package | SHA-256 |
|---|---|
| `Cohesive.0.1.0-alpha.1.8cf0242.nupkg` | `61e34836eb1f473c4e497ac2bda60124e800a825a52b9f0a1ccbf130a68cda16` |
| `Cohesive.Relations.0.1.0-alpha.1.8cf0242.nupkg` | `483fa75d0d4ed4d30be5238ae6f04c60f0ae18802d265139f2c07dd994ca6993` |

The condition lockfiles must be regenerated after a package version or content
change and subsequently restored only in locked mode.
