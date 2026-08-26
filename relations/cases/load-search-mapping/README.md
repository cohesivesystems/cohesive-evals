# Load Search Mapping

Load Search Mapping is the first evaluation case for the Cohesive.Relations
pilot. It is intentionally small enough for manual review while exercising a
relationship change, missing related data, output cardinality, nullability, and
preservation of downstream behavior.

This document specifies observable semantics. It does not prescribe the internal
design of either condition or reveal future hidden fixtures and checks.

## Application boundary

Both future condition repositories must expose the same neutral application
boundary and equivalent contracts. The conceptual input is:

```text
Load
  Id
  CustomerId   -> Customer.Id
  EquipmentId  -> Equipment.Id

Customer
  Id
  Name

Equipment
  Id
  Number
```

The Load Search operation projects the domain data into:

```text
LoadSearchResult
  LoadId
  CustomerName
  EquipmentNumber
```

The concrete C# namespace, assembly, and public adapter will be fixed when the
matched baselines are implemented and must be identical across conditions so a
shared oracle can exercise both without representation-specific branches.

The case includes a customer-only downstream consumer of search results. Its
output depends on `LoadId` and `CustomerName`, not Equipment. Both implementations
must expose the same consumer and observable output so collateral damage can be
detected.

## Starting behavior

At baseline:

- `Load.Id`, `Customer.Id`, and `Equipment.Id` are unique within an input.
- Customer and Equipment relationships are required.
- A valid Load produces exactly one result with the same Load identity.
- Results preserve Load input order.
- Customer name and Equipment number are copied from their related entities.
- An absent or dangling required Customer relationship rejects the operation
  with the case's stable missing-required-relation outcome.
- An absent or dangling required Equipment relationship rejects the operation
  with the equivalent outcome.
- The customer-only downstream consumer preserves Load identity, order, and
  Customer name.

The exact diagnostic prose may differ between conditions. The success/failure
classification, relationship named by a failure, result values, identity,
cardinality, and order may not differ.

Before admission to the pilot, a shared maintainer suite will run identical
complete, absent-relation, and dangling-relation inputs against both baselines.
Normalized observable results must match. The baselines must also pass manual
review for idiomatic implementation and comparable visible guidance.

## Task: Make Equipment Optional

The agent will receive the following frozen change request in both conditions:

> Equipment is now optional. Loads without Equipment must remain in Load Search
> results, with Equipment fields absent. Existing Loads with Equipment, required
> Customer behavior, result identity and ordering, and unrelated consumers must
> remain unchanged. Update the authoritative implementation and its public
> contracts as needed, and keep the repository building and its visible tests
> passing.

For this task, “without Equipment” means `Load.EquipmentId` is absent. After the
change, `EquipmentNumber` is represented as null/absence, never as an empty or
invented sentinel value. A non-null `EquipmentId` with no matching Equipment is
still a dangling reference and retains its existing validation failure. Making
Equipment optional does not make Customer optional.

Each run starts from a clean copy of the original required-Equipment baseline.
The task is not applied cumulatively across repetitions.

## Public obligations

These obligations define correctness without disclosing future oracle inputs or
test implementation. Stable IDs must be preserved when the oracle is added.

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

The later oracle may use multiple checks for one obligation and one check may
support multiple obligations. An obligation passes only when all of its assigned
checks pass. Hidden checks may vary data size, ordering, and combinations, but
may not introduce behavior beyond this document.

## Treatment integrity

Treatment integrity is reported separately from the public obligations:

- The conventional result must remain free of a Cohesive dependency and must not
  delegate its authoritative behavior to Cohesive.Relations.
- The Cohesive result must express Equipment optionality in the canonical
  relation and execute the public application behavior through that relation.
  A parallel handwritten mapper that bypasses it fails treatment integrity even
  if its output happens to satisfy the behavioral checks.

These checks provide no additional correctness credit. They establish whether a
run is evidence about the condition it was assigned.

## Planned condition layout

```text
conditions/
├── conventional/   # idiomatic C# baseline; implemented in a later issue
└── cohesive/       # matched Cohesive.Relations baseline; implemented later
```

The matched repositories, public adapter, visible tests, dependency versions,
and baseline-equivalence suite are intentionally not implemented by this issue.
The private oracle, runner, and results also live outside the condition folders
and must never be copied into an agent workspace.

## Out of scope for this case version

- Split Customer name or relationship-key changes.
- Sequential or long-lived repository evolution.
- Generated populations or Cohesive.Simulation integration.
- Semantic query tools or agent-tooling ablations.
- Runtime performance comparisons.
- Subjective architecture scoring.
- Any claim that Cohesive is more effective.
