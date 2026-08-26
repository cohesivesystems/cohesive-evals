using Cohesive.Relations.Authoring;
using Cohesive.Relations.Compilation;
using Cohesive.Relations.IR;
using Cohesive.Relations.Mapping;
using Cohesive.Relations.Model;

namespace LoadSearch.Application;

static class LoadSearchRelation
{
    public static readonly RelationshipId CustomerRelationshipId = new("Load.Customer");
    public static readonly RelationshipId EquipmentRelationshipId = new("Load.Equipment");

    static LoadSearchRelation()
    {
        var author = RelationQuery.Expression();
        var loads = author.Source<Load>();
        var customers = author.Traverse<Load, Customer>(
            loads,
            load => load.CustomerId,
            requirement: QueryInputRequirement.Required,
            relationshipId: CustomerRelationshipId);
        var loadEquipment = author.Relationship<Load, Equipment>(
            load => load.EquipmentId,
            id: EquipmentRelationshipId);
        var equipment = author.Traverse(
            customers,
            loads.Binding,
            loadEquipment,
            requirement: QueryInputRequirement.Required);
        var projection = author.Project(
            equipment,
            (Load load, Customer customer, Equipment unit) => new LoadSearchResult
            {
                LoadId = load.Id,
                CustomerName = customer.Name,
                EquipmentNumber = unit.Number
            },
            loads.Binding,
            customers.Binding);
        var relation = projection.BuildRelation(static result => result.LoadId);
        var compilation = RelationQueryStaticCompiler.Compile(new(
            relation.CreateDocument(),
            author.ShapeDocuments,
            author.CreateRelationshipCatalogDocument()));
        if (!compilation.IsSuccessful || compilation.Plan is null)
        {
            throw new InvalidOperationException(string.Join(
                Environment.NewLine,
                compilation.Diagnostics.Select(static diagnostic =>
                    $"{diagnostic.Code}: {diagnostic.Message}")));
        }

        Plan = compilation.Plan;
        var mapperCompilation = RelationDtoMapperCompiler.Default.Compile<LoadSearchResult>(Plan);
        Mapper = mapperCompilation.Mapper
            ?? throw new InvalidOperationException(string.Join(
                Environment.NewLine,
                mapperCompilation.Diagnostics.Select(static diagnostic =>
                    $"{diagnostic.Code}: {diagnostic.Message}")));
    }

    public static CompiledRelationQueryPlan Plan { get; }

    public static CompiledRelationDtoMapper<LoadSearchResult> Mapper { get; }
}
