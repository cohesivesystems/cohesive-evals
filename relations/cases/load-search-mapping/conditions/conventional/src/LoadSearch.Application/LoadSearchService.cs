namespace LoadSearch.Application;

public sealed class LoadSearchService : ILoadSearchService
{
    public LoadSearchOutcome Execute(LoadSearchInput input)
    {
        ArgumentNullException.ThrowIfNull(input);

        var customers = input.Customers.ToDictionary(static customer => customer.Id, StringComparer.Ordinal);
        var equipment = input.Equipment.ToDictionary(static unit => unit.Id, StringComparer.Ordinal);
        List<LoadSearchResult> results = new(input.Loads.Count);

        foreach (var load in input.Loads)
        {
            if (string.IsNullOrWhiteSpace(load.CustomerId)
                || !customers.TryGetValue(load.CustomerId, out var customer))
            {
                return LoadSearchOutcome.Failed("Customer", load.CustomerId);
            }

            if (string.IsNullOrWhiteSpace(load.EquipmentId)
                || !equipment.TryGetValue(load.EquipmentId, out var unit))
            {
                return LoadSearchOutcome.Failed("Equipment", load.EquipmentId);
            }

            results.Add(new()
            {
                LoadId = load.Id,
                CustomerName = customer.Name,
                EquipmentNumber = unit.Number
            });
        }

        return LoadSearchOutcome.Success(results);
    }
}

public sealed class CustomerLoadSummaryService : ICustomerLoadSummaryService
{
    public IReadOnlyList<CustomerLoadSummary> Summarize(IReadOnlyList<LoadSearchResult> results)
    {
        ArgumentNullException.ThrowIfNull(results);
        return [.. results.Select(static result => new CustomerLoadSummary(result.LoadId, result.CustomerName))];
    }
}
