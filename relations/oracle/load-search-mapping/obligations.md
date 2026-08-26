# Load Search Mapping oracle obligations

Status: design gate approved under COH-58 on 2026-08-26. The executable oracle
and qualification package implement this allocation and match all expected
vectors. The oracle remains a candidate—not frozen—until the independent
baseline review in COH-59 is complete.

The v0 starting repositories remain preserved by tag
`relations-load-search-v0-baseline` at commit `fdc65f8`. Package sanitization and
contract clarification require a new v0.1 baseline revision before calibration.
This document allocates checks to the public obligations in the
[case specification](../../cases/load-search-mapping/README.md) under the
proposed [v0.1 protocol](../../protocol.md).

## Review boundary

The reviewer is approving four things:

1. the unchanged public obligation wording;
2. the observable behavior each hidden check may inspect;
3. the check-to-obligation allocation used for scoring; and
4. the condition-specific treatment-integrity evidence.

The fixture literals, test implementation, known-correct patches, and seeded-bad
patches remain private maintainer material. After this gate, implementation may
vary only fixture values, collection sizes, ordering, and combinations within
the approved behavior.

## Public obligations

These IDs and statements are copied unchanged from the case.

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

## Proposed behavioral checks

Behavioral checks use the same black-box application boundary in both
conditions. They compare stable values, failure classifications, relationship
names, reference identities, cardinality, and ordering. They do not compare
condition-specific diagnostics or implementation details.

| Check ID | Approved observation | Fixture shape |
|---|---|---|
| `LSM-BHV-001` | A fully related Load succeeds with exactly its baseline `LoadId`, `CustomerName`, and `EquipmentNumber`. | One equipped Load with matching Customer and Equipment. |
| `LSM-BHV-002` | A Load with a null `EquipmentId` succeeds and its `LoadId` occurs exactly once in the results. | One unequipped Load with a matching Customer. |
| `LSM-BHV-003` | The result for a Load with a null `EquipmentId` has a null `EquipmentNumber`; empty strings and invented sentinels fail. | One unequipped Load with a matching Customer. |
| `LSM-BHV-004` | A mixed successful input has exactly one result per Load, no extra identities, and the same identity order as the input. | Interleaved equipped and unequipped Loads with deliberately non-sorted identities. |
| `LSM-BHV-005` | A null Customer reference produces `missing-required-relation` for `Customer`, preserves the null reference identity, and returns no partial results. | One Load with valid Equipment and an absent Customer reference. |
| `LSM-BHV-006` | A non-null Customer reference with no matching Customer produces `missing-required-relation` for `Customer`, preserves the reference identity, and returns no partial results. | One Load with valid Equipment and a dangling Customer reference. |
| `LSM-BHV-007` | A non-null Equipment reference with no matching Equipment produces `missing-required-relation` for `Equipment`, preserves the reference identity, and returns no partial results. | One Load with a matching Customer and a dangling Equipment reference. |
| `LSM-BHV-008` | Every successful result retains the source `LoadId` and the matching Customer's name, independently of Equipment presence. | A mixed successful input with multiple Customers and non-sorted Load identities. |
| `LSM-BHV-009` | Passing successful mixed search results to the customer-only consumer preserves Load identity, input order, and Customer name. | The successful output of a mixed equipped and unequipped search. |

Each check is intentionally narrow. For example, `LSM-BHV-004` ignores
Equipment field representation so an empty-sentinel defect fails
`REL-EVAL-003` without also being attributed to the cardinality obligation.

## Check allocation

An obligation passes only when every allocated check passes. A check is
allocated to one obligation unless two checks are necessary to distinguish
cases within one obligation.

| Obligation | Required checks |
|---|---|
| `REL-EVAL-001` | `LSM-BHV-001` |
| `REL-EVAL-002` | `LSM-BHV-002` |
| `REL-EVAL-003` | `LSM-BHV-003` |
| `REL-EVAL-004` | `LSM-BHV-004` |
| `REL-EVAL-005` | `LSM-BHV-005`, `LSM-BHV-006` |
| `REL-EVAL-006` | `LSM-BHV-007` |
| `REL-EVAL-007` | `LSM-BHV-008` |
| `REL-EVAL-008` | `LSM-BHV-009` |

Contract/build compatibility and the visible tests are independent completion
gates; neither is allocated to a behavioral obligation. If the application or
oracle adapter cannot build against the frozen public surface, behavioral
obligations are `not-evaluated` and the submission is a valid incomplete agent
outcome. It is not an invalid run.

## Proposed treatment-integrity checks

Treatment integrity is reported separately and awards no behavioral credit.

### Conventional condition

`LSM-TI-CONV-001` verifies the restored project graph and compiled application
assembly contain no package, project, or assembly reference whose identity is
`Cohesive` or begins with `Cohesive.`. With no Cohesive dependency, the ordinary
.NET implementation remains the authoritative condition representation.

### Cohesive.Relations condition

The Cohesive condition requires all three checks:

| Check ID | Required evidence |
|---|---|
| `LSM-TI-COH-001` | A compiled canonical relation plan contains `Load.Customer` as required and `Load.Equipment` as optional. |
| `LSM-TI-COH-002` | The call path reachable from `LoadSearchService.Execute` invokes the Cohesive.Relations interpreter and compiled DTO mapper used by that plan. |
| `LSM-TI-COH-003` | No path reachable from `LoadSearchService.Execute` separately constructs or populates `LoadSearchResult` outside canonical relation authoring and Cohesive mapping. |

