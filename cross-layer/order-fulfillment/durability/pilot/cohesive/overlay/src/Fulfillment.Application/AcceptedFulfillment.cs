using System.Text.Json;
using Cohesive.Processes.Runtime;
using Cohesive.Adapters.AspNet.Services;
using Cohesive.Adapters.DurableTask;
using Cohesive.Api.Execution.Services;
using Cohesive.Execution;
using Cohesive.Model;
using Cohesive.Prelude;
using Microsoft.DurableTask.Client;

namespace Fulfillment.Application;

public sealed partial class FulfillmentBackend
{
    public void MapFulfillment(WebApplication app)
    {
        var plan = Prepared.Plan;
        var client = app.Services.GetRequiredService<DurableTaskClient>();
        var start = client.CreateCohesiveProcessStartDispatcher((_, request, invocation) =>
            new(invocation.Authorization.AuthorityScope, new(request.Context.CommandId.Value),
                new(InteractionDurabilityDemand.Durable, InteractionVisibilityDemand.AfterOriginCommit),
                plan.Document.Metadata.Provenance), maximumRetainedInstances: 1000);
        var values = app.Services.GetRequiredService<IProcessExecutionValueRepository>();
        var runtime = new ServiceRuntime(api.Declaration,
            [new ServiceProcessBinding("fulfill", plan, "fulfillment", start),
             new ServiceProcessResultBinding("result", plan, "fulfillment", values)],
            new IdentityServiceInvocationAuthorization("demo", new("Partition")));
        app.MapServiceAcceptedProcess(api, runtime, (_, request) =>
        {
            if (string.IsNullOrWhiteSpace(request.OrderId)
                || string.IsNullOrWhiteSpace(request.Sku))
                throw new BadHttpRequestException("Missing fulfillment identifier.");
            return AcceptedProcessIntent.FromRequestId(request.RequestId,
                ObservationValue.FromObject(new FulfillOrder(request.OrderId, request.Sku, request.Quantity)));
        }, value => value.Value!.Value.Deserialize<FulfillmentResult>()!, (_, requirement) => requirement.Id);
    }
}
