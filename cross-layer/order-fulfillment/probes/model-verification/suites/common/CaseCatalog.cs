/// <summary>Scenario-owned bounds, template and independent requirement examples.</summary>
public static class CaseCatalog
{
    public const int MinimumStock = 0, MinimumLimit = 1, Maximum = int.MaxValue;
    public static readonly State Template = new("stock-😀", 4, 4, false);

    public static Case[] Freeze(IEnumerable<(State State, int Quantity)> proposals)
    {
        // These witnesses survive even if a defective generator loses the corresponding guard.
        (State State, int Quantity)[] required = [(Template, 0), (Template with { Quarantined = true }, 1)];
        return proposals.Concat(required).Distinct()
            .OrderBy(p => p.State.Available).ThenBy(p => p.State.MaxPerOrder)
            .ThenBy(p => p.State.Quarantined).ThenBy(p => p.Quantity)
            .Select((p, i) => new Case("case-" + i, p.State.Sku, p.State.Available,
                p.State.MaxPerOrder, p.State.Quarantined, p.Quantity)).ToArray();
    }
}
