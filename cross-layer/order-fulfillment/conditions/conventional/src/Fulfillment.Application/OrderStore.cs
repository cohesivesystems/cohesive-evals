using Npgsql;
using System.Text.Json;

namespace Fulfillment.Application;

public sealed class OrderStore(NpgsqlDataSource database)
{
    public async Task Initialize()
    {
        await using var command = database.CreateCommand("""
            CREATE TABLE IF NOT EXISTS orders(id text COLLATE "C" PRIMARY KEY, status text NOT NULL CHECK(status IN ('Draft','Submitted')));
            CREATE TABLE IF NOT EXISTS inventory(sku text COLLATE "C" PRIMARY KEY, available integer NOT NULL CHECK(available >= 0));
            CREATE TABLE IF NOT EXISTS reservations(id text COLLATE "C" PRIMARY KEY, order_id text COLLATE "C" NOT NULL REFERENCES orders(id),
                sku text COLLATE "C" NOT NULL REFERENCES inventory(sku), quantity integer NOT NULL CHECK(quantity > 0));
            CREATE TABLE IF NOT EXISTS operation_receipts(operation_key text COLLATE "C" PRIMARY KEY, input text NOT NULL, result jsonb NOT NULL);
            """);
        await command.ExecuteNonQueryAsync();
    }
    public async Task<OrderCreated> Create()
    {
        var id = Guid.NewGuid().ToString("D");
        await using var command = database.CreateCommand("INSERT INTO orders(id,status) VALUES($1,'Draft')");
        command.Parameters.AddWithValue(id); await command.ExecuteNonQueryAsync();
        return new(id);
    }
    public async Task<Order?> Order(string id)
    {
        await using var command = database.CreateCommand("SELECT id,status FROM orders WHERE id=$1");
        command.Parameters.AddWithValue(id); await using var reader = await command.ExecuteReaderAsync();
        return await reader.ReadAsync() ? new(reader.GetString(0), Enum.Parse<OrderStatus>(reader.GetString(1))) : null;
    }
    public async Task<InventoryItem?> Inventory(string sku)
    {
        await using var command = database.CreateCommand("SELECT sku,available FROM inventory WHERE sku=$1");
        command.Parameters.AddWithValue(sku); await using var reader = await command.ExecuteReaderAsync();
        return await reader.ReadAsync() ? new(reader.GetString(0), reader.GetInt32(1)) : null;
    }
    public async Task<Reservation?> Reservation(string id)
    {
        await using var command = database.CreateCommand("SELECT id,order_id,sku,quantity FROM reservations WHERE id=$1");
        command.Parameters.AddWithValue(id); await using var reader = await command.ExecuteReaderAsync();
        return await reader.ReadAsync() ? new(reader.GetString(0), reader.GetString(1), reader.GetString(2), reader.GetInt32(3)) : null;
    }
    public async Task<OrderDetailsView?> Details(string id)
    {
        await using var command = database.CreateCommand("""
            SELECT o.id,o.status,r.id,r.sku,r.quantity,i.available FROM orders o
            LEFT JOIN reservations r ON r.order_id=o.id LEFT JOIN inventory i ON i.sku=r.sku
            WHERE o.id=$1
            """);
        command.Parameters.AddWithValue(id); await using var reader = await command.ExecuteReaderAsync();
        if (!await reader.ReadAsync()) return null;
        var status = reader.GetString(1); var rows = new List<ReservationView>();
        do { if (!reader.IsDBNull(2)) rows.Add(new(reader.GetString(2), reader.GetString(3), reader.GetInt32(4), reader.GetInt32(5))); }
        while (await reader.ReadAsync());
        return new(id, status, rows.OrderBy(row => row.Id, StringComparer.Ordinal).ToArray());
    }
    // Each domain mutation and its optional process-step receipt share one local
    // transaction. The whole fulfillment sequence is deliberately not a transaction.
    async Task<T> Step<T>(string? key, string input, Func<NpgsqlConnection, NpgsqlTransaction, Task<T>> action)
    {
        await using var connection = await database.OpenConnectionAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        if (key is not null)
        {
            await using var receipt = new NpgsqlCommand("SELECT input,result::text FROM operation_receipts WHERE operation_key=$1", connection, transaction);
            receipt.Parameters.AddWithValue(key); await using var reader = await receipt.ExecuteReaderAsync();
            if (await reader.ReadAsync())
            {
                if (reader.GetString(0) != input) throw new InvalidOperationException("Operation identity conflict.");
                return JsonSerializer.Deserialize<T>(reader.GetString(1))!;
            }
        }
        var result = await action(connection, transaction);
        if (key is not null)
        {
            await using var receipt = new NpgsqlCommand("INSERT INTO operation_receipts(operation_key,input,result) VALUES($1,$2,$3::jsonb)", connection, transaction);
            receipt.Parameters.AddWithValue(key); receipt.Parameters.AddWithValue(input); receipt.Parameters.AddWithValue(JsonSerializer.Serialize(result));
            await receipt.ExecuteNonQueryAsync();
        }
        await transaction.CommitAsync(); return result;
    }
    public Task<SubmissionOutcome?> Submit(string id, string? key = null) => Step<SubmissionOutcome?>(key, id, async (connection, transaction) =>
    {
        Order order;
        await using (var command = new NpgsqlCommand("SELECT status FROM orders WHERE id=$1 FOR UPDATE", connection, transaction))
        {
            command.Parameters.AddWithValue(id); var status = await command.ExecuteScalarAsync();
            if (status is null) return null;
            order = new(id, Enum.Parse<OrderStatus>((string)status));
        }
        var decision = OrderRules.Submit(order);
        if (decision.Outcome == SubmissionOutcome.Submitted)
        {
            await using var command = new NpgsqlCommand("UPDATE orders SET status=$2 WHERE id=$1", connection, transaction);
            command.Parameters.AddWithValue(id); command.Parameters.AddWithValue(decision.State.Status.ToString());
            await command.ExecuteNonQueryAsync();
        }
        return decision.Outcome;
    });
    public Task<StockOutcome> Stock(string sku, int quantity, bool release, string key) =>
        Step(key, JsonSerializer.Serialize(new { sku, quantity, release }), async (connection, transaction) =>
    {
        InventoryItem item;
        await using (var command = new NpgsqlCommand("SELECT available FROM inventory WHERE sku=$1 FOR UPDATE", connection, transaction))
        {
            command.Parameters.AddWithValue(sku); var value = await command.ExecuteScalarAsync();
            if (value is null) throw new InvalidOperationException("Inventory disappeared.");
            item = new(sku, (int)value);
        }
        var (state, outcome) = release ? (InventoryRules.Release(item, quantity), StockOutcome.Released) : InventoryRules.Reserve(item, quantity);
        if (state != item)
        {
            await using var command = new NpgsqlCommand("UPDATE inventory SET available=$2 WHERE sku=$1", connection, transaction);
            command.Parameters.AddWithValue(sku); command.Parameters.AddWithValue(state.Available); await command.ExecuteNonQueryAsync();
        }
        return outcome;
    });
    public Task<bool> CreateReservation(Reservation reservation, string key) => Step(key, JsonSerializer.Serialize(reservation), async (connection, transaction) =>
    {
        await using var command = new NpgsqlCommand("INSERT INTO reservations(id,order_id,sku,quantity) VALUES($1,$2,$3,$4)", connection, transaction);
        command.Parameters.AddWithValue(reservation.Id); command.Parameters.AddWithValue(reservation.OrderId);
        command.Parameters.AddWithValue(reservation.Sku); command.Parameters.AddWithValue(reservation.Quantity);
        await command.ExecuteNonQueryAsync(); return true;
    });
}
