using System.Text.Json.Serialization;

namespace LoadSearch.Application;

public sealed record Load
{
    [JsonPropertyName("id")]
    public required string Id { get; init; }

    [JsonPropertyName("customerId")]
    public required string CustomerId { get; init; }

    [JsonPropertyName("equipmentId")]
    public required string EquipmentId { get; init; }
}

public sealed record Customer
{
    [JsonPropertyName("id")]
    public required string Id { get; init; }

    [JsonPropertyName("name")]
    public required string Name { get; init; }
}

public sealed record Equipment
{
    [JsonPropertyName("id")]
    public required string Id { get; init; }

    [JsonPropertyName("number")]
    public required string Number { get; init; }
}

public sealed record LoadSearchResult
{
    [JsonPropertyName("loadId")]
    public required string LoadId { get; init; }

    [JsonPropertyName("customerName")]
    public required string CustomerName { get; init; }

    [JsonPropertyName("equipmentNumber")]
    public required string EquipmentNumber { get; init; }
}

public sealed record LoadSearchInput(
    IReadOnlyList<Load> Loads,
    IReadOnlyList<Customer> Customers,
    IReadOnlyList<Equipment> Equipment);

public sealed record LoadSearchFailure(
    string Code,
    string Relationship,
    string? ReferenceId);

public sealed record LoadSearchOutcome
{
    public required IReadOnlyList<LoadSearchResult> Results { get; init; }

    public LoadSearchFailure? Failure { get; init; }

    [JsonIgnore]
    public bool Succeeded => Failure is null;

    public static LoadSearchOutcome Success(IReadOnlyList<LoadSearchResult> results) =>
        new() { Results = results };

    public static LoadSearchOutcome Failed(string relationship, string? referenceId) =>
        new()
        {
            Results = [],
            Failure = new("missing-required-relation", relationship, referenceId)
        };
}

public sealed record CustomerLoadSummary(string LoadId, string CustomerName);

public interface ILoadSearchService
{
    LoadSearchOutcome Execute(LoadSearchInput input);
}

public interface ICustomerLoadSummaryService
{
    IReadOnlyList<CustomerLoadSummary> Summarize(IReadOnlyList<LoadSearchResult> results);
}
