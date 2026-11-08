using Cohesive.Api.Execution.Services;
using Cohesive.Execution;
using Cohesive.Identity;
using Cohesive.Prelude;
using Cohesive.Processes.Execution;

namespace Fulfillment.Application;

// Test-only barrier decoration; the underlying native host owns all domain work.
public sealed class RecoveryHost(FulfillmentBackend backend) : IAsyncProcessReferenceHost
{
    static OperationContext Identity(OperationContext context) => context.WithIdentityContext(FulfillmentDemoIdentity.Context);
    public async ValueTask<ProcessOperationResult> InvokeTransitionAsync(OperationContext context, ProcessTransitionInvocation invocation)
    {
        var id = invocation.Definition.DefinitionId.Value;
        if (id == "fulfillment/reserve") await CrashBarrier.Reach("before-reserve");
        var result = await backend.Prepared.Host.InvokeTransitionAsync(Identity(context), invocation);
        var point = id switch
        {
            "fulfillment/reserve" => "reserve", "example/order/submit" => "submit",
            "fulfillment/reservation/create" => "reservation", "fulfillment/release" => "release",
            _ => "unknown"
        };
        await CrashBarrier.Reach("after-"+point);
        return result;
    }
    public ValueTask<ProcessOperationResult> EvaluateRelationAsync(OperationContext context, ProcessRelationEvaluation evaluation) =>
        backend.Prepared.Host.EvaluateRelationAsync(Identity(context),evaluation);
    public ValueTask<ProcessSignalTargetResult> ResolveSignalTargetAsync(OperationContext context, ProcessSignalTargetResolution resolution) =>
        backend.Prepared.Host.ResolveSignalTargetAsync(Identity(context),resolution);
}
