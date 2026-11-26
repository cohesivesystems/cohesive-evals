using System.Text.Json;
using Cohesive.Transitions.Assurance;
using Fulfillment.Application;

var commands = new FulfillmentDomain().OrderTransitions;
var probe = TransitionAssurance.ForSequences<Order>()
    .Command("Pack", commands.Pack)
    .Command("Unpack", commands.Unpack)
    .Command("Hold", commands.ChangeHold, new HoldSetting(true))
    .Command("Release", commands.ChangeHold, new HoldSetting(false))
    .Commands(commands.Ship, Enumerable.Range(-1, 6).Select(q => new OrderQuantity(q)), q => $"Ship:{q.Quantity}");

var sequences = JsonSerializer.Deserialize<string[][]>(Console.In.ReadToEnd())!;
var seed = new Order("order-A", FulfillmentStoragePolicy.LocalPartition, OrderStatus.Submitted, false, 3);
var traces = sequences.Select(path => probe.ExecuteSequence(seed, path).Select(step =>
    new { Accepted = step.IsAccepted, Status = step.State.Status.ToString(), step.State.Id,
        Hold = step.State.ShippingHold, step.State.Remaining }));
Console.WriteLine(JsonSerializer.Serialize(new { sequences, traces }));
