using System.Text.Json;
using Npgsql;

namespace Fulfillment.Application;

public interface IDurableExecution
{
    Task<Completion?> Advance(string id, FulfillmentRequest request, DateTimeOffset admittedAt);
}

// One host, serial dispatch. Admission is a persistent outbox; the durable engine
// owns step scheduling/recovery. An acknowledged row is never dependent on RAM.
public sealed class OperationQueue(NpgsqlDataSource database, IDurableExecution execution,
    ILogger<OperationQueue> logger) : BackgroundService
{
    static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    public async Task Initialize()
    {
        await using var command = database.CreateCommand("""
            CREATE TABLE IF NOT EXISTS durable_admissions(
              request_id text COLLATE "C" PRIMARY KEY, operation_id text UNIQUE NOT NULL,
              request jsonb NOT NULL, admitted_at timestamptz NOT NULL, result jsonb);
            """);
        await command.ExecuteNonQueryAsync();
    }
    public async Task<IResult> Admit(FulfillmentRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.RequestId) || string.IsNullOrWhiteSpace(request.OrderId)
            || string.IsNullOrWhiteSpace(request.Sku)) return Results.BadRequest(new ErrorResponse("InvalidRequest"));
        await using var connection = await database.OpenConnectionAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        // Serialize admission/capacity decisions across concurrent duplicate requests.
        await using (var gate = new NpgsqlCommand("LOCK TABLE durable_admissions IN EXCLUSIVE MODE", connection, transaction))
            await gate.ExecuteNonQueryAsync();
        await using (var lookup = new NpgsqlCommand("SELECT operation_id,request::text FROM durable_admissions WHERE request_id=$1", connection, transaction))
        {
            lookup.Parameters.AddWithValue(request.RequestId);
            await using var reader = await lookup.ExecuteReaderAsync();
            if (await reader.ReadAsync())
            {
                var id = reader.GetString(0);
                var previous = JsonSerializer.Deserialize<FulfillmentRequest>(reader.GetString(1), Json);
                return previous == request ? Results.Json(new Admission(id, $"/fulfillment/results/{id}"), statusCode:202)
                    : Results.Conflict(new ErrorResponse("RequestIdentityConflict"));
            }
        }
        await using (var count = new NpgsqlCommand("SELECT count(*) FROM durable_admissions", connection, transaction))
            if ((long)(await count.ExecuteScalarAsync())! >= 1000) return Results.StatusCode(503);
        var operation = Guid.NewGuid().ToString("N");
        await using (var insert = new NpgsqlCommand("INSERT INTO durable_admissions VALUES($1,$2,$3::jsonb,$4,NULL)", connection, transaction))
        {
            insert.Parameters.AddWithValue(request.RequestId); insert.Parameters.AddWithValue(operation);
            insert.Parameters.AddWithValue(JsonSerializer.Serialize(request, Json)); insert.Parameters.AddWithValue(DateTimeOffset.UtcNow);
            await insert.ExecuteNonQueryAsync();
        }
        await CrashBarrier.Reach("before-admission-commit");
        await transaction.CommitAsync();
        await CrashBarrier.Reach("after-admission-commit");
        return Results.Json(new Admission(operation, $"/fulfillment/results/{operation}"), statusCode:202);
    }
    public async Task<IResult> Result(string id)
    {
        await using var command = database.CreateCommand("SELECT result::text FROM durable_admissions WHERE operation_id=$1");
        command.Parameters.AddWithValue(id);
        await using var reader = await command.ExecuteReaderAsync();
        if (!await reader.ReadAsync()) return Results.NotFound();
        return reader.IsDBNull(0) ? Results.StatusCode(202)
            : Results.Ok(JsonSerializer.Deserialize<Completion>(reader.GetString(0), Json));
    }
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                string? id = null; FulfillmentRequest? request = null; DateTimeOffset admitted = default;
                await using (var command = database.CreateCommand("SELECT operation_id,request::text,admitted_at FROM durable_admissions WHERE result IS NULL ORDER BY admitted_at,operation_id LIMIT 1"))
                await using (var reader = await command.ExecuteReaderAsync(stoppingToken))
                    if (await reader.ReadAsync(stoppingToken))
                    { id=reader.GetString(0); request=JsonSerializer.Deserialize<FulfillmentRequest>(reader.GetString(1), Json); admitted=reader.GetFieldValue<DateTimeOffset>(2); }
                if (id is not null)
                {
                    await CrashBarrier.Reach("before-dispatch");
                    var result = await execution.Advance(id, request!, admitted);
                    if (result is not null)
                    {
                        await CrashBarrier.Reach("before-result-commit");
                        await using var save = database.CreateCommand("UPDATE durable_admissions SET result=$2::jsonb WHERE operation_id=$1");
                        save.Parameters.AddWithValue(id); save.Parameters.AddWithValue(JsonSerializer.Serialize(result, Json));
                        await save.ExecuteNonQueryAsync(stoppingToken);
                    }
                }
                await Task.Delay(100, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (Exception error) { logger.LogError(error, "Durable dispatch/recovery failed"); await Task.Delay(500, stoppingToken); }
        }
    }
}
