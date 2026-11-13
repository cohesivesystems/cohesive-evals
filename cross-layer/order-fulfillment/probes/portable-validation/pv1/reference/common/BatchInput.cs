using System.Text.Json;
using Microsoft.Extensions.Options;
using Microsoft.AspNetCore.Http.Json;
using System.Text.Json.Serialization;

namespace Fulfillment.Application;

public sealed record BatchItem(int Index, OperationReply Admission,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] OperationReply? Completion = null);

// A one-shot file adapter, using the same queue instance as the HTTP endpoints.
public sealed class BatchInput(IConfiguration configuration, OperationQueue queue,
    IHostApplicationLifetime lifetime, IOptions<JsonOptions> jsonOptions) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var input = configuration["batch-input"];
        var output = configuration["batch-output"];
        if (input is null && output is null) return;
        string? temporary = null;
        try
        {
            if (input is null || output is null) throw new ArgumentException("Supply both batch file options.");
            input = Path.GetFullPath(input);
            output = Path.GetFullPath(output);
            if (input == output || File.Exists(output)) throw new ArgumentException("Batch output must be a new, distinct file.");
            // Reserve a writable output before admitting anything; publishing uses a same-directory rename.
            temporary = output + "." + Guid.NewGuid().ToString("N") + ".tmp";
            await using var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None);
            var text = await File.ReadAllTextAsync(input, stoppingToken);
            var started = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            using var registration = lifetime.ApplicationStarted.Register(() => started.TrySetResult());
            await started.Task.WaitAsync(stoppingToken);
            object result;
            JsonDocument? document = null;
            try { document = JsonDocument.Parse(text); }
            catch (JsonException) { }
            using (document)
            {
                if (document is null || document.RootElement.ValueKind != JsonValueKind.Array
                    || document.RootElement.GetArrayLength() > 100)
                    result = new { error = "InvalidBatch" };
                else
                {
                    var items = new List<BatchItem>();
                    foreach (var item in document.RootElement.EnumerateArray())
                    {
                        FulfillmentRequest? request;
                        try { request = item.Deserialize<FulfillmentRequest>(jsonOptions.Value.SerializerOptions); }
                        catch (JsonException) { request = null; }
                        var admission = request is null ? new OperationReply(400) : queue.Submit(request);
                        var completion = admission.Body is Admission receipt
                            ? await queue.WaitForCompletion(receipt.OperationId, stoppingToken) : null;
                        items.Add(new(items.Count, admission, completion));
                    }
                    result = new { items };
                }
            }
            await JsonSerializer.SerializeAsync(stream, result, new JsonSerializerOptions(JsonSerializerDefaults.Web), stoppingToken);
            await stream.FlushAsync(stoppingToken);
            stream.Close();
            File.Move(temporary, output);
            temporary = null;
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { }
        catch
        {
            Environment.ExitCode = 1;
            lifetime.StopApplication();
            throw;
        }
        finally
        {
            if (temporary is not null) File.Delete(temporary);
        }
    }
}
