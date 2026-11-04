using System.Threading.Channels;

namespace Fulfillment.Application;

// Admission and completed results live only for this host lifetime. Execution is
// bounded and owned by the host; a client disconnect does not cancel admitted work.
public sealed class OperationQueue(IFulfillmentBackend backend, ILogger<OperationQueue> logger) : BackgroundService
{
    sealed class Entry(FulfillmentRequest request, Admission admission)
    {
        public FulfillmentRequest Request { get; } = request;
        public Admission Admission { get; } = admission;
        public Completion? Result { get; set; }
        public bool Failed { get; set; }
    }
    readonly object gate = new();
    readonly Dictionary<string, Entry> requests = new(StringComparer.Ordinal);
    readonly Dictionary<string, Entry> operations = new(StringComparer.Ordinal);
    readonly Channel<Entry> work = Channel.CreateBounded<Entry>(new BoundedChannelOptions(1000)
        { SingleReader = true, FullMode = BoundedChannelFullMode.Wait });

    public IResult Admit(FulfillmentRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.RequestId) || string.IsNullOrWhiteSpace(request.OrderId)
            || string.IsNullOrWhiteSpace(request.Sku)) return Results.BadRequest(new ErrorResponse("InvalidRequest"));
        lock (gate)
        {
            if (requests.TryGetValue(request.RequestId, out var previous))
                return previous.Request == request ? Results.Json(previous.Admission, statusCode: 202)
                    : Results.Conflict(new ErrorResponse("RequestIdentityConflict"));
            // Retain every admitted identity until shutdown; do not evict replay evidence.
            if (requests.Count >= 1000) return Results.StatusCode(503);
            var id = Guid.NewGuid().ToString("N");
            var entry = new Entry(request, new Admission(id, $"/fulfillment/results/{id}"));
            requests.Add(request.RequestId, entry);
            operations.Add(id, entry);
            if (!work.Writer.TryWrite(entry))
            {
                requests.Remove(request.RequestId); operations.Remove(id);
                return Results.StatusCode(503);
            }
            return Results.Json(entry.Admission, statusCode: 202);
        }
    }
    public IResult Result(string id)
    {
        lock (gate)
        {
            if (!operations.TryGetValue(id, out var entry)) return Results.NotFound();
            if (entry.Failed) return Results.Json(new ErrorResponse("ExecutionFailed"), statusCode: 500);
            return entry.Result is { } result ? Results.Ok(result) : Results.StatusCode(202);
        }
    }
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        try
        {
            await foreach (var entry in work.Reader.ReadAllAsync(stoppingToken))
            {
                try
                {
                    var result = await backend.Fulfill(entry.Admission.OperationId, entry.Request);
                    lock (gate) entry.Result = result;
                }
                catch (Exception ex)
                {
                    logger.LogError(ex, "Fulfillment execution failed: {OperationId}", entry.Admission.OperationId);
                    lock (gate) entry.Failed = true;
                }
            }
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { }
    }
}
