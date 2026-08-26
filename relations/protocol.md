# Cohesive.Relations evaluation protocol v0

Status: protocol draft for the first pilot. This document must be reviewed and
frozen before implementing or running the pilot. Any rule changed afterward
requires a new protocol version and must not be applied retroactively.

## Research question

For the **Make Equipment Optional** task in the **Load Search Mapping** case,
does changing the starting software representation from idiomatic conventional
C# to idiomatic `Cohesive.Relations` change a pinned coding agent's rate of
complete, obligation-correct solutions under otherwise controlled conditions?

This pilot first tests whether that question can be measured credibly. It is
not designed or powered to establish that Cohesive is generally more effective.

## Terminology

- **Case**: a bounded application, its two matched starting repositories, its
  public behavior, fixtures, consumers, and evaluation boundary. The first case
  is Load Search Mapping.
- **Task**: one change request applied independently to a clean case baseline.
  The first task is Make Equipment Optional.
- **Condition**: the software representation presented to the agent. The v0
  conditions are conventional C# and Cohesive.Relations.
- **Run**: one fresh agent instance attempting one task in one condition from a
  clean isolated workspace. A repetition is a distinct run, not a retry of the
  same conversation.
- **Obligation**: a stable, externally observable requirement of a correct
  result. Obligations are public; the concrete fixtures and checks used to test
  them may be hidden.
- **Oracle**: maintainer-only executable checks and their mapping to obligations.
  The oracle evaluates the final repository but does not instruct the agent.
- **Baseline equivalence**: agreement between the two starting repositories on
  public inputs, results, failures, identity, cardinality, ordering, and named
  consumers. Equivalent behavior does not require identical implementation.
- **Treatment integrity**: evidence that the final implementation still belongs
  to its assigned condition rather than bypassing or replacing its defining
  representation.

## Conditions and admissible differences

### Conventional C#

The application expresses joins, optionality, projection, and validation using
idiomatic C# and ordinary .NET abstractions. It does not reference Cohesive.

### Cohesive.Relations

The application expresses the same authoritative semantics through the
canonical `Cohesive.Relations` representation and executes the application
boundary through it. Condition-specific provenance or diagnostic detail may be
richer, but application-level outcomes must match the conventional baseline.

The repositories may differ in structure and dependency footprint where those
differences are inherent to the representation. They must expose the same
public application contract, start with equivalent behavior, contain comparable
documentation, and provide the same visible development feedback. Neither may
contain task-specific hints, a partial solution, or privileged oracle knowledge.

Baseline equivalence is an admission gate. Before any pilot run, both baselines
must build and pass a shared maintainer acceptance suite over the behavior
specified by the case. A manual review must confirm that both are idiomatic and
that neither is materially closer to the requested change. Failure pauses the
case; it is not repaired during a run.

## Controlled agent configuration

Every valid run records and holds constant:

- agent product, client version, exact model identifier, and reasoning setting;
- task wording, repository instructions, and visible tests;
- a fresh conversation with no prior task or cross-run state;
- starting baseline revision and dependency lock state;
- host image, SDK/toolchain versions, working directory, and environment policy;
- tool permissions, network policy, and available dependency caches;
- wall-clock, step/turn, token, and monetary limits where the agent supports them;
- whether usage and event traces are available.

The agent runs non-interactively in a fresh copy of exactly one condition. Human
help, mid-run prompt amendments, manual edits, and approval changes are not
allowed. Unsupported controls are recorded as unavailable rather than estimated.
Credentials, secrets, and unrelated host state must not be copied into run
artifacts.

The two conditions use the same configuration and task text. Their run order is
set before execution as five paired blocks. Within each block, condition order
is randomized using one recorded seed. Runs are not adaptively reordered based
on interim results.

## Material visibility

The coding agent can see:

- its assigned condition repository and repository-local instructions;
- the exact task and public obligation descriptions;
- the public application contract, documentation, and visible tests;
- normal build and visible-test output produced inside its workspace.

The coding agent cannot see:

- the other condition;
- oracle source, hidden fixtures, hidden test names, or expected patches;
- seeded-bad patches, known-correct patches, scorer implementation, or results
  from earlier runs;
- the condition-order seed or other agents' traces.

Evaluation maintainers may inspect all material. The runner exposes the private
oracle only in a separate scoring workspace after agent execution ends. The
runner must audit the agent workspace manifest before launch and after completion
to detect hidden-material leakage. Public obligations may not conceal behavior
that is absent from the task or starting application semantics.

## Run procedure

For each scheduled run, the future runner will:

1. Verify the frozen case, baseline revision, configuration, and oracle version.
2. Copy one condition to a fresh isolated directory and establish a clean Git
   baseline.
