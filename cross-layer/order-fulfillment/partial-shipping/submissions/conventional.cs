using Fulfillment.Application;

internal static class Cases
{
    // Select representatives directly from the two Stateless Ship transitions.
    // The held cases exercise each guard with its quantity condition satisfied.
    public static Input[] Propose() =>
    [
        new(OrderStatus.Packed, false, 4, 3),
        new(OrderStatus.Packed, false, 1, 1),
        new(OrderStatus.Packed, true, 4, 3),
        new(OrderStatus.Packed, true, 1, 1),
        new(OrderStatus.Packed, false, 4, 0),
        new(OrderStatus.Packed, false, 4, -1),
        new(OrderStatus.Packed, false, 4, 5),
        new(OrderStatus.Submitted, false, 4, 3)
    ];
}
