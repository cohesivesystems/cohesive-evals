# Tooling map

The .NET adapters own model input generation and execution. Python owns independent checking,
process orchestration and evidence. Public methods/classes in the current Python tooling have
docstrings; non-obvious provenance and failure behavior is commented. Repository-wide guidance
is in [AGENTS.md](../../../../AGENTS.md).

| Read this file | To understand |
| --- | --- |
| [suites/run.py](suites/run.py) | Build → generate → independently check → freeze |
| [suites/fixture.py](suites/fixture.py) | Pinned SDK/policy patches, shared production builder, adapter invocation |
| [suites/oracle.py](suites/oracle.py) | The independent business requirements |
| [evaluation/defects.py](evaluation/defects.py) | Paired deliberate application defects |
| [evaluation/qualify.py](evaluation/qualify.py) | Exact-assertion detection credit and integrity controls |
| [evaluation/integration.py](evaluation/integration.py) | Versioned HTTP, replay and physical-state witnesses |
| [evaluation/record.py](evaluation/record.py) | Reports and compressed, hashed review evidence |

Two test modules challenge the current Python harness. The older `audit` directory is a separate,
pinned SDK capability witness; it is not another current implementation of the suites.

## Structure review

The order-fulfillment tree currently has 82 Python files, including 15 `test_*.py` modules:
25 evolution, 22 portable-validation, 11 API-outcome, 11 model-verification, seven durability
and six in the remaining areas. These counts include historical checkpoints and their tests,
not 82 independent application implementations.

Changes made here:

- Removed `generate.py` and its handwritten expression-node matcher. Cohesive now owns this
  capability; the conventional adapter uses ordinary typed C# boundary generation.
- Reused the existing production build/manifest helpers and the PostgreSQL lifecycle, HTTP client
  and physical-state observer. No new Docker manager, test runner or expression evaluator.
- Kept deterministic assertions in Python's `unittest`/standard-library ecosystem. No third-party
  runtime dependency is needed for this bounded task; formatting tooling is development-only.
- Used the existing optional Transitions/Assurance package. SDK Simulation already supplies
  broader generation/property/shrinking machinery; the new API supplies guard-derived proposals.

The clearest next structural improvement is a shared importable tooling package for build,
PostgreSQL lifecycle and evidence helpers. Today later stages still reach back through earlier
`build.py` modules and path-based loading. Migrate that responsibility incrementally with its
existing classification/provenance tests, rather than rewriting independent requirement checks
or replacing the whole harness at once. This inventory is an initial structure review, not a
completed semantic audit of every historical script.
