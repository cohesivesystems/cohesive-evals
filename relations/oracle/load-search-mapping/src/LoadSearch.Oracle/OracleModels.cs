using System.Text.Json.Serialization;

namespace LoadSearch.Oracle;

[JsonConverter(typeof(JsonStringEnumConverter<OracleCondition>))]
enum OracleCondition
{
    Conventional,
    Cohesive
}

[JsonConverter(typeof(JsonStringEnumConverter<CheckStatus>))]
enum CheckStatus
{
    Passed,
    Failed
}

sealed record CheckResult(
    string Id,
    CheckStatus Status,
    string Evidence);

sealed record ObligationResult(
    string Id,
    CheckStatus Status,
    IReadOnlyList<string> Checks);

sealed record OracleReport(
    string SchemaVersion,
    OracleCondition Condition,
    IReadOnlyList<CheckResult> BehavioralChecks,
    IReadOnlyList<ObligationResult> Obligations,
    IReadOnlyList<CheckResult> TreatmentIntegrityChecks,
    CheckStatus TreatmentIntegrity,
    CheckStatus Outcome);

sealed class OracleAssertionException(string message) : Exception(message);

static class Require
{
    public static void True(bool condition, string message)
    {
        if (!condition)
            throw new OracleAssertionException(message);
    }

    public static void Equal<T>(T expected, T actual, string label)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new OracleAssertionException(
                $"{label}: expected {Display(expected)}, observed {Display(actual)}.");
    }

    public static void SequenceEqual<T>(
        IEnumerable<T> expected,
        IEnumerable<T> actual,
        string label)
    {
        var expectedValues = expected.ToArray();
        var actualValues = actual.ToArray();
        if (!expectedValues.SequenceEqual(actualValues))
        {
            throw new OracleAssertionException(
                $"{label}: expected [{string.Join(", ", expectedValues.Select(Display))}], "
                + $"observed [{string.Join(", ", actualValues.Select(Display))}].");
        }
    }

    static string Display<T>(T value) => value switch
    {
        null => "<null>",
        string text => $"'{text}'",
        _ => value.ToString() ?? "<null>"
    };
}
