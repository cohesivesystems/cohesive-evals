using Cohesive.Adapters.Mcp.Development;
if (args.Length != 1) throw new ArgumentException("Usage: Fulfillment.SemanticServer <workspace-root>");
var root = Path.GetFullPath(args[0]);
await DevelopmentMcpServer.RunAsync(
    DevelopmentMcpServer.CreateDefaultWorkspace(root, "artifacts/development.json"),
    new DevelopmentGuide("fulfillment-development/v1", File.ReadAllText(Path.Combine(root, "DEVELOPMENT.md"))));
