namespace Fulfillment.Application;

public static class BatchEndpoint
{
    public static async Task<IResult> Execute(FulfillmentRequest?[] requests,
        BatchService service, IHostApplicationLifetime lifetime)
    {
        // Accepted work belongs to the host, not the HTTP connection.
        var reply = await service.ExecuteAsync(requests, lifetime.ApplicationStopping);
        return reply.Error is null ? Results.Ok(reply) : Results.BadRequest(reply);
    }
}
