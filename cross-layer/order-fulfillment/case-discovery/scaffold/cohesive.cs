using Cohesive.Transitions.Execution;
using Fulfillment.Application;

internal static class Adapter
{
    static readonly FulfillmentDomain Domain = new();
    static readonly OfflineTransition<Order, Cohesive.Prelude.Unit, bool> ShipOrder =
        OfflineTransition.Prepare(Domain.OrderTransitions.Ship);

    public static Observed Ship(OrderStatus status, bool hold)
    {
        var before = new Order("order-A", "partition-A", status, hold);
        var result = ShipOrder.Execute(before, new("ship-case"));
        if (result.Decision.IsAccepted != result.Outcome)
            throw new InvalidOperationException("Inconsistent acceptance and typed outcome");
        return new(result.Decision.IsAccepted, result.State.Status, result.State.Id, result.State.ShippingHold);
    }
}
