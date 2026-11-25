using System.Text.Json;
using System.Text.Json.Serialization;
using Fulfillment.Application;

var json = new JsonSerializerOptions { Converters = { new JsonStringEnumConverter() } };
if (args is ["propose"])
{
    var inputs = Cases.Propose();
    Console.WriteLine(JsonSerializer.Serialize(inputs, json));
}
else if (args is ["execute"])
{
    var inputs = JsonSerializer.Deserialize<Input[]>(Console.In.ReadToEnd(), json)!;
    Console.WriteLine(JsonSerializer.Serialize(inputs.Select(Adapter.Ship), json));
}
else throw new ArgumentException("Expected propose or execute");

internal sealed record Input(OrderStatus Status, bool Hold, int Remaining, int Quantity);
internal sealed record Observed(bool Accepted, OrderStatus Status, string Id, bool Hold, int Remaining);
