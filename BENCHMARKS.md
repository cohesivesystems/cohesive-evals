# Benchmark landscape

A map of benchmarks and empirical studies relevant to cohesive-evals. It
classifies what coding-agent evaluations measure, identifies their limitations,
and connects their findings to this project's goals and experiment design.
It is a selected reading map, not an exhaustive survey or a ranking of agents.

Last source check: 2026-11-19. Linked primary-source abstracts support the
high-level descriptions below; this is not a fresh full-paper audit. Numerical
leaderboard results are deliberately omitted: versions, configurations, task
populations, and denominators differ. Recheck the full paper before drawing on a
specific result. “Implication” and proposed goals below are our
interpretation, not conclusions established by the cited authors.

## The organizing question

**What can agents reliably do across the intent → specification → implementation
→ execution loop, and what helps them preserve requirements as the system changes?**

The studies examine different parts of that question. Keep three distinctions:

- **Capability:** implementing, testing, proving, diagnosing, or recovering.
- **Difficulty:** accumulated changes, interacting requirements, unfamiliar
  languages, distributed behavior, or incomplete evidence.
- **Intervention:** changing the representation, guidance, tools, feedback loop,
  or decomposition of work.

A benchmark can span several dimensions. Longitudinal change is a task structure;
formal verification is an assurance method; distributed systems are a domain.
They are useful tags, but not mutually exclusive categories.

## High-level classification

| Dimension | Question | Relevant work | What to keep distinct |
|---|---|---|---|
| Longitudinal change | Can an agent complete dependent changes and preserve earlier behavior? | WEAVE; SlopCodeBench; SWE-CI; cohesive-evals evolution pilot | A dependency-structured milestone is not automatically a study of degradation across successive agent-edited checkpoints. Degradation of an agent's own code differs from preserving obligations in a fixed, matched starting design. |
| Interacting requirements | Can it satisfy all functional, structural, and procedural requirements together? | Constraint Decay; ANCHOR; CodeSpecWeave | Structural requirements on the product differ from instructions governing the agent's workflow. Neither alone measures interacting business invariants; synthesized interdependent specifications approach them but are scored by generated tests. |
| Testing | Can it produce evidence that distinguishes correct from incorrect implementations? | TestSuiteBench | Tests passing on correct software and tests detecting faults are separate outcomes. |
| Formal methods | Can it construct machine-checked arguments about system properties? | TLAPS-Bench | Proving a supplied model does not establish that the model captures intent or that deployed code refines it. |
| Operations | Can it move from symptoms to a repair and verified recovery? | SWEOps-Bench | Detection, reported diagnosis, symptom clearance, and functional recovery are separate outcomes. |
| Distributed systems | Can it diagnose failures involving interactions across components? | DistDebug-Bench; TLAPS-Bench; SWEOps-Bench | Code-level diagnosis, specification proof, and operational recovery test different capabilities. |
| Code and specification structure | How does the representation of the problem affect implementation? | Skeleton Coding; AgentScript-Eval | A supplied skeleton, a DSL, and the surrounding guidance are different interventions. |
| Work structure and guidance | How do decomposition, ordering, instructions, and feedback affect success? | WEAVE; ANCHOR; AgentScript-Eval; context-file adherence study | Model capability and harness/guidance effects should not be conflated. |

## Benchmarks and studies

### Implementation and evolution

