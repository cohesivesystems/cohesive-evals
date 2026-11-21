using Cohesive.Adapters.Postgres;
using Npgsql;
using NpgsqlTypes;

namespace Fulfillment.Application;

public sealed class AvailabilityProjection(NpgsqlDataSource database)
{
    PostgresQueryReader<string, ReservationAvailability[]> rows = null!;

    public async Task Initialize(PostgresQueryReader<string, ReservationAvailability[]> reader)
    {
        rows = reader;
        await using var schema = database.CreateCommand("""
            CREATE TABLE IF NOT EXISTS order_availability (
                order_id text NOT NULL, reservation_id text, sku text, quantity integer, available integer);
            CREATE INDEX IF NOT EXISTS order_availability_order ON order_availability(order_id)
            """);
        await schema.ExecuteNonQueryAsync();
        await Refresh();
    }

    public async Task Refresh()
    {
        await using var connection = await database.OpenConnectionAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await using var replace = new NpgsqlCommand("""
            LOCK TABLE order_availability IN EXCLUSIVE MODE;
            DELETE FROM order_availability
            """, connection, transaction);
        await replace.ExecuteNonQueryAsync();
        var snapshot = await rows.ReadAsync(FulfillmentStoragePolicy.LocalPartition);
        await using (var writer = await connection.BeginBinaryImportAsync("""
            COPY order_availability (order_id, reservation_id, sku, quantity, available) FROM STDIN (FORMAT BINARY)
            """))
        {
            foreach (var row in snapshot)
            {
                await writer.StartRowAsync();
                await writer.WriteAsync(row.OrderId, NpgsqlDbType.Text);
                await writer.WriteAsync(row.ReservationId, NpgsqlDbType.Text);
                await writer.WriteAsync(row.Sku, NpgsqlDbType.Text);
                await writer.WriteAsync(row.Quantity, NpgsqlDbType.Integer);
                await writer.WriteAsync(row.Available, NpgsqlDbType.Integer);
            }
            await writer.CompleteAsync();
        }
        await transaction.CommitAsync();
    }

    public async Task<AvailabilityView[]?> Read(string id)
    {
        await using var command = database.CreateCommand("""
            SELECT reservation_id, sku, quantity, available FROM order_availability WHERE order_id = $1
            """);
        command.Parameters.AddWithValue(id);
        await using var reader = await command.ExecuteReaderAsync();
        if (!await reader.ReadAsync()) return null;
        var rows = new List<AvailabilityView>();
        do
        {
            if (!reader.IsDBNull(0))
                rows.Add(new(reader.GetString(0), reader.GetString(1), reader.GetInt32(2), reader.GetInt32(3)));
        } while (await reader.ReadAsync());
        return rows.OrderBy(row => row.ReservationId, StringComparer.Ordinal).ToArray();
    }
}
