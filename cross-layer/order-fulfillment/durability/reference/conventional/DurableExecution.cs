using Microsoft.DurableTask;
using Microsoft.DurableTask.Client;
using Npgsql;

namespace Fulfillment.Application;

public sealed record Work(string OperationId, FulfillmentRequest Request);
public sealed record StepInput(string OperationId, FulfillmentRequest Request, string Step);

public sealed class DurableExecution(DurableTaskClient client) : IDurableExecution
{
    public async Task<Completion?> Advance(string id, FulfillmentRequest request, DateTimeOffset admittedAt)
    {
        var state = await client.GetInstanceAsync(id, getInputsAndOutputs:true);
        if (state is null)
        {
            await client.ScheduleNewOrchestrationInstanceAsync("Fulfillment", new Work(id, request), new StartOrchestrationOptions(id));
            return null;
        }
        if (state.RuntimeStatus == OrchestrationRuntimeStatus.Failed) throw new InvalidOperationException(state.FailureDetails?.ErrorMessage);
        return state.RuntimeStatus == OrchestrationRuntimeStatus.Completed ? state.ReadOutputAs<Completion>() : null;
    }
}

public sealed class FulfillmentWorkflow : TaskOrchestrator<Work, Completion>
{
    public override async Task<Completion> RunAsync(TaskOrchestrationContext context, Work work)
    {
        var request = work.Request;
        Task<T> Step<T>(string name) => context.CallActivityAsync<T>("FulfillmentStep", new StepInput(work.OperationId, request, name));
        static Completion Reject(string outcome) => new("Rejected", outcome);
        var order = await Step<Order?>("order");
        if (order is null) return Reject("OrderMissing");
        var existing = await Step<Reservation?>("existing");
        if (existing is not null)
            return existing.OrderId == request.OrderId && existing.Sku == request.Sku && existing.Quantity == request.Quantity && order.Status == OrderStatus.Submitted
                ? new("Submitted","ReservedAndSubmitted") : Reject("ReservationConflict");
        if (await Step<InventoryItem?>("inventory") is null) return Reject("InventoryMissing");
        var reserved = await Step<StockOutcome>("reserve");
        if (reserved == StockOutcome.InvalidQuantity) return Reject("InvalidQuantity");
        if (reserved == StockOutcome.InsufficientStock) return Reject("InsufficientStock");
        if (await Step<SubmissionOutcome?>("submit") == SubmissionOutcome.Submitted)
        {
            await Step<bool>("reservation");
            return new("Submitted","ReservedAndSubmitted");
        }
        await Step<StockOutcome>("release");
        return Reject("OrderRejected");
    }
}

public sealed class FulfillmentStep(NpgsqlDataSource database) : TaskActivity<StepInput, object?>
{
    public override async Task<object?> RunAsync(TaskActivityContext context, StepInput input)
    {
        var store = new OrderStore(database); var r = input.Request; var key = input.OperationId+"/"+input.Step;
        object? result = input.Step switch
        {
            "order" => await store.Order(r.OrderId),
            "existing" => await store.Reservation(r.OrderId),
            "inventory" => await store.Inventory(r.Sku),
            "reserve" => await store.Stock(r.Sku,r.Quantity,false,key),
            "submit" => await store.Submit(r.OrderId,key),
            "reservation" => await store.CreateReservation(new(r.OrderId,r.OrderId,r.Sku,r.Quantity),key),
            "release" => await store.Stock(r.Sku,r.Quantity,true,key),
            _ => throw new InvalidOperationException("Unknown step")
        };
        await CrashBarrier.Reach("after-"+input.Step);
        return result;
    }
}
