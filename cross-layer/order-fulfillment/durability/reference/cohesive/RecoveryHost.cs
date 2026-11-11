using Cohesive.Api.Execution.Services;
using Cohesive.Execution;
using Cohesive.Processes.Compilation;
using Cohesive.Processes.IR;
using Cohesive.Identity;
using Cohesive.Prelude;
using Cohesive.Processes.Execution;

namespace Fulfillment.Application;

// Test-only barrier decoration; the underlying native host owns all domain work.
public sealed class RecoveryHost(FulfillmentBackend backend) : IAsyncProcessReferenceHost
{
    static readonly Dictionary<string, string> Points = new()
    {
        ["fulfillment/reserve"] = "reserve", ["example/order/submit"] = "submit",
        ["fulfillment/reservation/create"] = "reservation", ["fulfillment/release"] = "release"
    };
    public static void Validate(CompiledProcessPlan plan)
    {
        var actual = plan.Definition.Nodes.OfType<InvokeTransitionProcessNode>()
            .Select(n => n.Transition.DefinitionId.Value).ToHashSet(StringComparer.Ordinal);
        if (!actual.SetEquals(Points.Keys))
            throw new InvalidOperationException("Recovery barrier transitions differ: " + string.Join(", ", actual.Order()));
    }
    static OperationContext Identity(OperationContext context) => context.WithIdentityContext(FulfillmentDemoIdentity.Context);
    public async ValueTask<ProcessOperationResult> InvokeTransitionAsync(OperationContext context, ProcessTransitionInvocation invocation)
    {
        var id = invocation.Definition.DefinitionId.Value;
        if (id == "fulfillment/reserve") await CrashBarrier.Reach("before-reserve");
        var result = await backend.Prepared.Host.InvokeTransitionAsync(Identity(context), invocation);
        var point = Points.TryGetValue(id, out var name) ? name
            : throw new InvalidOperationException($"Unregistered recovery barrier transition: {id}");
        await CrashBarrier.Reach("after-"+point);
        return result;
    }
    public ValueTask<ProcessOperationResult> EvaluateRelationAsync(OperationContext context, ProcessRelationEvaluation evaluation) =>
        backend.Prepared.Host.EvaluateRelationAsync(Identity(context),evaluation);
    public ValueTask<ProcessSignalTargetResult> ResolveSignalTargetAsync(OperationContext context, ProcessSignalTargetResolution resolution) =>
        backend.Prepared.Host.ResolveSignalTargetAsync(Identity(context),resolution);
}
