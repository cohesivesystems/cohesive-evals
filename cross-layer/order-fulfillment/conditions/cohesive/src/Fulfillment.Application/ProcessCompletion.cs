using Cohesive.Execution;
using Cohesive.Model;

namespace Fulfillment.Application;

public static class ProcessCompletion
{
    public static Completion Read(ExecutionTerminalOutcome? terminal)
    {
        var output = terminal?.Detail?.Value?.Value
            ?? throw new InvalidOperationException("Process returned no public result.");
        return new(output.GetProperty("Status").GetRequiredString(), output.GetProperty("Outcome").GetRequiredString());
    }
}
