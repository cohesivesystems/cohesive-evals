using Fulfillment.Application;

internal static class Adapter
{
    public static Observed Ship(OrderStatus status, bool hold)
    {
        var before = new Order("order-A", status, hold);
        var next = before.Apply(OrderCommand.Ship);
        var after = next ?? before;
        return new(next is not null, after.Status, after.Id, after.ShippingHold);
    }
}
