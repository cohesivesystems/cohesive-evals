# Load Search Mapping oracle obligations

Status: design gate approved under COH-58 on 2026-08-26. The implementation was
subsequently simplified to keep task-specific machinery proportional to this
small change. The oracle remains a candidate—not frozen—until the independent
baseline review in COH-59 is complete.

The v0 starting repositories remain preserved by tag
`relations-load-search-v0-baseline` at commit `fdc65f8`. Package sanitization and
contract clarification require a new v0.1 baseline revision before calibration.

## Public obligations

These statements are copied unchanged from the
[case specification](../../cases/load-search-mapping/README.md).

| ID | Observable obligation |
|---|---|
| `REL-EVAL-001` | A Load with matching Customer and Equipment retains its existing mapped result. |
| `REL-EVAL-002` | A Load whose `EquipmentId` is absent remains in the result set. |
| `REL-EVAL-003` | An unequipped Load has an absent/null `EquipmentNumber`, not an empty or invented value. |
| `REL-EVAL-004` | Mixed equipped and unequipped Loads produce one result per input Load with identity and input order preserved. |
| `REL-EVAL-005` | Customer remains required; an absent or dangling Customer relationship retains the baseline failure. |
| `REL-EVAL-006` | A non-null but dangling Equipment reference retains the baseline failure rather than being treated as absence. |
| `REL-EVAL-007` | Load identity and Customer fields are unchanged for all successful results. |
| `REL-EVAL-008` | The customer-only downstream consumer retains its baseline identity, order, and Customer output. |

## Behavioral checks

Six black-box scenarios exercise the same public application boundary in both
conditions. Combining assertions that naturally belong to one input avoids a
mutation matrix larger than the task itself.

| Check | Scenario | Obligations |
|---|---|---|
| `LSM-BHV-001` | One fully related Load retains its identity, Customer name, and Equipment number. | `REL-EVAL-001` |
| `LSM-BHV-002` | One unequipped Load occurs once with unchanged identity and Customer name and a null Equipment number. | `REL-EVAL-002`, `REL-EVAL-003` |
| `LSM-BHV-003` | Interleaved equipped and unequipped Loads retain cardinality, input order, identity, Customer names, and Equipment values. | `REL-EVAL-004`, `REL-EVAL-007` |
| `LSM-BHV-004` | Both absent and dangling Customer references retain the structured required-relationship failure. | `REL-EVAL-005` |
| `LSM-BHV-005` | A dangling non-null Equipment reference retains the structured failure. | `REL-EVAL-006` |
| `LSM-BHV-006` | The existing customer-only consumer retains identity, order, and Customer output for mixed results. | `REL-EVAL-008` |

The checks compare stable values, failure classifications, relationship names,
reference identities, cardinality, and ordering. They do not compare diagnostic
prose or condition-specific implementation details.

An obligation passes when its allocated check passes. Contract/build
compatibility and visible tests are separate completion gates. If the application
or oracle adapter cannot build against the frozen public surface, behavioral
obligations are not evaluated and the submission is a valid incomplete outcome.

## Treatment integrity

Treatment integrity is reported separately and awards no behavioral credit.

- `LSM-TI-CONV-001` rejects a Cohesive package, project, or compiled assembly
  reference in the conventional application.
- `LSM-TI-COH-001` requires a compiled relation plan that declares
  `Load.Customer` required and `Load.Equipment` optional.

Together with the black-box behavior, these checks provide proportional evidence
that the assigned representation was changed correctly. This v0 oracle is not a
security boundary: it does not include a bespoke IL analyzer to prove the absence
of deliberately hidden dead code or every possible parallel implementation. A
manual review finding that the service bypasses a compliant plan still fails the
case's treatment-integrity rule.

## Qualification

Qualification is a smoke test of the oracle and gate plumbing, not an attempt to
enumerate every incorrect program. Ten reconstructed submissions cover:

- each untouched baseline and each condition's known-correct solution;
- one deliberately broad behavioral regression per condition that makes every
  behavioral check fail without requiring a separate mutation for each check;
- one incompatible public-contract change;
- one visible-test-only failure;
- a conventional solution with a Cohesive dependency; and
- a behaviorally correct Cohesive bypass whose canonical plan remains required.

The compact manifest and observed results live in
[`qualification`](qualification). Known-correct and deliberately bad changes are
stored as eight standard Git patches. The runner records patch hashes and compares
the failed-check and failed-obligation summaries with expectations declared next
to each case.

## Explicit exclusions

The v0.1 oracle does not score:

- exact diagnostic prose, exception stack traces, or condition-specific
  provenance;
- JSON wire formatting beyond the shared in-process application contract;
- empty or whitespace `EquipmentId` as an alternate spelling of absence;
- duplicate Load, Customer, or Equipment identities;
- failure precedence when Customer and Equipment are invalid simultaneously;
- source formatting, filenames, patch size, subjective architecture quality, or
  runtime performance; or
- behavior outside the frozen task and case specification.

Any addition requires an explicit case or protocol revision before pilot runs.

The executable implementation is in [`src/LoadSearch.Oracle`](src/LoadSearch.Oracle).
