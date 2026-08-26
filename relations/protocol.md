# Cohesive.Relations evaluation protocol v0.1

Status: approved and frozen for protocol v0.1 on 2026-08-26. No calibration or
evaluated runs have occurred. The frozen v0 text remains preserved at commit
`8cafef7`. Baseline admission and oracle freeze remain separate gates.

## v0.1 revision summary

Relative to frozen v0, this candidate:

- defines the exact public API that hidden checks may use and treats an agent's
  incompatible API change as a valid but incomplete result, rather than
  discarding the run as a harness failure;
- makes visible-test success an explicit completion gate;
- names model familiarity and task-selection bias, requires baseline provenance
  and independent conventional review, and audits package documentation hints;
- requires condition-specific known-correct and per-obligation seeded oracle
  qualification, with whole-oracle versioning and rescoring for defects;
- adds a preregistered ceiling/floor calibration screen and constrains
  failed-obligation comparisons to submissions whose checks execute;
- scrubs evaluation framing and parent Git history from agent workspaces; and
- limits the run batch to 24 hours while recording served-model fallback and
  documentation-reading evidence when available.

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
- **Condition**: the software representation presented to the agent. The v0.1
  conditions are conventional C# and Cohesive.Relations.
- **Run**: one fresh agent instance attempting one task in one condition from a
  clean isolated workspace. A repetition is a distinct run, not a retry of the
  same conversation.
- **Obligation**: a stable, externally observable requirement of a correct
  result. Obligations are public; the concrete fixtures and checks used to test
  them may be hidden.
- **Oracle**: maintainer-only executable checks and their mapping to obligations.
  The oracle evaluates the final repository but does not instruct the agent.
- **Freeze / frozen artifact**: approval of one exact, content-addressed version
  for a pilot stage. After an artifact is frozen, maintainers cannot change it
  selectively or retroactively within that version. A change requires a new
  version and repetition of any affected qualification or runs. Freezing the
  public contract fixes the names, kinds, and CLR signatures that the oracle may
  compile against. It does not make an agent's workspace read-only: the agent
  may edit that API, but an incompatible edit is then scored as an incomplete
  solution.
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

Model familiarity is an uncontrolled confound: idiomatic C# is common in model
training, while Cohesive.Relations is unfamiliar. Repository-local documentation
can mitigate API discovery cost but cannot equalize training prior. Documentation
and package-content audits therefore record both insufficient guidance and
task-specific examples. Time and tool activity spent reading documentation are
reported descriptively when they can be classified reliably; they do not affect
correctness.

Baseline equivalence is an admission gate. Before any pilot run, both baselines
must build and pass a shared maintainer acceptance suite over the behavior
specified by the case. A manual review must confirm that both are idiomatic and
that neither is materially closer to the requested change. Failure pauses the
case; it is not repaired during a run.

The admission record names the author and reviewer of each baseline, discloses
their relationship to Cohesive, and preserves their findings. The conventional
baseline requires review by a C# developer who did not author Cohesive.Relations
and has no direct stake in the comparison. Both baselines and this provenance
record are published with the results.

## Controlled agent configuration

Every valid run records and holds constant:

- agent product, client version, requested and served model identifiers when
  exposed, reasoning setting, and any fallback or routing event;
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

The ten-run schedule is executed as one time-bounded batch. Here, a batch means
one predeclared execution campaign, not one shared conversation or one
long-running agent process: every run still uses a fresh workspace and fresh
conversation with no cross-run state.

The 24-hour clock begins when the first run attempt in the batch starts. Every
run counted among the ten valid runs must have its own start timestamp before
that clock expires; a run may finish after the deadline. Runs may execute
sequentially or at a concurrency level fixed before launch, but maintainers may
not deliberately pause the campaign, change configuration, or use interim
results to decide when or how later runs start. This narrow start window reduces
(but cannot eliminate) the chance that day-to-day model-serving changes become
confounded with condition.

If an invalid attempt cannot be replaced inside the original 24-hour window,
its evidence and the rest of that batch are retained, but that partial batch is
not combined with later runs as the primary ten-run evidence set. After the
cause is fixed, maintainers start a new batch ID and rerun the complete
predeclared schedule under the same frozen configuration. An explicit fallback
to, or turn served by, a different model is an invalid run. When the service
does not expose served-model identity, that uncertainty is recorded as a
limitation rather than inferred.

## Material visibility

The coding agent can see:

- its assigned condition repository and repository-local instructions;
- the exact task and public obligation descriptions;
- the public application contract, documentation, and visible tests;
- normal build and visible-test output produced inside its workspace.

The coding agent cannot see:

- the other condition;
- protocol, case, oracle, runner, result, or other evaluation-repository files;
- the evaluation repository's Git metadata or commit history;
- oracle source, hidden fixtures, hidden test names, or expected patches;
- seeded-bad patches, known-correct patches, scorer implementation, or results
  from earlier runs;
- the condition-order seed or other agents' traces.

Evaluation maintainers may inspect all material. The runner exposes the private
oracle only in a separate scoring workspace after agent execution ends. The
runner must audit the agent workspace manifest before launch and after completion
to detect hidden-material leakage. Public obligations may not conceal behavior
that is absent from the task or starting application semantics.

Each agent workspace is constructed from an allowlisted snapshot of one
condition directory, excluding build outputs and parent-repository metadata,
then initialized as a new standalone Git repository. Repository instructions
must describe the application, not the evaluation or the other condition.

## Difficulty calibration

After the protocol, case, baselines, agent configuration, and qualified oracle
are review-complete and content-addressed—but before the evidence freeze—the
maintainers execute exactly two fresh calibration runs per condition using that
unchanged candidate configuration. The four calibration runs are labeled
permanently as calibration, retained, and never reclassified as pilot evidence.

