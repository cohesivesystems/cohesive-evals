# MV1 test matrix

The rows below preserve the protocol obligations. The [implementation report](implementation.md)
records executed coverage and limitations; fault families here are examples, not a claim
that every listed fault was planted. The [audit](audit/run.py) separately establishes SDK capabilities.

| ID | Obligation | Independent observation | Planned fault family |
| --- | --- | --- | --- |
| MV1-01 | Same production authority | Exact source hashes; Cohesive transition reference and definition; no rewritten rule body | Stale/copied model or wrong transition revision |
| MV1-02 | Positive quantity and boundaries | Zero/negative rejection; valid positive and Int32 endpoints | Missing/shifted quantity guard, overflow/narrowing |
| MV1-03 | Limit and stock boundaries | Below/at/above each threshold; check effects and exact outcome | Strict/inclusive comparison drift, wrong threshold, wrong subtraction |
| MV1-04 | Overlapping rejections | Nonpositive first; original quarantine/limit/stock order; distinct revised precedence expectations | Swapped checks, stale expected outcomes, generic rejection |
| MV1-05 | Preservation and non-vacuity | Rejection changes no entity field; accepted reserve subtracts exactly quantity, preserves identity/configuration | Reject-all, mutation on rejection, omitted/double decrement |
| MV1-06 | Model-assisted case generation | Cases/coverage obligations trace to inspected constructs; independent policy assertions remain separate | Dropped/unsupported predicate, expectations copied from faulty model |
| MV1-07 | Claim/evidence integrity | Negative independent-claim control; exact subject/revision; completeness and scope retained | Vacuous success, wrong subject, stale evidence, Unknown treated as pass |
| MV1-08 | Maintenance | Before/after suite pins; new overlap case detects stale precedence; unaffected obligations remain | Generator or test cache not invalidated by policy change |
| MV1-09 | Qualification classification | Named requirement failure; known-good pass; explicit unsupported/infrastructure category | Compile/setup failure credited as detection, unrelated assertion credited |
| MV1-10 | Integration boundary | Retained external HTTP/physical-state verifier remains independent | Offline success masks adapter/persistence/outcome-mapping defect |

Use equivalent conceptual defects in both conditions, not forced identical source
patches. Classify implementation defects, generator/assertion defects and evidence
binding defects separately. A missing production guard may also disappear from a
model-derived case catalog: the held-out requirement suite must still expose it.

Persist the actual generated inputs, assertion provenance, outcomes, post-states,
source/build/package hashes, diagnostic text and false alarms. Budget exhaustion,
unsupported operations and infrastructure failures are inconclusive, not detected
behavioral defects. Never claim an exhaustive Int32 state/input search from a
small finite grid. Shrinking may simplify a witness only if the failure rechecks.

## Implemented coverage

- MV1-01/08: source/build freeze, actual transition identity, stale-model refusal and stale-policy failures.
- MV1-02–05: matched 388-case catalogs, independent outcomes/full-state checks and ten paired production fault families. Rejection-state corruption has oracle controls only.
- MV1-06: guard-to-boundary traces, explicit unsupported-node control and regeneration from wrong/omitted guards.
- MV1-07: exact authority checks here; independent Assurance claim/finite-scope controls remain in the pinned audit. No new general Assurance proof.
- MV1-09: named-assertion credit, known-good reruns and build/runtime/timeout/malformed-result controls. Initial unqualified runs remain recorded.
- MV1-10: unchanged original integration suites plus versioned single/batch/replay/physical-state witnesses.

This is public, feedback-exposed maintainer qualification. Sealed participant cases and
a blinded trial have not been performed.
