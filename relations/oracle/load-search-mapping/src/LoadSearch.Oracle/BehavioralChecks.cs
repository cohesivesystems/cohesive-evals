using LoadSearch.Application;

namespace LoadSearch.Oracle;

static class BehavioralChecks
{
    public static IReadOnlyList<CheckResult> Execute() =>
    [
        Run("LSM-BHV-001", EquippedMapping),
        Run("LSM-BHV-002", UnequippedRetention),
        Run("LSM-BHV-003", UnequippedNullRepresentation),
        Run("LSM-BHV-004", MixedCardinalityAndOrder),
        Run("LSM-BHV-005", AbsentCustomerFailure),
        Run("LSM-BHV-006", DanglingCustomerFailure),
        Run("LSM-BHV-007", DanglingEquipmentFailure),
        Run("LSM-BHV-008", SuccessfulIdentityAndCustomerMapping),
        Run("LSM-BHV-009", CustomerOnlyConsumer)
    ];

    static string EquippedMapping()
    {
        var outcome = Execute(Input(
            [Load("freight-41", "account-north", "tractor-9")],
            [Customer("account-north", "Northwind")],
            [Equipment("tractor-9", "TX-904")]));

        Success(outcome, 1);
        var result = outcome.Results.Single();
        Require.Equal("freight-41", result.LoadId, "Load identity");
        Require.Equal("Northwind", result.CustomerName, "Customer name");
        Require.Equal("TX-904", result.EquipmentNumber, "Equipment number");
        return "Equipped Load retained its baseline identity and mapped fields.";
    }

    static string UnequippedRetention()
    {
        var outcome = Execute(Input(
            [Load("freight-unassigned", "account-west", null)],
            [Customer("account-west", "Westward")],
            [Equipment("unused-unit", "UNUSED")]));

        Success(outcome, 1);
        Require.Equal(
            1,
            outcome.Results.Count(result => result.LoadId == "freight-unassigned"),
            "Occurrences of unequipped Load identity");
        return "Unequipped Load occurred exactly once in a successful result.";
    }

    static string UnequippedNullRepresentation()
    {
        var outcome = Execute(Input(
            [Load("freight-open", "account-east", null)],
            [Customer("account-east", "Eastern")],
            []));

        Success(outcome, 1);
        Require.Equal<string?>(null, outcome.Results.Single().EquipmentNumber, "Equipment number absence");
        return "Unequipped result represented Equipment number as null.";
    }

    static string MixedCardinalityAndOrder()
    {
        var outcome = Execute(MixedInput());

        Success(outcome, 4);
        Require.SequenceEqual(
            ["freight-z", "freight-open", "freight-a", "freight-spare"],
            outcome.Results.Select(static result => result.LoadId),
            "Mixed result identities and order");
        Require.Equal(4, outcome.Results.Select(static result => result.LoadId).Distinct().Count(), "Distinct identities");
        return "Mixed input retained one result per Load in source order.";
    }

    static string AbsentCustomerFailure()
    {
        var outcome = Execute(Input(
            [Load("freight-no-account", null, "tractor-3")],
            [Customer("account-other", "Other")],
            [Equipment("tractor-3", "TX-303")]));

        Failure(outcome, "Customer", null);
        return "Absent Customer retained the required-relationship failure.";
    }

    static string DanglingCustomerFailure()
    {
        var outcome = Execute(Input(
            [Load("freight-bad-account", "account-missing", "tractor-4")],
            [Customer("account-present", "Present")],
            [Equipment("tractor-4", "TX-404")]));

        Failure(outcome, "Customer", "account-missing");
        return "Dangling Customer retained its reference identity and required failure.";
    }

    static string DanglingEquipmentFailure()
    {
        var outcome = Execute(Input(
            [Load("freight-bad-unit", "account-south", "tractor-missing")],
            [Customer("account-south", "Southern")],
            [Equipment("tractor-present", "TX-101")]));

        Failure(outcome, "Equipment", "tractor-missing");
        return "Dangling non-null Equipment retained its reference identity and required failure.";
    }

    static string SuccessfulIdentityAndCustomerMapping()
    {
        var outcome = Execute(MixedInput());

        Success(outcome, 4);
        Require.SequenceEqual(
            ["freight-z:Zulu", "freight-open:Alpha", "freight-a:Alpha", "freight-spare:Zulu"],
            outcome.Results.Select(static result => $"{result.LoadId}:{result.CustomerName}"),
            "Successful Load and Customer fields");
        return "Successful results retained every source Load identity and matched Customer name.";
    }

    static string CustomerOnlyConsumer()
    {
        var outcome = Execute(MixedInput());
        Success(outcome, 4);

        var summaries = new CustomerLoadSummaryService().Summarize(outcome.Results);
        Require.SequenceEqual(
            ["freight-z:Zulu", "freight-open:Alpha", "freight-a:Alpha", "freight-spare:Zulu"],
            summaries.Select(static result => $"{result.LoadId}:{result.CustomerName}"),
            "Customer-only summaries");
        return "Customer-only consumer retained identity, order, and Customer output.";
    }

    static LoadSearchOutcome Execute(LoadSearchInput input) => new LoadSearchService().Execute(input);

    static void Success(LoadSearchOutcome outcome, int count)
    {
        Require.True(outcome.Succeeded, $"Expected success, observed failure {outcome.Failure}.");
        Require.Equal<LoadSearchFailure?>(null, outcome.Failure, "Success failure value");
        Require.Equal(count, outcome.Results.Count, "Result count");
    }

    static void Failure(LoadSearchOutcome outcome, string relationship, string? referenceId)
    {
        Require.True(!outcome.Succeeded, "Expected failure, observed success.");
        Require.Equal(0, outcome.Results.Count, "Partial result count");
        Require.True(outcome.Failure is not null, "Expected a structured failure.");
        Require.Equal("missing-required-relation", outcome.Failure!.Code, "Failure code");
        Require.Equal(relationship, outcome.Failure.Relationship, "Failure relationship");
        Require.Equal(referenceId, outcome.Failure.ReferenceId, "Failure reference identity");
    }

    static LoadSearchInput MixedInput() => Input(
        [
            Load("freight-z", "account-z", "tractor-z"),
            Load("freight-open", "account-a", null),
            Load("freight-a", "account-a", "tractor-a"),
            Load("freight-spare", "account-z", null)
        ],
        [Customer("account-a", "Alpha"), Customer("account-z", "Zulu")],
        [Equipment("tractor-a", "TX-001"), Equipment("tractor-z", "TX-999")]);

    static LoadSearchInput Input(
        IReadOnlyList<Load> loads,
        IReadOnlyList<Customer> customers,
        IReadOnlyList<Equipment> equipment) => new(loads, customers, equipment);

    static Load Load(string id, string? customerId, string? equipmentId) => new()
    {
        Id = id,
        CustomerId = customerId!,
        EquipmentId = equipmentId!
    };

    static Customer Customer(string id, string name) => new() { Id = id, Name = name };

    static Equipment Equipment(string id, string number) => new() { Id = id, Number = number };

    static CheckResult Run(string id, Func<string> check)
    {
        try
        {
            return new(id, CheckStatus.Passed, check());
        }
        catch (Exception exception)
        {
            return new(id, CheckStatus.Failed, RootMessage(exception));
        }
    }

    static string RootMessage(Exception exception)
    {
        while (exception is TypeInitializationException or System.Reflection.TargetInvocationException
            && exception.InnerException is not null)
        {
            exception = exception.InnerException;
        }

        return $"{exception.GetType().Name}: {exception.Message}";
    }
}