If all four calibration runs are complete, the task has a common ceiling. If all
four are incomplete, it has a common floor. Either result pauses this pilot and
requires a versioned case or task revision before evidence runs. Otherwise the
identical candidate artifacts are frozen without alteration and the predeclared
five-per-condition schedule proceeds; calibration results may not be used to
alter prompts, budgets, scoring, or run order.

## Run procedure

For each scheduled run, the future runner will:

1. Verify the frozen case, baseline revision, configuration, and oracle version.
2. Copy the allowlisted contents of one condition—not its parent repository or
   Git history—to a fresh isolated directory and establish a new clean Git
   baseline.
3. Verify that evaluation framing, hidden material, the other condition, and
   results from prior runs are absent.
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

The **oracle adapter** is maintainer-owned code compiled only in the separate
scoring workspace. It references the application's frozen public types and
members so hidden checks can exercise the submitted implementation. For
example, this case fixes the name and CLR type of
`LoadSearchResult.EquipmentNumber`, while allowing only the nullable-annotation
change explicitly listed by the case.

If the adapter cannot compile because the agent renamed, removed, or
incompatibly changed that surface, the submission caused the failure. The
contract/build gate fails, runtime obligations are `not-evaluated`, and the run
is retained as a valid incomplete outcome. It is not discarded as an
infrastructure failure. Conversely, if the same adapter fails against a frozen
known-correct submission, the oracle or harness is defective; scoring pauses
and follows the whole-oracle versioning rule below.

The primary task outcome is **complete** only when:

1. the application and oracle adapter build against the frozen contract;
2. the repository's visible test suite passes;
3. every public behavioral obligation passes; and
4. the assigned condition's treatment-integrity checks pass.

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

There is no weighted or composite efficacy score in v0.1. Timing, token use, tool
calls, and patch size never compensate for incorrect behavior. Medians and
ranges may summarize descriptive measurements, but no significance test or
population claim is planned for ten runs.

Failed-obligation counts are compared only among submissions for which the
application and oracle adapter build and the relevant behavioral checks execute.
`not-evaluated` is neither zero failures nor eight failures and is never imputed.

## Evidence capture

Every run receives a stable ID and preserves, when available:

- case, task, condition, protocol, baseline, oracle, runner, agent, model, SDK,
  and host identifiers;
- the frozen task and effective non-secret configuration;
- start/end timestamps, elapsed duration, resource-limit events, and exit state;
- raw agent events plus stdout and stderr;
- served-model or fallback events and documentation-reading activity when the
  product exposes enough information to identify them reliably;
- final Git status, commit metadata, repository archive, and patch;
- build logs and machine-readable visible/hidden test results;
- obligation mapping, score result, and treatment-integrity evidence;
- input/output/cached tokens, model calls, tool calls, and cost only when exposed
  reliably by the agent.

Original evidence is retained alongside any normalized summary so later parser
improvements do not require rerunning the agent. The runner must redact secrets
and must not record a complete environment dump.

## Repetitions and invalid runs

The v0.1 pilot schedules five independent runs per condition, ten valid runs in
total. A valid run is never discarded because its result is unfavorable.
Reaching an agent time, token, or step limit is a valid incomplete outcome.
Likewise, an agent-authored build failure or incorrect patch is valid evidence.

A run is **invalid** only when it cannot answer the research question because
the experimental procedure failed, including:

- wrong or contaminated baseline, task, model, permissions, or budget, including
  an explicitly reported served-model fallback;
- hidden material leaked into the agent workspace;
- human intervention or cross-run conversational state affected execution;
- the agent could not be launched because of runner, authentication, host, or
  unrelated service failure;
- scoring infrastructure failed independently of the submitted patch and also
  fails against the frozen known-correct qualification submissions;
- evidence required to establish the run's configuration or result is lost.

Invalid runs and their evidence remain recorded with a reason. If the cause is
fixed while the original batch window remains open, the run is replaced at the
end of the predeclared schedule using the same frozen configuration and a new
run ID. If the replacement cannot start within that window, the complete batch
is rerun under a new batch ID as specified above. If a discovered defect changes
the task, obligations, baseline semantics, or scoring policy, the pilot pauses
and requires a new protocol/case version rather than silently replacing runs.

An oracle defect is never used to discard one unfavorable run. Discovery that a
hidden check is ambiguous, contradicts the public specification, or fails a
frozen known-correct submission pauses scoring for every affected run. The
oracle is version-bumped, fully requalified, and all preserved affected
submissions are rescored under the same corrected oracle. If complete rescoring
is impossible, the pilot version is abandoned rather than selectively repaired.

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

In particular, a null or negative Cohesive result cannot distinguish the value
of its representation from model unfamiliarity with its API. The task was
selected from Cohesive.Relations' home domain—changing relationship
optionality—and may favor that condition. This pilot contains no negative-control
task on which the representation is expected to be neutral or harmful.

Five runs per condition can reveal harness failures or extreme separation but
cannot support ordinary comparative inference; a ceiling such as 5/5 versus 5/5
is expected to be uninformative. Any later efficacy study must preregister a
power analysis and will likely require tens of runs per condition (roughly
20–30 even for a very large effect), plus a negative-control task.

The permitted conclusion is limited to a descriptive statement about the
observed outcomes under this frozen protocol. The first success criterion is a
trustworthy evaluation case: matched baselines, clear obligations, a validated
oracle, and complete evidence—not a favorable comparison.

## Deferred work

The matched application implementations and baseline-equivalence tests are
complete. Hidden checks, known-correct and per-condition seeded-bad submissions,
the evaluation CLI, agent driver, scorer, calibration, and pilot execution remain
deferred. Their implementation must conform to the approved version of this
protocol or propose another explicit revision.
