using System.Text.Json;
using System.Text.Json.Serialization;
using Cohesive.Transitions.Assurance;
using Fulfillment.Application;

var probe = TransitionAssurance.Prepare(new FulfillmentDomain().OrderTransitions.Ship);
var options = new CaseSelectionOptions<Order, ShipQuantity> { MaxCases = 8, MaxCandidates = 1024 }
    .StateRange(order => order.Remaining, 1, 4)
    .InputRange(command => command.Quantity, -1, 5);
var suite = probe.SelectCases(new Order("order-A", "partition-A", OrderStatus.Packed, false, 4),
    new ShipQuantity(1), options);

var evidence = new {
    suite.CandidateCount,
    Cases = suite.Cases.Select(c => new {
        Input = new { c.State.Status, Hold = c.State.ShippingHold, c.State.Remaining, c.Input.Quantity },
        c.CoveredGoals
    }),
#if DECISION_PAIRS
    Pairs = suite.DecisionPairs.Select(p => new { p.FirstCase, p.SecondCase, p.Scope, Field = p.Field.ToString(), p.FirstDecision, p.SecondDecision }),
#endif
    suite.UncoveredGoals
};
Console.WriteLine(JsonSerializer.Serialize(evidence, new JsonSerializerOptions {
    Converters = { new JsonStringEnumConverter() }
}));
