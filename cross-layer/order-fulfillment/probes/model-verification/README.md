# MV1: reuse a model for verification

[#28](https://github.com/cohesivesystems/cohesive-evals/issues/28) asks whether the
same model that executes business rules can help author and maintain useful tests.

- [Capability audit](capability-audit.md): actual reservation execution works in both conditions. Assurance can evaluate independent claims and state-only finite admission; quantity-dependent finite admission and ordinary typed Int32 subtraction hit explicit limits.
- [Protocol](protocol.md): matched authoring/maintenance tasks, independent requirements, held-out defects, feedback and measurement boundaries.
- [Planned matrix](test-matrix.md): obligations for the separate implementation PR.
- [Runnable witness](audit/run.py): ten manually selected examples per condition, positive/negative capability controls and pinned evidence. This is evaluator tooling, not application code under evaluation.

No automatic test generator or MV1 defect suite is implemented here. The independent
Python oracle remains authoritative for external behavior. Model-derived tests
must not be allowed to validate an incorrect model against itself.
