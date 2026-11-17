# Tooling map

MV1 now uses the importable [`cohesive_evals`](../../../../cohesive_evals/README.md) package.
Run `python3 -m cohesive_evals --help` from the checkout; no runtime Python dependencies are required.

| Read | Purpose |
| --- | --- |
| [`mv1/run.py`](../../../../cohesive_evals/mv1/run.py) | Build, generate, independently check and freeze |
| [`mv1/references.py`](../../../../cohesive_evals/mv1/references.py) | Preserved source recipe; no historical module chains |
| [`adapters/dotnet.py`](../../../../cohesive_evals/adapters/dotnet.py) | Locked builds and typed executable invocation |
| [`mv1/oracle.py`](../../../../cohesive_evals/mv1/oracle.py) | Independent business requirements |
| [`mv1/qualify.py`](../../../../cohesive_evals/mv1/qualify.py) | Paired defects, exact assertion credit and controls |
| [`mv1/integration.py`](../../../../cohesive_evals/mv1/integration.py) | HTTP, replay and physical-state witnesses |
| [`mv1/record.py`](../../../../cohesive_evals/mv1/record.py) | Hashed JSON reports and raw evidence |

Shared snapshot, lifecycle, qualification and evidence helpers are documented in the package.
Methods/classes explain purpose and consequential failures. Standard imports replace MV1's
`sys.path` edits and dynamic module loading. Independent requirement checks remain scenario-owned.

The package README defines adapter v1, assesses Pydantic/pytest/reporting, and specifies the
TypeScript follow-up and Alchemy capability audit. PostgreSQL is optional infrastructure for
HTTP witnesses; offline grading needs neither a database nor a Cohesive dependency.

Older probes and the pinned capability audit retain their implementations for now. This is an
incremental extraction of MV1's infrastructure, not an audit or rewrite of every historical script.
