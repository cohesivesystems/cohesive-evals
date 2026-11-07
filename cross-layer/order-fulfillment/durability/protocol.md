# Durable Order Fulfillment probe — candidate supplement

This is the separate G0 durability probe tracked in COH-131. It does not extend
E1–E3, change the hold/review-marker comparison, or add runs to its schedule.
Reference solutions and this harness are maintainer-only, outside participant
starting workspaces. No scored runs are authorized by this supplement.

## Question and comparator

Does Cohesive require less application restructuring to strengthen execution
from host-lifetime to durable submission, compared with an idiomatic conventional
application integrating an established workflow library? Correctness is primary;
changed domain/process code, integration work, time/tokens/cost and operational
dependencies explain the result. Do not assume either a trivial configuration
change or a large rewrite, and do not treat patch size as success.

The selected reference comparator is Microsoft Durable Task, standalone .NET SDK
1.25.0, using the same scheduler backend in both conditions. The pinned Cohesive
revision already supplies a Durable Task Process interpreter and native host
binding. Conventional uses an ordinary TaskOrchestrator and TaskActivity with
its existing domain rules and transactional step receipts. Temporal or another
library remains a possible separately versioned comparison, not a post-outcome
substitution. Library selection precedes scored runs.

Both reference solutions share a PostgreSQL admission outbox, public identity and
result retention, and a serial dispatcher. Durable Task owns step history and
recovery. This intentionally measures workflow integration on a common execution
backend, not the relative strengths of different scheduling services. The shared
outbox is reference code; participants must implement durable admission from the
original G0 unless a later version explicitly changes the starting treatment.

Pin and pre-provision packages, emulator image, service endpoints and ordinary
SDK documentation. Maintainer setup is reported separately; agent integration and
application configuration count in the task budget. Dependencies are pinned in
`dependency-manifest.json`; the Cohesive source remains
`b0af008d85871ad8866d7d4311707ecd926529de`.

## Target public guarantees

1. Acknowledged admission survives abrupt API/worker process death. Admission
   interrupted before acknowledgment may be absent or committed; retrying the same
   request resolves it without duplicate effects.
2. The same request ID and payload retain one operation ID and eventual result
   across restart. Different input under that ID returns 409 without new work.
3. After restart with the databases and scheduler available, admitted work reaches
   its correct business completion within 120 seconds of the host becoming ready.
4. A crash after stock reservation cannot reserve twice; after order submission,
   recovery creates the missing reservation; interrupted compensation restores the
   original stock exactly once as an observable net effect.
5. Existing G0 outcomes, precedence, reads, rejection preservation and unrelated
   state remain correct. Activity execution may repeat; business effects may not.
6. Admission/results are retained for the qualification campaign without purge,
   including completed-result replay after a second restart. The 1,000-identity
   capacity limit becomes persistent; existing identities replay at capacity.

Scope is one active host, sequential independent intents, concurrent duplicates,
and abrupt host/worker termination. Scheduler and PostgreSQL remain available
and retain their data. Scheduler/data loss, code-version migration, distributed
transactions, multiple active hosts and independent-intent contention are outside
this supplement. A local emulator qualifies this failure model, not production
scheduler disaster recovery.

## Oracle and failure schedule

Use the same reference HTTP commands and business-fact assertions. A common
read-only observer checks persisted reservation cardinality/quantity, stock,
reference integrity and unrelated state. Continuous safety claims require
committed-effect observation; sampled reads alone cannot prove them. Conservation
against completed reservations is checked after recovery because a legitimate
intermediate state can have decremented stock without a reservation row.

Reference-only barriers notify the parent and block before the worker can report
activity success. The parent sends an abrupt kill, restarts the host without
resetting stores, then retries/inspects the original request. Both conditions
place barriers at the same business-effect boundaries:

- No crash, as a positive control.
- Before admission commit; after commit but before HTTP acknowledgment.
- After acknowledged admission and before dispatch.
- After committed reserve, submit, reservation creation, or release, but before
  activity completion is reported to the scheduler.
- After workflow completion and before publishing the retained public result.

Each scenario starts from a fresh application database. For success scenarios,
reserve three of five units, recover, reserve the remaining two for another
order, then reject a further unit. Require exactly two reservations totaling five
and zero available stock. For compensation, start with a directly Submitted
order; after recovery require no reservation and all five units available.
Replay the completed result after another restart. Keep timeout failures visible.

A test barrier is instrumentation, not a required production architecture. Any
participant adapter must identify equivalent boundaries without altering domain
behavior. Before admission to scored runs, qualify the oracle using broken
admission, lost identity, duplicate effects, missing reservation and abandoned
compensation implementations. Preserve exact source/artifact hashes, build and
scheduler logs, crash markers, receipts and assertion evidence.

## Admission still required

- Independent conventional/library integration review and baseline equivalence.
- Common durability prompt and ordinary documentation, with hidden schedules kept
  outside participant workspaces.
- Known-good recovery and application-defect qualification of this oracle.
- Frozen SDK/package locks, runtime/resource configuration and failure schedule.
- Separate repetition/budget/calibration policy and monetary cap. The existing
  hold matrix is not reused as an implicit authorization or sample count.

References: [Durable Task SDK](https://github.com/microsoft/durabletask-dotnet),
[standalone SDK setup](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-task-scheduler/quickstart-portable-durable-task-sdks).
