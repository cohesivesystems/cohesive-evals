using Microsoft.DurableTask;
using Microsoft.DurableTask.Client;
using Microsoft.DurableTask.Worker;
using Microsoft.DurableTask.Client.AzureManaged;
using Microsoft.DurableTask.Worker.AzureManaged;
using Cohesive.Adapters.DurableTask;
using Cohesive.Processes.Execution;
namespace Fulfillment.Application;
public static class DurableSetup
{
    public static void Configure(IServiceCollection services)
    {
        var connection = Environment.GetEnvironmentVariable("DURABLE_TASK_CONNECTION") ?? throw new InvalidOperationException("Missing scheduler connection.");
        services.AddSingleton<IAsyncProcessReferenceHost, RecoveryHost>();
        services.AddDurableTaskWorker(worker => {
            worker.AddCohesiveSequentialProcesses(p => {
                var plan = p.GetRequiredService<FulfillmentBackend>().Prepared.Plan;
                RecoveryHost.Validate(plan);
                var compiled = DurableTaskProcessRealizationCompiler.CompileExecutable(plan);
                if (!compiled.IsSuccessful)
                    throw new InvalidOperationException("Durable process realization failed: " +
                        string.Join("; ", compiled.Realization.Diagnostics.Select(d => $"{d.Code}: {d.Message}")));
                return new DurableTaskSequentialProcessPlanCatalog([compiled.Plan!]);
            });
            worker.UseDurableTaskScheduler(connection);
        });
        services.AddDurableTaskClient(client => client.UseDurableTaskScheduler(connection));
    }
}
