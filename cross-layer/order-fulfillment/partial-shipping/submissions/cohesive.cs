using Cohesive.Transitions.Assurance;
using Fulfillment.Application;

internal static class Cases
{
    public static Input[] Propose()
    {
        var probe = TransitionAssurance.Prepare(new FulfillmentDomain().OrderTransitions.Ship);
        var template = new Order("order-A", "partition-A", OrderStatus.Packed, false, 4);
        var domain = new StateCaseOptions<Order> { MaxCases = 1024 }.Range(o => o.Remaining, 1, 4);
        var groups = probe.GenerateCases(template, new ShipQuantity(1), domain);
        var pool = (from groupCases in groups
                    from command in groupCases.Commands.Inputs
                    where command.Quantity is >= -1 and <= 5
                    let o = groupCases.State
                    orderby o.Remaining descending, command.Quantity descending
                    select new Input(o.Status, o.ShippingHold, o.Remaining, command.Quantity)).ToArray();

        // Spend the budget on isolated contract boundaries. A three-unit partial
        // shipment distinguishes subtraction from decrementing by one.
        var packed = pool.Where(c => c.Status == OrderStatus.Packed && !c.Hold).ToArray();
        return [
            packed.Last(c => c.Quantity == c.Remaining && c.Remaining > 1),
            packed.First(c => c.Quantity == c.Remaining - 1 && c.Quantity > 1),
            packed.First(c => c.Quantity == 1 && c.Remaining == 3),
            packed.First(c => c.Quantity == 0),
            packed.First(c => c.Quantity == c.Remaining + 1),
            pool.First(c => c.Status == OrderStatus.Packed && c.Hold && c.Quantity == c.Remaining - 1),
            pool.First(c => c.Status == OrderStatus.Submitted && !c.Hold && c.Quantity == c.Remaining - 1),
            pool.First(c => c.Status == OrderStatus.Shipped && !c.Hold && c.Quantity == c.Remaining)
        ];
    }
}
