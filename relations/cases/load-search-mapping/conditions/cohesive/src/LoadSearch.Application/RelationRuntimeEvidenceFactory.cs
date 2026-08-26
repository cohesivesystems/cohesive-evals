using System.Collections.Immutable;
using Cohesive.Model;
using Cohesive.Relations.Compilation;
using Cohesive.Relations.Diagnostics;
using Cohesive.Relations.IR;

namespace LoadSearch.Application;

static class RelationRuntimeEvidenceFactory
{
    public static RelationQueryRuntimeEvidence Create(LoadSearchInput input)
    {
        var plan = LoadSearchRelation.Plan;
        var source = plan.InputContract.Sources.Single();
        var customerTraversal = plan.InputContract.Traversals.Single(traversal =>
            traversal.Definition.Id == LoadSearchRelation.CustomerRelationshipId);
        var equipmentTraversal = plan.InputContract.Traversals.Single(traversal =>
            traversal.Definition.Id == LoadSearchRelation.EquipmentRelationshipId);
        var customers = input.Customers.ToDictionary(static customer => customer.Id, StringComparer.Ordinal);
        var equipment = input.Equipment.ToDictionary(static unit => unit.Id, StringComparer.Ordinal);

        List<(Load Value, RelationQueryObservationOccurrence Occurrence)> loads = [];
        Dictionary<string, (Customer Value, RelationQueryObservationOccurrence Occurrence)> customerOccurrences =
            new(StringComparer.Ordinal);
        Dictionary<string, (Equipment Value, RelationQueryObservationOccurrence Occurrence)> equipmentOccurrences =
            new(StringComparer.Ordinal);
        ImmutableArray<RelationQueryTraversalEvidence>.Builder traversals = ImmutableArray.CreateBuilder<RelationQueryTraversalEvidence>();

        for (var index = 0; index < input.Loads.Count; index++)
        {
            var load = input.Loads[index];
            var loadOccurrence = new RelationQueryObservationOccurrence(
                new($"load/{index:D8}"),
                source.Binding,
                source.Shape,
                load.Id);
            loads.Add((load, loadOccurrence));

            RelationQueryObservationOccurrence? customerOccurrence = null;
            if (customers.TryGetValue(load.CustomerId, out var customer))
            {
                customerOccurrence = GetOrAdd(
                    customerOccurrences,
                    customer.Id,
                    customer,
                    customerTraversal.Result,
                    customerTraversal.ResultShape,
                    "customer");
            }

            traversals.Add(new(
                customerTraversal.Input.Id,
                loadOccurrence.Id,
                RelationQueryTraversalEvidenceState.Completed,
                customerOccurrence is null ? [] : [customerOccurrence],
                RelationQueryEvidenceCompleteness.Complete,
                $"load-search/customer/{index:D8}"));

            RelationQueryObservationOccurrence? equipmentOccurrence = null;
            if (equipment.TryGetValue(load.EquipmentId, out var unit))
            {
                equipmentOccurrence = GetOrAdd(
                    equipmentOccurrences,
                    unit.Id,
                    unit,
                    equipmentTraversal.Result,
                    equipmentTraversal.ResultShape,
                    "equipment");
            }

            traversals.Add(new(
                equipmentTraversal.Input.Id,
                loadOccurrence.Id,
                RelationQueryTraversalEvidenceState.Completed,
                equipmentOccurrence is null ? [] : [equipmentOccurrence],
                RelationQueryEvidenceCompleteness.Complete,
                $"load-search/equipment/{index:D8}"));
        }

        ImmutableArray<RelationQueryFieldEvidence>.Builder fields = ImmutableArray.CreateBuilder<RelationQueryFieldEvidence>();
        foreach (var field in plan.RequirementGraph.Inputs.OfType<RelationQueryFieldInput>())
        {
            if (field.Binding == source.Binding)
            {
                foreach (var load in loads)
                    fields.Add(Value(field, load.Occurrence, LoadValue(load.Value, field.Field.Path)));
            }
            else if (field.Binding == customerTraversal.Result)
            {
                foreach (var customer in customerOccurrences.Values)
                    fields.Add(Value(field, customer.Occurrence, CustomerValue(customer.Value, field.Field.Path)));
            }
            else if (field.Binding == equipmentTraversal.Result)
            {
                foreach (var unit in equipmentOccurrences.Values)
                    fields.Add(Value(field, unit.Occurrence, EquipmentValue(unit.Value, field.Field.Path)));
            }
            else
            {
                throw new InvalidOperationException($"Unexpected relation binding '{field.Binding.Value}'.");
            }
        }

        return new(
            new("load-search/application"),
            plan,
            sources:
            [
                new(
                    source.Input.Id,
                    RelationQuerySourceEvidenceState.Provided,
                    [.. loads.Select(static load => load.Occurrence)])
            ],
            fields: fields.ToImmutable(),
            traversals: traversals.ToImmutable(),
            capabilities:
            [
                .. plan.RequirementGraph.Inputs
                    .OfType<RelationQueryCapabilityInput>()
                    .Select(static capability => new RelationQueryCapabilityEvidence(
                        capability.Id,
                        RelationQueryCapabilityEvidenceState.Available,
                        "load-search/in-memory"))
            ]);
    }

    static RelationQueryObservationOccurrence GetOrAdd<T>(
        Dictionary<string, (T Value, RelationQueryObservationOccurrence Occurrence)> occurrences,
        string identity,
        T value,
        ValueBindingId binding,
        QualifiedShapeId shape,
        string prefix)
        where T : notnull
    {
        if (occurrences.TryGetValue(identity, out var existing))
            return existing.Occurrence;

        var occurrence = new RelationQueryObservationOccurrence(
            new($"{prefix}/{Uri.EscapeDataString(identity)}"),
            binding,
            shape,
            identity);
        occurrences.Add(identity, (value, occurrence));
        return occurrence;
    }

    static RelationQueryFieldEvidence Value(
        RelationQueryFieldInput input,
        RelationQueryObservationOccurrence owner,
        string value) => new(
        input.Id,
        owner.Id,
        RelationQueryFieldEvidenceState.Value,
        ObservationValue.FromString(value));

    static string LoadValue(Load load, FieldPath path) => path.ToString() switch
    {
        "id" => load.Id,
        "customerId" => load.CustomerId,
        "equipmentId" => load.EquipmentId,
        _ => throw new InvalidOperationException($"Unexpected Load field '{path}'.")
    };

    static string CustomerValue(Customer customer, FieldPath path) => path.ToString() switch
    {
        "name" => customer.Name,
        _ => throw new InvalidOperationException($"Unexpected Customer field '{path}'.")
    };

    static string EquipmentValue(Equipment equipment, FieldPath path) => path.ToString() switch
    {
        "number" => equipment.Number,
        _ => throw new InvalidOperationException($"Unexpected Equipment field '{path}'.")
    };
}
