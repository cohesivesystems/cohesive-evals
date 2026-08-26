using LoadSearch.Application;

namespace LoadSearch.Oracle;

// This code is deliberately compiled, not reflected. An incompatible change to
// any frozen public member makes the oracle adapter fail its contract/build gate.
static class ContractSurface
{
    public static object Bind()
    {
        Load load = new() { Id = "contract", CustomerId = "customer", EquipmentId = "equipment" };
        Customer customer = new() { Id = "customer", Name = "Customer" };
        Equipment equipment = new() { Id = "equipment", Number = "Equipment" };
        LoadSearchResult result = new()
        {
            LoadId = load.Id,
            CustomerName = customer.Name,
            EquipmentNumber = equipment.Number
        };
        LoadSearchInput input = new([load], [customer], [equipment]);
        LoadSearchFailure failure = new("missing-required-relation", "Equipment", load.EquipmentId);
        ILoadSearchService search = new LoadSearchService();
        ICustomerLoadSummaryService summaries = new CustomerLoadSummaryService();
        LoadSearchOutcome outcome = search.Execute(input);
        IReadOnlyList<CustomerLoadSummary> summary = summaries.Summarize([result]);

        return new
        {
            LoadId = load.Id,
            CustomerId = load.CustomerId,
            EquipmentId = load.EquipmentId,
            CustomerName = customer.Name,
            EquipmentNumber = equipment.Number,
            ResultLoadId = result.LoadId,
            ResultCustomerName = result.CustomerName,
            ResultEquipmentNumber = result.EquipmentNumber,
            OutcomeResults = outcome.Results,
            OutcomeFailure = outcome.Failure,
            OutcomeSucceeded = outcome.Succeeded,
            ConstructedFailure = failure,
            Summary = summary
        };
    }
}
