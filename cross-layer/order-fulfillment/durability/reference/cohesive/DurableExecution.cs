using Cohesive.Adapters.DurableTask;
using Cohesive.Api.Execution.Services;
using Cohesive.Execution;
using Cohesive.Model;
using Cohesive.Identity;
using Cohesive.Prelude;
using Cohesive.Processes.Execution;
using Microsoft.DurableTask.Client;

namespace Fulfillment.Application;

public sealed class DurableExecution(DurableTaskClient client, FulfillmentBackend backend) : IDurableExecution
{
    static readonly InteractionAuthorityScope Scope = new("fulfillment", "local");
    public async Task<ExecutionState> EnsureStartedAndInspect(string id, FulfillmentRequest request, DateTimeOffset admittedAt)
    {
        var plan = backend.Prepared.Plan;
        var physicalId = DurableTaskProcessExecutionIdentity.GetPhysicalInstanceId(Scope, new(id));
        var state = await client.GetInstanceAsync(physicalId, getInputsAndOutputs:true);
        if (state is null)
        {
            var continuation = new ProcessContinuationIdentity(new(id), new("attempt/1"));
            var input = PortableValue.Concrete(plan.Definition.Input, ObservationValue.FromObject(new FulfillOrder(request.OrderId, request.Sku, request.Quantity)));
            var context = new ProcessControlCommandContext(new(id),new(request.RequestId),new(id),
                new("local-demo", Scope, "local-example"), admittedAt, plan.Document.Metadata.Provenance);
            var start = new ProcessStartRequest(ProcessStartRequest.CurrentSchemaVersion,plan.DefinitionReference,context,continuation,input);
            // The shared PostgreSQL admission row is the durable acceptance authority.
            await client.ScheduleCohesiveProcessAsync(new(new ProcessStartReceipt(start,admittedAt),
                new ProcessActivationContext(Scope,new(id),new(InteractionDurabilityDemand.Durable,InteractionVisibilityDemand.AfterOriginCommit),plan.Document.Metadata.Provenance)));
            return new ExecutionState.Pending();
        }
        if (state.RuntimeStatus is OrchestrationRuntimeStatus.Failed or OrchestrationRuntimeStatus.Terminated)
            return new ExecutionState.Failed(state.FailureDetails?.ErrorMessage ?? state.RuntimeStatus.ToString());
        if (state.RuntimeStatus != OrchestrationRuntimeStatus.Completed) return new ExecutionState.Pending();
        var output = state.ReadOutputAs<DurableTaskSequentialProcessResult>()!.State.Terminal.Detail!.Value!.Value!.Value;
        return new ExecutionState.Completed(new(output.GetProperty("Status").GetRequiredString(),output.GetProperty("Outcome").GetRequiredString()));
    }
}

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
