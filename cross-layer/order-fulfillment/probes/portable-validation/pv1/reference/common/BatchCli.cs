using System.Text.Json;
using Microsoft.Extensions.Options;
using Microsoft.AspNetCore.Http.Json;

namespace Fulfillment.Application;

// One JSON array per input line; one result per output line. The shell owns files.
public sealed class BatchCli(BatchService service, IOptions<JsonOptions> jsonOptions)
{
    public async Task RunAsync(TextReader input, TextWriter output, CancellationToken cancellationToken)
    {
        while (await input.ReadLineAsync(cancellationToken) is { } line)
        {
            var requests = Decode(line);
            var reply = requests is null ? new BatchReply(Error: "InvalidBatch")
                : await service.ExecuteAsync(requests, cancellationToken);
            await output.WriteLineAsync(JsonSerializer.Serialize(reply, jsonOptions.Value.SerializerOptions));
            await output.FlushAsync(cancellationToken);
        }
    }

    FulfillmentRequest?[]? Decode(string line)
    {
        try
        {
            using var document = JsonDocument.Parse(line);
            if (document.RootElement.ValueKind != JsonValueKind.Array) return null;
            return document.RootElement.EnumerateArray().Select(item =>
            {
                try { return item.Deserialize<FulfillmentRequest>(jsonOptions.Value.SerializerOptions); }
                catch (JsonException) { return null; }
            }).ToArray();
        }
        catch (JsonException) { return null; }
    }
}
