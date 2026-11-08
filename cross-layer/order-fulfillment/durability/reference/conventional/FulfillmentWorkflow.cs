using Microsoft.DurableTask;
using Microsoft.DurableTask.Client;
using Npgsql;

namespace Fulfillment.Application;

public sealed record Work(string OperationId, FulfillmentRequest Request);

// Typed call sites bind each activity name to its input and result types once.
public static class Activities
{
    public static Task<Order?> Order(TaskOrchestrationContext c, string id) => c.CallActivityAsync<Order?>(nameof(ReadOrder), id);
    public static Task<Reservation?> Reservation(TaskOrchestrationContext c, string id) => c.CallActivityAsync<Reservation?>(nameof(ReadReservation), id);
    public static Task<InventoryItem?> Inventory(TaskOrchestrationContext c, string sku) => c.CallActivityAsync<InventoryItem?>(nameof(ReadInventory), sku);
    public static Task<StockOutcome> Reserve(TaskOrchestrationContext c, Work work) => c.CallActivityAsync<StockOutcome>(nameof(ReserveStock), work);
    public static Task<SubmissionOutcome?> Submit(TaskOrchestrationContext c, Work work) => c.CallActivityAsync<SubmissionOutcome?>(nameof(SubmitOrder), work);
    public static Task<bool> CreateReservation(TaskOrchestrationContext c, Work work) => c.CallActivityAsync<bool>(nameof(CreateReservation), work);
    public static Task<StockOutcome> Release(TaskOrchestrationContext c, Work work) => c.CallActivityAsync<StockOutcome>(nameof(ReleaseStock), work);
}

public sealed class FulfillmentWorkflow : TaskOrchestrator<Work, Completion>
{
    public override async Task<Completion> RunAsync(TaskOrchestrationContext context, Work work)
    {
        var request = work.Request;
        static Completion Reject(string outcome) => new("Rejected", outcome);
        var order = await Activities.Order(context, request.OrderId);
        if (order is null) return Reject("OrderMissing");
        var existing = await Activities.Reservation(context, request.OrderId);
        if (existing is not null)
            return existing.OrderId == request.OrderId && existing.Sku == request.Sku && existing.Quantity == request.Quantity && order.Status == OrderStatus.Submitted
                ? new("Submitted","ReservedAndSubmitted") : Reject("ReservationConflict");
        if (await Activities.Inventory(context, request.Sku) is null) return Reject("InventoryMissing");
        var reserved = await Activities.Reserve(context, work);
        if (reserved == StockOutcome.InvalidQuantity) return Reject("InvalidQuantity");
        if (reserved == StockOutcome.InsufficientStock) return Reject("InsufficientStock");
        if (reserved != StockOutcome.Reserved) throw new InvalidOperationException("Unknown reserve outcome.");
        if (await Activities.Submit(context, work) == SubmissionOutcome.Submitted)
        {
            await Activities.CreateReservation(context, work);
            return new("Submitted","ReservedAndSubmitted");
        }
        await Activities.Release(context, work);
        return Reject("OrderRejected");
    }
}

public sealed class ReadOrder(NpgsqlDataSource database) : TaskActivity<string, Order?>
{
    public override Task<Order?> RunAsync(TaskActivityContext context, string id) => new OrderStore(database).Order(id);
}
public sealed class ReadReservation(NpgsqlDataSource database) : TaskActivity<string, Reservation?>
{
    public override Task<Reservation?> RunAsync(TaskActivityContext context, string id) => new OrderStore(database).Reservation(id);
}
public sealed class ReadInventory(NpgsqlDataSource database) : TaskActivity<string, InventoryItem?>
{
    public override Task<InventoryItem?> RunAsync(TaskActivityContext context, string sku) => new OrderStore(database).Inventory(sku);
}
public sealed class ReserveStock(NpgsqlDataSource database) : TaskActivity<Work, StockOutcome>
{
    public override async Task<StockOutcome> RunAsync(TaskActivityContext context, Work work)
    {
        await CrashBarrier.Reach("before-reserve");
        var result = await new OrderStore(database).Stock(work.Request.Sku,work.Request.Quantity,false,work.OperationId+"/reserve");
        await CrashBarrier.Reach("after-reserve");
        return result;
    }
}
public sealed class SubmitOrder(NpgsqlDataSource database) : TaskActivity<Work, SubmissionOutcome?>
{
    public override async Task<SubmissionOutcome?> RunAsync(TaskActivityContext context, Work work)
    {
        var result = await new OrderStore(database).Submit(work.Request.OrderId,work.OperationId+"/submit");
        await CrashBarrier.Reach("after-submit");
        return result;
    }
}
public sealed class CreateReservation(NpgsqlDataSource database) : TaskActivity<Work, bool>
{
    public override async Task<bool> RunAsync(TaskActivityContext context, Work work)
    {
        var r=work.Request;
        var result = await new OrderStore(database).CreateReservation(new(r.OrderId,r.OrderId,r.Sku,r.Quantity),work.OperationId+"/reservation");
        await CrashBarrier.Reach("after-reservation");
        return result;
    }
}
public sealed class ReleaseStock(NpgsqlDataSource database) : TaskActivity<Work, StockOutcome>
{
    public override async Task<StockOutcome> RunAsync(TaskActivityContext context, Work work)
    {
        var result = await new OrderStore(database).Stock(work.Request.Sku,work.Request.Quantity,true,work.OperationId+"/release");
        await CrashBarrier.Reach("after-release");
        return result;
    }
}
