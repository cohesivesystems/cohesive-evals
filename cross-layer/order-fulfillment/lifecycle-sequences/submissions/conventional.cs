using System.Globalization;
using Fulfillment.Application;

internal static class Submission
{
    public static string[][] Propose() =>
    [
        ["Pack", "Ship:1", "Hold", "Ship:2", "Release", "Ship:2", "Unpack", "Ship:1"],
        ["Hold", "Release", "Ship:1", "Pack", "Ship:3", "Pack", "Hold", "Release"],
        ["Pack", "Hold", "Hold", "Pack", "Unpack", "Unpack", "Pack", "Ship:1"],
        ["Pack", "Release", "Ship:0", "Ship:-1", "Ship:4", "Ship:2", "Ship:2", "Ship:1"]
    ];

    public static IEnumerable<Seen> Execute(string[] commands)
    {
        var order = new Order("order-A", OrderStatus.Submitted, ShippingHold: false, Remaining: 3);
        foreach (var command in commands)
        {
            var parts = command.Split(':', 2);
            var trigger = Enum.Parse<OrderCommand>(parts[0]);
            var quantity = parts.Length == 2 ? int.Parse(parts[1], CultureInfo.InvariantCulture) : 1;
            var result = order.Apply(trigger, quantity);
            order = result ?? order;
            yield return new Seen(result is not null, order.Status.ToString(), order.Id, order.ShippingHold, order.Remaining);
        }
    }
}
