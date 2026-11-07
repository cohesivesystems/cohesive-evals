using Npgsql;
namespace Fulfillment.Application;

public static class Seeding
{
    public static async Task Write(NpgsqlDataSource database, SeedData data)
    {
        await using var connection = await database.OpenConnectionAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        foreach (var order in data.Orders)
        {
            await using var command = new NpgsqlCommand("INSERT INTO orders(id,status) VALUES($1,$2)", connection, transaction);
            command.Parameters.AddWithValue(order.Id); command.Parameters.AddWithValue(order.Status); await command.ExecuteNonQueryAsync();
        }
        foreach (var item in data.Inventory)
        {
            await using var command = new NpgsqlCommand("INSERT INTO inventory(sku,available) VALUES($1,$2)", connection, transaction);
            command.Parameters.AddWithValue(item.Sku); command.Parameters.AddWithValue(item.Available); await command.ExecuteNonQueryAsync();
        }
        foreach (var reservation in data.Reservations)
        {
            await using var command = new NpgsqlCommand("INSERT INTO reservations(id,order_id,sku,quantity) VALUES($1,$2,$3,$4)", connection, transaction);
            command.Parameters.AddWithValue(reservation.Id); command.Parameters.AddWithValue(reservation.OrderId);
            command.Parameters.AddWithValue(reservation.Sku); command.Parameters.AddWithValue(reservation.Quantity); await command.ExecuteNonQueryAsync();
        }
        await transaction.CommitAsync();
    }
}
