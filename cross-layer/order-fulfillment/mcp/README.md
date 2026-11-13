# Unscored semantic MCP integration pilot

This separate integration candidate adds a development MCP host to the actual G0 Cohesive fixture.
It does not change the existing conditions, Relations runner configuration or frozen protocol decisions.
It runs scripted edits, not a coding agent, and never invokes the private oracle or emits a benchmark score.

The main protocol excludes dedicated semantic tools. A future evaluated `cohesive-mcp` condition therefore
needs its own approved treatment and admission record. This preparer supplies two byte-identical participant
starting trees, `cohesive-mcp-off` and `cohesive-mcp`, with the same upgraded framework, neutral guide and
published server. Only the connection configuration differs. An eventual agent driver must enforce the off
condition's prohibition on semantic tool use, including manual launches; this local harness is not a security
sandbox and does not yet enforce an experimental treatment against an agent.

## Reproduce

Use Python 3.13+, Git, the fixture's pinned .NET SDK (10.0.402), and an authorized local Cohesive checkout
containing the commit in `pilot.json`. Preparation can restore external packages from the configured feeds.
Parity checking also requires Docker and `postgres:17.10-alpine3.24` available locally.
Use fresh output directories outside this repository. From the repository root:

```sh
python3.13 -B cross-layer/order-fulfillment/packaging/build-packages.py /absolute/path/to/cohesive \
  --revision 8be91cec2f13b9ac3700eecfc41e85d3b2c26e40 \
  --version 0.1.0-eval.mcp.8be91cec \
  --extra-root src/Cohesive.Semantics/Cohesive.Semantics.csproj \
  --output /tmp/mcp-pilot-dependencies/packages

python3.13 -B cross-layer/order-fulfillment/mcp/prepare.py \
  --cohesive-source /absolute/path/to/cohesive \
  --packages /tmp/mcp-pilot-dependencies/packages \
  --output /tmp/mcp-pilot

python3.13 -B cross-layer/order-fulfillment/mcp/smoke.py /tmp/mcp-pilot \
  --output /tmp/mcp-pilot-smoke

python3.13 -B cross-layer/order-fulfillment/mcp/qualify.py /tmp/mcp-pilot \
  --output /tmp/mcp-pilot-parity

python3.13 -B -m unittest discover -s cross-layer/order-fulfillment/mcp -p 'test_*.py'
```

The framework pin is the reviewed #509 head, now merged upstream. The fixture pin is independent and retains
G0 application source. The existing baseline's `b0af008` packages remain untouched; the custom package builder
requires explicit revision, version and separate empty output. Archives may have different package hashes when
rebuilt; retain and review the new manifest instead of claiming byte-for-byte reproducible archives.

Preparation exports immutable Git trees, excluding dirty/untracked source. It replaces only the candidate's
framework references, creates new lockfiles, adds the source exporter and builds the server from the same
framework revision. A normal application/exporter build must succeed with warnings treated as errors.
No runtime application startup is needed to export semantics. The published server, rather than the Cohesive
source checkout, is placed in participant files. Each participant gets fresh single-commit Git history.

The output contains:

- `cohesive-mcp/` and `cohesive-mcp-off/`: matching public application, exporter, guidance, pinned packages,
  lockfiles and server binaries; no parent protocol, qualification cases or private oracle.
- `connections.json`: evaluator-side launch configuration; off has no MCP connection.
- `evidence/`: input pins, tooling hashes, commands, build logs, finite leakage audit and participant manifest.
- `preparation.json`: prepared/invalid status, never a score.

Only the selected participant directory belongs in an eventual agent environment. Do not mount this repository,
its parent directories, the Cohesive source archive, the evidence directory or private scoring files into that
environment. Source path checks and leakage markers are finite checks, not OS isolation. Production sandboxing,
resource budgets, credential filtering and network policy are still required before model execution.

## Coverage and authority

`Development/Program.cs` invokes the fixture's existing typed authoring objects and exports entities, shapes,
relationships, transitions, the fulfillment process and native queries. Its declared inputs include source,
project/lock/configuration files, neutral guidance, dependency manifest and local package bytes. The bundle is
derived; edit authored C#, rebuild and re-export. The published server receives a workspace root and serves
`artifacts/development.json`. Its `learn` content comes from the participant-visible `DEVELOPMENT.md`.

The G0 HTTP handlers, queue identity/replay behavior and persistence wiring are ordinary C#. There is no portable
API contract authority for the full HTTP surface here. We deliberately do not synthesize a duplicate API catalog;
`compatibility` is discoverable but unsupported for these absent contracts. A successful check or impact path is
not proof about those C# behaviors. This is a coverage limit to measure, not a successful compatibility verdict.

## Evidence and failure handling

The smoke exercise first checks the prepared participant manifest, then works on its own copy. It records raw
JSON-RPC requests/responses, server identity, per-request elapsed time, stderr, export logs and snapshot identities.
It requires exactly nine tools, fixture guidance, entity/query coverage and valid document checks. It checks a
comment edit, stale-snapshot rejection, same-session comparison and a separate reservation-policy edit that must
change the exported reservation definition. These scripted changes are not a benchmark task or an agent result.
The original source is restored and re-exported; stdin is closed and the server must exit cleanly.

The parity wrapper reuses the existing independent HTTP/invariant verifier against the pinned conventional G0
and upgraded Cohesive candidate in separate databases. Since MCP-on/off application files are identical, this
qualifies their common dependency-upgraded starting behavior; it does not measure an MCP benefit. The verifier
owns creation and removal of its disposable PostgreSQL container. The full held-out evolution oracle remains
outside scope, and no private results are returned to a participant.

Existing output directories are refused. Preparation, build, transport, timeout, missing evidence and cleanup
failures are infrastructure failures (`invalid`, no score), never agent failures. Artifacts remain writable by
the local owner; append-only storage is an evaluator deployment responsibility. Setup errors before a usable run
may fail without a report. Prepared manifests and exact package hashes must pass before execution.

## Next admission steps

1. Review this candidate protocol separately from the no-MCP comparison.
2. Add an agent driver with enforced per-condition tool permissions, OS isolation, resource budgets and retained
   model/tool traces. The existing Relations runner is reused for manifest/audit utilities, not silently replaced.
3. Integrate the independently qualified cross-layer scorer and its obligation-level failure classification.
4. Run unscored agent calibration, then freeze matched pins and approve scored runs.

See `validation.json` for the tested preparation, smoke and HTTP evidence summary. It establishes integration
readiness only; no effectiveness or productivity claim follows from this pilot.
