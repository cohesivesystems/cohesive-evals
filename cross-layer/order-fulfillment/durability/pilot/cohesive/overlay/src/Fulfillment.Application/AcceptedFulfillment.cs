using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Cohesive.Api;
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
                plan.Document.Metadata.Provenance));
        var values = app.Services.GetRequiredService<IProcessExecutionValueRepository>();
        var runtime = new ServiceRuntime(api.Declaration,
            [new ServiceProcessBinding("fulfill", plan, "fulfillment", async (context, request, invocation) =>
            {
                await AdmissionCapacity.Reserve(database, request.Context.CommandId.Value, context.CancellationToken);
                return await start(context, request, invocation);
            }),
             new ServiceProcessResultBinding("result", plan, "fulfillment", values)],
            new IdentityServiceInvocationAuthorization("demo", new("Partition")));
        var routes = app.MapGroup("").AddEndpointFilter(async (context, next) =>
        {
            object? response;
            try
            {
                response = await next(context);
            }
            catch (AdmissionCapacity.CapacityExceededException)
            {
                return Results.StatusCode(503);
            }
            catch (BadHttpRequestException) when (HttpMethods.IsGet(context.HttpContext.Request.Method))
            {
                return Results.NotFound();
            }
            catch (BadHttpRequestException error) when (error.StatusCode == 400)
            {
                return Results.BadRequest(new ErrorResponse("InvalidRequest"));
            }
            catch (JsonException)
            {
                return Results.BadRequest(new ErrorResponse("InvalidRequest"));
            }
            return response switch
            {
                IValueHttpResult { Value: ServiceProcessReceipt receipt } =>
                    Results.Json(new Admission(receipt.ResultLocation.Split('/')[^1], receipt.ResultLocation), statusCode: 202),
                IStatusCodeHttpResult { StatusCode: 409 } => Results.Conflict(new ErrorResponse("RequestIdentityConflict")),
                IValueHttpResult { Value: ApiProblem { Code: "services.process.notCompleted" } } => Results.Json(new ErrorResponse("ExecutionFailed"), statusCode: 500),
                IValueHttpResult { Value: ApiProblem { Code: "services.process.evidenceUnavailable" } }
                    when await EngineFailed(context.HttpContext) => Results.Json(new ErrorResponse("ExecutionFailed"), statusCode: 500),
                IStatusCodeHttpResult { StatusCode: 202 } => Results.StatusCode(202),
                IStatusCodeHttpResult { StatusCode: 404 } => Results.NotFound(),
                _ => response
            };
        });
        // The native reader reports missing terminal evidence for a failed worker
        // activity. Distinguish that retained engine failure from a storage error.
        async Task<bool> EngineFailed(HttpContext http)
        {
            var token = (string)http.Request.RouteValues["instanceId"]!;
            var id = Encoding.UTF8.GetString(Microsoft.AspNetCore.WebUtilities.WebEncoders.Base64UrlDecode(token));
            var physical = DurableTaskProcessExecutionIdentity.GetPhysicalInstanceId(Authority, new(id));
            var metadata = await client.GetInstanceAsync(physical, cancellation: http.RequestAborted);
            return metadata?.RuntimeStatus is OrchestrationRuntimeStatus.Failed or OrchestrationRuntimeStatus.Terminated;
        }

        routes.MapServiceAcceptedProcess(api, runtime, (_, request) =>
        {
            if (string.IsNullOrWhiteSpace(request.RequestId) || string.IsNullOrWhiteSpace(request.OrderId)
                || string.IsNullOrWhiteSpace(request.Sku))
                throw new BadHttpRequestException("Missing fulfillment identifier.");
            var id = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(request.RequestId)));
            return (new(id), new(id), new(new(id), new("attempt/1")),
                ObservationValue.FromObject(new FulfillOrder(request.OrderId, request.Sku, request.Quantity)));
        }, value => value.Value!.Value.Deserialize<FulfillmentResult>()!, (_, requirement) => requirement.Id);
    }
}
