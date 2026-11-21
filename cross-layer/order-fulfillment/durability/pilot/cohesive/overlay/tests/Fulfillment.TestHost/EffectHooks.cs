using Cohesive.Identity;
using Cohesive.Prelude;
using Cohesive.Processes.Execution;

namespace Fulfillment.Application;

internal sealed class EffectHooks(IAsyncProcessReferenceHost inner) : IAsyncProcessReferenceHost
{
    public async ValueTask<ProcessOperationResult> InvokeTransitionAsync(OperationContext context, ProcessTransitionInvocation invocation)
    {
        var point = invocation.Definition.DefinitionId.Value switch
        {
            "fulfillment/reserve" => "reserve",
            "example/order/submit" => "submit",
            "fulfillment/reservation/create" => "reservation",
            "fulfillment/release" => "release",
            _ => null
        };
        if (point == "reserve")
            EvaluationHooks.FailBeforeReserve();
        var result = await inner.InvokeTransitionAsync(context, invocation);
        // A successfully executed transition may still be a domain rejection.
        // Match only its applied domain outcome before exposing a post-commit barrier.
        if (point is not null && EvaluationHooks.Enabled("after-" + point) && result.IsSuccessful
            && result.Value?.Value is { } output)
        {
            var applied = point switch
            {
                "reserve" => output.Deserialize<StockResult>()?.Outcome == StockOutcome.Reserved,
                "submit" => output.Deserialize<SubmitOrderResult>()?.Outcome == SubmissionOutcome.Submitted,
                "reservation" => output.Deserialize<ReservationCreationOutcome>() == ReservationCreationOutcome.Created,
                "release" => output.Deserialize<StockResult>()?.Outcome == StockOutcome.Released,
                _ => false
            };
            if (applied) await EvaluationHooks.Block("after-" + point);
        }
        return result;
    }

    public ValueTask<ProcessOperationResult> EvaluateRelationAsync(OperationContext context, ProcessRelationEvaluation evaluation) =>
        inner.EvaluateRelationAsync(context, evaluation);

    public ValueTask<ProcessSignalTargetResult> ResolveSignalTargetAsync(OperationContext context, ProcessSignalTargetResolution resolution) =>
        inner.ResolveSignalTargetAsync(context, resolution);
}

internal static class EvaluationHooks
{
    public static bool Enabled(string point) => Environment.GetEnvironmentVariable("EVAL_CRASH_POINT") == point;

    public static async Task Block(string point)
    {
        if (!Enabled(point)) return;
        var path = Environment.GetEnvironmentVariable("EVAL_CRASH_MARKER") ?? throw new InvalidOperationException("Missing crash marker path.");
        await File.WriteAllTextAsync(path, point);
        await Task.Delay(Timeout.InfiniteTimeSpan);
    }

    public static void FailBeforeReserve()
    {
        if (Environment.GetEnvironmentVariable("EVAL_FAIL_POINT") != "before-reserve") return;
        var path = Environment.GetEnvironmentVariable("EVAL_FAIL_MARKER") ?? throw new InvalidOperationException("Missing failure marker path.");
        try
        {
            using var marker = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read);
        }
        catch (IOException) when (File.Exists(path)) { return; }
        throw new InvalidOperationException("Injected activity failure before reserve.");
    }
}
