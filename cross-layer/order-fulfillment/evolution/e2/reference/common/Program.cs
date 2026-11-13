using Fulfillment.Application;
using Npgsql;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);
var connection = builder.Configuration.GetConnectionString("Orders")
    ?? throw new InvalidOperationException("Set ConnectionStrings__Orders to a dedicated PostgreSQL database.");
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.Converters.Add(new JsonStringEnumConverter());
    options.SerializerOptions.RespectRequiredConstructorParameters = true;
});
builder.Services.AddSingleton(_ => NpgsqlDataSource.Create(connection));
builder.Services.AddSingleton<IFulfillmentBackend, FulfillmentBackend>();
builder.Services.AddSingleton<OperationQueue>();
builder.Services.AddHostedService(provider => provider.GetRequiredService<OperationQueue>());
HostSetup.Configure(builder.Services);
var app = builder.Build();
await app.Services.GetRequiredService<IFulfillmentBackend>().Initialize();
if (builder.Configuration["seed"] is { } seedFile)
{
    if (Environment.GetEnvironmentVariable("FULFILLMENT_SETUP") != "1")
        throw new InvalidOperationException("Seeding requires FULFILLMENT_SETUP=1 and a dedicated database.");
    var data = System.Text.Json.JsonSerializer.Deserialize<SeedData>(await File.ReadAllTextAsync(seedFile),
        new System.Text.Json.JsonSerializerOptions(System.Text.Json.JsonSerializerDefaults.Web))
        ?? throw new InvalidOperationException("Missing seed data.");
    data.Validate();
    await app.Services.GetRequiredService<IFulfillmentBackend>().Seed(data);
    await app.DisposeAsync();
    return;
}
HostSetup.Configure(app);
// The local fixture has one host-provided identity/scope. It exposes no seed,
// reset or arbitrary SQL route, and never derives identity from request JSON.
app.MapPost("/orders", async (IFulfillmentBackend backend) =>
{
    var created = await backend.CreateOrder();
    return Results.Created($"/orders/{created.Id}", created);
});
app.MapGet("/orders/{id}", async (string id, IFulfillmentBackend backend) =>
    await backend.GetOrder(id) is { } order ? Results.Ok(order) : Results.NotFound());
app.MapGet("/inventory/{sku}", async (string sku, IFulfillmentBackend backend) =>
    await backend.GetInventory(sku) is { } item ? Results.Ok(item) : Results.NotFound());
app.MapGet("/orders/{id}/details", async (string id, IFulfillmentBackend backend) =>
    await backend.GetDetails(id) is { } details ? ReadResults.Reply(details, details.Reservations.Count) : Results.NotFound());
app.MapGet("/orders/{id}/availability", async (string id, IFulfillmentBackend backend) =>
    await backend.GetDetails(id) is { } details
        ? ReadResults.Reply(details.Reservations.Select(r => new AvailabilityView(r.Id, r.Sku, r.Quantity, r.AvailableStock)).ToArray(), details.Reservations.Count)
        : Results.NotFound());
app.MapPost("/fulfillment", (FulfillmentRequest request, OperationQueue queue) => queue.Admit(request));
app.MapGet("/fulfillment/results/{operationId}", (string operationId, OperationQueue queue) => queue.Result(operationId));
app.Services.GetRequiredService<IFulfillmentBackend>().MapSubmit(app);
app.Services.GetRequiredService<IFulfillmentBackend>().MapInventoryLimits(app);
app.Services.GetRequiredService<IFulfillmentBackend>().MapCancel(app);
await app.RunAsync();
