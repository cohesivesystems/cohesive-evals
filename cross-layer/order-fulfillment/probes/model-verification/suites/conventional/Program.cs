using System.Text.Json;
using Fulfillment.Application;

var cases = JsonSerializer.Deserialize<Case[]>(File.ReadAllText(args[0]))!;
var results = cases.Select(c =>
{
    var (state, outcome) = InventoryRules.Reserve(new(c.Sku, c.Available, c.MaxPerOrder, c.Quarantined), c.Quantity);
    var terminal = outcome == StockOutcome.Reserved ? "ReservedAndSubmitted" : FulfillmentResults.FromStock(outcome).Outcome;
    return new Result(c.Name, outcome.ToString(), terminal,
        new(state.Sku, state.Available, state.MaxPerOrder, state.Quarantined), true);
});
Console.WriteLine(JsonSerializer.Serialize(results));