| Work and source | Kind / evaluation unit | What it evaluates and how | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [WEAVE](https://arxiv.org/abs/2610.22039) | Benchmark construction and training framework; related PRs organized into a bounded dependency DAG | Executable multi-PR tasks; Graph Credit measures dependency-consistent partial progress using test evidence. | Preserve dependency information and cumulative obligations rather than counting independent patches. | Dependency-aware partial credit is not a general measure of maintainability or semantic preservation over time. |
| [Constraint Decay](https://arxiv.org/abs/2605.06445) | Controlled empirical study; backend generation and feature tasks | Holds an API contract fixed while varying structural requirements; uses behavioral tests and static verifiers. | Score behavior and structural compliance separately, including whether both hold simultaneously. | Structural constraint burden is not identical to semantic coupling among business rules. |
| [SlopCodeBench](https://arxiv.org/abs/2603.24755) | Long-horizon benchmark; agents repeatedly extend their own code across checkpoints as requirements evolve | Requires each checkpoint's tests to pass; tracks structural erosion (concentrated complexity) and verbosity (redundant code), compared with open-source Python repositories. | Measure code structure at each checkpoint as well as behavior, and attribute degradation to the change sequence rather than to one patch. | Erosion of agent-authored code does not show which representation preserves obligations; structural metrics are proxies until tied to later change cost or regressions. |
| [SWE-CI](https://arxiv.org/abs/2603.03823) | Maintenance benchmark; tasks derived from real repository histories spanning many commits | Agents work through repeated analysis/coding rounds with CI feedback; maintainability is assessed through functional correctness across successive iterations. | Score correctness cumulatively across iterations and record the feedback available at each round. | Real histories improve realism but raise contamination risk and do not control the starting design; correctness over time is an indirect maintainability measure. |
| [CodeSpecWeave](https://arxiv.org/abs/2610.40256) | Task-synthesis framework and benchmark; tasks with interdependent specifications grounded in developer seeds | A synthesis agent builds coupled requirements and executable tests; a review agent audits test reliability against multiple models' trajectories. | Construct obligations whose interactions, not individual rules, are the hard part; qualify the tests that score them. | Synthesized specifications and generated tests bound the claims; interaction difficulty is not the same as accumulated evolution of one system. |
| [Skeleton Coding](https://arxiv.org/abs/2610.38214) | Representation/specification study across coding benchmarks | Supplies types, modules, signatures, and behavioral specifications; compares implementation error and cost across specification forms. | Treat the representation supplied to an agent as an experimental variable. | Benefits of supplied structure do not establish the cost of eliciting and authoring the right structure from stakeholder intent. |
| [AgentScript-Eval](https://arxiv.org/abs/2611.13183) | Execution-graded enterprise DSL benchmark; authoring, debugging, and optimization tasks | Separates compilation and behavioral outcomes; varies zero-shot versus compile-and-edit workflows and domain guidance. | Control documentation and feedback, record unfamiliarity, and score semantics beyond successful compilation. | Results combine a particular DSL, task set, model, and harness; they do not establish that DSLs generally help or hurt. |

### Assurance

| Work and source | Kind / evaluation unit | What it evaluates and how | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [TestSuiteBench](https://arxiv.org/abs/2610.13065) | Test-generation benchmark; complete application test suites from behavioral specifications | Evaluates generated suites against a reference implementation and requirement-targeted mutants. | Qualify the oracle with known-correct implementations and deliberate defects; distinguish validity from fault detection. | The reference behavior and mutant population bound what the scores establish; mutation score is not production defect coverage. |
| [TLAPS-Bench](https://arxiv.org/abs/2611.02849) | Formal-proof benchmark and harness; proof targets in TLA+ system specifications | Agents construct machine-checked proofs using TLAPS, including invariant discovery and proof decomposition. | State properties explicitly and distinguish executable test evidence from proof evidence. | Proof success is relative to the formal specification and assumptions; implementation conformance and intent validation remain separate. |

### Diagnosis and recovery

| Work and source | Kind / evaluation unit | What it evaluates and how | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [DistDebug-Bench](https://arxiv.org/abs/2611.03523) | Distributed-system debugging benchmark; historical bugs | Evaluates code-level diagnosis of real failures across distributed-system repositories. | Distinguish locating/explaining a failure from repairing it and demonstrating preserved invariants. | Diagnosis performance should not be presented as verified repair or production reliability. |
| [SWEOps-Bench](https://arxiv.org/abs/2611.06099) | Interactive operations benchmark; reproducible software-induced incidents in Kubernetes operators | Agents inspect runtime evidence and submit source/configuration repairs; evaluation covers recovery, stage accuracy, latency, and tokens. | Verify externally observable recovery and behavior, not just an agent's explanation or disappearance of symptoms. | A bounded, reproducible incident suite does not cover every failure mode or the full operational lifecycle. |

### Engineering instructions and workflow

| Work and source | Kind / evaluation unit | What it evaluates and how | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [ANCHOR](https://arxiv.org/abs/2610.16859) | Constraint-following benchmark; repository tasks with composed engineering instructions | Scores atomic constraints and AND/THEN/PRIORITY relations using diffs, trajectories, rule-based checks, and LLM judges. | Separate task correctness, individual compliance, and satisfaction of all required constraints; retain execution evidence. | Some judgments are not executable behavioral oracles; workflow compliance does not imply product correctness. |
| [Do They Do as They Are Told?](https://arxiv.org/abs/2611.13709) | Observational empirical study; context-file instructions and associated agent commits | Operationalizes observable instructions into executable compliance checks and studies adherence. | Do not assume that writing an obligation in AGENTS.md enforces it; check consequential requirements directly. | Observational adherence does not isolate the causal effect of a particular instruction or establish compliance with unobservable rules. |

## Where cohesive-evals fits

Proposed overarching goal:

> Determine whether explicit, executable system semantics help coding agents
> implement changes while preserving interacting behavioral obligations, and
> whether that advantage changes as software evolves, under matched conditions
> and independently qualified evaluation.

This is a hypothesis to investigate, not a claim that existing results establish.
The repository's protocols remain authoritative; this landscape does not change
their scope, scoring, or admission requirements.

| Existing work in this repository | Place in the landscape | Boundary |
|---|---|---|
| [Relations pilot](relations/protocol.md) | Controlled representation comparison for a single application change | Establishes a credible measurement procedure; cannot establish longitudinal effects or general efficacy. |
| [Order-fulfillment pilot](cross-layer/order-fulfillment/protocol.md) | Representation × accumulated evolution × probe family; preservation of interacting obligations | Fresh/aged checkpoints and hold/review-marker probes address the intersection of structure, change, and correctness. The probe contrast does not isolate coupling perfectly. |
| [Durability qualification](cross-layer/order-fulfillment/durability/README.md) | Recovery and invariant evidence under controlled worker failures | Qualifies reference applications and checks; it is not a scored agent benchmark result or a production durability claim. |

The useful intersection for this project is **representation × evolution ×
interacting obligations**. Other studies motivate its components; they do not
settle whether Cohesive improves the outcome.

Questions still outside the current pilots include whether humans specified the
right behavior, whether the representation reduces total specification and
maintenance effort, and how evidence should govern release or rollback decisions.
These are possible research directions, not missing features to add to this pilot.

## Measurement map

Candidate measures for discussing the landscape and designing later experiments.
Only measures admitted by each protocol belong in its actual scoring.

| Concern | Useful measure | Main caution |
|---|---|---|
| Task success | Fraction of valid runs satisfying every required obligation | Keep complete success distinct from average check pass rate. |
| Correctness preservation | Per-obligation outcomes across checkpoints; regressions and repairs | Check all active obligations; distinguish failure from not evaluated. |
| Intent preservation | Trace stakeholder examples/decisions to explicit obligations; measure preservation of those obligations | This measures specified intent. Validating that the specification captures actual intent requires separate stakeholder evidence. |
| Joint satisfaction | Fraction satisfying all active behavioral and structural requirements | High average compliance can coexist with low complete success. |
| Assurance quality | Acceptance of known-correct implementations; detection of qualified seeded defects; checked proof obligations | State the fault model and assumptions. Tests, mutation scores, and proofs supply different evidence. |
| Agent effort | Tokens, model/tool calls, elapsed time, and monetary cost where reliably exposed | Report alongside correctness; cheap failure is not efficiency. |
| Change footprint | Changed files, authored LOC, generated LOC, patch size | Separate authored and generated artifacts; fewer lines do not by themselves imply higher quality. |
| Complexity and coupling | Explicitly defined dependency, duplication, or affected-obligation measures | Avoid an undefined “entropy” score or mixing unrelated measures into a quality index. |
| Runtime performance | Latency, throughput, memory, and resource use under a fixed workload | Separate application performance from agent execution time. |
| Human effort | Specification, review, oracle construction, and repair time in a dedicated study | Automation cost alone omits work shifted to humans; current pilots do not measure general human productivity. |

## Interpreting results across studies

Do not combine headline percentages into a common ranking. For each quantitative
claim, record the paper version, task population, solver configuration, budget,
oracle, denominator, and limitations. Retain negative and neutral findings.

## Maintaining this map

Add a study when it introduces a relevant task, measurement method, intervention,
or failure mode—not simply another leaderboard. Record its primary source,
evaluation unit, evidence, relevance, and limitation. Keep supporting case studies
and quality frameworks distinct from executable benchmarks. Add detailed result
notes separately if needed so this document remains a navigable map.
