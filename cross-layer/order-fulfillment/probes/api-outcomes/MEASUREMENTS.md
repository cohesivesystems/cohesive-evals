# AO1 measurements

Retrospective description of the qualified implementation at `7db195a`, using
[pinned evidence](evidence.json). [Machine-readable counts](measurements.json)
are reproduced by `python3 -B cross-layer/order-fulfillment/probes/api-outcomes/measure.py --check`.
No application or runtime expectations changed for this report.

## Change footprint

| Changed artifact | Conventional | Cohesive |
| --- | ---: | ---: |
| Application C# files | 5 | 3 |
| Application lines added / removed | +12 / −5 | +13 / −6 |
| Public/seed schema files | 2 | 2 |
| Schema lines added / removed | +10 / −5 | +10 / −5 |
| Contract documentation files | 1 | 1 |
| Contract documentation lines added / removed | +9 / −0 | +9 / −0 |

Counts come from the reference patches, excluding harnesses, evidence and this
report. Lines include comments, formatting and revision metadata; replacements
count as both additions and removals. Files are organizational boundaries, not
units of difficulty. Fewer files here does not mean less code or less effort.

Manual semantic audit (reviewable in the [patches](reference)):

| Application edit category | Conventional | Cohesive |
| --- | --- | --- |
| New archived-submission domain rule | 1 switch arm | 1 transition guard |
| Outcome projection sites | 2: direct HTTP and fulfillment map | 2: direct HTTP and the guard's typed fulfillment result |
| New enum members | 2 | 3 |
| Status-membership declarations updated, excluding public schemas | 3: enum, seed validator, SQL CHECK | 2: enum, seed validator; SQL derived |
| Explicit revision stamps updated | 0 | 3 |
| Orchestration body edits | 0 | 0 |

A projection site translates a domain decision into a public or terminal outcome;
it is not automatically a duplicated business rule. Both conditions author the
new rejection rule once and its outcome representation in two places. Cohesive
co-locates the terminal projection with the transition; conventional uses its
existing typed map. The observed difference is locality and derived schema,
not elimination of all repeated outcome knowledge. These manual counts are
coding judgments, not automatically inferred metrics.

## Paired detection matrix

The 14 shared behavioral cases below target the same named assertion in both
conditions. Each built and started successfully, then failed the independent
verifier. This is the **observed enforced detection stage**, not a claim that no
compiler warning or other unused tool could offer earlier feedback.

| Paired conceptual fault (recorded case) | Conventional | Cohesive |
| --- | --- | --- |
| Missing archived guard (`missing-archived-guard`) | Verifier | Verifier |
| Stale direct error (`stale-direct-code`) | Verifier | Verifier |
| Existing outcome changed (`existing-outcome-drift`) | Verifier | Verifier |
| Stale fulfillment outcome (`stale-terminal-code`) | Verifier | Verifier |
| Omitted compensation (`skip-release`) | Verifier | Verifier |
| Excess compensation (`double-release`) | Verifier | Verifier |
| Reservation after rejection (`reservation-on-rejection`) | Verifier | Verifier |
| Incorrect precedence (`archived-before-inventory`) | Verifier | Verifier |
| Wrong entity ID (`wrong-entity-id`) | Verifier | Verifier |
| Constant input (`constant-input`) | Verifier | Verifier |
| Forgotten replay (`replay-evicted`) | Verifier | Verifier |
| Conflicting intent replayed (`conflicting-intent-replayed`) | Verifier | Verifier |
| Batch stops after rejection (`batch-stops-at-rejection`) | Verifier | Verifier |
| Read erases status (`read-status-erased`) | Verifier | Verifier |
| Incompatible input type (`wrong-input-type`, separate static suite) | Compile: CS1503 | Compile: CS0029 |

This pairs conceptual mistakes, not identical source edits: wrong-ID faults use
a conventional callback versus Cohesive route middleware; wrong input types use
an invalid scalar argument versus an incompatible typed input object. No new
randomized or prospectively matched experiment was run to construct this matrix.

Unpaired results stay outside the comparison: conventional has one additional
behavioral HTTP-category defect and one identity-type compiler fixture. Cohesive
has three registration fixtures (wrong transition reference, response contract,
missing input). The conventional reference has no separate declaration contract
to mismatch; that is **not tested/not applicable**, not a failed detection.
No combined early-detection percentage is justified by these unequal sets.

## Diagnostic information and limits

A descriptive rubric records location, cause specificity, and explicit repair
instruction separately; no weighted score or repair-speed inference is used.
Compiler type errors identify a source location and incompatible types. All three
registration failures have application locations in their stack traces. The
transition message identifies a reference mismatch; the response-contract message
lists several possible causes; the missing-input message explicitly says to
configure Input. Exact messages and stacks remain in the evidence archive.

Both correct references pass the tested obligations. The shared fault set is
caught 14/14 in each; the full deliberately selected sets are 15/15 and 14/14.
These are finite fixture results, not estimated real-world defect detection rates.
The separate alias witness identifies a Cohesive SDK limitation, not a win for
its correct reference or an extra member of this paired fault set.

Development time, repair time, repair iterations and repair-induced regressions
are **unmeasured**, represented as null in the data. Controlled trials should
preselect the same task/fault families and feedback access; record active elapsed
time to a passing independent suite, edit/test iterations, final application diff,
and new retained-suite failures. Record infrastructure interruptions separately
and keep unsuccessful/censored attempts. Report each outcome separately before
considering any aggregate. Maintainer terminal history cannot substitute for
those measurements.
