using System.Text.Json;
using Fulfillment.Application;

if (args[0] == "--generate")
{
    // Ordinary boundary testing: the developer identifies the policy's thresholds.
    var seed = CaseCatalog.Template;
    var proposals = from stock in StateBoundaries(CaseCatalog.MinimumStock, seed.Available)
                    from limit in StateBoundaries(CaseCatalog.MinimumLimit, seed.MaxPerOrder)
                    from flag in new[] { false, true }
                    from quantity in Neighbors(0, stock, limit).Concat([int.MinValue, int.MaxValue])
                    select (seed with { Available = stock, MaxPerOrder = limit, Quarantined = flag }, quantity);
    var generated = CaseCatalog.Freeze(proposals);
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        cases = generated,
        generationCoverage = new[] { "policy-authored quantity, stock and limit boundaries" },
        modelReference = (object?)null
    }));
    return;
}

var cases = JsonSerializer.Deserialize<Case[]>(File.ReadAllText(args[0]))!;
var results = cases.Select(c =>
{
    var (state, outcome) = InventoryRules.Reserve(new(c.Sku, c.Available, c.MaxPerOrder, c.Quarantined), c.Quantity);
    var terminal = outcome == StockOutcome.Reserved ? "ReservedAndSubmitted" : FulfillmentResults.FromStock(outcome).Outcome;
    return new Result(c.Name, outcome.ToString(), terminal,
        new(state.Sku, state.Available, state.MaxPerOrder, state.Quarantined), true);
});
Console.WriteLine(JsonSerializer.Serialize(results));

// Widen before arithmetic so Int32 endpoints cannot wrap into misleading test inputs.
static IEnumerable<int> Neighbors(params int[] thresholds) =>
    thresholds.SelectMany(n => new[] { (long)n - 1, n, (long)n + 1 })
        .Where(n => n >= int.MinValue && n <= int.MaxValue).Select(n => (int)n);

static int[] StateBoundaries(int minimum, int seed) =>
    [minimum, minimum + 1, seed, CaseCatalog.Maximum - 1, CaseCatalog.Maximum];
