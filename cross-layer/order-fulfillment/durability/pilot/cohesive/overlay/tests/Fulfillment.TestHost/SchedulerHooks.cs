using Cohesive.Adapters.DurableTask;
using Grpc.Core;
using Grpc.Core.Interceptors;
using Microsoft.DurableTask.Protobuf;

namespace Fulfillment.Application;

// The native engine owns these commits. Pause its outbound worker RPC on
// the corresponding side of scheduler acknowledgement, before replying to the host.
internal sealed class SchedulerHooks : Interceptor
{
    public override AsyncUnaryCall<TResponse> AsyncUnaryCall<TRequest, TResponse>(
        TRequest request, ClientInterceptorContext<TRequest, TResponse> context,
        AsyncUnaryCallContinuation<TRequest, TResponse> continuation)
    {
        var (before, after) = request switch
        {
            EntityBatchResult batch when batch.Actions.Any(a =>
                a.StartNewOrchestration?.Name == DurableTaskSequentialProcessNames.Orchestration)
                => ("before-admission-commit", "after-admission-commit"),
            OrchestratorResponse turn when turn.Actions.Any(a =>
                a.ScheduleTask?.Name == DurableTaskSequentialProcessNames.HostOperationActivity)
                => ("before-dispatch", (string?)null),
            OrchestratorResponse turn when turn.InstanceId.StartsWith("cohesive-process:v1:", StringComparison.Ordinal)
                && turn.Actions.Any(a => a.CompleteOrchestration is not null)
                => ("before-result-commit", (string?)null),
            _ => ((string?)null, (string?)null)
        };
        if (before is not null && EvaluationHooks.Enabled(before))
            EvaluationHooks.Block(before).GetAwaiter().GetResult();
        var call = continuation(request, context);
        if (after is null || !EvaluationHooks.Enabled(after)) return call;
        async Task<TResponse> AfterCommit()
        {
            var response = await call.ResponseAsync;
            await EvaluationHooks.Block(after);
            return response;
        }
        return new(AfterCommit(), call.ResponseHeadersAsync, call.GetStatus, call.GetTrailers, call.Dispose);
    }
}
