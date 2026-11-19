# What Coding Agents Can Teach Us About Software Engineering

Suppose two teams build the same order fulfillment service. One represents the order lifecycle as an explicit state machine. The other puts the rules in the handlers that need them. Both implementations pass every acceptance test. Then a customer asks for the ability to put an order on hold. A warehouse worker may already have picked it. A shipment request may already be in flight. Tomorrow, the order may be released again. Which design would you rather change?

Most experienced engineers have an opinion. They can tell you where they expect a mistake, which code they would want to read, and what they think will happen on the fifth change. Much of what we call *taste* consists of predictions like these. The consequences are real even when they are difficult to measure.

A question Ron Minsky raised gets at why this is newly interesting. Which software design practices are useful to coding agents, and which ones can they do without? We developed much of our engineering advice around the abilities and limitations of human programmers. An agent may get a different return from a small module, an explicit type, a unit test, or an extra layer of indirection. The human who reviews its work still has a stake in all four.

Coding agents also give us a way to investigate the question. We can start from the same repository, issue the same sequence of requests, change one aspect of the design, and repeat the experiment. Empirical software engineering has a long history. What has changed is the cost of asking another programmer to do the whole thing over again.

I started reading software engineering benchmarks to understand how well agents can build and maintain software. The more interesting papers also shed light on the environment we ask them to work in. Take three pieces of familiar engineering advice and ask what each predicts. If an agent writes the tests first, does it catch more regressions on the next change? If it introduces an architectural boundary, which later changes become cheaper? If we give it a type signature, which mistakes does it avoid that it makes with the same requirement expressed in prose?

## What a benchmark score tells us

A benchmark can rank agents, diagnose a weakness, or test an engineering practice. Those goals call for different experiments. To rank agents, we can give them the same repository issue and score the resulting patch. To study design, we might hold the agent fixed, supply two different starting designs, and examine the changes it makes to each. A leaderboard can tell us which system to try. Explaining *why* it did better takes another comparison.

It helps to understand what goes into that system. During pre-training, a model learns patterns from code and text. Two libraries that provide equivalent functionality may present very different tasks to a model that has encountered one library’s idioms extensively. Post-training further shapes how a model uses tools, follows instructions, and responds to feedback. In a reinforcement learning environment, a model can take actions in a repository and receive a reward when its patch passes checks. The reward captures whatever the checks discriminate. A missing requirement can be invisible both to the model and to the process training it.

At evaluation time, the model operates inside a harness. The harness determines which files it can see, which tools it can call, how much history it retains, and when it must stop. An agent that corrects a patch after a failed build can do so with fixed model weights. The compiler diagnostic has changed the information available for its next decision. This matters when interpreting progress. A better model, a better diagnostic, and a larger retry budget can all raise the same score.

For each study, I want to know what the agent received, what the experiment varied, what the authors held fixed, and **what counted as success**. The last question concerns the *oracle* — the mechanism that determines whether the result is acceptable. An oracle might run hidden tests, inspect a dependency graph, check a proof, or observe a service after a repair. Each can justify a different claim.

This also clarifies saturation. Once leading systems solve nearly every task within the allowed budget, the benchmark loses much of its ability to distinguish them by pass rate. Solving those tasks reliably at a tenth of the cost would still be progress. Asking the agent to maintain the resulting software through six more changes would be a different experiment altogether.

## A map of the work

The evaluations span CLI programs, SaaS backends, distributed systems, and deployed infrastructure. Within any of those settings an agent might implement a feature, diagnose a failure, write tests, or prove a property. I find it easier to navigate the literature by asking what responsibility the experiment gives the agent.

