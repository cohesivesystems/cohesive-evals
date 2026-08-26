using System.Collections;
using System.Reflection;
using System.Text.Json;
using System.Xml.Linq;
using LoadSearch.Application;

namespace LoadSearch.Oracle;

static class TreatmentIntegrityChecks
{
    const BindingFlags AllStatic = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static;

    public static IReadOnlyList<CheckResult> Execute(
        OracleCondition condition,
        string submissionRoot) => condition switch
    {
        OracleCondition.Conventional =>
            [Run("LSM-TI-CONV-001", () => ConventionalHasNoCohesiveReference(submissionRoot))],
        OracleCondition.Cohesive =>
        [
            Run("LSM-TI-COH-001", CanonicalPlanRequirements),
            Run("LSM-TI-COH-002", ServiceExecutesInterpreterAndMapper),
            Run("LSM-TI-COH-003", ServiceHasNoParallelResultMapper)
        ],
        _ => throw new ArgumentOutOfRangeException(nameof(condition), condition, null)
    };

    static string ConventionalHasNoCohesiveReference(string submissionRoot)
    {
        var assemblyReferences = ApplicationAssembly.GetReferencedAssemblies()
            .Select(static reference => reference.Name ?? string.Empty)
            .Where(IsCohesiveIdentity);
        var projectPath = Path.Combine(
            submissionRoot,
            "src",
            "LoadSearch.Application",
            "LoadSearch.Application.csproj");
        var projectReferences = XDocument.Load(projectPath)
            .Descendants()
            .Where(static element => element.Name.LocalName is "PackageReference" or "ProjectReference" or "Reference")
            .Select(static element => element.Attribute("Include")?.Value ?? string.Empty)
            .Where(IsCohesiveIdentity);
        var assetsPath = Path.Combine(
            submissionRoot,
            "src",
            "LoadSearch.Application",
            "obj",
            "project.assets.json");
        Require.True(File.Exists(assetsPath), "Restored project.assets.json was not found.");
        using var assets = JsonDocument.Parse(File.ReadAllText(assetsPath));
        var assetReferences = assets.RootElement.GetProperty("libraries")
            .EnumerateObject()
            .Select(static library => library.Name.Split('/')[0])
            .Where(IsCohesiveIdentity);
        var references = assemblyReferences
            .Concat(projectReferences)
            .Concat(assetReferences)
            .Distinct(StringComparer.Ordinal)
            .Order(StringComparer.Ordinal)
            .ToArray();
        Require.Equal(0, references.Length, "Cohesive project, package, or assembly references");
        return "Restored project graph and application assembly have no Cohesive reference.";
    }

    static string CanonicalPlanRequirements()
    {
        var candidates = FindCompiledPlans()
            .Distinct(ReferenceEqualityComparer.Instance)
            .Select(plan => new { Plan = plan, Traversals = Traversals(plan).ToArray() })
            .Where(static candidate => candidate.Traversals.Any(traversal => traversal.Id == "Load.Customer")
                && candidate.Traversals.Any(traversal => traversal.Id == "Load.Equipment"))
            .ToArray();
        var matching = candidates.Where(static candidate =>
        {
            var customer = candidate.Traversals.Single(traversal => traversal.Id == "Load.Customer");
            var equipment = candidate.Traversals.Single(traversal => traversal.Id == "Load.Equipment");
            return customer.Requirement == "Required" && equipment.Requirement == "Optional";
        }).ToArray();
        Require.True(matching.Length > 0,
            "No compiled plan declares Load.Customer required and Load.Equipment optional.");
        return "Compiled relation plan declares Load.Customer required and Load.Equipment optional.";
    }

    static string ServiceExecutesInterpreterAndMapper()
    {
        var calls = ReachableServiceCalls();
        var interpreter = calls.Any(static call =>
            IsCohesiveNamespace(call.Callee.DeclaringType)
            && call.Callee.Name == "Execute"
            && (call.Callee.DeclaringType?.Name.Contains("Interpreter", StringComparison.Ordinal) ?? false));
        var mapper = calls.Any(static call =>
            (call.Callee.DeclaringType?.Namespace?.StartsWith(
                "Cohesive.Relations.Mapping",
                StringComparison.Ordinal) ?? false)
            && call.Callee.Name == "Map");
        Require.True(interpreter, "No reachable Cohesive.Relations interpreter Execute call was found.");
        Require.True(mapper, "No reachable Cohesive.Relations mapper Map call was found.");
        return "LoadSearchService.Execute reaches the Cohesive interpreter and compiled DTO mapper.";
    }

