using System.Text.Json;
using Fulfillment.Application;

var inputs = JsonSerializer.Deserialize<AuditInput[]>(File.ReadAllText(args[0]))!;
var rows = inputs.Select(input =>
{
    var before = new InventoryItem("audit", input.Available, input.MaxPerOrder, input.Quarantined);
    var (after, outcome) = InventoryRules.Reserve(before, input.Quantity);
    return new { input.Name, Outcome = outcome.ToString(), After = after.Available,
        Unchanged = after == before };
});
Console.WriteLine(JsonSerializer.Serialize(new { rows }));
