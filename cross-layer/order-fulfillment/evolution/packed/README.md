# Packed order lifecycle

[Issue #61](https://github.com/cohesivesystems/cohesive-evals/issues/61) extends the qualified G2 cancellation fixtures at `211a0022` with bodyless pack and unpack commands. Each condition starts from the same public behavior. The build checks each condition’s G2 input fingerprint before applying its patch.

| Behavior | Conventional · Stateless 5.21.0 | Cohesive · SDK 54e9910b |
|---|---|---|
| Pack | `Configure(Submitted).Permit(Pack, Packed)` and `Configure(Packed).Ignore(Pack)` | Declare a movement from Submitted to Packed and a named self-loop for repeat Pack. Map the machine discriminator to `Order.Status`. |
| Decide and save | `Order.Apply(command)` fires the machine. The store locks the order, applies the decision and saves a changed status in its transaction. | The transition calls `.Move(lifecycle.Pack, (_, _) => false)`. The SDK selects the enabled edge and assigns its target. The entity endpoint reads and commits through the repository. |
| Submit via fulfillment | The HTTP handler and fulfillment call `store.Apply(..., OrderCommand.Submit)`. | The HTTP binding and fulfillment process reference the same `OrderTransitions.Submit`. |
| Handle concurrent commands | PostgreSQL row locking serializes decisions. | The route filter reevaluates a bodyless command after an SDK conditional-write conflict. Domain rejections are final. |
| Offline verification | Enumerate states and triggers. Execute the production aggregate method on a fresh order for each cell. | Read the machine document from the production entity. Enumerate its states and actions and evaluate its edges. The transition compiler also rejects an applied path that updates status without declaring a movement. |

[Conventional patch](reference/conventional.patch) · [Cohesive patch](reference/cohesive.patch) · [Stateless probe](offline/conventional.cs) · [Cohesive probe](offline/cohesive.cs)

## What the checks establish

The [independent table](packing_checks.py) grades all 16 decisions offline and over HTTP. The live checks compare summaries, details, availability and scoped PostgreSQL facts. They exercise completed-request replay while Packed, compensated rejection, restart, and two pairs of concurrent commands. Either race winner is acceptable when both responses and the final state agree with one serial history.

Four defects per condition exercise draft packing, an incorrect unpack destination, loss of Packed across restart, and an inventory mutation on a repeated command. The qualifier credits only the named failure for each defect. The Cohesive offline probe also executes the production Pack transition from Submitted and Packed and checks the recorded edge IDs (`pack` and `pack-again`). The compiler coverage control separately checks that a direct assignment bypassing the machine is rejected.

The first live run exposed a storage-level 409 during concurrent pack/unpack. The submitted binding retries that failed conditional write before returning an HTTP response. The portable graph makes lifecycle decisions inspectable, but checking the graph alone would have missed this behavior. Stateless expresses idempotence more concisely with `Ignore`. This pair measures neither authoring time nor throughput.

## Reproduce

Run from the repository root with the pinned .NET SDK, Python and Docker. Each output directory must be new.

```sh
export PYTHONPATH=.
evolution=cross-layer/order-fulfillment/evolution
python3 -B "$evolution/packed/build.py" --output /tmp/packing-fixtures
python3 -B "$evolution/packed/verify_offline.py" /tmp/packing-fixtures /tmp/packing-offline.json
python3 -B "$evolution/verify.py" --generation packed --fixtures /tmp/packing-fixtures --output /tmp/packing-verification
python3 -B "$evolution/qualify.py" --generation packed --output /tmp/packing-qualification
```

The [SDK prerelease](https://github.com/cohesivesystems/cohesive/releases/tag/eval-sdk-54e9910b) supports binding a discovered entity to a discriminator machine and dispatching its typed actions. The [package manifest](sdk/dependency-manifest.json) records its source revision and SHA-256 digests.

[Offline decisions and compiler diagnostics](evidence/offline.json) · [Retained integration results](evidence/integration.json) · [Qualification by defect and assertion](evidence/qualification.json) · [Conventional HTTP/SQL trace](evidence/conventional.jsonl) · [Cohesive HTTP/SQL trace](evidence/cohesive.jsonl) · [Original concurrency failure](evidence/pre-fix-concurrency.json)
