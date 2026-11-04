# Fulfillment service

Requires .NET SDK 10.0.402, Python 3.9+ for the HTTP checks, and PostgreSQL 17.

```sh
dotnet restore Fulfillment.slnx --locked-mode
dotnet build Fulfillment.slnx --no-restore
export ConnectionStrings__Orders='Host=127.0.0.1;Database=orders;Username=postgres;Password=local-password'
python3 tests/contract_tests.py --seed > /tmp/fulfillment-seed.json
FULFILLMENT_SETUP=1 dotnet run --no-build --project src/Fulfillment.Application -- --seed /tmp/fulfillment-seed.json
dotnet run --no-build --project src/Fulfillment.Application -- --urls http://127.0.0.1:5080
```

With that fresh host running, execute `python3 tests/contract_tests.py http://127.0.0.1:5080`.
The checks mutate data; use a new database for every complete test run.
`CONTRACT.md` describes the public behavior. `schemas.json` specifies wire shapes.

The application separates HTTP and host-lifetime admission from domain decisions,
execution and persistence. The host owns its database pool and background worker.
Request results and replay identities remain private to that host; PostgreSQL owns
entity state and mutation receipts. `Program.cs`, `Contracts.cs` and
`OperationQueue.cs` implement transport and admission. Domain and backend files
own submission, inventory and workflow behavior. Read projections return current
persisted facts. There is no implicit rollback of the whole fulfillment sequence.
