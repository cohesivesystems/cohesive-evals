namespace Fulfillment.Application;

public enum OrderStatus { Draft, Submitted }
public sealed record Order(string Id, OrderStatus Status);
public sealed record InventoryItem(string Sku, int Available, int MaxPerOrder = int.MaxValue);
public sealed record Reservation(string Id, string OrderId, string Sku, int Quantity);
public enum SubmissionOutcome { Submitted, NotDraft }
public enum StockOutcome { Reserved, Released, InvalidQuantity, QuantityLimitExceeded, InsufficientStock }

public static class OrderRules
{
    public static (Order State, SubmissionOutcome Outcome) Submit(Order order) =>
        order.Status == OrderStatus.Draft
            ? (order with { Status = OrderStatus.Submitted }, SubmissionOutcome.Submitted)
            : (order, SubmissionOutcome.NotDraft);
}

public static class InventoryRules
{
    public static (InventoryItem State, StockOutcome Outcome) Reserve(InventoryItem item, int quantity) =>
        quantity <= 0 ? (item, StockOutcome.InvalidQuantity)
        : quantity > item.MaxPerOrder ? (item, StockOutcome.QuantityLimitExceeded)
        : item.Available < quantity ? (item, StockOutcome.InsufficientStock)
        : (item with { Available = item.Available - quantity }, StockOutcome.Reserved);
    public static InventoryItem Release(InventoryItem item, int quantity) => quantity > 0
        ? item with { Available = checked(item.Available + quantity) }
        : throw new ArgumentOutOfRangeException(nameof(quantity));
}
