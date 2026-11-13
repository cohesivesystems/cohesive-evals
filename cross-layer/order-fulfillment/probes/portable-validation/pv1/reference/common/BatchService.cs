using System.Text.Json.Serialization;

namespace Fulfillment.Application;

public sealed record BatchItem(int Index, OperationReply Admission,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] OperationReply? Completion = null);

public sealed record BatchReply(
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] IReadOnlyList<BatchItem>? Items = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Error = null);

// Typed application operation: no console, files, JSON parsing or host lifecycle.
// A null item represents input the adapter could not deserialize.
public sealed class BatchService(OperationQueue queue)
{
    public async Task<BatchReply> ExecuteAsync(IReadOnlyList<FulfillmentRequest?> requests, CancellationToken cancellationToken)
    {
        if (requests.Count > 100) return new(Error: "InvalidBatch");
        var items = new List<BatchItem>();
        foreach (var request in requests)
        {
            var admission = request is null ? new OperationReply(400) : queue.Submit(request);
            var completion = admission.Body is Admission receipt
                ? await queue.WaitForCompletion(receipt.OperationId, cancellationToken) : null;
            items.Add(new(items.Count, admission, completion));
        }
        return new(Items: items);
    }
}
