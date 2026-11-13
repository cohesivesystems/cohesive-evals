using System.Reflection;
using System.Text.Json;
using Cohesive.Execution;
using Cohesive.Model.Serialization;
using Cohesive.Relations.Serialization;
using Cohesive.Semantics;
using Fulfillment.Application;

if (args.Length != 1) throw new ArgumentException("Usage: Fulfillment.Development <workspace-root>");
var root = Path.GetFullPath(args[0]);
var inputs = SemanticWorkspaceExport.DiscoverInputs(root, ["src", "Development"],
    ["Directory.Build.props", "global.json", "NuGet.config", "dependency-manifest.json", "DEVELOPMENT.md",
     ..Directory.EnumerateFiles(Path.Combine(root, "packages"), "*.nupkg").Select(path => Path.GetRelativePath(root, path))]);
var version = typeof(SemanticWorkspaceExport).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion;
var output = SemanticWorkspaceExport.WriteDocuments(root, "artifacts/development.json", inputs, version, _ =>
{
    var domain = new FulfillmentDomain();
    var process = new FulfillmentProcess(domain);
    var queries = new FulfillmentQueries(domain);
    var requests = new[] { queries.OrderDetails.CompilationRequest, queries.ReservationAvailability.CompilationRequest };
    var executions = new[] { domain.OrderTransitions.Submit.Document, domain.InventoryTransitions.Reserve.Document,
        domain.InventoryTransitions.Release.Document, domain.ReservationTransitions.Create.Document, process.Definition.Document };
    var options = RelationQueryJsonSerializer.CreateOptions();
    var entities = domain.Definition.Entities;
    var shapes = requests.SelectMany(r => r.ShapeDocuments)
        .Concat(entities.Select(e => e.ShapeGraph?.Document ?? ShapeGraphDocument.FromGraph(e.StateShape.Graph)))
        .Select(d => JsonSerializer.Serialize(d, options)).Distinct().Select(Json);
    var catalogs = requests.Select(r => r.RelationshipCatalogDocument).OfType<RelationshipCatalogDocument>()
        .DistinctBy(d => d.CatalogFingerprint).Select(d => Json(RelationshipCatalogJsonSerializer.Serialize(d)));
    return [..entities.Select(Cohesive.Transitions.Model.EntityStateDocument.Export), ..shapes, ..catalogs,
        ..executions.Select(d => Json(ExecutionDefinitionJsonSerializer.Serialize(d))),
        ..requests.Select(r => Json(RelationQueryJsonSerializer.Serialize(r.DefinitionDocument)))];
});
Console.WriteLine(output);
static JsonElement Json(string value) => JsonSerializer.Deserialize<JsonElement>(value);