| Engineering question | Representative work | What the evaluator can inspect |
|---|---|---|
| Can the agent deliver dependent changes toward a milestone? | WEAVE | Test results and dependencies among related pull requests |
| Can it satisfy several requirements together? | Constraint Decay, ANCHOR, CodeSpecWeave | Functional behavior, structural constraints, and evidence of required steps |
| Does the representation or guidance help? | Skeleton Coding, AgentScript-Eval | Outcomes as interfaces, instructions, or compiler feedback change |
| Can the agent maintain software across changes? | SlopCodeBench, SWE-CI | Code structure and behavior across successive versions |
| Can the agent establish that software behaves correctly? | TestSuiteBench, TLAPS-Bench | Detection of deliberate faults or acceptance of machine-checked proofs |
| Can it diagnose a failure and restore service? | DistDebug-Bench, SWEOps-Bench | Code-level diagnoses, submitted repairs, or observed recovery |

The unit of scoring matters even within one row. Imagine an agent satisfies nine of ten requirements on every task. It scores 90% by requirement and 0% by complete task. If the missed requirement is “a retry must never charge the customer twice,” the second number is closer to the release decision. I’d still want the first number and the identity of the failed requirement to understand what to fix.

CodeSpecWeave constructs tasks in which the requirements interact. Its benchmark contains 100 tasks with 1,044 specifications across them. Think of an order service that must retry a failed shipment request and must never ship the same order twice. Either rule is straightforward to test in isolation. The interesting case comes when the warehouse accepts the first request but its acknowledgment never arrives. That is the kind of interaction I’d want a benchmark to exercise before giving an agent credit for satisfying both requirements. [CodeSpecWeave](https://arxiv.org/abs/2610.40256)

## Which kinds of structure help?

Who does the design work? In *Skeleton Coding*, the agent receives part of the design up front through types, module boundaries, and function signatures. In *Constraint Decay*, the agent has to produce a working design under additional architectural requirements. That difference matters when interpreting what each study says about structure.

The *Skeleton Coding* authors find that a supplied skeleton can improve implementation outcomes over a prose task description. A signature narrows several decisions at once. It tells the agent which component owns an operation, what information reaches it, and what its callers can expect back. There is a cost outside the measured implementation step, though. Someone had to discover that decomposition. A skeleton extracted from a reference solution gives the agent the benefit of design work already done. [Skeleton Coding](https://arxiv.org/abs/2610.38214)

*Constraint Decay* holds a backend API contract fixed and adds structural requirements such as architectural layering or database access through an ORM. Behavioral success can fall as those obligations accumulate. Giving an agent a good interface resolves a design decision. Asking it to invent and implement an architecture adds decisions, integration work, and opportunities for error. [Constraint Decay](https://arxiv.org/abs/2605.06445)

That distinction carries over to libraries. A durable workflow library might discharge much of the work of persisting and resuming a process. It also asks the programmer to understand its execution semantics. A useful comparison would give agents the same recovery obligation and observe what happens after a crash. It would charge the library condition for documentation and integration effort, and the conventional condition for building and maintaining whatever recovery mechanism it needs.

Work and context have structure too. WEAVE groups related pull requests by their dependencies, which makes it possible to distinguish independently passing patches from progress toward a usable milestone. ANCHOR examines engineering instructions that must hold together or be carried out in order. An observational study of repository context files asks a narrower question familiar to anyone who has written an `AGENTS.md` file. Which instructions leave enough evidence in a commit to determine whether the agent followed them? An instruction to use a particular API may be visible in the diff. An instruction to think through failure cases before editing generally leaves less evidence. [WEAVE](https://arxiv.org/abs/2610.22039) · [ANCHOR](https://arxiv.org/abs/2610.16859) · [Do They Do as They Are Told?](https://arxiv.org/abs/2611.13709)

Guidance can matter even when the language and tools stay fixed. In AgentScript-Eval, improving the guidance helped agents produce programs that passed behavioral checks. Compiler feedback also gave them an opportunity to repair invalid programs. These interventions suggest different experiments for teams designing agent memory. Should an agent retain the history of a decision, retrieve a worked example when it needs one, or encounter the rule as a compiler check at the point of violation? The answer depends partly on whether its difficulty is finding the rule, interpreting it, or noticing that it has broken it. [AgentScript-Eval](https://arxiv.org/abs/2611.13183)

## The fifth change is where design earns its keep

A first implementation is a poor place to settle arguments about maintainability. The team that invested in the order state machine may have spent more time and written more code. Its claim is that when the hold feature arrives, the permissible transitions will be easier to identify and change. An experiment that ends before the hold request measures the investment and misses the proposed return.

SlopCodeBench gives an agent a succession of extensions to the same program. The authors track how much code becomes redundant or duplicated and how much complexity accumulates in already complex functions. SWE-CI follows maintenance through repeated rounds of analysis and coding with feedback from continuous integration. Together they suggest a way to investigate a familiar code-review judgment. If I say a function is becoming too complicated, I’m making a prediction about the next person or agent who changes it. Can they still find the right place to edit? How long does the change take? Which earlier behavior breaks? [SlopCodeBench](https://arxiv.org/abs/2603.24755) · [SWE-CI](https://arxiv.org/abs/2603.03823)

We can expose that return by saving checkpoints and asking fresh agents to make equivalent changes to an early and a later version. We can record whether the requested feature works, which previously satisfied requirements regress, and how much effort goes into finding and repairing them. A handoff adds a further test. Can a new maintainer explain whether shipment is allowed while a hold is pending, predict what happens after release, and locate the code responsible? Those questions give readability an audience and a purpose.

The same reasoning applies to claims about FP, OOP, SOLID, and clean code. Each label bundles many choices. One tractable comparison would represent order states as a closed set of cases in one implementation and as mutable flags in another, then ask both agents to introduce a new state. Now there is a specific mechanism to investigate. Which illegal combinations can each representation express? When a case is missed, who discovers it, and when? A result on that experiment would tell me more about the next design decision than an overall quality score for either paradigm.

Scalability likewise becomes measurable once we say *what grows*. Increasing concurrent orders for one tenant can expose a bottleneck that adding many low-volume tenants never reaches. Maintainability depends on the distribution of future changes in much the same way that scalability depends on the distribution of workloads. Selecting those changes is itself an engineering judgment.

## Testing and verification are capabilities of their own

One of the most revealing experiments reverses the familiar benchmark setup. Give the agent a specification and ask it to write the *tests*. Run those tests against a reference implementation, then against versions containing deliberately introduced faults. A good suite needs to accept correct behavior and reject meaningful deviations.

TestSuiteBench illustrates the size of the distinction. In the reported Claude Opus 5 evaluation, 96.1% of generated tests passed on the reference implementation, while the generated suites detected 55.5% of the injected faults. Those percentages have different denominators. The first tells us how often individual tests accept the reference. The second tells us how often a suite distinguishes a faulty implementation from it. The remaining faults survived a suite that could look reassuring on a clean run. The faults were constructed for the experiment, so the detection rate is specific to that population. [TestSuiteBench](https://arxiv.org/abs/2610.13065)

If we want to know whether writing tests *first* helps, the order of the work has to be part of the experiment. Give two groups the same requirement and budget. Ask one to write a failing test before implementing each behavior, and the other to write its tests afterward. Keep the execution history so we can check which process each group followed. Then give both groups the same follow-up change and see which regressions their suites catch. We could learn whether test-first development improves the initial implementation, the ability of the tests to detect errors, or the cost of later changes. Those are three different reasons an engineer might practice TDD.

Formal verification moves the question again. TLAPS-Bench asks agents to construct machine-checked proofs about TLA+ system specifications. A successful proof can cover all executions admitted by the model under its assumptions, including executions nobody thought to write as tests. There is still engineering work on either side of the proof. Someone must establish that the property captures what stakeholders intend and that the deployed implementation realizes the modeled behavior. For the order service, proving that a held order cannot transition to *shipped* means something quite different depending on whether the model includes a shipment request already accepted by the warehouse. [TLAPS-Bench](https://arxiv.org/abs/2611.02849)

## When the system is already running

A distributed failure gives the agent a different starting point. It may have an incident report, logs from several components, and a repository in which every individual handler looks locally reasonable. DistDebug-Bench uses historical distributed-system bugs to study code-level diagnosis. SWEOps-Bench places agents in reproducible incidents involving Kubernetes operators, where they can inspect the environment, change source or configuration, and be evaluated on recovery. A correct explanation and a successful repair are distinct accomplishments. [DistDebug-Bench](https://arxiv.org/abs/2611.03523) · [SWEOps-Bench](https://arxiv.org/abs/2611.06099)

Consider a worker that makes duplicate shipment requests after restarting. Pausing the worker stops the duplicates. It also stops fulfillment. A recovery oracle needs evidence that the worker resumed useful work *and* preserved the constraint on duplicate shipments. This is where operational evaluation meets specification. Deciding what counts as recovered requires a statement of what the service owes its users. Reproducible incidents make that decision tractable, while leaving open how agents perform on rare races or silent drift that takes weeks to surface.

## What I would measure

For an evolving system, my headline measure would be the fraction of runs in which the agent delivers the requested milestone **and all active mandatory obligations pass independent evaluation**. I’d report that alongside cost, including failed attempts. Then I’d keep enough detail to explain the result.

| Question | What I would record |
|---|---|
| Did the change preserve stated intent? | Version the obligations. At each checkpoint distinguish new, modified, retained, and retired requirements. Report which previously passing obligations regressed and which went unevaluated. |
| How credible is the evidence? | Check whether the agent’s tests accept known-correct implementations and detect qualified faults. For proofs, report the property and assumptions. Record cases where the agent declared success despite a failed independent check. |
| What did the work cost? | Record tokens, tool calls by purpose, elapsed time, and monetary cost. Include human time spent preparing specifications, supplying skeletons, reviewing results, and repairing mistakes. |
| How well does the application run? | Measure throughput, tail latency, memory, and recovery under named workloads and failure conditions. |
| Did the design make later work easier? | Track change cost, rework, and regressions across checkpoints. Use authored and generated LOC, churn, duplication, and dependencies to investigate observed differences. |

I’d leave *entropy* out until I could say exactly what quantity it denoted. If the concern is that the same business rule has spread across five components, count the places that encode it, change the rule, and see which copies go stale. That gives the structural measure a consequence we can check.

Even a careful scorecard has limits. A specification recovered from an existing program tells us how well an agent can reproduce selected behavior. It says little about whether anyone wanted that behavior in the first place. A historical repository improves realism while raising the possibility that the model has seen related code. A hand-built fixture gives tighter control while reflecting its author’s expectations about which changes matter. Repeated runs help quantify variability within a setup. Generalizing the result requires trying other tasks, tools, and agents.

## Where I’d take this next

Across these studies, the unit of evaluation is expanding. We can ask an agent to complete dependent changes, meet several obligations at once, produce evidence about its own implementation, and restore a running service. We can also vary the environment and observe the same agent behave differently. That opens up a question I care about as a software designer. **Which representations help a maintainer preserve the rules of a system as the system evolves?**

That is the question behind **cohesive-evals**. The first pilot compares idiomatic C# with `Cohesive.Relations` on a small application change. Its immediate purpose is to establish a fair comparison, with equivalent starting behavior and an independent evaluator. The order fulfillment pilot goes further by comparing changes at fresh and evolved checkpoints and probing obligations that can interact. Separate durability checks exercise recovery under controlled worker failures. These are experimental designs. Whether explicit, executable representations produce better outcomes is the question they are meant to answer.

I’d like to come back to the two fulfillment services with a more precise answer than “I prefer the state machine.” Perhaps it costs more to introduce and prevents a regression on the third change. Perhaps a conventional handler with a good test suite does just as well. Perhaps both agents succeed, but the engineer reviewing one solution can determine in ten minutes whether an in-flight shipment violates the hold. Each outcome would tell us something worth knowing about design. The fifth change gives us a chance to find out.
