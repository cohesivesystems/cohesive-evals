using Cohesive.Api.Execution.Services;
using Cohesive.Execution;
using Cohesive.Model;
using Cohesive.Storage;

namespace Fulfillment.Application;

// The pinned SDK exposes this lookup only inside Bind. Share the same exact-contract
// lookup and diagnostic codes between our ephemeral binding and durable preparation.
public static class RepositoryBindings
{
    public static Func<ValueContract, IEntityRepository> Resolve(params IEntityRepository[] repositories)
    {
        var selected = new Dictionary<ValueContract, IEntityRepository>();
        foreach (var repository in repositories)
        {
            ArgumentNullException.ThrowIfNull(repository);
            if (!selected.TryAdd(ValueContract.FromShape(repository.EntityDefinition.Shape), repository))
                throw Error(ServiceBindingDiagnosticCodes.RepositoryAmbiguous, "Multiple repositories claim the same entity observation.");
        }
        return observation => selected.TryGetValue(observation, out var repository)
            ? repository : throw Error(ServiceBindingDiagnosticCodes.RepositoryMissing, "No repository supplies the required entity observation.");
    }

    static ServiceBindingValidationException Error(string code, string message) =>
        new(new([new(code, DiagnosticSeverity.Error, message, "/bindings/repositories")]));
}
