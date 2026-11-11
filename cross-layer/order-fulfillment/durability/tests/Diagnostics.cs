using System.Reflection;
using Cohesive.Api.Execution.Services;
using Cohesive.Execution;
using Cohesive.Model;
using Cohesive.Storage;
using Fulfillment.Application;

static void Expect<T>(Action action, string message) where T : Exception
{
    try { action(); }
    catch (T error) when (error.Message.Contains(message)) { return; }
    throw new Exception($"Expected {typeof(T).Name}: {message}");
}
Expect<InvalidOperationException>(() => ProcessCompletion.Read(null), "Process returned no public result.");
Expect<InvalidOperationException>(() => ProcessCompletion.Read(ExecutionTerminalOutcome.None), "Process returned no public result.");
var repository = DispatchProxy.Create<IEntityRepository, RepositoryProxy>();
var contract = ValueContract.FromShape(new FulfillmentDomain().Orders.Definition.Shape);
Expect<ServiceBindingValidationException>(() => RepositoryBindings.Resolve()(contract), ServiceBindingDiagnosticCodes.RepositoryMissing);
Expect<ServiceBindingValidationException>(() => RepositoryBindings.Resolve(repository, repository), ServiceBindingDiagnosticCodes.RepositoryAmbiguous);
if (!ReferenceEquals(RepositoryBindings.Resolve(repository)(contract), repository))
    throw new Exception("Unique repository lookup did not preserve the selected repository.");
Console.WriteLine("Missing-result and repository diagnostics passed (5 checks).");

public class RepositoryProxy : DispatchProxy
{
    protected override object? Invoke(MethodInfo? method, object?[]? args) => method?.Name == "get_EntityDefinition"
        ? new FulfillmentDomain().Orders.Definition : throw new NotSupportedException(method?.Name);
}
