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

var request = JsonSerializer.Deserialize<ReplayRequest>(Console.In.ReadToEnd())!;
lifecycle.RequireScenario(request.Required);
var seed = new Order("order-A", "partition-A", OrderStatus.Submitted, false, 3);
var options = new SequenceSelectionOptions { MaxSequences = 4, MaxStepsPerSequence = 8 };

if (args.Contains("--measure"))
{
    foreach (var settings in new[] { options, options with { BeamWidth = 128, MaxStepsPerSequence = 16 } })
    {
        lifecycle.SelectSequences(seed, settings); // Warm compilation and model caches.
        for (var run = 0; run < 5; run++)
        {
            long before = GC.GetAllocatedBytesForCurrentThread();
            long start = System.Diagnostics.Stopwatch.GetTimestamp();
            var measured = lifecycle.SelectSequences(seed, settings);
            var elapsed = System.Diagnostics.Stopwatch.GetElapsedTime(start);
            long allocated = GC.GetAllocatedBytesForCurrentThread() - before;
            Console.WriteLine(JsonSerializer.Serialize(new { run, settings.BeamWidth, settings.MaxStepsPerSequence,
                measured.CandidateCount, elapsed.TotalMilliseconds, allocated }));
        }
    }
    return;
}

var suite = lifecycle.SelectSequences(seed, options);
var sequences = suite.Sequences.Select(s => s.Commands.ToArray()).ToArray();
var paths = request.Qualification.Concat(sequences).ToArray();
var traces = paths.Select(path => lifecycle.ExecuteSequence(seed, path).Select(step =>
    new { Accepted = step.IsAccepted, Status = step.State.Status.ToString(), step.State.Id,
        Hold = step.State.ShippingHold, step.State.Remaining }));
Console.WriteLine(JsonSerializer.Serialize(new {
    sequences, traces, suite.CandidateCount, suite.SearchTruncated,
    coveredGoals = suite.Sequences.SelectMany(s => s.CoveredGoals).Distinct().Count(),
    uncoveredObservedGoals = suite.UncoveredGoals.Length
}));

internal sealed record ReplayRequest(string[] Required, string[][] Qualification);
