using System.Globalization;
using Cohesive.Execution;
using Cohesive.Prelude;
using Cohesive.Transitions.Execution;
using Fulfillment.Application;

internal static class Submission
{
    private static readonly OrderTransitions Transitions = new FulfillmentDomain().OrderTransitions;
    private static readonly OfflineTransition<Order, Unit, bool> Pack = OfflineTransition.Prepare(Transitions.Pack);
    private static readonly OfflineTransition<Order, Unit, bool> Unpack = OfflineTransition.Prepare(Transitions.Unpack);
    private static readonly OfflineTransition<Order, HoldSetting, bool> ChangeHold = OfflineTransition.Prepare(Transitions.ChangeHold);
    private static readonly OfflineTransition<Order, ShipQuantity, bool> Ship = OfflineTransition.Prepare(Transitions.Ship);

    public static string[][] Propose() =>
    [
        ["Pack", "Ship:1", "Hold", "Ship:2", "Release", "Ship:2", "Hold", "Release"],
        ["Pack", "Hold", "Hold", "Unpack", "Release", "Pack", "Ship:1", "Release"],
        ["Ship:1", "Hold", "Release", "Unpack", "Pack", "Ship:-1", "Ship:0", "Ship:4"],
        ["Pack", "Pack", "Ship:2", "Ship:2", "Ship:1", "Pack", "Unpack", "Ship:1"]
    ];

    public static IEnumerable<Seen> Execute(string[] commands)
    {
        var order = new Order("order-A", "partition-A", OrderStatus.Submitted, false, 3);
        for (var index = 0; index < commands.Length; index++)
        {
            var command = commands[index];
            var activation = new ActivationId($"step-{index}");
            var result = command switch
            {
                "Pack" => Pack.Execute(order, activation),
                "Unpack" => Unpack.Execute(order, activation),
                "Hold" => ChangeHold.Execute(order, new HoldSetting(true), activation),
                "Release" => ChangeHold.Execute(order, new HoldSetting(false), activation),
                _ when command.StartsWith("Ship:", StringComparison.Ordinal) =>
                    Ship.Execute(order, new ShipQuantity(int.Parse(command.AsSpan(5), CultureInfo.InvariantCulture)), activation),
                _ => throw new ArgumentException($"Unknown command '{command}'.", nameof(commands))
            };
            order = result.State;
            yield return new Seen(result.Outcome, order.Status.ToString(), order.Id, order.ShippingHold, order.Remaining);
        }
    }
}
