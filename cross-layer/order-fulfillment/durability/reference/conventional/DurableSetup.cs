using Microsoft.DurableTask;
using Microsoft.DurableTask.Client;
using Microsoft.DurableTask.Worker;
using Microsoft.DurableTask.Client.AzureManaged;
using Microsoft.DurableTask.Worker.AzureManaged;
namespace Fulfillment.Application;
public static class DurableSetup
{
    public static void Configure(IServiceCollection services)
    {
        var connection = Environment.GetEnvironmentVariable("DURABLE_TASK_CONNECTION") ?? throw new InvalidOperationException("Missing scheduler connection.");
        services.AddDurableTaskWorker(worker => {
            worker.AddTasks(tasks => { tasks.AddOrchestrator<FulfillmentWorkflow>(nameof(FulfillmentWorkflow));
                tasks.AddActivity<ReadOrder>(nameof(ReadOrder)); tasks.AddActivity<ReadReservation>(nameof(ReadReservation));
                tasks.AddActivity<ReadInventory>(nameof(ReadInventory)); tasks.AddActivity<ReserveStock>(nameof(ReserveStock));
                tasks.AddActivity<SubmitOrder>(nameof(SubmitOrder)); tasks.AddActivity<CreateReservation>(nameof(CreateReservation));
                tasks.AddActivity<ReleaseStock>(nameof(ReleaseStock)); });
            worker.UseDurableTaskScheduler(connection);
        });
        services.AddDurableTaskClient(client => client.UseDurableTaskScheduler(connection));
    }
}
