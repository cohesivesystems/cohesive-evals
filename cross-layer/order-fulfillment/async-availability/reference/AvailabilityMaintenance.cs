using Npgsql;

namespace Fulfillment.Application;

// PostgreSQL serializes updates to the request row in source-commit order.
// Separate progress storage lets source writers commit while a worker publishes or acknowledges.
public sealed partial class AvailabilityMaintenance(NpgsqlDataSource database, AvailabilityProjection projection)
{
    public async Task Initialize()
    {
        await using var connection = await database.OpenConnectionAsync();
        await using var tx = await connection.BeginTransactionAsync();
        await using var cmd = connection.CreateCommand();
        cmd.Transaction = tx;
        cmd.CommandText = """
            CREATE TABLE IF NOT EXISTS availability_request (singleton bool PRIMARY KEY CHECK(singleton), revision bigint NOT NULL);
            CREATE TABLE IF NOT EXISTS availability_progress (singleton bool PRIMARY KEY CHECK(singleton), revision bigint NOT NULL);
            INSERT INTO availability_request VALUES (true, 1) ON CONFLICT DO NOTHING;
            INSERT INTO availability_progress VALUES (true, 0) ON CONFLICT DO NOTHING;
            CREATE OR REPLACE FUNCTION request_availability_refresh() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN UPDATE availability_request SET revision = revision + 1; RETURN NULL; END $$;
            """;
        await cmd.ExecuteNonQueryAsync();
        using var identifiers = new NpgsqlCommandBuilder();
        foreach (var table in SourceTables)
        {
            cmd.CommandText = $"""
                CREATE OR REPLACE TRIGGER availability_changed AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE
                ON {identifiers.QuoteIdentifier(table)} FOR EACH STATEMENT EXECUTE FUNCTION request_availability_refresh()
                """;
            await cmd.ExecuteNonQueryAsync();
        }
        await tx.CommitAsync();
    }

    public async Task<long> RequestResync()
    {
        await using var cmd = database.CreateCommand("UPDATE availability_request SET revision = revision + 1 RETURNING revision");
        return (long)(await cmd.ExecuteScalarAsync())!;
    }

    public async Task<AvailabilityCheckpoint> Checkpoint()
    {
        await using var cmd = database.CreateCommand("""
            SELECT r.revision, p.revision FROM availability_request r CROSS JOIN availability_progress p
            """);
        await using var reader = await cmd.ExecuteReaderAsync();
        await reader.ReadAsync();
        return new(reader.GetInt64(0), reader.GetInt64(1));
    }

    public async Task RunOnce()
    {
        await using var connection = await database.OpenConnectionAsync();
        await using var tx = await connection.BeginTransactionAsync(System.Data.IsolationLevel.ReadCommitted);
        await using var cmd = connection.CreateCommand();
        cmd.Transaction = tx;
        // Lock only worker ownership. Source writers never need this lock.
        cmd.CommandText = "SELECT pg_advisory_xact_lock(hashtextextended('availability/worker', 0))";
        await cmd.ExecuteNonQueryAsync();
        var cut = await Checkpoint();
        if (cut.Requested > cut.Applied)
        {
            await projection.Refresh();
            cmd.CommandText = "UPDATE availability_progress SET revision = $1 WHERE singleton";
            cmd.Parameters.AddWithValue(cut.Requested);
            await cmd.ExecuteNonQueryAsync();
        }
        await tx.CommitAsync();
    }
}

public sealed record AvailabilityCheckpoint(long Requested, long Applied);
