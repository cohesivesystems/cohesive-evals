# Order Fulfillment baseline fixtures

These are the matched G0 starting applications for the [pilot protocol](protocol.md).
Each condition is a standalone .NET 10 service with PostgreSQL persistence,
order submission, stock reservation and compensation, and nested order reads.
The conventional condition uses domain methods and explicit Npgsql persistence.
The Cohesive condition uses entity transitions, a process definition, query models,
and the native PostgreSQL and ASP.NET adapters.

## Run and verify

Each condition contains its own setup README, public contract, schemas, package
lockfile and identical visible HTTP checks. From this directory:

```sh
(cd conditions/conventional && dotnet restore --locked-mode && dotnet build --no-restore)
(cd conditions/cohesive && dotnet restore --locked-mode && dotnet build --no-restore)
python3 verification/verify.py
```

Verification requires Docker with `postgres:17.10-alpine3.24` available locally.
It creates a disposable container and separate databases, seeds both fixtures,
compares normalized HTTP observations, and removes the container afterward.
Logs and reports are written under ignored `artifacts/verification/`.
Give a participant only the selected condition directory. Parent protocol,
packaging and verification files are maintainer material.

## Dependency provenance

Cohesive packages were built from source revision
`b0af008d85871ad8866d7d4311707ecd926529de`, using SDK 10.0.402, at version
`0.1.0-eval.b0af008`. The 21 vendored packages include the dependency closure and
analyzers; the adjacent manifest records SHA-256 hashes. The packager exports
that Git revision, excluding working-tree changes. To rebuild from an authorized
local Cohesive source checkout:

```sh
python3.13 packaging/build-packages.py /absolute/path/to/cohesive
```

Rebuilding may change archive hashes; review and update the manifest together
with the packages. Source access and redistribution follow the upstream project
terms. These packages are fixture dependencies, not a public package release.

## Verification status

On 2026-11-03 both builds completed with zero warnings and errors. Both services
passed all 52 visible HTTP checks with identical normalized observations against
PostgreSQL 17.10. Checks cover domain outcomes, precedence, compensation, reads,
request replay, identity conflicts, invalid inputs and unrelated-state preservation.
Regression checks also cover Unicode ordinal sorting and exact row/serialized-byte
limits on both read endpoints (1,000 rows and 1,000,000 bytes; excess returns 422).
The verifier also runs [maintainer invariant sequences](verification/README.md)
against an independent settled-state model and read-only persistence observer.
This establishes tested G0 parity, not independent design review or full oracle qualification.

Independent conventional review, the private oracle, evolved checkpoints,
calibration and scored agent runs remain pending. Hold and review-marker target
implementations are deliberately absent from participant starting applications.

## Qualification and durability follow-through

[Application-defect qualification](qualification/README.md) builds isolated broken
applications and requires obligation-specific verifier failures. The separate
[durability supplement and reference solutions](durability/README.md) add Durable
Task execution, controlled worker crashes, recovery qualification and baseline
regression checks. All of this material remains outside participant G0 fixtures.

## Hold/control and evolution preparation

The maintainer-only [milestone-to-test matrix](evolution/test-matrix.md) maps
G0–G3 and the independent fresh/aged H/L probes to visible examples, hidden
checks, reference behavior and deliberate defects. It also records contract
decisions and the implementation/qualification sequence. The shared
[contract bundle generator](evolution/contracts/README.md) provides active-only
public supplements, wire/seed schemas and examples for both conditions. It is a preparation
plan. The [E1 quantity-limit references and qualification](evolution/e1/README.md)
implement G1 in both conditions while retaining G0. The [E2 cancellation references](evolution/e2/README.md)
add G2 with cumulative G0/E1 checks and cancellation qualification. The
[E3 quarantine references](evolution/e3/README.md) add G3 with cumulative checks
and quarantine qualification. H/L references, acceptance-breadth review and
campaign admission remain outstanding.

## Follow-up probes

The separate [single/batch API validation specification](probes/portable-validation/protocol.md)
defines single-item/batch API validation reuse followed by a shared input-rule change.
The [PV1 batch references](probes/portable-validation/pv1/README.md) implement its
first step with independent qualification. The [PV2 request ID limit](probes/portable-validation/pv2/README.md)
adds the shared 64-UTF-16-unit input rule and its qualification. These separate
probes do not extend the existing pilot matrix.
