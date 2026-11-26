using Npgsql;

namespace Fulfillment.Application;

public static class PickList
{
    public sealed record Row(string OrderId, int Priority);

    public static async Task MapPickList(this WebApplication app)
    {
        var database = app.Services.GetRequiredService<NpgsqlDataSource>();
        await using var migration = database.CreateCommand(await File.ReadAllTextAsync(
            Path.Combine(AppContext.BaseDirectory, "pick-schema.sql")));
        await migration.ExecuteNonQueryAsync();
        var query = await File.ReadAllTextAsync(Path.Combine(AppContext.BaseDirectory, "pick-list.sql"));
        app.MapGet("/locations/{id}/pick-list", async (string id, CancellationToken cancellation) =>
        {
            await using var command = database.CreateCommand(query);
            command.Parameters.AddWithValue(id);
            await using var reader = await command.ExecuteReaderAsync(cancellation);
            var rows = new List<Row>(50);
            while (await reader.ReadAsync(cancellation))
                rows.Add(new(reader.GetString(0), reader.GetInt32(1)));
            return rows;
        });
    }
}