    static string ServiceHasNoParallelResultMapper()
    {
        var resultType = typeof(LoadSearchResult);
        var forbidden = ReachableServiceCalls()
            .Where(call => call.Callee.DeclaringType == resultType)
            .Where(static call => call.Callee.IsConstructor
                || call.Callee.Name is "set_LoadId" or "set_CustomerName" or "set_EquipmentNumber")
            .Select(static call => $"{Display(call.Caller)} -> {Display(call.Callee)}")
            .Order(StringComparer.Ordinal)
            .ToArray();
        Require.Equal(0, forbidden.Length, "Reachable handwritten LoadSearchResult construction calls");
        return "No reachable application path constructs or populates LoadSearchResult outside Cohesive mapping.";
    }

    static Assembly ApplicationAssembly => typeof(LoadSearchService).Assembly;

    static IEnumerable<object> FindCompiledPlans()
    {
        const string planTypeName = "Cohesive.Relations.Compilation.CompiledRelationQueryPlan";
        foreach (var type in ApplicationAssembly.GetTypes().OrderBy(static type => type.FullName, StringComparer.Ordinal))
        {
            foreach (var property in type.GetProperties(AllStatic)
                .Where(property => property.PropertyType.FullName == planTypeName && property.GetMethod is not null))
            {
                object? value;
                try
                {
                    value = property.GetValue(null);
                }
                catch (TargetInvocationException)
                {
                    continue;
                }

                if (value is not null)
                    yield return value;
            }

            foreach (var field in type.GetFields(AllStatic).Where(field => field.FieldType.FullName == planTypeName))
            {
                object? value;
                try
                {
                    value = field.GetValue(null);
                }
                catch (TypeInitializationException)
                {
                    continue;
                }

                if (value is not null)
                    yield return value;
            }
        }
    }

    static IEnumerable<(string Id, string Requirement)> Traversals(object plan)
    {
        var contract = Get(plan, "InputContract");
        var traversals = Get(contract, "Traversals") as IEnumerable
            ?? throw new OracleAssertionException("Compiled plan traversals were not enumerable.");
        foreach (var traversal in traversals)
        {
            Require.True(traversal is not null, "Compiled plan contained a null traversal.");
            var definition = Get(traversal!, "Definition");
            var id = Get(definition, "Id").ToString()
                ?? throw new OracleAssertionException("Relationship ID was null.");
            var requirement = Get(traversal!, "Requirement").ToString()
                ?? throw new OracleAssertionException("Traversal requirement was null.");
            yield return (id, requirement);
        }
    }

    static object Get(object value, string propertyName) => value.GetType()
        .GetProperty(propertyName, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
        ?.GetValue(value)
        ?? throw new OracleAssertionException(
            $"Expected property '{propertyName}' on '{value.GetType().FullName}'.");

    static IReadOnlyList<MethodCall> ReachableServiceCalls()
    {
        var entry = typeof(LoadSearchService).GetMethod(
            nameof(LoadSearchService.Execute),
            BindingFlags.Instance | BindingFlags.Public)
            ?? throw new OracleAssertionException("LoadSearchService.Execute was not found.");
        return IlCallGraph.ReachableCalls(entry);
    }

    static bool IsCohesiveNamespace(Type? type) =>
        type?.Namespace?.StartsWith("Cohesive.Relations", StringComparison.Ordinal) ?? false;

    static bool IsCohesiveIdentity(string identity)
    {
        var name = Path.GetFileName(identity.Replace('\\', '/')).Split(',')[0];
        foreach (var extension in new[] { ".csproj", ".dll" })
        {
            if (name.EndsWith(extension, StringComparison.OrdinalIgnoreCase))
                name = name[..^extension.Length];
        }

        return name.Equals("Cohesive", StringComparison.Ordinal)
            || name.StartsWith("Cohesive.", StringComparison.Ordinal);
    }

    static string Display(MethodBase method) =>
        $"{method.DeclaringType?.FullName ?? "<unknown>"}.{method.Name}";

    static CheckResult Run(string id, Func<string> check)
    {
        try
        {
            return new(id, CheckStatus.Passed, check());
        }
        catch (Exception exception)
        {
            while (exception is TypeInitializationException or TargetInvocationException
                && exception.InnerException is not null)
            {
                exception = exception.InnerException;
            }

            return new(id, CheckStatus.Failed, $"{exception.GetType().Name}: {exception.Message}");
        }
    }
}
