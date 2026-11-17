using System.Text.Json;
using Fulfillment.Application;

if (args[0] == "--generate")
{
    // Ordinary boundary testing: the developer identifies the policy's thresholds.
    var generated = CaseCatalog.Generate(state => Neighbors(0, state.Available, state.MaxPerOrder));
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
