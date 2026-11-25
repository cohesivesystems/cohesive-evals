using Fulfillment.Application;

internal static class Adapter
{
    public static Observed Ship(Input input)
    {
        var before = new Order("order-A", input.Status, input.Hold, input.Remaining);
        var next = before.Apply(OrderCommand.Ship, input.Quantity);
        var after = next ?? before;
        return new(next is not null, after.Status, after.Id, after.ShippingHold, after.Remaining);
    }
}
