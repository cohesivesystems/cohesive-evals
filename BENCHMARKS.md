# Benchmark landscape

A map of benchmarks and empirical studies relevant to cohesive-evals. It
classifies what coding-agent evaluations measure, identifies their limitations,
and connects their findings to this project's goals and experiment design.
It is a selected reading map, not an exhaustive survey or a ranking of agents.

Reading-list sync: 2026-11-25, from the [Benchmarks & related papers database](https://app.notion.com/p/cohesivesystems/41c8cf7881f98170835af51d553b02cb).
The source contains 54 rows representing 52 distinct works. This map merges the
duplicate SWE-Clar and AlphaProof Code entries and retains DistDebug-Bench from
the earlier repo list, for 53 distinct works. Categories below group the works
by evaluation purpose rather than copying the database's single-category labels.

The scoring table was checked against the benchmark papers and official
evaluation documentation on 2026-11-25. The broader landscape draws on reading
notes and an earlier abstract review. Numerical leaderboard results are omitted because versions,
configurations, task populations, and denominators differ. Recheck primary
sources before drawing on a specific result. Linked sources identify the works;
“implication” and proposed goals are our interpretation, not established findings.

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
| Longitudinal change | Can agents complete dependent changes while preserving earlier behavior? | SWE-Milestone; Multi-step SWE; WEAVE; SlopCodeBench; SWE-CI; SWE-EVO; RoadmapBench; DeepSWE | Milestone dependencies, release-sized tasks, and degradation of an agent's own code are different experimental settings. |
| Interacting requirements | Can functional, structural, and procedural requirements hold together? | CodeSpecWeave; Constraint Decay; ANCHOR; Beyond Prompts; ContextCov | Product invariants, workflow rules, and enforcement mechanisms require separate measures. |
| Intent and specification fidelity | Does the agent elicit the requirements, and does the specification capture them? | SWE-Clar; formal-specification faithfulness study; Specification Before Generation | Elicitation from fixed hidden requirements differs from deciding intent; satisfying a weak specification can still be wrong. |
| Testing and oracle quality | Can the evaluation distinguish correct from incorrect implementations? | TestSuiteBench; Spec-Driven PBT; BackendForge; EvalPlus; UTBoost; CodeT | Test validity, fault detection, and grading-pipeline correctness are separate concerns. |
| Formal methods | Can agents produce and check proofs of relevant properties? | TLAPS-Bench; AlphaProof Code; Hickey proposal | Specification proof, implementation conformance, and specification validity are distinct. Proposals and case studies are not benchmarks. |
| Operations and distributed systems | Can agents diagnose failures and demonstrate correct recovery? | DistDebug-Bench; SWEOps-Bench; TLAPS-Bench | Diagnosis, operational recovery, and proof of a system model test different capabilities. |
| Code and specification structure | Does representation change implementation success? | Skeleton Coding; CodeSpec; Architecture as Capability Equalizer; RPG / RepoCraft | Structure, executable feedback, and added information can each affect results. |
| Language and stack familiarity | How much does unfamiliarity affect apparent representation benefits? | AgentScript-Eval; ScarfBench; LLM Framework Benchmark; Matthew effect; metaprogramming study | Model exposure, framework version, documentation, and helper tools are separate factors. |
| Work and memory structure | How do decomposition, context, and compaction affect success? | Spine; Beyond Compaction; Benchmarks Are Surprisingly Compaction-Friendly; ANCHOR; context-file adherence study | Persisted program semantics, agent working memory, and workflow instructions are different interventions. |
| Product construction and use | Can agents build or operate complete applications? | SaaSBench; SaaS-Bench; microservices generation study | Using a SaaS product does not measure building it; construction does not establish maintainability. |
| Measurement and trend context | How trustworthy, current, and comparable is the evidence? | EA-Graph; SaltBench; AIDev; METR; Epoch; SWE-bench | Evidence provenance, observational datasets, experimental methods, and aggregate trends answer different questions. |

## Benchmarks and related work

The **Depth** labels reproduce the Notion reading status: **In depth** or
**Supporting**. They describe prior reading, not evidence quality or the extent
of verification during this sync. Findings added here are qualitative summaries
of those notes; implications and interpretation limits are our synthesis.

### Evolution and dependent changes

| Work and source | Type / reading depth | Evaluation focus or idea | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [CodeSpecWeave](https://arxiv.org/abs/2610.40256) | Benchmark; In depth | A synthesis agent builds coupled requirements and executable tests; a review agent audits test reliability against multiple models' trajectories. | Construct obligations whose interactions, not individual rules, are the hard part; qualify the tests that score them. | Synthesized specifications and generated tests bound the claims; interaction difficulty is not the same as accumulated evolution of one system. |
| [DeepSWE](https://arxiv.org/abs/2607.07946) | Benchmark; Supporting | Original long-horizon repository tasks with independently written functional verifiers. | Public reference for task-size and long-horizon work, and for independent functional verifiers rather than inherited tests. | Judge/verifier agreement is evidence about grading, not proof that either captures all requirements. |
| [Multi-step SWE](https://arxiv.org/abs/2611.07166) | Benchmark; In depth | Sequences of dependent implementation steps, with complete-task success distinct from step success and failures propagating across steps. | Require all steps for complete success and re-test earlier obligations; report regressions and partial progress separately. | Use an isolated-step comparison to separate accumulated errors from intrinsic step difficulty. |
| [RoadmapBench](https://github.com/UniPat-AI/RoadmapBench) | Benchmark; Supporting | Substantial multi-target changes drawn from open-source upgrade roadmaps, withholding target code, tests, and reference patches. | Another long-horizon evolution setting for comparing roadmap-style change to semantic obligation tracking. | Release-scale scope does not by itself isolate effects of accumulated agent-authored changes. |
| [SlopCodeBench](https://arxiv.org/abs/2603.24755) | Benchmark; Supporting | Requires each checkpoint's tests to pass; tracks structural erosion (concentrated complexity) and verbosity (redundant code), compared with open-source Python repositories. | Measure code structure at each checkpoint as well as behavior, and attribute degradation to the change sequence rather than to one patch. | Erosion of agent-authored code does not show which representation preserves obligations; structural metrics are proxies until tied to later change cost or regressions. |
| [SWE-CI](https://arxiv.org/abs/2603.03823) | Benchmark; Supporting | Agents work through repeated analysis/coding rounds with CI feedback; maintainability is assessed through functional correctness across successive iterations. | Score correctness cumulatively across iterations and record the feedback available at each round. | Real histories improve realism but raise contamination risk and do not control the starting design; correctness over time is an indirect maintainability measure. |
| [SWE-EVO](https://arxiv.org/abs/2512.18470) | Benchmark; Supporting | Release-sized evolution tasks requiring coordinated changes across files. | Use release-scale change as a separate evaluation setting rather than extrapolating from isolated-issue success. | Comparisons with single-issue benchmarks involve different task populations and cannot isolate a causal difficulty factor. |
| [SWE-Milestone](https://arxiv.org/abs/2603.13428) | Benchmark; In depth | Compares isolated milestones with building on an agent's own prior work; the notes identify regressions as a major failure source. | Primary public reference for the age and longevity axis in the evaluation grid. | Distinguish degraded agent-produced checkpoints from matched reference checkpoints. |
| [WEAVE](https://arxiv.org/abs/2610.22039) | Benchmark; In depth | Executable multi-PR tasks; Graph Credit measures dependency-consistent partial progress using test evidence. | Preserve dependency information and cumulative obligations rather than counting independent patches. | Dependency-aware partial credit is not a general measure of maintainability or semantic preservation over time. |

### Requirements, specifications, and enforcement

| Work and source | Type / reading depth | Evaluation focus or idea | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [ANCHOR](https://arxiv.org/abs/2610.16859) | Benchmark; Supporting | Scores atomic constraints and AND/THEN/PRIORITY relations using diffs, trajectories, rule-based checks, and LLM judges. | Separate task correctness, individual compliance, and satisfaction of all required constraints; retain execution evidence. | Some judgments are not executable behavioral oracles; workflow compliance does not imply product correctness. |
| [Architecture as Capability Equalizer](https://arxiv.org/abs/2608.21747) | Study; Supporting | Studies how explicit TypeScript contracts affect models of differing capability. | Model capability may moderate the value of explicit contracts, so it should be treated as a factor, not only a nuisance variable. | Effects may depend on model strength; do not extrapolate a weaker-model gain to all solvers. |
| [Are LLM-Generated Formal Specifications Faithful to Their Requirements?](https://arxiv.org/abs/2610.32053) | Study; In depth | Studies generated ACSL specifications and Frama-C verification; weak or implementation-mirroring specifications can admit incorrect code. | Grade whether the spec captures the requirements separately from whether the implementation satisfies it. Check that the spec rejects known incorrect implementations. | Successful verification is relative to the supplied specification; specification fidelity needs an independent assessment. |
| [Beyond Prompts: Runtime Contracts for Coding Agents](https://arxiv.org/abs/2611.19549) | Study; In depth | Compares execution-time rule enforcement with prompt guidance and checks after generation. | Motivates a future enforcement comparison; distinguish runtime prevention from later repair and qualify the oracle against faults the gate may miss. | Zero detected violations is bounded by oracle coverage; gates and graders can share blind spots, and later repair cannot undo executed commands. |
| [CodeSpec](https://arxiv.org/abs/2607.26777) | Study; Supporting | Compares executable architectural specifications with textual designs. | Supports distinguishing executable structure from prose design guidance. | Executable structure, feedback, and information content must be accounted for before attributing a gain to representation alone. |
| [Constraint Decay (v2, Sep 2026)](https://arxiv.org/abs/2605.06445) | Study; In depth | Holds an API contract fixed while varying structural requirements; uses behavioral tests and static verifiers. | Score behavior and structural compliance separately, including whether both hold simultaneously. | Structural constraint burden is not identical to semantic coupling among business rules. |
| [Hickey spec-first proposal](https://arxiv.org/abs/2611.02285) | Proposal; In depth | Proposes making formal specifications the primary reviewed artifact, with code and proofs as build outputs. | A kindred spec-first architecture, useful as a conceptual comparison rather than a Cohesive efficacy result. | A conceptual proposal is not empirical evidence of Cohesive efficacy. |
| [RPG / RepoCraft](https://arxiv.org/abs/2509.16198) | Method; Supporting | Uses a repository planning graph to organize whole-repository construction. | Another structured-spec approach to compare with Cohesive's persisted semantic model. | A planning graph is not automatically an executable semantic model or a correctness guarantee. |
| [SaltBench](https://arxiv.org/abs/2609.11076) | Benchmark; Supporting | Uses a preregistered, referee-gated protocol for comparing development methods. | Methodological model for an independent referee and pre-registered comparisons. | An external referee still needs a qualified oracle and a clearly defined evaluation boundary. |
| [Skeleton Coding](https://arxiv.org/abs/2610.38214) | Study; In depth | Supplies types, modules, signatures, and behavioral specifications; compares implementation error and cost across specification forms. | Treat the representation supplied to an agent as an experimental variable. | Benefits of supplied structure do not establish the cost of eliciting and authoring the right structure from stakeholder intent. |
| [Specification Before Generation](https://arxiv.org/abs/2609.23270) | Study; Supporting | Advocates specifying requirements before generating code so the oracle is not simply inferred from the implementation. | Aligns with Cohesive's spec-first, checkable-meaning stance. | Specification-first ordering alone does not guarantee specification fidelity or oracle independence. |
| [SWE-Clar](https://arxiv.org/abs/2610.31854) | Benchmark; In depth | Separately evaluates clarification with a simulated client, requirement understanding, and implementation against acceptance tests. | Assess elicitation, understanding, and implementation separately; isolate requirement-understanding questions from implementation runs. | The client answers from fixed hidden requirements; this measures elicitation and transmission, not how stakeholders decide what they want. Keep understanding assessments isolated to prevent leakage. |
| [SWE-CoWork](https://arxiv.org/abs/2611.20218) | Benchmark; In depth | Agents gather requirements from coworkers in a simulated company and implement assignments. The Oracle-Spec condition supplies complete requirements. | Compare an agent’s completion claims with executable assignment checks. | Simulated coworkers and testable assignments bound how far the results generalize to real teams. |

### Engineering instructions and observed changes

| Work and source | Type / reading depth | Evaluation focus or idea | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [AIDev dataset](https://arxiv.org/abs/2507.15003) | Dataset; Supporting | Dataset of agent-authored pull requests for studying repository changes. | Observational evidence on agent-authored change, useful context rather than a Cohesive benchmark. | Observational context; agent selection and repository selection do not constitute a controlled treatment. |
| [ContextCov](https://arxiv.org/abs/2603.00822) | Study; Supporting | Turns context-file instructions into executable checks and compares compliance with prompt-only guidance. | Compare prompt-only guidance with executable enforcement while measuring behavioral correctness separately. | Check coverage and correctness bound the enforcement claim; compliance is not application correctness. |
| [Do They Do as They Are Told?](https://arxiv.org/abs/2611.13709) | Study; In depth | Operationalizes observable instructions into executable compliance checks and studies adherence. | Do not assume that writing an obligation in AGENTS.md enforces it; check consequential requirements directly. | Observational adherence does not isolate the causal effect of a particular instruction or establish compliance with unobservable rules. |
| [Needle in the Repo](https://arxiv.org/abs/2603.27745) | Benchmark; Supporting | Evaluates maintainability using structural checks in addition to functional behavior. | Supports scoring structure and maintainability as first-class outcomes. | Structural scores remain proxies until related to change effort or regressions. |

### Language and stack familiarity

| Work and source | Type / reading depth | Evaluation focus or idea | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [AgentScript-Eval](https://arxiv.org/abs/2611.13183) | Benchmark; In depth | Separates compilation and behavioral outcomes; varies zero-shot versus compile-and-edit workflows and domain guidance. | Control documentation and feedback, record unfamiliarity, and score semantics beyond successful compilation. | Results combine a particular DSL, task set, model, and harness; they do not establish that DSLs generally help or hurt. |
| [Can AI Agents Generate Microservices?](https://arxiv.org/abs/2603.09004) | Study; Supporting | Studies generation of multi-service systems rather than single-service patches. | Extend the domain comparison toward multi-service construction while independently checking interaction semantics. | Generating multiple services does not establish distributed correctness or operational reliability. |
| [LLM Framework Benchmark](https://github.com/tomas-samek/llm-framework-benchmark) | Benchmark; Supporting | Compares implementation of a shared specification across frameworks and versions. | Studies must report a familiarity control and pin framework versions. | Version recency, tool support, and familiarity can confound comparisons; pin the tested versions. |
| [Matthew effect paper](https://arxiv.org/abs/2509.23261) | Study; Supporting | Studies differences between popular and niche technology stacks in agent performance. | Record low-exposure and familiarized conditions separately; do not infer equal model familiarity from matched tooling. | Training exposure is a possible explanatory factor, not a directly controlled measure of familiarity. |
| [Metaprogramming for unfamiliar languages](https://arxiv.org/abs/2606.10933) | Study; Supporting | Studies executable helper code as support for unfamiliar languages, compared with textual guidance. | Supports separating executable feedback from textual skills when evaluating a new language. | Separate helper execution, feedback, and documentation from the language representation itself. |
| [ScarfBench](https://arxiv.org/abs/2605.06754) | Benchmark; Supporting | Enterprise Java migration tasks provide a legacy-stack evaluation setting. | Use migration tasks to examine version and stack sensitivity separately from representation effects. | Migration difficulty and stack familiarity are distinct factors; legacy does not necessarily mean unfamiliar. |

### Assurance and oracle quality

| Work and source | Type / reading depth | Evaluation focus or idea | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [AlphaProof Code (Signal verification)](https://google-deepmind.github.io/code-verification) | Study; In depth | Uses human-approved Lean specifications and machine-checked proofs of selected security properties of compiled libsignal; includes mutation-based specification validation. | Separate approval of specifications, proof production, proof checking, and mutation-based validation of specification strength. | A verification case study, not a general coding benchmark. Claims remain subject to the modeled execution and cryptographic assumptions. |
| [BackendForge](https://arxiv.org/abs/2607.11042) | Benchmark; Supporting | Backend evaluation with strengthened behavioral oracles that expose previously accepted incorrect solutions. | Apparent success depends on oracle strength; architecture checks cannot replace robust behavioral grading. | Oracle hardening changes the measurement; record evaluator versions and rescore comparable submissions. |
| [CodeT](https://arxiv.org/abs/2207.10397) | Method; Supporting | Selects among generated candidate programs using generated tests. | Early method for test-based selection; still leaves the oracle dependent on generated tests. | Consensus between generated programs and tests is not an independent correctness oracle. |
| [EvalPlus](https://arxiv.org/abs/2305.01210) | Benchmark; Supporting | Augments function-level coding benchmarks with stronger test suites. | Foundational warning that a weak oracle inflates scores. | Additional tests improve fault detection without establishing complete behavioral coverage. |
| [HumanEval / Codex](https://arxiv.org/abs/2107.03374) | Benchmark; Supporting | Function-level code generation evaluated using handwritten tests. | Foundational coding eval; later work showed its tests are too thin for a trustworthy oracle. | Small function tasks and thin suites do not establish repository-level or system correctness. |
| [Spec-Driven PBT (ViBench, PBTBench)](https://arxiv.org/abs/2611.15920) | Method; In depth | Compares specification-derived and implementation-derived property-based tests, which expose different bugs. | Supports deriving the oracle from requirements, with Cohesive types and checks as a further step toward checkable properties. | Specification-derived tests can still share omissions with the specification; use complementary evidence and qualify the oracle. |
| [SWEOps-Bench](https://arxiv.org/abs/2611.06099) | Benchmark; In depth | Agents inspect runtime evidence and submit source/configuration repairs; evaluation covers recovery, stage accuracy, latency, and tokens. | Verify externally observable recovery and behavior, not just an agent's explanation or disappearance of symptoms. | A bounded, reproducible incident suite does not cover every failure mode or the full operational lifecycle. |
| [Test/verification technique effectiveness with Astra](https://danluu.com/astra-testing/) | Study; In depth | Compares testing and verification approaches using independent holdouts on tasks of differing difficulty. | Use independent holdouts and tasks hard enough to distinguish verification strategies. Compare cost and correctness across task sizes rather than generalizing from a saturated benchmark. | Ceiling effects obscure differences; task-specific results do not establish a universally best verification technique. |
| [TestSuiteBench](https://arxiv.org/abs/2610.13065) | Benchmark; In depth | Evaluates generated suites against a reference implementation and requirement-targeted mutants. | Qualify independent evaluation rather than relying solely on an agent's own tests. | The reference behavior and mutant population bound what the scores establish; mutation score is not production defect coverage. |
| [TLAPS-Bench](https://arxiv.org/abs/2611.02849) | Benchmark; In depth | Agents construct machine-checked proofs using TLAPS, including invariant discovery and proof decomposition. | Keep targets and grading tools protected; check proofs in a clean environment and track dependencies as well as proof completion. | Proof success is relative to the formal specification and assumptions; implementation conformance and intent validation remain separate. |
| [UTBoost: Rigorous Evaluation of Coding Agents on SWE-Bench](https://arxiv.org/pdf/2506.09289v1) | Method; Supporting | Strengthens issue-specific tests and audits evaluation parsing, uncovering patches previously marked as passing. | Passing existing tests is not a sufficient correctness oracle. Augment issue-specific tests against a reference implementation and audit the grading pipeline itself; keep verification independent of the agent's patch. | Grading pipeline defects and weak behavioral coverage are distinct causes of false success. |

### Product construction and use

| Work and source | Type / reading depth | Evaluation focus or idea | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [SaaS-Bench (agents using SaaS apps)](https://arxiv.org/abs/2605.15777) | Benchmark; In depth | Professional workflows performed by agents across deployable SaaS applications. | Shows agents using SaaS apps, not building them; a reminder not to conflate product-use evals with construction evals. | Evaluates using products, not constructing or maintaining them. |
| [SaaSBench](https://arxiv.org/abs/2605.17526) | Benchmark; Supporting | Evaluates enterprise SaaS application construction. | Closer in domain to Cohesive's intended product setting than issue-to-patch benches. | Product-build success does not establish preservation of obligations through later evolution. |

### Work structure, evidence, and trend context

| Work and source | Type / reading depth | Evaluation focus or idea | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [Benchmarks Are Surprisingly Compaction-Friendly](https://arxiv.org/abs/2610.31778) | Study; Supporting | Compares context-compaction strategies and studies which instructions summaries lose, including differences between benchmark tasks and real sessions. | Track which requirements remain available after compaction; compare persisted, checkable constraints with conversation-only guidance. | Stable objectives and persisted artifacts can make benchmark sessions easier to compact than real work. |
| [Beyond Compaction (Context Window Lifecycle)](https://arxiv.org/abs/2606.11213) | Method; Supporting | Structures working memory into typed episodes and dependencies, with deterministic eviction when context exceeds budget. | Treat working-memory structure as an experimental factor distinct from code and task structure. | Sequential independent tasks are not equivalent to evolving one coupled system; the compaction comparison is a qualitative case study. |
| [EA-Graph](https://arxiv.org/abs/2608.04278) | Method; In depth | Associates verification claims with exact artifacts and tracks evidence strength, freshness, and invalidation under drift. | Methodological source for evidence provenance and versioned evaluator semantics in cohesive-evals. | An evidence-management method does not itself establish the truth or completeness of the underlying claims. |
| [Epoch benchmark saturation](https://epoch.ai/benchmarks) | Trend tracker; Supporting | Tracks model scores and saturation across benchmarks. | Explains why saturated single-issue benches are a weak place to claim a Cohesive advantage. | Aggregate trends combine task sets, grading practices, and model configurations; they do not measure Cohesive efficacy. |
| [METR time horizon](https://metr.org/time-horizons/) | Trend tracker; Supporting | Estimates the human-expert task duration corresponding to specified agent success probabilities. | A trend ruler for long-horizon capability, not a substitute for Cohesive's semantic-obligation measures. | A task-duration reliability estimate is not the length of time an agent can operate autonomously in production. |
| [Spine](https://arxiv.org/abs/2610.37224) | Method; In depth | Compiles subtask trees into structured context and evaluates the method on SWE-Milestone. | A context-management method tested on SWE-Milestone; a factor to distinguish from structuring the program itself. | Changes to agent context must be distinguished from changes to the program representation. |
| [SWE-bench Verified (Pro noted separately)](https://www.swebench.com/verified) | Benchmark; Supporting | Repository issue-repair benchmark family used as a capability reference. | Use as issue-repair context, with benchmark variant and oracle version explicitly identified. | The supplied link identifies Verified, not Pro; treat them as distinct benchmark variants, not one score. |

### Distributed-system diagnosis

This earlier repo entry is retained although it is absent from the current
Notion database. Its reading depth is not recorded there.

| Work and source | Kind / evaluation unit | What it evaluates and how | Implication for cohesive-evals | Interpretation limit |
|---|---|---|---|---|
| [DistDebug-Bench](https://arxiv.org/abs/2611.03523) | Distributed-system debugging benchmark; historical bugs | Evaluates code-level diagnosis of real failures across distributed-system repositories. | Distinguish locating/explaining a failure from repairing it and demonstrating preserved invariants. | Diagnosis performance should not be presented as verified repair or production reliability. |

## Benchmark scoring metrics

The linked papers and official evaluator documentation define the scores. The
[RoadmapBench paper](https://arxiv.org/abs/2605.15846) accompanies its linked repository.
The Pro variant has a separate [official evaluation protocol](https://labs.scale.com/leaderboard/swe_bench_pro?tab=public).

The table covers all 26 distinct works tagged **Benchmark** in the Notion database. Both SWE-Clar records use the same scoring description. Each row identifies the unit that earns credit and the evidence used to grade it. The landscape entries above give the interpretation limits for each work.

| Benchmark and source | Scoring metric and unit of credit | Methodology |
|---|---|---|
| [AgentScript-Eval](https://arxiv.org/abs/2611.13183) | Direct-generation pass@3 counts tasks where every check passes in at least one of three executions of the same compiled program. Pass rate averages the fraction of checks passed per task. | Generate and compile once for direct prompting. Repeat execution to capture runtime variability. Compiler-feedback agent configurations use pass@1. |
| [ANCHOR](https://arxiv.org/abs/2610.16859) | Report atomic and relation compliance separately. Full-checklist compliance counts tasks passing every scored item. Task completion is graded independently. | Scores atomic constraints and AND/THEN/PRIORITY relations using diffs, trajectories, rule-based checks, and LLM judges. |
| [BackendForge](https://arxiv.org/abs/2607.11042) | Task success is the fraction of submitted backends that build, start and pass the entire hidden oracle. Rescoring a fixed submission against successive oracle versions measures attrition. | Run the service against specification-grounded pytest checks. Review candidate checks against the written contract and OpenAPI definition before admitting them. |
| [CodeSpecWeave](https://arxiv.org/abs/2610.40256) | Pass rate counts task attempts accepted by the executable verifier. The paper’s requirement-level error categories come from qualitative review of failed attempts. | A synthesis agent builds coupled requirements and executable tests; a review agent audits test reliability against multiple models' trajectories. |
| [DeepSWE](https://arxiv.org/abs/2607.07946) | Pass@1 averages per-task success rates with equal task weights. Pass@4 counts tasks solved in any of four rollouts. | Grade with handwritten functional verifiers. Timeouts and context exhaustion count as failures. Provider, network and verifier errors are excluded. |
| [EvalPlus](https://arxiv.org/abs/2305.01210) | Function-level pass@k under the original and expanded suites. Compare the same generated candidates at the same k. | Run the same function completions on HumanEval and HumanEval+. The augmented suite uses generated and mutated inputs with expected results derived from the reference implementation. |
| [HumanEval / Codex](https://arxiv.org/abs/2107.03374) | Function-level pass@k estimates the chance that at least one of k sampled programs passes every handwritten test, averaged over problems. | Sample n completions for each prompt and count c that pass all tests. Estimate pass@k as 1 − C(n−c,k)/C(n,k) per problem, then average over problems. |
| [LLM Framework Benchmark](https://github.com/tomas-samek/llm-framework-benchmark) | Conformance rate by framework, version and stage. Count passing trials within each configuration using the stage-specific external oracle. | Start trials from the supplied scaffold and specification. Stage 1 uses an external Kafka fixture oracle. Later stages also grade criteria such as code quality and ticket handling with separate rubrics. |
| [Multi-step SWE](https://arxiv.org/abs/2611.07166) | Solve rate divides rollouts passing every step by all rollouts. Pass@4 divides tasks solved in any of four rollouts by all tasks. Step pass rate counts steps receiving full credit. | Sequences of dependent implementation steps, with complete-task success distinct from step success and failures propagating across steps. |
| [Needle in the Repo](https://arxiv.org/abs/2603.27745) | A probe passes only when both the hidden functional tests and its structural oracle succeed. | Build the edited repository and run both checks. A micro probe grades one change. A multi-step probe grades the code left after successive changes. |
| [RoadmapBench](https://github.com/UniPat-AI/RoadmapBench) | Resolved Rate is the share of tasks with full reward. Completion Score averages each task’s complexity-weighted fraction of passing targets. | Substantial multi-target changes drawn from open-source upgrade roadmaps, withholding target code, tests, and reference patches. |
| [SaaS-Bench (agents using SaaS apps)](https://arxiv.org/abs/2605.15777) | Resolved Score requires every checkpoint to pass. Checkpoint Score divides the weight of passing checkpoints by the total checkpoint weight for the workflow. | Reset the applications, let the agent operate through the browser, then grade final state and artifacts using state queries, content checks and rubric-based judgments. |
| [SaaSBench](https://arxiv.org/abs/2605.17526) | The single-rollout score averages earned points divided by available points per build, weighting the 30 builds equally. Node coverage separately counts the fraction of nodes marked passed. | Evaluate validation nodes in dependency order with executable checks and rubric-based judgments. Exclude unavailable or unparseable judge results (SKIPPED_LLM) from the task’s available points. |
| [SaltBench](https://arxiv.org/abs/2609.11076) | Withheld referee outcomes and paired method costs on the same components. Budget halts are recorded separately. | Compare preregistered method arms on matched Rust components with a pinned Verus toolchain. A withheld suite outside the agent’s toolchain grades the submissions. |
| [ScarfBench](https://arxiv.org/abs/2605.06754) | Aggregate behavioral test pass rate and fully passing migrations, grouped by layer and framework direction. Compilation and deployment gate behavioral testing. | Migrate a working Java application to another framework. Build and deploy it in a container, then exercise its observable interface with application-specific tests. |
| [SlopCodeBench](https://arxiv.org/abs/2603.24755) | Checkpoint pass rate and complete-problem success. Complexity concentration and redundant code are tracked along each solution trajectory. | Requires each checkpoint's tests to pass; tracks structural erosion (concentrated complexity) and verbosity (redundant code), compared with open-source Python repositories. |
| [SWE-bench Verified / Pro](https://www.swebench.com/verified) | Resolve Rate is the fraction of instances whose patch passes every required fail-to-pass and pass-to-pass test. Report Verified and Pro separately by evaluation split. | Apply the patch to the starting revision and run issue-specific tests. Verified uses 500 human-screened instances. Pro uses its own repository population and splits. |
| [SWE-CI](https://arxiv.org/abs/2603.03823) | EvoScore averages normalized changes in passing tests across iterations, with configurable weighting toward later rounds. Gains are scaled by the baseline-to-target gap and losses by the baseline passing count. | Agents work through repeated analysis/coding rounds with CI feedback; maintainability is assessed through functional correctness across successive iterations. |
| [SWE-Clar](https://arxiv.org/abs/2610.31854) | Implementation score counts tasks passing every acceptance test. Clarification answers earn 0, 0.5 or 1. Average first over questions within each task, then equally over tasks. | Freeze the simulated-client conversation and fork it into isolated implementation and question-answering runs. A judge compares answers with references. |
| [SWE-CoWork](https://arxiv.org/abs/2611.20218) | Pool passing and total test nodes across assignments separately for fail-to-pass and pass-to-pass rates. Complete pass rate counts assignments passing every node of both types in one run. | Agents gather requirements from coworkers in a simulated company and implement assignments. The Oracle-Spec condition supplies complete requirements. |
| [SWE-EVO](https://arxiv.org/abs/2512.18470) | Resolved Rate requires every repair and regression test to pass. Per-instance Fix Rate credits the fraction of fail-to-pass tests fixed, but drops to zero if any pass-to-pass test regresses. | Implement release-note requirements from a starting revision. Apply the patch and grade new functionality and preserved behavior with the release’s tests. |
| [SWE-Milestone](https://arxiv.org/abs/2603.13428) | Per milestone, recall = fixed/required and precision = (fixed+1)/(fixed+broken+1). Average their harmonic mean within each evolution range, then equally across ranges. Resolve Rate requires all milestone tests to pass. | Compare continuous edits on agent-produced code with independent attempts from canonical snapshots. Count newly fixed feature tests and newly broken regression tests. |
| [SWEOps-Bench](https://arxiv.org/abs/2611.06099) | Incident recovery rate across scenarios, with faulty-state detection, stage accuracy, latency and token use reported separately. | Agents inspect runtime evidence and submit source/configuration repairs; evaluation covers recovery, stage accuracy, latency, and tokens. |
| [TestSuiteBench](https://arxiv.org/abs/2610.13065) | Validity is the fraction of generated tests passing on the reference. Mutation Score is the fraction of targeted mutants killed by at least one valid generated test. | Evaluates generated suites against a reference implementation and requirement-targeted mutants. |
| [TLAPS-Bench](https://arxiv.org/abs/2611.02849) | Proof pass@3 estimates the share of targets with at least one accepted proof in three attempts. | Agents construct machine-checked proofs using TLAPS, including invariant discovery and proof decomposition. |
| [WEAVE](https://arxiv.org/abs/2610.22039) | Graph Credit averages effective credit over evaluable nodes. Each node’s credit is capped recursively by its own test completion and the least credit among its prerequisites. | Executable multi-PR tasks; Graph Credit measures dependency-consistent partial progress using test evidence. |

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

The expanded reading list suggests several additional experimental distinctions:

- **Accumulation versus step difficulty:** compare a step on an agent-produced
  checkpoint with the same step on a qualified reference checkpoint.
- **Representation versus enforcement:** distinguish the value of expressing a
  rule from checks that enforce it, and from guidance to follow it.
- **Specification fidelity versus conformance:** test whether a specification
  rejects known requirement violations as well as whether code satisfies it.
- **Program structure versus context management:** record compaction, memory,
  documentation, and tool support independently of the software condition.
- **Oracle strength versus apparent capability:** version graders, qualify their
  failure detection, and protect grading tools from candidate modifications.

These are design considerations for later experiments, not new conditions or
scoring rules for the existing pilots.

## Measurement map

Candidate measures for discussing the landscape and designing later experiments.
Only measures admitted by each protocol belong in its actual scoring.

| Concern | Useful measure | Main caution |
|---|---|---|
| Task success | Fraction of valid runs satisfying every required obligation | Keep complete success distinct from average check pass rate. |
| Correctness preservation | Per-obligation outcomes across checkpoints; regressions and repairs | Check all active obligations; distinguish failure from not evaluated. |
| Intent preservation | Trace stakeholder examples/decisions to explicit obligations; measure preservation of those obligations | This measures specified intent. Validating that the specification captures actual intent requires separate stakeholder evidence. |
| Specification fidelity | Requirement-understanding checks and known incorrect implementations rejected by the specification | Separate elicitation from stakeholder intent validation; keep assessment questions from leaking into implementation. |
| Evidence provenance | Artifact, specification, checker, and oracle versions attached to each claim | Evidence can become stale after changes; a previously valid proof or test result does not automatically transfer. |
| Context preservation | Active requirements retained or recoverable after compaction; subsequent compliance | Memory retention is not correctness, and on-disk artifacts can make benchmark compaction unusually forgiving. |
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
