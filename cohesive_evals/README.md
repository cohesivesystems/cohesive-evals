# Evaluation tooling

Run from the checkout with Python 3.11+: `python3 -m cohesive_evals --help`.
An optional `python3 -m pip install -e .` installs the same `cohesive-evals` command.
The package expects repository assets beside it; it is not a standalone benchmark distribution.

| Boundary | Responsibility |
| --- | --- |
| `snapshots`, `evidence` | Checked source deltas, hashes and JSON artifacts |
| `runtime`, optional `postgres` | Bounded commands, HTTP, process/container cleanup |
| `contracts`, `adapters/dotnet` | Versioned execution interface and .NET-specific mechanics |
| `qualification` | Credit only the expected named behavioral assertion |
| `mv1/references`, `fixture` | Scenario source recipe and condition configuration |
| `mv1/oracle`, `http_checks` | Independent business expectations |
| `mv1/run`, `qualify`, `integration`, `record` | Scenario orchestration and evidence |

MV1 imports no historical `build.py` modules and changes no import search paths. It consumes
preserved patches and the contract bundle's public CLI. Older probes retain their commands;
move them onto these helpers incrementally when their next changes require it.

## Adapter v1

`AdapterConfig` names the condition, language, framework, contract version and independently
supported capabilities: `http`, `offline`, `model-inspection`, `input-generation`. No capability
implies another. A conventional implementation needs no model representation to be graded.

The host-side `Adapter` protocol in [contracts.py](contracts.py) defines:

- `build`: build checked inputs and return an evidence identity.
- `start`: managed HTTP host context; owns cleanup. Unsupported when HTTP is undeclared.
- `execute`: offline execution, inspection or generation; returns `ExecutionResult(version=1,
  capability, payload)`. Unsupported capabilities fail before spawning work.
- `observe`: verify build integrity and return its manifest identity. Business-state observation
  is scenario-owned; MV1's optional read-only SQL observer is separate from the .NET adapter.

The adapter maps its own native conventions to these operations. It does not need to use C#
classes or expose Cohesive IR on the wire. The current .NET consumer uses JSON arrays for
execution and JSON objects for generation/inspection; paths, NuGet and assemblies stay in
its adapter. `mv1/observations.py` strictly decodes the scenario's outcome/state fields before
independent assertions run. Integers and booleans are distinct; malformed evidence is unqualified.

Failures carry `configuration`, `build`, `infrastructure`, `protocol` or `unsupported` categories.
Only a verifier's named business failure can earn detection credit, and only when it matches the
fault's declared assertion. Missing expected behavior, wrong assertions, exceptions and unavailable
evidence remain separate. Rich JSON retains traces, manifests and diagnostic detail.

## Libraries and reporting

The [TestSuiteBench package](https://github.com/eth-sri/testsuitebench/blob/main/pyproject.toml),
[evaluator](https://github.com/eth-sri/testsuitebench/blob/main/src/programbench/eval/test_suite_eval.py)
and [overlay workflow](https://github.com/eth-sri/testsuitebench/blob/main/docs/explore.md) inform
these package/result boundaries. Its executable-specific runner is not imported.

For this small contract, standard-library dataclasses, explicit strict decoding, argparse and
unittest are sufficient. Pydantic's strict mode becomes useful if external configurations grow;
its default coercion would be inappropriate for these observations. Pytest can run the existing
unittest suite unchanged and optionally export JUnit (`pytest tests --junitxml=report.xml`);
it is not a required dependency. JSON remains the authoritative evidence. One CLI replaces
MV1's separate executable scripts, without introducing a plugin discovery framework.

## Next adapters

1. Cohesive TypeScript: implement these four host operations and declare capabilities actually
   available in its SDK. Reuse the scenario wire observations and independent assertions; test
   unsupported capabilities, Int32 boundaries and failure categories before running qualification.
   Generation should report comparable model/revision/fingerprint, per-candidate motivations and
   coverage limits without copying C# API shapes. Add SDK capabilities before eval-side substitutes.
2. Alchemy: first audit whether its application/runtime scope supports this fulfillment task,
   offline execution, input generation and observable effects. Do not assume its abstractions
   match Cohesive or require it to invent an IR just to participate.
3. Report within-language framework comparisons separately from cross-language comparisons;
   language/runtime differences are additional variables. The Python control in the infrastructure
   tests checks the interface boundary only; it is not an evaluated framework condition.
