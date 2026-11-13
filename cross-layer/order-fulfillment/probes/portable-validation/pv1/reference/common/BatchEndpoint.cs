using System.Text.Json;
using Microsoft.Extensions.Options;
using Microsoft.AspNetCore.Http.Json;

namespace Fulfillment.Application;

public static class BatchEndpoint
{
    public static async Task<IResult> Execute(JsonElement body, BatchService service,
        IOptions<JsonOptions> jsonOptions, IHostApplicationLifetime lifetime)
    {
        if (body.ValueKind != JsonValueKind.Array)
            return Results.BadRequest(new BatchReply(Error: "InvalidBatch"));
        var requests = body.EnumerateArray().Select(item =>
        {
            try { return item.Deserialize<FulfillmentRequest>(jsonOptions.Value.SerializerOptions); }
            catch (JsonException) { return null; }
        }).ToArray();
        // Once decoded, accepted batch work belongs to the host, not the connection.
        var reply = await service.ExecuteAsync(requests, lifetime.ApplicationStopping);
        return reply.Error is null ? Results.Ok(reply) : Results.BadRequest(reply);
    }
}
