using Cohesive.Adapters.Postgres;
using Cohesive.Adapters.Postgres.Services;
using Cohesive.Adapters.Sql;
using Cohesive.Adapters.AspNet;
using Cohesive.Adapters.AspNet.Entities;
using Cohesive.Api;
using Cohesive.Api.Execution.Services;
using Cohesive.Execution;
using Cohesive.Prelude;
using Cohesive.Model;
using Cohesive.Identity;
using Cohesive.Storage;
using Microsoft.AspNetCore.Mvc;
using Npgsql;

namespace Fulfillment.Application;

public sealed class FulfillmentBackend(NpgsqlDataSource database) : IFulfillmentBackend
{
    readonly FulfillmentDomain domain = new();
    IEntityRepository<Order> orders = null!;
    IEntityRepository<InventoryItem> inventory = null!;
    IEntityRepository<Reservation> reservations = null!;
    PostgresQueryReader<string, OrderDetails?> details = null!;
    HostedServiceProcess<FulfillOrder, FulfillmentResult> hosted = null!;
    static OperationContext Context() => OperationContext.Create().WithIdentityContext(FulfillmentDemoIdentity.Context);

    public async Task Initialize()
    {
        var mappings = new FulfillmentPostgresMappings(domain);
        var bindings = PostgresPersistenceBindings.Define(new("orders"), storage =>
        {
            storage.Schema(PostgresSchemaInitialization.CreateIfMissing, schema =>
            {
                mappings.ConfigureOrderSchema(schema);
                schema.ForeignKey(domain.ReservationItem)
                    .Collation(domain.Inventory, item => item.Sku, "C")
                    .Check(domain.Inventory, item => item.Partition, SqlBinaryOperator.Equal, "local")
                    .Check(domain.Inventory, item => item.Available, SqlBinaryOperator.GreaterThanOrEqual, 0)
                    .Check(domain.Inventory, item => item.MaxPerOrder, SqlBinaryOperator.GreaterThan, 0);
            });
            storage.Entity(domain.Orders, mappings.Orders);
            storage.Entity(domain.Inventory, mappings.Inventory);
            storage.Entity(domain.Reservations, mappings.Reservations);
        });
        await bindings.PrepareSchemaAsync(database);
        var receipts = new PostgresTransitionReceiptOptions("public", "cohesive_process_receipts", "local");
        await using (var command = database.CreateCommand(receipts.SchemaSql)) await command.ExecuteNonQueryAsync();
        var receiptStorage = await receipts.BindAsync(database);
        var persistence = bindings.Bind(database, authority: "fulfillment");
        orders = persistence.Repository(domain.Orders, transitionReceipts: receiptStorage);
        inventory = persistence.Repository(domain.Inventory, transitionReceipts: receiptStorage);
        reservations = persistence.Repository(domain.Reservations, transitionReceipts: receiptStorage);
        // Public row/serialized-byte limits are enforced by shared ReadResults.
        // Adapter decoded-row limits must not reject an otherwise allowed response.
        details = persistence.Query(new FulfillmentQueries(domain).OrderDetails, maximumRows: int.MaxValue - 1, maximumBytes: long.MaxValue);
        var process = new FulfillmentProcess(domain);
        hosted = Service.Define(new("fulfillment"), new("1"), process.Provenance)
            .Use(new ServiceDependencies().Process(process))
            .Operation("fulfill").Require(new("fulfillment.write")).Run(process.Definition).ExecuteEphemerally(TimeSpan.FromSeconds(15))
            .Bind(process.Definition, RepositoryBindings.Resolve(orders, inventory, reservations))
            .Build("fulfillment", new IdentityServiceInvocationAuthorization("demo", new(FulfillmentDomain.PartitionField)));
    }
    public async Task Seed(SeedData data)
    {
        foreach (var order in data.Orders) await orders.Upsert(Context(), new Order(order.Id, "local", Enum.Parse<OrderStatus>(order.Status)));
        foreach (var item in data.Inventory) await inventory.Upsert(Context(), new InventoryItem(item.Sku, "local", item.Available, item.MaxPerOrder));
        foreach (var row in data.Reservations) await reservations.Upsert(Context(), new Reservation(row.Id, "local", row.OrderId, row.Sku, row.Quantity));
    }
    public async Task<OrderCreated> CreateOrder()
    {
        var id = Guid.NewGuid().ToString("D");
        await orders.Upsert(Context(), new Order(id, "local")); return new(id);
    }
    public async Task<OrderSummary?> GetOrder(string id) =>
        await orders.TryGetEntity(Context(), id, new(partitionKey: "local")) is { } order ? new(order.Id, order.Status.ToString()) : null;
    public async Task<InventoryView?> GetInventory(string sku) =>
        await inventory.TryGetEntity(Context(), sku, new(partitionKey: "local")) is { } item ? new(item.Sku, item.Available, item.MaxPerOrder) : null;
    public void MapInventoryLimits(WebApplication app)
    {
        var endpoint = Cohesive.Api.Api.Define().Entity<InventoryItem>().Command("SetQuantityLimit")
            .Route("PUT", "/inventory/{id}/quantity-limit").RouteParameter<string>("id")
            .Transition(domain.InventoryTransitions.SetLimit.Reference).Returns<InventoryView>()
            .Result<ErrorResponse>(ApiResultKind.Conflict).Result(ApiResultKind.NotFound).Build();
        app.MapGroup("").AddEndpointFilter<QuantityLimitInput>()
            .MapEntityApi<InventoryItem>(domain.Inventory.Definition, inventory, "local", bindings => bindings
                .Transition(endpoint, domain.InventoryTransitions.SetLimit)
                .Input(context => QuantityLimitInput.Get(context.HttpContext))
                .OnApplied((state, _) => TypedResults.Ok(new InventoryView(state.Sku, state.Available, state.MaxPerOrder)))
                .OnRejected(_ => TypedResults.Conflict(new ErrorResponse("InvalidQuantityLimit"))));
    }
    public async Task<OrderDetailsView?> GetDetails(string id)
    {
        var result = await details.ReadAsync(id);
        return result is null ? null : new(result.Id, result.Status.ToString(), result.Reservations
            .OrderBy(r => r.Id, StringComparer.Ordinal).Select(r => new ReservationView(r.Id, r.Sku, r.Quantity, r.AvailableStock)).ToArray());
    }
    public void MapSubmit(WebApplication app)
    {
        // Preserve the common wire code while the native binding owns exhaustive
        // outcome classification. This filter changes only the transport envelope.
        var routes = app.MapGroup("").AddEndpointFilter(async (context, next) =>
        {
            var result = await next(context);
            if (result is IValueHttpResult { Value: ProblemDetails problem } && problem.Status == 409
                && problem.Extensions.TryGetValue("code", out var raw) && raw is string code && code.StartsWith("orders.submit.", StringComparison.Ordinal))
                return Results.Conflict(new ErrorResponse(code["orders.submit.".Length..]));
            return result;
        });
        routes.MapEntityApi<Order>(domain.Orders.Definition, orders, "local", bindings => bindings
            .Transition("Submit", "/orders/{id}/submit", domain.OrderTransitions.Submit)
            .OnApplied((state, outcome) => TypedResults.Ok(new OrderSummary(state.Id, state.Status.ToString())))
            .OnRejected(outcome => outcome.Outcome, "orders.submit", responses => responses
                .Conflict(SubmissionOutcome.NotDraft, "Order cannot be submitted", "Order must be Draft.")
                .NotRejected(SubmissionOutcome.Submitted)));
    }
    public async Task<Completion> Fulfill(string operationId, FulfillmentRequest request)
    {
        var result = await hosted.Runtime.ExecuteProcessAsync(Context(), "fulfill", new(new(operationId), new("attempt/1")),
            ObservationValue.FromObject(new FulfillOrder(request.OrderId, request.Sku, request.Quantity)));
        if (result.Kind != ApiResultKind.Success) throw new InvalidOperationException("Process execution did not succeed.");
        return ProcessCompletion.Read(result.Outcome?.Decision.State.Terminal);
    }
}

public static class HostSetup
{
    public static void Configure(IServiceCollection services)
    {
        services.AddAuthorization();
        services.AddRequestOperationContext();
        services.AddFixedRequestIdentity(FulfillmentDemoIdentity.Context);
    }
    public static void Configure(WebApplication app)
    {
        app.UseRequestOperationContext();
        app.UseAuthorization();
    }
}
