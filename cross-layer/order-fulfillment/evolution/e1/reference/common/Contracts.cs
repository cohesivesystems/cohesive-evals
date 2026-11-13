namespace Fulfillment.Application;

public sealed record OrderSummary(string Id, string Status);
public sealed record OrderCreated(string Id);
public sealed record ReservationView(string Id, string Sku, int Quantity, int AvailableStock);
public sealed record OrderDetailsView(string Id, string Status, IReadOnlyList<ReservationView> Reservations);
public sealed record AvailabilityView(string ReservationId, string Sku, int Quantity, int AvailableStock);
public sealed record InventoryView(string Sku, int Available, int MaxPerOrder);
public sealed record FulfillmentRequest(string RequestId, string OrderId, string Sku, int Quantity);
public sealed record Completion(string Status, string Outcome);
public sealed record Admission(string OperationId, string ResultUrl);
public sealed record ErrorResponse(string Code);

public interface IFulfillmentBackend
{
    Task Initialize();
    Task Seed(SeedData data);
    Task<OrderCreated> CreateOrder();
    Task<OrderSummary?> GetOrder(string id);
    Task<InventoryView?> GetInventory(string sku);
    Task<OrderDetailsView?> GetDetails(string id);
    Task<Completion> Fulfill(string operationId, FulfillmentRequest request);
    void MapSubmit(WebApplication app);
    void MapInventoryLimits(WebApplication app);
}

public sealed record SeedOrder(string Id, string Status);
public sealed record SeedInventory(string Sku, int Available, int MaxPerOrder = int.MaxValue);
public sealed record SeedReservation(string Id, string OrderId, string Sku, int Quantity);
public sealed record SeedData(SeedOrder[] Orders, SeedInventory[] Inventory, SeedReservation[] Reservations)
{
    public void Validate()
    {
        if (Orders is null || Inventory is null || Reservations is null
            || Orders.Any(x => string.IsNullOrWhiteSpace(x.Id) || x.Status is not ("Draft" or "Submitted"))
            || Inventory.Any(x => string.IsNullOrWhiteSpace(x.Sku) || x.Available < 0 || x.MaxPerOrder <= 0)
            || Reservations.Any(x => string.IsNullOrWhiteSpace(x.Id) || string.IsNullOrWhiteSpace(x.OrderId) || string.IsNullOrWhiteSpace(x.Sku) || x.Quantity <= 0))
            throw new ArgumentException("Invalid seed data.");
    }
}
