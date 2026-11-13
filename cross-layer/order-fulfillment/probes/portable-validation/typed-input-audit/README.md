# Typed input constraint audit

Audit for [#42](https://github.com/cohesivesystems/cohesive-evals/issues/42),
2026-11-13. **The SDK can describe the rule, but the pinned validator does not
execute it. An SDK change is needed before replacing PV2's predicate with declared
length-constraint enforcement.** Tracked in
[Cohesive #529](https://github.com/cohesivesystems/cohesive/issues/529).

## Evidence

Runtime tested package `0.1.0-eval.b0af008` (source `b0af008d85871ad8866d7d4311707ecd926529de`).
Also inspected committed SDK main `4d6d588357d701035c8a86715250dd897b00974d`;
this is a source comparison, not a runtime qualification of newer packages.
Uncommitted SDK work is outside the audit.

| Capability | Finding |
|---|---|
| Declare a length constraint | `FieldDefinition.Constraints` and `Shape.Constraints` accept `MaxLengthConstraint(64)`. |
| Attach metadata to CLR inputs | `ClrShapeGraphBuilder.AddMetadataProvider` accepts `ClrShapeMetadata.Constraints`. Default attribute projection does **not** import `[MaxLength]`. |
| Enforce shape/type structure | Required fields, nullability and scalar types are checked. |
| Enforce declared length | Both dictionary-backed and object-backed `TryValidateAgainstShape` accept 65-unit strings despite the constraint. Shape-targeted constraints also do not reject them. |
| Preserve the rule in a value contract | `ValueContract.FromField` copies type/cardinality/presence/nullability, not `FieldDefinition.Constraints`; its constant check accepts the long string. |
| Infer length semantics | No executable string-length semantics are established by this metadata. UTF-16 units must be specified explicitly for PV2. |

The [executable witness](Program.cs) declares the existing API directly:

```csharp
var field = new FieldDefinition(
    new("RequestId"), new ScalarTypeRef(ScalarTypeKind.String),
    constraints: [new MaxLengthConstraint(64)]);
```

[observed.json](observed.json) records acceptance of ASCII lengths 64/65 and
32 emoji / 32 emoji plus ASCII. The 65-unit cases should fail PV2, but all four
pass the SDK checks. Three missing/null/type controls reject as expected.
This is a characterization of a gap, not application qualification.

Reproduce from this directory with the existing vendored package and locked dependencies:

```sh
dotnet restore --locked-mode
dotnet run --no-restore --project ConstraintAudit.csproj
```

## Integration decision

Keep ordinary ASP.NET DTO/array binding. Declare the constraint once on the
**admission input** (`FulfillmentRequest`), then invoke the SDK's supported input
validation from the common `OperationQueue.Submit` path **before identity lookup,
capacity checks and insertion**. Both single-item and batch operations already use
that path. Map an input violation to the existing 400 outcome; retain valid siblings,
shared receipts and host-owned execution.

The current workflow input, `FulfillOrder`, contains order ID, SKU and quantity;
it does not contain request ID. A process `Requires` check would run after queue
admission and turn an input failure into a retained workflow outcome. It therefore
cannot substitute for this admission rule.

After #529, pin the SDK upgrade in a separate reference stage, keep the conventional
shared validator idiomatic, and run the unchanged independent PV2/PV1/G0–G3 suites.
Add a witness that removes or changes the declaration and proves admission changes,
so a leftover handwritten length check cannot masquerade as model enforcement.
Keep the existing nonblank checks unless their exact semantics are also covered;
`RequiredConstraint` metadata alone is not proof of whitespace rejection.

No application or pinned package changed in this audit. The next step is SDK
constraint enforcement and admission integration, not another handwritten adapter
that reimplements the same length predicate. Newer typed expression inputs and
Assurance claims do not by themselves install runtime admission validation.

## Source anchors

- [Constraint definitions](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive/Model/ShapeConstraints.cs), [field metadata](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive/Model/FieldDefinition.cs).
- [Observation validation](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive/Model/ObservationValidator.cs): `TryValidateFieldValue` checks type/nullability/cardinality, not constraints.
- [Value contracts](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive/Model/ValueContract.cs): `FromField` and `FromShape` project structural contracts.
- [CLR shape projection](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive/Model/ClrShapeGraphBuilder.cs), [default attributes](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive/Model/ClrShapeAttributeMetadataProvider.cs).
- [Portable definition validation](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive/Execution/PortableExecutionValidator.cs): `ValidateConstraint` checks declaration well-formedness, not incoming string length.
- [Current typed expression inputs](https://github.com/cohesivesystems/cohesive/blob/4d6d588357d701035c8a86715250dd897b00974d/src/Cohesive/Authoring/ExpressionAuthoring.cs) retain authoring bindings; they do not execute input validation.

[evidence.json](evidence.json) records exact inspected revisions and source/package/witness hashes.
