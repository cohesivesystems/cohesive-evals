using System.Text.Json;
using Cohesive.Transitions.Assurance;
using Fulfillment.Application;

var transitions = new FulfillmentDomain().OrderTransitions;
var lifecycle = TransitionAssurance.ForSequences<Order>()
    .Command("Pack", transitions.Pack)
    .Command("Unpack", transitions.Unpack)
    .Command("Hold", transitions.ChangeHold, new HoldSetting(true))
    .Command("Release", transitions.ChangeHold, new HoldSetting(false))
    .Commands(transitions.Ship, Enumerable.Range(-1, 6).Select(q => new ShipQuantity(q)),
        input => $"Ship:{input.Quantity}");

var required = JsonSerializer.Deserialize<string[]>(Console.In.ReadToEnd())!;
var suite = lifecycle.SelectSequences(new Order("order-A", "partition-A", OrderStatus.Submitted, false, 3),
    new() { MaxSequences = 4, MaxStepsPerSequence = 8, RequiredScenarios = [required] });

Console.WriteLine(JsonSerializer.Serialize(new {
    sequences = suite.Sequences.Select(s => s.Commands),
    suite.CandidatesExplored, suite.SearchTruncated,
    coveredGoals = suite.Sequences.SelectMany(s => s.CoveredGoals).Distinct().Count(),
    uncoveredObservedGoals = suite.UncoveredObservedGoals.Length
}));
