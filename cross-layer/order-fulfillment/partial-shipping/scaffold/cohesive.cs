using Cohesive.Transitions.Execution;
using Fulfillment.Application;

internal static class Adapter
{
    static readonly FulfillmentDomain Domain = new();
    static readonly OfflineTransition<Order, ShipQuantity, bool> Transition =
        OfflineTransition.Prepare(Domain.OrderTransitions.Ship);

    public static Observed Ship(Input input)
    {
        var before = new Order("order-A", "partition-A", input.Status, input.Hold, input.Remaining);
        var result = Transition.Execute(before, new(input.Quantity), new("ship-case"));
        if (result.Outcome != result.Decision.IsAccepted)
            throw new InvalidOperationException("Decision and outcome disagree");
        var after = result.State;
        return new(result.Outcome, after.Status, after.Id, after.ShippingHold, after.Remaining);
    }
}
