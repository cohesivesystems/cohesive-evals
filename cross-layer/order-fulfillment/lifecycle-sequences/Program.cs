using System.Text.Json;

var sequences = args.Length == 0
    ? Submission.Propose()
    : JsonSerializer.Deserialize<string[][]>(Console.In.ReadToEnd())!;
var traces = sequences.Select(commands => Submission.Execute(commands).ToArray()).ToArray();
Console.WriteLine(JsonSerializer.Serialize(new { sequences, traces }));

public sealed record Seen(bool Accepted, string Status, string Id, bool Hold, int Remaining);
