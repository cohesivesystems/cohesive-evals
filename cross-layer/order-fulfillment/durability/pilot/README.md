# G0 durability pilot

The conventional implementation came from one fresh authoring session. The Cohesive implementation is a maintainer-guided replacement using the pinned SDK's native accepted-process API. Both start from the G0 trees recorded in [#55](https://github.com/cohesivesystems/cohesive-evals/issues/55). The [task](task.md) and [authoring budget](pins.json) describe the original sessions. The guided replacement has no authoring-time measurement.

| Qualified behavior | Conventional | Guided Cohesive |
|---|---:|---:|
| Recovery scenarios | 10/10 | 10/10 |
| Retained HTTP checks | 52/52 | 52/52 |
| Invariant sequences, 60 commands each | 3/3 | 3/3 |
| 1,000 retained identities, overflow, replay and conflict before and after restart | Passed | Passed |

## Implementation

The [conventional submission](conventional/submission.patch) moves fulfillment decisions into a Durable Task orchestrator with five activities. Its application queue persists admission, dispatches pending work, and records completion. The store reuses transactional effect receipts.

The [Cohesive binding](cohesive/overlay/src/Fulfillment.Application/AcceptedFulfillment.cs) pairs `ReturnAfterDurableAdmission()` with `ReadResultOf(process)`. The native dispatcher owns replay, conflict detection and scheduling. The Durable Task execution repository serves the retained result. The existing fulfillment process runs unchanged. PostgreSQL transition receipts protect its effects. The service declaration links submit and poll to the same process and declares a separate authorization requirement for each. The HTTP declaration specifies the public receipt and error bodies, a bodyless 503 at capacity, and bodyless 202 and 404 polling responses. The SDK uses those mappings for routing and OpenAPI.

The [published SDK](https://github.com/cohesivesystems/cohesive/releases/tag/eval-sdk-b6d6874d) meters admission through `maximumRetainedInstances: 1000` on the worker catalog. The admission orchestrator resolves replay and conflict before checking capacity. It locks the quota for the authority, tenant and process definition, then commits quota consumption and the scheduling action in one durable entity turn. The first admission pins the worker policy in a durable entity. Every start checks it, including starts on workers configured for unlimited retention. Completed identities still occupy a slot because they remain replayable. The app supplies its request ID through `AcceptedProcessIntent.FromRequestId`. The SDK derives stable retry identities. The app explicitly maps canonical and engine failures to the same execution error. Missing result evidence has the same error body type with a distinct `ResultUnavailable` code. Capacity exhaustion and a mismatched worker policy each produce an empty 503. PostgreSQL continues to store the order data and effect receipts.

The production app registers the SDK's worker authority projector for the fixture identity. All deliberate failures and crash barriers live in a [separate test host](cohesive/overlay/tests/Fulfillment.TestHost). Its transition decorator pauses after a committed reserve, submit, reservation or release. Its scheduler interceptor observes the worker RPC that commits the native quota entity's increment-and-schedule action, on either side of acknowledgement. The test host holds the HTTP response for the post-commit crash. Because native admission schedules the process in the same action, the acknowledged `before-dispatch` scenario stops before dispatch of the first business activity. The result barrier stops the process worker before its terminal completion reaches the scheduler.

The recovery grader launches that test host. Capacity and G0 launch the ordinary app. Both use the same application assembly, pinned durable scheduler emulator, and PostgreSQL. [Conventional evidence](conventional/evidence) · [Guided Cohesive evidence](cohesive/evidence) · [Known-good controls](control.json)

## Unmetered admission latency

This local emulator check measured POST-to-202 latency before worker-policy pinning (SDK `141ffd18`) and after it (`b27c9a08`). Both builds used unlimited retention. Each cell gives the median and p95 in milliseconds across 200 distinct submissions to one scope.

| Concurrent clients | Before, median / p95 | After, median / p95 |
|---:|---:|---:|
| 1 | 16.1 / 23.6 | 17.8 / 23.6 |
| 8 | 50.5 / 131.7 | 54.8 / 136.8 |

For reproduction, materialize eval commits `0eb6c36` and `517f064` respectively, omit `maximumRetainedInstances: 1000` from each worker catalog and build both apps in Debug. From the repo root run `PYTHONPATH=. python3 cross-layer/order-fulfillment/durability/pilot/admission_latency.py BEFORE_DLL AFTER_DLL FRESH_DIR`. For each concurrency level the script runs before/after/after/before, with a fresh database and scheduler per trial and 16 warm-up submissions. The figures include HTTP, scheduling and concurrent fulfillment work. [Raw samples](cohesive/evidence/unmetered-latency.json)

## Reproduce

1. Copy the corresponding G0 condition at the commit in [pins.json](pins.json). For Cohesive, copy the three packages from `durability/packages` into its `packages` directory. Add the pilot's `task.md` as `TASK.md`. Initialize a separate Git repository and stage the starting files including packages. Check the starting Git tree against the pin.
2. Apply the conventional submission patch to its starting tree. For Cohesive, apply [baseline.patch](cohesive/baseline.patch) with `git apply`, remove the materialized starting tree’s `packages` directory, then copy the contents of [overlay](cohesive/overlay) into its root. Stage the result and compare `git write-tree` with [implementation.json](cohesive/implementation.json).
3. Run `durability/build.py::build_candidate` for each materialized condition. It performs a locked restore, builds the solution, and fingerprints the sources and executable outputs. The Cohesive manifest covers both entry points. [Guided SDK pin](cohesive/implementation.json) · [Starting SDK and scheduler pins](../dependency-manifest.json)
4. From the case directory run `python3 durability/verify.py --condition cohesive --references CANDIDATE_PARENT --test-host --point POINT --output FRESH_DIR` once per point in the verifier. For conventional, use `--condition conventional` and omit `--test-host`. Each run starts an isolated database and task hub.
5. From the repo root run `PYTHONPATH=. python3 cross-layer/order-fulfillment/durability/pilot/capacity.py APP_DLL FRESH_OUTPUT CONDITION` against the production DLL. For G0 run `verification/verify.py --condition CONDITION --fixtures CANDIDATE_PARENT --output FRESH_DIR` from the case directory with a fresh scheduler connection in `DURABLE_TASK_CONNECTION`.
