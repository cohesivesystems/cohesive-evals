using Npgsql;
namespace Fulfillment.Application;

public sealed class FulfillmentBackend(NpgsqlDataSource database) : IFulfillmentBackend
{
    readonly OrderStore store = new(database);
    public Task Seed(SeedData data) => Seeding.Write(database, data);
    public Task Initialize() => store.Initialize();
    public Task<OrderCreated> CreateOrder() => store.Create();
    public async Task<OrderSummary?> GetOrder(string id) => await store.Order(id) is { } order ? new(order.Id, order.Status.ToString()) : null;
    public async Task<InventoryView?> GetInventory(string sku) => await store.Inventory(sku) is { } item ? new(item.Sku, item.Available, item.MaxPerOrder) : null;
    public void MapInventoryLimits(WebApplication app) => app.MapPut("/inventory/{sku}/quantity-limit", async (string sku, HttpContext context) =>
        await store.SetLimit(sku, QuantityLimitInput.Get(context).MaxPerOrder) is { } item
            ? Results.Ok(item) : Results.NotFound()).AddEndpointFilter<QuantityLimitInput>();
    public Task<OrderDetailsView?> GetDetails(string id) => store.Details(id);
    public void MapSubmit(WebApplication app) => app.MapPost("/orders/{id}/submit", async (string id) =>
        await store.Submit(id) switch
        {
            null => Results.NotFound(),
            SubmissionOutcome.Submitted => Results.Ok(new OrderSummary(id, "Submitted")),
            SubmissionOutcome.NotDraft => Results.Conflict(new ErrorResponse("OrderNotDraft")),
            _ => throw new InvalidOperationException("Unknown submission outcome.")
        });

    public async Task<Completion> Fulfill(string operationId, FulfillmentRequest request)
    {
        static Completion Reject(string outcome) => new("Rejected", outcome);
        var order = await store.Order(request.OrderId);
        if (order is null) return Reject("OrderMissing");
        var existing = await store.Reservation(request.OrderId);
        if (existing is not null)
            return existing.OrderId == request.OrderId && existing.Sku == request.Sku && existing.Quantity == request.Quantity && order.Status == OrderStatus.Submitted
                ? new("Submitted", "ReservedAndSubmitted") : Reject("ReservationConflict");
        if (await store.Inventory(request.Sku) is null) return Reject("InventoryMissing");
        var reserved = await store.Stock(request.Sku, request.Quantity, false, operationId + "/reserve");
        if (reserved == StockOutcome.InvalidQuantity) return Reject("InvalidQuantity");
        if (reserved == StockOutcome.QuantityLimitExceeded) return Reject("QuantityLimitExceeded");
        if (reserved == StockOutcome.InsufficientStock) return Reject("InsufficientStock");
        if (reserved != StockOutcome.Reserved) throw new InvalidOperationException("Unknown reserve outcome.");
        var submitted = await store.Submit(request.OrderId, operationId + "/submit");
        if (submitted == SubmissionOutcome.Submitted)
        {
            await store.CreateReservation(new(request.OrderId, request.OrderId, request.Sku, request.Quantity), operationId + "/reservation");
            return new("Submitted", "ReservedAndSubmitted");
        }
        await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");
        return Reject("OrderRejected");
    }
}

public static class HostSetup
{
    public static void Configure(IServiceCollection services) { }
    public static void Configure(WebApplication app) { }
}
