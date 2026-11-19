using Npgsql;

namespace Fulfillment.Application;

// The pilot caps retained identities, including completed work. This table stores
// only quota membership. Durable Task owns commands, conflicts, dispatch and results.
internal static class AdmissionCapacity
{
    public static async Task Initialize(NpgsqlDataSource database)
    {
        await using var command = database.CreateCommand("""
            CREATE TABLE IF NOT EXISTS fulfillment_capacity(identity text COLLATE "C" PRIMARY KEY)
            """);
        await command.ExecuteNonQueryAsync();
    }

    public static async Task Reserve(NpgsqlDataSource database, string identity, CancellationToken cancellation)
    {
        await using var connection = await database.OpenConnectionAsync(cancellation);
        await using var transaction = await connection.BeginTransactionAsync(cancellation);
        await using var gate = new NpgsqlCommand("LOCK TABLE fulfillment_capacity IN EXCLUSIVE MODE", connection, transaction);
        await gate.ExecuteNonQueryAsync(cancellation);
        await using var reserve = new NpgsqlCommand("""
            WITH added AS (
                INSERT INTO fulfillment_capacity(identity)
                SELECT $1 WHERE (SELECT count(*) FROM fulfillment_capacity) < 1000
                ON CONFLICT DO NOTHING RETURNING identity
            )
            SELECT EXISTS(SELECT FROM added) OR EXISTS(SELECT FROM fulfillment_capacity WHERE identity = $1)
            """, connection, transaction);
        reserve.Parameters.AddWithValue(identity);
        if (await reserve.ExecuteScalarAsync(cancellation) is not true) throw new CapacityExceededException();
        await transaction.CommitAsync(cancellation);
    }

    internal sealed class CapacityExceededException : Exception;
}
