using System.Text.Json;
using Cohesive.Execution;
using Cohesive.Model.Serialization;
using Cohesive.Transitions.Assurance;
using Fulfillment.Application;

var domain = new FulfillmentDomain();
var transition = domain.InventoryTransitions.Reserve;
var probe = TransitionAssurance.Prepare(transition);
if (args[0] == "--describe")
{
    Console.WriteLine(ExecutionDefinitionJsonSerializer.Serialize(transition.Document));
    return;
}
if (args[0] == "--unsupported-control")
{
    // An authored compound guard must be refused, even when an earlier guard could reject.
    var unsupported = domain.Inventory.Transition<StockQuantity, bool>(
        new("audit/compound"), new("1"), t => t
            .Requires((s, input) => input.Quantity > 0 && input.Quantity < 10, (_, _) => false)
            .Return(true));
    try
    {
        TransitionAssurance.Prepare(unsupported).GenerateInputs(new("control", "local", 7, 4, false), new(0));
        throw new InvalidOperationException("Unsupported generator control unexpectedly succeeded.");
    }
    catch (NotSupportedException error)
    {
        Console.WriteLine(JsonSerializer.Serialize(new { kind = "unsupported", detail = error.Message }));
    }
    return;
}
if (args[0] == "--generate")
{
    var nodes = new SortedSet<string>(StringComparer.Ordinal);
    var generated = CaseCatalog.Generate(state =>
    {
        var proposals = probe.GenerateInputs(new(state.Sku, "local", state.Available, state.MaxPerOrder, state.Quarantined), new(0));
        foreach (var node in proposals.InspectedNodes) nodes.Add(node.Value);
        return proposals.Inputs.Select(input => input.Quantity);
    });
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        cases = generated,
        generationCoverage = nodes,
        modelReference = new
        {
            definitionId = probe.Reference.DefinitionId.Value,
            revisionId = probe.Reference.RevisionId.Value,
            fingerprint = new
            {
                algorithm = probe.Reference.Fingerprint.Algorithm,
                canonicalization = probe.Reference.Fingerprint.Canonicalization,
                value = probe.Reference.Fingerprint.Value
            }
        }
    }));
    return;
}

var cases = JsonSerializer.Deserialize<Case[]>(File.ReadAllText(args[0]))!;
var results = cases.Select(c =>
{
    var result = probe.Execute(new(c.Sku, "local", c.Available, c.MaxPerOrder, c.Quarantined),
        new StockQuantity(c.Quantity), new(c.Name));
    var state = result.State;
    return new Result(c.Name, result.Outcome.Outcome.ToString(), result.Outcome.FulfillmentOutcome.ToString(),
        new(state.Sku, state.Available, state.MaxPerOrder, state.Quarantined), state.Partition == "local");
});
Console.WriteLine(JsonSerializer.Serialize(results));
