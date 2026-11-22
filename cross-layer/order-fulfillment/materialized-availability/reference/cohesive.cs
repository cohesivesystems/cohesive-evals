using Cohesive.Adapters.Postgres;
using Npgsql;

namespace Fulfillment.Application;

public sealed class AvailabilityProjection(NpgsqlDataSource database, PostgresMaterializedRows target)
{
    public Task Refresh() => target.ResyncAsync();

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