3. Verify that hidden material and results from prior runs are absent.
4. Start the pinned agent with the frozen task and resource policy.
5. Preserve the agent's exit state and final workspace when execution stops.
6. Capture the final patch and copy the repository to a separate scoring area.
7. Build the submission and execute visible and hidden checks.
8. Map check evidence to obligations and evaluate treatment integrity.
9. Write an immutable run record before inspecting aggregate results.

Scoring occurs even when the agent reports failure, exits nonzero, reaches its
budget, or leaves the project unbuildable, provided the experimental harness
itself remained valid.

## Scoring

Each obligation is reported as `passed`, `failed`, or `not-evaluated`, with the
supporting check evidence retained. An obligation passes only when all checks
assigned to it pass. If a submission cannot build, the build outcome fails and
runtime obligations are `not-evaluated`; this is an unsuccessful agent outcome,
not an invalid experiment.

The primary task outcome is **complete** only when:

1. the final repository builds;
2. every public behavioral obligation passes; and
3. the assigned condition's treatment-integrity checks pass.

Otherwise the outcome is **incomplete**. Treatment-integrity checks do not award
extra correctness credit and their mechanism may be condition-specific. They
only establish that a result is evidence about the assigned condition.

The pilot will report:

- complete runs per condition;
- the full obligation result vector and failed-obligation counts;
- build, visible-test, hidden-test, and treatment-integrity outcomes;
- collateral behavior regressions;
- elapsed time and available agent usage data;
- changed-file count and patch size as descriptive evidence.

There is no weighted or composite efficacy score in v0. Timing, token use, tool
calls, and patch size never compensate for incorrect behavior. Medians and
ranges may summarize descriptive measurements, but no significance test or
population claim is planned for ten runs.

## Evidence capture

Every run receives a stable ID and preserves, when available:

- case, task, condition, protocol, baseline, oracle, runner, agent, model, SDK,
  and host identifiers;
- the frozen task and effective non-secret configuration;
- start/end timestamps, elapsed duration, resource-limit events, and exit state;
- raw agent events plus stdout and stderr;
- final Git status, commit metadata, repository archive, and patch;
- build logs and machine-readable visible/hidden test results;
- obligation mapping, score result, and treatment-integrity evidence;
- input/output/cached tokens, model calls, tool calls, and cost only when exposed
  reliably by the agent.

Original evidence is retained alongside any normalized summary so later parser
improvements do not require rerunning the agent. The runner must redact secrets
and must not record a complete environment dump.

## Repetitions and invalid runs

The v0 pilot schedules five independent runs per condition, ten valid runs in
total. A valid run is never discarded because its result is unfavorable.
Reaching an agent time, token, or step limit is a valid incomplete outcome.
Likewise, an agent-authored build failure or incorrect patch is valid evidence.

A run is **invalid** only when it cannot answer the research question because
the experimental procedure failed, including:

- wrong or contaminated baseline, task, model, permissions, or budget;
- hidden material leaked into the agent workspace;
- human intervention or cross-run conversational state affected execution;
- the agent could not be launched because of runner, authentication, host, or
  unrelated service failure;
- scoring infrastructure failed independently of the submitted patch;
- a hidden check is ambiguous, contradicts the public specification, or is shown
  by a known-correct patch to be defective;
- evidence required to establish the run's configuration or result is lost.

Invalid runs and their evidence remain recorded with a reason. After the cause
is fixed, the run is replaced at the end of the predeclared schedule using the
same frozen configuration and a new run ID. If a discovered defect changes the
task, obligations, baseline semantics, or scoring policy, the pilot pauses and
requires a new protocol/case version rather than silently replacing runs.

## Limits of interpretation

The pilot covers one manually authored C# application, one relationship-
optionality task, two representations, one pinned agent configuration, and five
runs per condition. It cannot establish:

- general Cohesive or Cohesive.Relations efficacy;
- human developer productivity, maintainability, or comprehension;
- performance on other agents, models, languages, domains, or change types;
- long-term semantic longevity or sequences of dependent changes;
- the value of semantic query tools, generated cases, or `Cohesive.Simulation`;
- causal mechanisms behind any observed difference;
- statistical or production significance.

The permitted conclusion is limited to a descriptive statement about the
observed outcomes under this frozen protocol. The first success criterion is a
trustworthy evaluation case: matched baselines, clear obligations, a validated
oracle, and complete evidence—not a favorable comparison.

## Deferred work

The two application implementations, visible and hidden tests, known-correct and
seeded-bad patches, evaluation CLI, agent driver, scorer, and pilot execution are
deliberately deferred. Their later implementation must conform to this protocol
or propose an explicit protocol revision.
