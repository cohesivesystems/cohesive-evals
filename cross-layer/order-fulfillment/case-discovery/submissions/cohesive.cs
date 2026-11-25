using Cohesive.Transitions.Assurance;
using Fulfillment.Application;

internal static class Cases
{
    public static (OrderStatus Status, bool Hold)[] Propose()
    {
        var domain = new FulfillmentDomain();
        var ship = TransitionAssurance.Prepare(domain.OrderTransitions.Ship);
        var cases = ship.GenerateCases(new Order("order-A", "partition-A"), default, new() { MaxCases = 10 });
        return cases.Select(group => (group.State.Status, group.State.ShippingHold)).ToArray();
    }
}
