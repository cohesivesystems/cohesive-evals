# Semantic development tools

Edit the source under `src/Fulfillment.Application`. The typed entity and transition declarations
and the fulfillment process live in `FulfillmentDomain.cs`; native read queries live in
`FulfillmentQueries.cs`. `Program.cs` and `FulfillmentBackend.cs` own HTTP routing and runtime wiring.

Build and export from this workspace root:

    dotnet run --project Development -- "$PWD"

Call `learn`, then `workspace` and retain snapshotId. Resolve definitions before inspection.
Use source mappings when supplied, references for direct consumers and impact for bounded transitive
paths. Review incompleteDefinitions, edge evidence and truncation flags. Edit source, rebuild/export,
get a fresh snapshot, check diagnostics and compare with the retained baseline. A stale snapshot
must be rejected; nonempty changedInputs requires a rebuild/export. Never edit the derived bundle.

This export covers entities, shapes, relationships, transitions, the fulfillment process and native
queries. HTTP handlers, queue/replay logic and persistence wiring are ordinary C# and are not fully
represented. No portable API contracts are exported: do not infer API compatibility from this bundle.
Use the public contract tests and application behavior for HTTP evidence. The tools do not start the
application or database and do not prove runtime behavior. Unknown or missing coverage is not a pass.

The server exposes nine read-only tools: learn, workspace, resolve, inspect, references, impact,
check, compare and compatibility. The last tool needs portable API contracts that this host does
not currently export. Keep one server session alive for comparisons; only four snapshots are retained.
