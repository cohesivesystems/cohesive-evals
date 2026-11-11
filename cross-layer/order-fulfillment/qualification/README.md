# Application-defect qualification

Run `python3 qualification/run.py` from the case directory. This creates temporary
copies of both conditions, restores/builds each, and runs the invariant verifier
against a fresh PostgreSQL database for every candidate. Participant source is
never modified. The unmodified applications must pass before mutants count.

| Mutation in each condition | Required behavioral assertion |
|---|---|
| Extra stock decrement despite a successful result | Stock conservation |
| Skip release after submission rejects | Stock conservation |
| Return success without creating a reservation | Stock conservation |
| Create another reservation under a different ID | Duplicate reservation per order |
| Lose exact-request replay | Admission replay |
| Accept different input under an existing request ID | Identity conflict |

An expected failure requires all of: successful restore/build, a running seeded
application, nonzero verifier exit, and an assertion record naming the intended
obligation. Compilation errors, startup failures, timeouts, incidental assertion
failures and infrastructure faults do not count as detection. Mutation anchors
must match exactly once; source drift fails qualification rather than silently
skipping a mutation.

`artifacts/qualification/` retains original source hashes, exact before/after
mutations, build logs, verifier logs, failing prefixes and observed/expected
state. `report.json` exists only after the entire matrix passes. The report
contains 14 candidates: two known-good and twelve broken applications.

This qualifies these six defect classes for G0 sequential behavior. It does not
qualify the cumulative hold/evolution oracle, durable recovery, independent-intent
concurrency, or every possible defect. Independent conventional review remains
outstanding even though the baseline PR has merged.
