# Evaluation tooling conventions

- Document Python modules, classes and functions with concise docstrings explaining purpose, inputs/outputs and important failure behavior. Add comments where orchestration, provenance or failure classification is not obvious. Avoid dense one-line methods and compound statements.
- Keep Python focused on orchestration, independent assertions and evidence collection. Reuse existing lifecycle/build helpers; prefer SDK APIs for model inspection, input generation and execution over parsing serialized IR in scripts.
- Before adding a script or dependency, inspect existing repository helpers and relevant established libraries. Consolidate a repeated responsibility when its contract is clear; do not create a generic framework merely to reduce file count.
- Keep test expectations independent from candidate models. Report build/setup/unsupported failures separately from named behavioral failures.
- During benchmark development, improve and publish required Cohesive capabilities first, then update the current eval PR. Preserve honest development evidence without creating separate findings-only PRs for ordinary iteration.
