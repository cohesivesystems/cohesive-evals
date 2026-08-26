using System.Diagnostics;
using System.Text.Json.Nodes;

namespace LoadSearch.BaselineEquivalence.Tests;

public sealed class BaselineEquivalenceTests
{
    static readonly string RepositoryRoot = FindRepositoryRoot();
    static readonly string CaseRoot = Path.Combine(
        RepositoryRoot,
        "relations",
        "cases",
        "load-search-mapping");
    static readonly string Conventional = Path.Combine(CaseRoot, "conditions", "conventional");
    static readonly string Cohesive = Path.Combine(CaseRoot, "conditions", "cohesive");

    [Fact]
    public void Public_contracts_visible_tests_and_probe_are_byte_identical()
    {
        AssertSameFile("src/LoadSearch.Application/Contracts.cs");
        AssertSameFile("tests/LoadSearch.Application.Tests/LoadSearch.Application.Tests.csproj");
        AssertSameFile("tests/LoadSearch.Application.Tests/LoadSearchServiceTests.cs");
        AssertSameFile("tools/LoadSearch.Probe/LoadSearch.Probe.csproj");
        AssertSameFile("tools/LoadSearch.Probe/Program.cs");
        AssertSameFile("Directory.Build.props");
        AssertSameFile("global.json");
        AssertSameFile("LoadSearch.slnx");
    }

    [Fact]
    public async Task All_baseline_scenarios_have_equivalent_normalized_observations()
    {
        string[] scenarios =
        [
            "complete",
            "ordered",
            "absent-customer",
            "dangling-customer",
            "absent-equipment",
            "dangling-equipment"
        ];

        foreach (var scenario in scenarios)
        {
            var conventional = await RunProbe(Conventional, scenario);
            var cohesive = await RunProbe(Cohesive, scenario);
            Assert.True(
                JsonNode.DeepEquals(conventional, cohesive),
                $"Scenario '{scenario}' differed.{Environment.NewLine}"
                + $"Conventional: {conventional}{Environment.NewLine}"
                + $"Cohesive: {cohesive}");
        }
    }

    static void AssertSameFile(string relativePath)
    {
        var conventional = File.ReadAllBytes(Path.Combine(Conventional, relativePath));
        var cohesive = File.ReadAllBytes(Path.Combine(Cohesive, relativePath));
        Assert.True(conventional.SequenceEqual(cohesive), $"'{relativePath}' differs between conditions.");
    }

    static async Task<JsonNode> RunProbe(string condition, string scenario)
    {
        ProcessStartInfo start = new("dotnet")
        {
            WorkingDirectory = condition,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        };
        start.ArgumentList.Add("run");
        start.ArgumentList.Add("--project");
        start.ArgumentList.Add("tools/LoadSearch.Probe/LoadSearch.Probe.csproj");
        start.ArgumentList.Add("--configuration");
        start.ArgumentList.Add("Debug");
        start.ArgumentList.Add("--no-build");
        start.ArgumentList.Add("--");
        start.ArgumentList.Add(scenario);

        using var process = Process.Start(start)
            ?? throw new InvalidOperationException($"Could not start the {Path.GetFileName(condition)} probe.");
        var standardOutput = process.StandardOutput.ReadToEndAsync();
        var standardError = process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(30));
        var output = await standardOutput;
        var error = await standardError;
        Assert.True(
            process.ExitCode == 0,
            $"Probe '{scenario}' in '{condition}' exited {process.ExitCode}: {error}");
        return JsonNode.Parse(output)
            ?? throw new InvalidOperationException($"Probe '{scenario}' returned no JSON.");
    }

    static string FindRepositoryRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "relations", "protocol.md")))
                return current.FullName;
            current = current.Parent;
        }

        throw new InvalidOperationException("Could not locate the cohesive-evals repository root.");
    }
}
