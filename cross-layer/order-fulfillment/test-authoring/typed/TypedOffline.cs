using Cohesive.Prelude;
using Cohesive.Transitions.Execution;
using Fulfillment.Application;

// Post-session counterpart to Offline(). Decide, the wire tests and the
// assertion scaffold come directly from the hash-checked frozen submission.
internal static partial class Program
{
    private static void TypedOffline()
    {
        var transitions = new FulfillmentDomain().OrderTransitions;
        var pack = OfflineTransition.Prepare(transitions.Pack);
        var unpack = OfflineTransition.Prepare(transitions.Unpack);
        var submit = OfflineTransition.Prepare(transitions.Submit);
        var cancel = OfflineTransition.Prepare(transitions.Cancel);

        foreach (var state in States)
        {
            var before = new Order("case-Sensitive/ß", "partition-X", Enum.Parse<OrderStatus>(state));
            Verify("pack", pack, (label, expected, outcome) =>
                Check.Equal(label + "/outcome", expected.Http == 200, outcome));
            Verify("unpack", unpack, (label, expected, outcome) =>
                Check.Equal(label + "/outcome", expected.Http == 200, outcome));
            Verify("submit", submit, (label, expected, outcome) =>
            {
                var expectedOutcome = expected.Code == "OrderNotDraft" ? "NotDraft" : expected.Code ?? "Submitted";
                Check.Equal(label + "/outcome", expectedOutcome, outcome.Outcome.ToString());
                Check.Equal(label + "/reported-state", expected.Status, outcome.Status.ToString());
                Check.Equal(label + "/process-outcome", state switch {
                    "Draft" => "ReservedAndSubmitted", "Cancelled" => "OrderCancelled", _ => "OrderRejected"
                }, outcome.FulfillmentOutcome.ToString());
            });
            Verify("cancel", cancel, (label, expected, outcome) =>
                Check.Equal(label + "/outcome", expected.Http == 200 ? "Cancelled" : "NotCancellable", outcome.ToString()));

            void Verify<T>(string command, OfflineTransition<Order, Unit, T> runner, Action<string, Expected, T> checkOutcome)
            {
                var label = $"offline/{state}/{command}";
                var expected = Decide(state, command);
                var result = runner.Execute(before, new(label));
                Check.Equal(label + "/accepted", expected.Http == 200, result.Decision.IsAccepted);
                Check.Equal(label + "/state", expected.Status, result.State.Status.ToString());
                Check.Equal(label + "/id", before.Id, result.State.Id);
                Check.Equal(label + "/partition", before.Partition, result.State.Partition);
                checkOutcome(label, expected, result.Outcome);
            }
        }
    }
}
