# Load Search Mapping baseline audit

Status: open admission record for protocol v0.1. Calibration and pilot runs are
blocked until every required review below is complete.

## Provenance and authorship

- Baseline commit: `fdc65f8b118b60c54894e2fc9055b4a76f7b5a41`
  (the v0 baseline; a new v0.1 baseline revision is required after package
  sanitization).
- Git author and committer: Leo Gorodinski `<eulerfx@gmail.com>`.
- Implementation authorship: both conditions were produced in the same Codex
  workstream under maintainer direction and reviewed together through the
  baseline-equivalence suite.
- Cohesive.Relations source revision:
  `8cf02424cfe9c097e90eebcc96118cf78e5e1fc0`.

Using one workstream controls contract drift but is not independent authorship.
The conventional implementation therefore requires review by a C# developer
who did not author Cohesive.Relations and has no direct stake in the comparison.

### Independent review gate

- [ ] Reviewer name and relevant C# experience recorded.
- [ ] Relationship to Cohesive and conflicts of interest recorded.
- [ ] Conventional implementation judged idiomatic without reference to the
  Cohesive implementation.
- [ ] Visible guidance and task distance compared across conditions.
- [ ] Requested changes, disposition, and final sign-off recorded.

### Provisional maintainer self-review

Date: 2026-08-27

Reviewer: Leo Gorodinski

Leo has approximately 20 years of C#/.NET experience and regularly evaluates
C# code for idiomatic design, API clarity, nullability, collection handling,
and test quality.

Leo is the creator of Cohesive, including Cohesive.Relations, directed the
evaluation baseline work, and hopes Cohesive proves useful. He therefore has a
direct stake in the experiment. He believes that usefulness should be
established through appropriately designed experimentation and is motivated to
identify bias or methodological weaknesses rather than optimize for a favorable
result.

Review findings:

- The conventional implementation is idiomatic C#. A LINQ join would be a
  reasonable alternative, but the dictionary-based implementation is also
  appropriate.
- Nothing in the implementation appears unnecessarily awkward or contrived.
- The visible README provides sufficient guidance.
- Making Equipment optional is a natural, simple, and appropriately bounded C#
  maintenance task. An ordinary production task would often be broader, but
  this scope is suitable for a controlled experiment. Adding a new optional
  field and similar relationship-evolution changes would be useful related
  tasks in a broader suite.
- No changes are requested at this time.
- Provisional maintainer sign-off: approved.

This self-review is useful design feedback but does **not** satisfy the
independent review gate above. Leo authored and has a direct stake in the work,
so every independent-gate checkbox remains open pending an eligible reviewer.

## Task-selection disclosure

The task was chosen by Cohesive maintainers from Cohesive.Relations' home domain:
changing a required relationship to optional. That choice plausibly favors the
Cohesive condition and is a researcher degree of freedom, not a neutral sample
of software maintenance. The v0.1 pilot is a harness-validation exercise and
contains no negative-control task. Any later efficacy study must preregister at
least one task where the representation is expected to be neutral or unhelpful.

## Package-documentation audit

The original v0 package
`Cohesive.Relations.0.1.0-eval.coh56.8cf0242.nupkg` failed the no-task-hint gate.
Its `docs/GETTING_STARTED.md` used the same Load/Customer/Equipment domain and
demonstrated this exact change:

```csharp
requirement: QueryInputRequirement.Optional
```

That guide was reachable by unpacking the vendored package and gave the
Cohesive condition a representation-specific solution hint. The v0.1 candidate
package is rebuilt from the same pinned source revision with:

- the task-specific `docs/GETTING_STARTED.md` omitted;
- the now-invalid README link to that guide removed;
- general library README, execution, capability, diagnostic, migration, and XML
  API documentation retained; and
- a neutral package version that carries no evaluation or issue identifier.

The retained XML API documentation necessarily exposes the public
`QueryInputRequirement.Optional` enum and its general meaning. That is ordinary
API reference needed to mitigate library unfamiliarity; it does not demonstrate
the task's domain or the change sequence.

### Package audit gate

- [x] Original package contents inspected for optional-relationship examples.
- [x] Task-specific optionality guide identified and excluded from the v0.1
  candidate package.
- [x] Remaining Markdown package documentation searched for
  `QueryInputRequirement.Optional`; no occurrence remains.
- [x] Candidate package hashes and dependency locks recorded after the condition
  workspace is updated and verified.
- [x] Final condition snapshot audited for evaluation framing, future-task hints,
  parent-repository files, and Git history before v0.1 is tagged.
