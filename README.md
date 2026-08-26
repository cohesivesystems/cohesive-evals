# Cohesive evaluations

This repository contains controlled evaluations of whether Cohesive's semantic
representations help a coding agent make correct software changes. It keeps the
experimental protocol, matched application fixtures, private scoring oracles,
runner, and run evidence together without making any one evaluation a general
claim about Cohesive.

The first pilot compares idiomatic conventional C# with
`Cohesive.Relations` on one small application change. Its purpose is to prove
that the comparison can be fair, repeatable, and independently scored before
we automate or broaden it.

## Repository layout

```text
relations/
├── protocol.md
├── cases/
│   └── load-search-mapping/
│       ├── README.md
│       ├── conditions/
│       │   ├── conventional/
│       │   └── cohesive/
│       └── equivalence/
├── oracle/
├── runner/
└── results/
```

- [`relations/protocol.md`](relations/protocol.md) fixes the rules for the v0
  pilot before any evaluated run is performed.
- [`relations/cases/load-search-mapping/README.md`](relations/cases/load-search-mapping/README.md)
  specifies the application case, first task, and observable obligations.
- `conditions/` contains the independently buildable conventional and Cohesive
  starting repositories.
- `equivalence/` contains maintainer checks that enforce matching public
  surfaces and normalized baseline behavior.
- `oracle/` is maintainer-only evaluation material. It must never be copied
  into an agent workspace.
- `runner/` will contain orchestration and scoring code.
- `results/` will contain immutable evidence from evaluation runs.

The v0 protocol is frozen and the two baseline conditions are implemented. The
private oracle's obligation-to-check mapping is at its maintainer review gate;
executable oracle checks, the runner, and run results remain deferred and will
be added without changing the frozen experimental policy.

## Working principles

1. Compare equivalent starting behavior, not identical source code.
2. Change only the software representation between conditions.
3. Give the agent the same task, feedback, permissions, and resource limits.
4. Judge correctness at a shared public application boundary.
5. Keep hidden checks outside the agent's workspace.
6. Treat a harness defect as an invalid experiment, not an agent failure.
7. Preserve obligation-level evidence instead of reducing a run to one score.

## Current scope

The v0 pilot has one case, **Load Search Mapping**, and one task,
**Make Equipment Optional**. It schedules five independent runs per condition.
The results will be descriptive evidence about this configuration only; they
will not establish general developer productivity or Cohesive efficacy.