The proposed implementation combines compiled-plan inspection with semantic
assembly/source inspection. It deliberately avoids requiring exact filenames,
private type names, local variable names, or diagnostic text. These checks are
the only condition-specific part of the oracle.

## Oracle qualification cases

Before the oracle can be frozen, it must be run against immutable submissions
derived from the baseline tag.

The two known-correct submissions are distinct condition-specific patches. Each
seeded behavior defect below is also authored independently in both conditions,
using suffixes `-CONV` and `-COH`; a conventional mutation is not treated as
validation of the Cohesive checker or vice versa. At least one seeded submission
must target every `REL-EVAL-*` obligation in each condition. Where one obligation
has multiple checks, each check receives targeted seeded coverage. Contract and
visible-test gate failures are likewise qualified once per condition.

| Qualification ID | Submission characteristic | Expected detection |
|---|---|---|
| `LSM-QUAL-GOOD-CONV` | Known-correct conventional change. | All gates, obligations, and conventional integrity pass. |
| `LSM-QUAL-GOOD-COH` | Known-correct canonical Cohesive.Relations change. | All gates, obligations, and Cohesive integrity pass. |
| `LSM-QUAL-CONTRACT` | Public Equipment absence is replaced by an incompatible wrapper or renamed member. | Oracle-adapter contract/build gate fails; run is valid incomplete and behavioral obligations are `not-evaluated`. |
| `LSM-QUAL-VISIBLE` | Behavior passes the hidden obligations but a visible application test fails. | Visible-test gate fails; run is valid incomplete. |
| `LSM-QUAL-BASELINE` | Unchanged required-Equipment baseline. | `REL-EVAL-002` and `REL-EVAL-003` fail in both conditions; submission is incomplete. |
| `LSM-QUAL-EQUIPPED-REGRESSION` | Existing equipped mapping is corrupted. | Equipped-regression check fails. |
| `LSM-QUAL-DROP` | Unequipped Loads are filtered out. | Retention and mixed cardinality checks fail. |
| `LSM-QUAL-SENTINEL` | Missing Equipment is represented by an empty or invented value. | Null-representation check fails. |
| `LSM-QUAL-ORDER` | Mixed results are reordered or deduplicated. | Mixed identity/cardinality/order check fails. |
| `LSM-QUAL-CUSTOMER-ABSENT` | An absent Customer is accepted. | Absent-Customer check fails. |
| `LSM-QUAL-CUSTOMER-DANGLING` | A dangling Customer is accepted. | Dangling-Customer check fails. |
| `LSM-QUAL-EQUIPMENT-DANGLING` | A dangling Equipment reference is treated as absence. | Dangling-Equipment check fails. |
| `LSM-QUAL-CUSTOMER-MAPPING` | Load identity or Customer mapping is corrupted. | Successful-result mapping check fails. |
| `LSM-QUAL-CONSUMER` | The customer-only consumer changes identity, order, or Customer output. | Downstream-consumer check fails. |
| `LSM-QUAL-CONV-DEPENDENCY` | Conventional solution delegates to Cohesive.Relations. | Conventional integrity fails even if behavior passes. |
| `LSM-QUAL-COH-BYPASS` | Cohesive solution uses a parallel handwritten result mapper. | Cohesive integrity fails even if behavior passes. |

Qualification records the complete observed check vector, not only the expected
failure named above. A seeded defect may have legitimate downstream effects,
but it must fail its targeted check and must not create false passes.

The frozen oracle release includes a machine-readable qualification manifest
mapping every obligation and treatment-integrity check to its known-correct and
seeded submission IDs, hashes, expected vector, and observed vector. Missing
per-condition coverage blocks calibration.

## Explicit exclusions

The v0.1 oracle will not score:

- exact diagnostic prose, exception stack traces, or condition-specific
  provenance;
- JSON wire formatting beyond the shared in-process application contract;
- empty or whitespace `EquipmentId` as an alternative spelling of absence;
- inputs with duplicate Load, Customer, or Equipment identities;
- failure precedence when Customer and Equipment are invalid simultaneously;
- source formatting, filenames, patch size, subjective architecture quality, or
  runtime performance; or
- behavior outside the frozen task and case specification.

These exclusions prevent hidden fixtures from silently creating new task
requirements. Any desired addition requires an explicit case/protocol revision
before pilot runs begin.

## Review decision

Approval of this document authorizes implementation and qualification of the
oracle without changing the obligations or check allocation. Requested changes
must be resolved here before executable hidden checks are authored.

The review should explicitly resolve:

- [x] the eight public obligation statements;
- [x] the nine behavioral check scopes and their allocation;
- [x] the three Cohesive treatment-integrity checks, especially the proposed
  semantic assembly/source inspection for excluding a parallel mapper;
- [x] the explicit exclusions, including empty/whitespace Equipment references
  and simultaneously invalid relationships; and
- [x] contract/adapter compilation and visible-test failures as valid incomplete
  completion-gate failures under protocol v0.1.

The accepted implementation is in [`src/LoadSearch.Oracle`](src/LoadSearch.Oracle).
Its reproducible qualification inputs, complete expected vectors, and observed
evidence are in [`qualification`](qualification).
