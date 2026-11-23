using System.Text.Json;
using Cohesive.Machines;
using Cohesive.Transitions.Compilation;
using Cohesive.Execution;
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

var document = domain.Orders.Definition.Machine!.Machine;
var graph = MachineDefinition.Deserialize(ExecutionDefinitionJsonSerializer.Serialize(document));
var actions = graph.Edges.Select(edge => edge.Action).Distinct().Order();
var rows = from state in graph.States
           from command in actions
           select new { state, command, destination = graph.Decide(state, command)?.To };
Console.WriteLine(JsonSerializer.Serialize(rows));
