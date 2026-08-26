using System.Text.Json;
using System.Text.Json.Serialization;
using LoadSearch.Oracle;

var options = ParseArguments(args);
var behavioral = BehavioralChecks.Execute();
var treatment = TreatmentIntegrityChecks.Execute(options.Condition, options.SubmissionRoot);
var obligations = Aggregate(behavioral);
var treatmentStatus = treatment.All(static result => result.Status == CheckStatus.Passed)
    ? CheckStatus.Passed
    : CheckStatus.Failed;
var outcome = obligations.All(static result => result.Status == CheckStatus.Passed)
    && treatmentStatus == CheckStatus.Passed
        ? CheckStatus.Passed
        : CheckStatus.Failed;
var report = new OracleReport(
    "cohesive.relations.load-search.oracle/v1",
    options.Condition,
    behavioral,
    obligations,
    treatment,
    treatmentStatus,
    outcome);
var serializerOptions = new JsonSerializerOptions
{
    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    WriteIndented = true,
    Converters = { new JsonStringEnumConverter(JsonNamingPolicy.CamelCase) }
};
var json = JsonSerializer.Serialize(report, serializerOptions);
Console.WriteLine(json);
if (options.Output is not null)
{
    var parent = Path.GetDirectoryName(Path.GetFullPath(options.Output));
    if (!string.IsNullOrEmpty(parent))
        Directory.CreateDirectory(parent);
    File.WriteAllText(options.Output, json + Environment.NewLine);
}

return outcome == CheckStatus.Passed ? 0 : 1;

static IReadOnlyList<ObligationResult> Aggregate(IReadOnlyList<CheckResult> checks)
{
    Dictionary<string, string[]> allocation = new(StringComparer.Ordinal)
    {
        ["REL-EVAL-001"] = ["LSM-BHV-001"],
        ["REL-EVAL-002"] = ["LSM-BHV-002"],
        ["REL-EVAL-003"] = ["LSM-BHV-003"],
        ["REL-EVAL-004"] = ["LSM-BHV-004"],
        ["REL-EVAL-005"] = ["LSM-BHV-005", "LSM-BHV-006"],
        ["REL-EVAL-006"] = ["LSM-BHV-007"],
        ["REL-EVAL-007"] = ["LSM-BHV-008"],
        ["REL-EVAL-008"] = ["LSM-BHV-009"]
    };
    var byId = checks.ToDictionary(static result => result.Id, StringComparer.Ordinal);
    return
    [
        .. allocation.Select(pair => new ObligationResult(
            pair.Key,
            pair.Value.All(id => byId[id].Status == CheckStatus.Passed)
                ? CheckStatus.Passed
                : CheckStatus.Failed,
            pair.Value))
    ];
}

static Arguments ParseArguments(string[] arguments)
{
    OracleCondition? condition = null;
    string? output = null;
    string? submissionRoot = null;
    for (var index = 0; index < arguments.Length; index++)
    {
        switch (arguments[index])
        {
            case "--condition" when index + 1 < arguments.Length:
                condition = arguments[++index].ToLowerInvariant() switch
                {
                    "conventional" => OracleCondition.Conventional,
                    "cohesive" => OracleCondition.Cohesive,
                    var value => throw new ArgumentException($"Unknown condition '{value}'.")
                };
                break;
            case "--output" when index + 1 < arguments.Length:
                output = arguments[++index];
                break;
            case "--submission-root" when index + 1 < arguments.Length:
                submissionRoot = Path.GetFullPath(arguments[++index]);
                break;
            default:
                throw new ArgumentException($"Unknown or incomplete argument '{arguments[index]}'.");
        }
    }

    return new(
        condition ?? throw new ArgumentException("Provide --condition conventional|cohesive."),
        submissionRoot ?? throw new ArgumentException("Provide --submission-root PATH."),
        output);
}

sealed record Arguments(OracleCondition Condition, string SubmissionRoot, string? Output);
