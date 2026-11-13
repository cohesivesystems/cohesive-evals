# Pinned SDK audit

Reviewed source revision `b0af008d85871ad8866d7d4311707ecd926529de`, matching
vendored package version `0.1.0-eval.b0af008`. No SDK/package changes in PV1.

| Capability | Source evidence at the pinned revision | PV1 use |
|---|---|---|
| Portable shape/type checking | [`ObservationValidator.TryValidateAgainstType` / `TryValidateAgainstShape`](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive/Model/ObservationValidator.cs) validate portable observations. The type-only overload explicitly leaves field presence/nullability to its caller. | Available, but not automatically applied to this application's `FulfillmentRequest` DTO. |
| Value contracts | [`ValueContract`](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/Cohesive/Model/ValueContract.cs) declares type, shape, cardinality, presence and nullability. | No request-ID length constraint is declared by this fixture; PV2 must not assume one is generated. |
| HTTP process input | [`ProcessApiRequestSupport`](https://github.com/cohesivesystems/cohesive/blob/b0af008d85871ad8866d7d4311707ecd926529de/src/adapters/Cohesive.Adapters.AspNet/Processes/ProcessApiRequestSupport.cs) delegates binding through an HTTP context/API operation. | The existing fulfillment route manually admits a DTO to `OperationQueue`; this helper is not a file adapter. |
| State-dependent validation | The fixture's G3 `Requires` transitions enforce quantity, quarantine, stock and lifecycle guards; its compiled process composes the transitions. | Both transports enter the same backend/process. Conventional enters the same domain services. |

PV1 uses one handwritten `FulfillmentInput` decoder/validator and the same queue
implementation in both conditions. Portable shape/type validation is a real SDK
capability, but this fixture does not demonstrate generated input-rule portability.
No unsupported-feature or future Assurance claim is inferred from source search.
A future use of model-authored input constraints needs a separately reviewed,
pinned implementation and independent boundary checks.

The new HTTP parser also closes a preexisting gap between published schemas and
framework-default DTO binding: integral decimal/exponent encodings now work;
numeric strings, wrong-case required names and duplicate fields are rejected.
These decisions are explicit in the reviewed probe contract and tested through
both transports. Original G0–G3 snapshots and their evidence are preserved.

The unrelated rejection-handler requirement remains tracked in
[Cohesive #513](https://github.com/cohesivesystems/cohesive/issues/513).
