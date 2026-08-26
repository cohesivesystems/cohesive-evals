using Cohesive.Relations.Compilation;
using Cohesive.Relations.Execution;
using Cohesive.Relations.Mapping;

namespace LoadSearch.Application;

public sealed class LoadSearchService : ILoadSearchService
{
    public LoadSearchOutcome Execute(LoadSearchInput input)
    {
        ArgumentNullException.ThrowIfNull(input);

        foreach (var load in input.Loads)
        {
            if (string.IsNullOrWhiteSpace(load.CustomerId))
                return LoadSearchOutcome.Failed("Customer", load.CustomerId);
            if (string.IsNullOrWhiteSpace(load.EquipmentId))
                return LoadSearchOutcome.Failed("Equipment", load.EquipmentId);
        }

        var execution = RelationQueryInMemoryInterpreter.Default.Execute(new(
            LoadSearchRelation.Plan,
            RelationRuntimeEvidenceFactory.Create(input)));
        if (execution.Status != RelationQueryExecutionStatus.Succeeded)
        {
            if (MissingRequiredRelation(input, execution) is { } failure)
                return failure;

            throw new InvalidOperationException(string.Join(
                Environment.NewLine,
                execution.Diagnostics.Select(static diagnostic =>
                    $"{diagnostic.Code}: {diagnostic.Message}")));
        }

        var mapped = LoadSearchRelation.Mapper.Map(execution);
        if (mapped.Status != RelationDtoMappingStatus.Succeeded)
        {
            throw new InvalidOperationException(string.Join(
                Environment.NewLine,
                mapped.Diagnostics.Select(static diagnostic =>
                    $"{diagnostic.Code}: {diagnostic.Message}")));
        }

        var results = mapped.Rows.ToDictionary(static row => row.Value.LoadId, static row => row.Value, StringComparer.Ordinal);
        return LoadSearchOutcome.Success([.. input.Loads.Select(load => results[load.Id])]);
    }

    static LoadSearchOutcome? MissingRequiredRelation(
        LoadSearchInput input,
        RelationQueryExecutionResult execution)
    {
        var loadOrder = input.Loads
            .Select((load, index) => (load.Id, index))
            .ToDictionary(static pair => pair.Id, static pair => pair.index, StringComparer.Ordinal);
        var missing = execution.RequirementGapAnalysis.Gaps
            .Select(gap => (Gap: gap, Relationship: gap.Input as RelationQueryRelationshipInput))
            .Where(static candidate => candidate.Relationship is not null)
            .Select(candidate => new
            {
                candidate.Gap,
                Relationship = candidate.Relationship!,
                LoadIndex = candidate.Gap.Occurrence?.ObservationIdentity is { } id
                    && loadOrder.TryGetValue(id, out var index)
                        ? index
                        : int.MaxValue
            })
            .OrderBy(static candidate => candidate.LoadIndex)
            .ThenBy(candidate => candidate.Relationship.Relationship == LoadSearchRelation.CustomerRelationshipId ? 0 : 1)
            .FirstOrDefault();
        if (missing is null)
            return null;

        var load = input.Loads[missing.LoadIndex];
        return missing.Relationship.Relationship == LoadSearchRelation.CustomerRelationshipId
            ? LoadSearchOutcome.Failed("Customer", load.CustomerId)
            : LoadSearchOutcome.Failed("Equipment", load.EquipmentId);
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
