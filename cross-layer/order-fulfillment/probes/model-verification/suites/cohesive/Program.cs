using System.Text.Json;
using Cohesive.Execution;
using Cohesive.Model;
using Cohesive.Model.Serialization;
using Cohesive.Transitions.Execution;
using Cohesive.Transitions.IR;
using Fulfillment.Application;

var transition = new FulfillmentDomain().InventoryTransitions.Reserve;
if (args[0] == "--describe")
{
    Console.WriteLine(ExecutionDefinitionJsonSerializer.Serialize(transition.Document));
    return;
}
var compilation = transition.Compile();
if (!compilation.IsSuccessful) throw new InvalidOperationException(string.Join(";", compilation.Validation.Diagnostics));
var plan = compilation.Plan!;
var cases = JsonSerializer.Deserialize<Case[]>(File.ReadAllText(args[0]))!;
var results = cases.Select(c =>
{
    var before = ObservationValue.FromObject(new InventoryItem(c.Sku, "local", c.Available, c.MaxPerOrder, c.Quarantined));
    var decision = TransitionReferenceInterpreter.DecideFullState(plan, new(c.Name),
        PortableValue.Concrete(plan.Definition.Input, ObservationValue.FromObject(new StockQuantity(c.Quantity))),
        PortableValue.Concrete(plan.Definition.Observation, before));
    if (decision.Kind is not (TransitionDecisionKind.Applied or TransitionDecisionKind.NoChange or TransitionDecisionKind.AdmissionRejected))
        throw new InvalidOperationException(decision.Kind.ToString());
    var state = TransitionStateProjector.Apply(before, decision).Deserialize<InventoryItem>()!;
    var outcome = (decision.Outcome?.Value ?? throw new InvalidOperationException("No typed outcome")).Deserialize<StockResult>()!;
    return new Result(c.Name, outcome.Outcome.ToString(), outcome.FulfillmentOutcome.ToString(),
        new(state.Sku, state.Available, state.MaxPerOrder, state.Quarantined), state.Partition == "local");
});
Console.WriteLine(JsonSerializer.Serialize(results));
