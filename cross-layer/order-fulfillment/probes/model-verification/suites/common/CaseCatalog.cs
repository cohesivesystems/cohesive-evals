/// <summary>Shared experimental state envelope; contains no expected business outcomes.</summary>
public static class CaseCatalog
{
    /// <summary>Expand each supplied state's proposed quantities into stable, matched case records.</summary>
    public static Case[] Generate(Func<State, IEnumerable<int>> propose)
    {
        List<Case> cases = [];
        foreach (var available in new[] { 0, 1, 4, 7, int.MaxValue })
        foreach (var limit in new[] { 1, 4, 7, int.MaxValue })
        foreach (var quarantined in new[] { false, true })
        {
            var state = new State("stock-😀", available, limit, quarantined);
            // Independent baseline inputs survive missing model guards.
            int[] baseline = [int.MinValue, -1, 0, 1, int.MaxValue];
            foreach (var quantity in propose(state).Concat(baseline).Distinct().Order())
                cases.Add(new("case-" + cases.Count, state.Sku, available, limit, quarantined, quantity));
        }
        return [.. cases];
    }
}
