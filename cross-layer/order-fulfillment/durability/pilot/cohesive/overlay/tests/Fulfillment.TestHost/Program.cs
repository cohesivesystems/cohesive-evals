using Fulfillment.Application;
using Cohesive.Processes.Execution;
using Microsoft.DurableTask.Worker.Grpc;
using Grpc.Core.Interceptors;

await FulfillmentApp.Run(args, services =>
{
    if (EvaluationHooks.Enabled("after-admission-commit"))
        services.AddSingleton<IStartupFilter, HoldAdmissionResponse>();
    var registration = services.Single(s => s.ServiceType == typeof(IAsyncProcessReferenceHost));
    services.Remove(registration);
    services.AddSingleton<IAsyncProcessReferenceHost>(sp =>
        new EffectHooks((IAsyncProcessReferenceHost)registration.ImplementationFactory!(sp)));
    services.PostConfigureAll<GrpcDurableTaskWorkerOptions>(options =>
    {
        var channel = options.Channel ?? throw new InvalidOperationException("Missing scheduler channel.");
        options.CallInvoker = channel.Intercept(new SchedulerHooks());
        options.Channel = null;
    });
});

// Keep the HTTP caller unacknowledged while the scheduler-side post-commit
// barrier is active, even when another worker turn completes the start first.
internal sealed class HoldAdmissionResponse : IStartupFilter
{
    public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next) => app =>
    {
        app.Use(async (http, run) =>
        {
            if (HttpMethods.IsPost(http.Request.Method) && http.Request.Path == "/fulfillment")
                http.Response.OnStarting(() => Task.Delay(Timeout.InfiniteTimeSpan, http.RequestAborted));
            await run();
        });
        next(app);
    };
}
