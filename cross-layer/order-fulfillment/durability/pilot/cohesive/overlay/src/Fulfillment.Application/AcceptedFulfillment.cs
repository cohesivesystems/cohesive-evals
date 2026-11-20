using System.Security.Cryptography;
using System.Text;
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
        var routes = app.MapGroup("").AddEndpointFilter(async (context, next) =>
        {
            object? response;
            try
            {
                response = await next(context);
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
                IStatusCodeHttpResult { StatusCode: 409 } => Results.Conflict(new ErrorResponse("RequestIdentityConflict")),
                IStatusCodeHttpResult { StatusCode: 202 } when HttpMethods.IsGet(context.HttpContext.Request.Method) => Results.StatusCode(202),
                IStatusCodeHttpResult { StatusCode: 404 } => Results.NotFound(),
                _ => response
            };
        });
        routes.MapServiceAcceptedProcess(api, runtime, (_, request) =>
        {
            if (string.IsNullOrWhiteSpace(request.RequestId) || string.IsNullOrWhiteSpace(request.OrderId)
                || string.IsNullOrWhiteSpace(request.Sku))
                throw new BadHttpRequestException("Missing fulfillment identifier.");
            var id = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(request.RequestId)));
            return (new(id), new(id), new(new(id), new("attempt/1")),
                ObservationValue.FromObject(new FulfillOrder(request.OrderId, request.Sku, request.Quantity)));
        }, value => value.Value!.Value.Deserialize<FulfillmentResult>()!, (_, requirement) => requirement.Id,
            projectReceipt: receipt => Results.Json(new Admission(receipt.ResultToken, receipt.ResultLocation), statusCode: 202),
            projectFailure: _ => Results.Json(new ErrorResponse("ExecutionFailed"), statusCode: 500));
    }
}
