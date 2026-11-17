# MV1: reuse a model for verification

[#28](https://github.com/cohesivesystems/cohesive-evals/issues/28) asks whether the
same model that executes business rules can help author and maintain useful tests.

- [Capability audit](capability-audit.md): actual reservation execution works in both conditions. Assurance can evaluate independent claims and state-only finite admission; quantity-dependent finite admission and ordinary typed Int32 subtraction hit explicit limits.
- [Protocol](protocol.md): matched authoring/maintenance tasks, independent requirements, held-out defects, feedback and measurement boundaries.
- [Test matrix](test-matrix.md): protocol obligations and implementation coverage.
- [Tooling map](tooling.md): script roles, comments and consolidation assessment.
- [Implemented suites and qualification](implementation.md): matched generated inputs, independent assertions, paired faults and retained integration checks.
- [Runnable witness](audit/run.py): ten manually selected examples per condition, positive/negative capability controls and pinned evidence. This is evaluator tooling, not application code under evaluation.

The independent Python assertions remain authoritative. Model inspection proposes inputs;
it never supplies the expected answers. The implementation is maintainer qualification,
not a blinded trial or an exhaustive proof.
