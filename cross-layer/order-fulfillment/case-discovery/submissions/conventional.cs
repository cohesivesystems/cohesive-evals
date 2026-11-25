using Fulfillment.Application;

internal static class Cases
{
    public static (OrderStatus Status, bool Hold)[] Propose()
    {
        return (from status in Enum.GetValues<OrderStatus>()
                from hold in new[] { false, true }
                select (status, hold)).ToArray();
    }
}
