using System.Text.Json;
using Cohesive.Machines;
using Cohesive.Model;
using Cohesive.Transitions.Compilation;
using Cohesive.Execution;
using Cohesive.Transitions.Execution;
using Cohesive.Prelude;
using Fulfillment.Application;

var domain = new FulfillmentDomain();
if (args is ["--coverage-control"])
{
    var bypass = domain.Orders.Transition<bool>(new("control/pack-without-movement"), new("1"), t => t
        .Set(order => order.Status, OrderStatus.Packed)
        .Return(true));
    var compilation = TransitionStaticCompiler.Compile(bypass.Document);
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        accepted = compilation.IsSuccessful,
        diagnostics = compilation.Validation.Diagnostics.Select(d => d.Code)
    }));
    return;
}

if (args is ["--pack-movements"])
{
    var compilation = TransitionStaticCompiler.Compile(domain.OrderTransitions.Pack.Document);
    var plan = compilation.Plan ?? throw new InvalidOperationException(string.Join("; ", compilation.Validation.Diagnostics));
    var results = new[] { OrderStatus.Submitted, OrderStatus.Packed }.Select(status =>
    {
        var decision = TransitionReferenceInterpreter.DecideFullState(plan, new("verify-pack"),
            PortableValue.Concrete(plan.Definition.Input, ObservationValue.FromObject(Unit.Value)),
            PortableValue.Concrete(plan.Definition.Observation, ObservationValue.FromObject(new Order("probe", "local", status))));
        return new { state = status.ToString(), edge = decision.MachineMovements.Single().Edge.Value };
    });
    Console.WriteLine(JsonSerializer.Serialize(results));
    return;
}

var document = domain.Orders.Definition.Machine!.Machine;
var graph = MachineDefinition.Deserialize(ExecutionDefinitionJsonSerializer.Serialize(document));
var actions = graph.Edges.Select(edge => edge.Action).Distinct().Order();
var rows = from state in graph.States
           from command in actions
           select new { state, command, destination = graph.Decide(state, command)?.To };
Console.WriteLine(JsonSerializer.Serialize(rows));
