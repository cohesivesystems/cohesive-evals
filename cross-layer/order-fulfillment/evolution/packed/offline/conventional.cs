using System.Text.Json;
using Fulfillment.Application;

var rows = from state in Enum.GetValues<OrderStatus>()
           from trigger in Enum.GetValues<OrderCommand>()
           let result = new Order("probe", state).Apply(trigger)
           select new { state = state.ToString(), command = trigger.ToString().ToLowerInvariant(), destination = result?.Status.ToString() };
Console.WriteLine(JsonSerializer.Serialize(rows));
