using LoadSearch.Application;

namespace LoadSearch.Application.Tests;

public sealed class LoadSearchServiceTests
{
    readonly LoadSearchService subject = new();

    [Fact]
    public void Complete_input_maps_related_values()
    {
        var outcome = subject.Execute(Input(
            loads: [Load("load-1", "customer-1", "equipment-1")],
            customers: [Customer("customer-1", "Acme")],
            equipment: [Equipment("equipment-1", "TRUCK-001")]));

        Assert.True(outcome.Succeeded);
        Assert.Equal(
            [new LoadSearchResult
            {
                LoadId = "load-1",
                CustomerName = "Acme",
                EquipmentNumber = "TRUCK-001"
            }],
            outcome.Results);
    }

    [Fact]
    public void Multiple_loads_preserve_identity_cardinality_and_input_order()
    {
        var outcome = subject.Execute(Input(
            loads:
            [
                Load("load-z", "customer-2", "equipment-2"),
                Load("load-a", "customer-1", "equipment-1")
            ],
            customers:
            [
                Customer("customer-1", "Acme"),
                Customer("customer-2", "Beta")
            ],
            equipment:
            [
                Equipment("equipment-1", "TRUCK-001"),
                Equipment("equipment-2", "TRAILER-002")
            ]));

        Assert.True(outcome.Succeeded);
        Assert.Equal(["load-z", "load-a"], outcome.Results.Select(static result => result.LoadId));
        Assert.Equal(["Beta", "Acme"], outcome.Results.Select(static result => result.CustomerName));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("customer-missing")]
    public void Customer_is_required(string? customerId)
    {
        var outcome = subject.Execute(Input(
            loads: [Load("load-1", customerId!, "equipment-1")],
            customers: [Customer("customer-1", "Acme")],
            equipment: [Equipment("equipment-1", "TRUCK-001")]));

        Assert.False(outcome.Succeeded);
        Assert.Equal(new("missing-required-relation", "Customer", customerId), outcome.Failure);
        Assert.Empty(outcome.Results);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("equipment-missing")]
    public void Equipment_is_required(string? equipmentId)
    {
        var outcome = subject.Execute(Input(
            loads: [Load("load-1", "customer-1", equipmentId!)],
            customers: [Customer("customer-1", "Acme")],
            equipment: [Equipment("equipment-1", "TRUCK-001")]));

        Assert.False(outcome.Succeeded);
        Assert.Equal(new("missing-required-relation", "Equipment", equipmentId), outcome.Failure);
        Assert.Empty(outcome.Results);
    }

    [Fact]
    public void Customer_only_consumer_preserves_identity_order_and_customer_name()
    {
        var search = subject.Execute(Input(
            loads:
            [
                Load("load-2", "customer-2", "equipment-2"),
                Load("load-1", "customer-1", "equipment-1")
            ],
            customers:
            [
                Customer("customer-1", "Acme"),
                Customer("customer-2", "Beta")
            ],
            equipment:
            [
                Equipment("equipment-1", "TRUCK-001"),
                Equipment("equipment-2", "TRAILER-002")
            ]));

        var summary = new CustomerLoadSummaryService().Summarize(search.Results);

        Assert.Equal(
            [new CustomerLoadSummary("load-2", "Beta"), new CustomerLoadSummary("load-1", "Acme")],
            summary);
    }

    static LoadSearchInput Input(
        IReadOnlyList<Load> loads,
        IReadOnlyList<Customer> customers,
        IReadOnlyList<Equipment> equipment) => new(loads, customers, equipment);

    static Load Load(string id, string customerId, string equipmentId) => new()
    {
        Id = id,
        CustomerId = customerId,
        EquipmentId = equipmentId
    };

    static Customer Customer(string id, string name) => new() { Id = id, Name = name };

    static Equipment Equipment(string id, string number) => new() { Id = id, Number = number };
}
