using System.Text.Json;
using LoadSearch.Application;

var scenario = args.SingleOrDefault()
    ?? throw new ArgumentException("Provide exactly one application scenario name.");
var input = scenario switch
{
    "complete" => Input(
        [Load("load-1", "customer-1", "equipment-1")],
        [Customer("customer-1", "Acme")],
        [Equipment("equipment-1", "TRUCK-001")]),
    "ordered" => Input(
        [Load("load-z", "customer-2", "equipment-2"), Load("load-a", "customer-1", "equipment-1")],
        [Customer("customer-1", "Acme"), Customer("customer-2", "Beta")],
        [Equipment("equipment-1", "TRUCK-001"), Equipment("equipment-2", "TRAILER-002")]),
    "absent-customer" => Input(
        [Load("load-1", null!, "equipment-1")],
        [Customer("customer-1", "Acme")],
        [Equipment("equipment-1", "TRUCK-001")]),
    "dangling-customer" => Input(
        [Load("load-1", "customer-missing", "equipment-1")],
        [Customer("customer-1", "Acme")],
        [Equipment("equipment-1", "TRUCK-001")]),
    "absent-equipment" => Input(
        [Load("load-1", "customer-1", null!)],
        [Customer("customer-1", "Acme")],
        [Equipment("equipment-1", "TRUCK-001")]),
    "dangling-equipment" => Input(
        [Load("load-1", "customer-1", "equipment-missing")],
        [Customer("customer-1", "Acme")],
        [Equipment("equipment-1", "TRUCK-001")]),
    _ => throw new ArgumentOutOfRangeException(nameof(scenario), scenario, "Unknown application scenario.")
};

var outcome = new LoadSearchService().Execute(input);
var summary = new CustomerLoadSummaryService().Summarize(outcome.Results);
Console.WriteLine(JsonSerializer.Serialize(
    new ProbeObservation(outcome.Results, outcome.Failure, summary),
    new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase }));

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

sealed record ProbeObservation(
    IReadOnlyList<LoadSearchResult> Results,
    LoadSearchFailure? Failure,
    IReadOnlyList<CustomerLoadSummary> CustomerSummary);
