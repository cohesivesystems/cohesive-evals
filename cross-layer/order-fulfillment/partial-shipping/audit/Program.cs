using System.Text.Json;
using Cohesive.Transitions.Assurance;
using Fulfillment.Application;

var probe = TransitionAssurance.Prepare(new FulfillmentDomain().OrderTransitions.Ship);
probe.EnsureGenerationSupported();
var template = new Order("order-A", "partition-A", OrderStatus.Packed, false, 4);
var seed = new ShipQuantity(1);
StateCaseOptions<Order> Options(int budget) =>
    new StateCaseOptions<Order> { MaxCases = budget }.Range(order => order.Remaining, 1, 4);

string? budgetError = null;
try { probe.GenerateCases(template, seed, Options(8)); }
catch (InvalidOperationException e) { budgetError = e.Message; }

var groups = probe.GenerateCases(template, seed, Options(1024));
var pairs = groups.SelectMany(group => group.Commands.Inputs.Select(command =>
    (group.State, command.Quantity))).ToArray();
Console.WriteLine(JsonSerializer.Serialize(new {
    directBudget = 8, budgetError, explorationBudget = 1024, stateCount = groups.Length,
    pairCount = pairs.Length, inDomain = pairs.Count(pair => pair.Quantity is >= -1 and <= 5),
    containsClearLastUnit = pairs.Any(pair => pair.State.Status == OrderStatus.Packed && !pair.State.ShippingHold
        && pair.State.Remaining == 1 && pair.Quantity == 1)
}));
