# Pinned API capability audit

Source inspected: `b0c442ab5645907968d6b605edeb1dd54550130d`, matching the package
closure qualified by eval PR #44. This is a **source audit**, not execution of the
new AO1 witnesses. Existing qualification demonstrates the current endpoints, not
all hypothetical malformed bindings. No newer SDK behavior is assumed.

All links below are pinned to that revision.

| Capability | Evidence | Consequence for AO1 |
| --- | --- | --- |
| Typed entity/result binding | [TypedEntityApiBindings](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/adapters/Cohesive.Adapters.AspNet/Entities/TypedEntityApiBindings.cs), `Validate` and `Complete<TResponse>` check entity, operation kind, body/result contracts, required handlers and compilation diagnostics. | Wrong contracts have a registration-check path; arbitrary callback behavior still needs HTTP verification. |
| Exact transition identity | [TransitionEntityApiOperationBinding.CreateHandler](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/adapters/Cohesive.Adapters.AspNet/Entities/TransitionEntityApiOperationBinding.cs) compares canonical transition reference/revision. | Include a separately classified registration-negative fixture with its exact diagnostic. |
| Exhaustive classified rejections | [TransitionRejectionResponses](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/adapters/Cohesive.Adapters.AspNet/Entities/TransitionRejectionResponses.cs) checks every enum member, duplicates/undefined members and wire names. [SDK tests](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/Cohesive.Tests/Api/TypedEntityApiBindingsTests.cs) include missing classification. | This overload emits Problem Details. It does not supply exhaustive custom ErrorResponse bodies. Keep it as capability evidence, not an automatic benefit for the pilot's existing simple callback. |
| Route/body extraction | [EntityApiRequestSupport](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/adapters/Cohesive.Adapters.AspNet/Entities/EntityApiRequestSupport.cs) resolves route IDs and delegates declared body binding; typed Input callbacks construct domain inputs. | A well-typed callback can still select the wrong ID/quantity. Use sentinel/wire witnesses rather than assuming semantic intent is statically checked. |
| Process enum representation | [ProcessComputationSourceGenerator](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/Cohesive.Analyzers/ProcessComputationSourceGenerator.cs), `TryEmitConstant`, emits an enum member's declared name; enum switches without defaults require declared-case coverage. | Reproduce the CLR-name/JSON-alias drift at runtime; distinguish exhaustive switch diagnostics from correct wire representation. Do not claim the earlier E2 witness already qualifies this newer package. |
| Portable contract comparison | [ApiContractDocument](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/Cohesive.Api/ApiContractDocument.cs) and [ApiContractCompatibility](https://github.com/cohesivesystems/cohesive/blob/b0c442ab5645907968d6b605edeb1dd54550130d/src/Cohesive.Api/ApiContractCompatibility.cs) implement directional `http-json-tolerant-readers/v2` checks with Breaking/Unknown/Compatible verdicts. | This capability exists. Generic string outcome codes, ordinary C# routes and callback behavior limit what an exported declaration proves. Runtime parity remains independent; full surface migration is #34. |

The immediate ergonomic question is exhaustive rejection classification with the
existing custom response format. Also record repeated declaration/transition
references and input-binding boilerplate. Do not add a fixture-local copy of SDK
semantics or change public wire behavior to make the framework appear stronger.
A concrete runtime witness should precede any new SDK refinement issue.

Fixture coverage: order submit/cancel and inventory limit/quarantine commands use
Cohesive entity API bindings. Fulfillment admission, batch handling and ordinary
read routes remain host-authored C#. Do not credit declarations for behavior on
those routes unless the implementation actually migrates and separately qualifies
them. No whole-surface migration is part of AO1.
