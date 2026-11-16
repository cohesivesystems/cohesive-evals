using System.ComponentModel.DataAnnotations;
using System.Text.Json;
using Cohesive.Model;

// Characterize the pinned SDK, not the desired PV2 behavior. Acceptance of an
// overlength string is the gap under audit, never a passing application result.
var field = new FieldDefinition(new("RequestId"), new ScalarTypeRef(ScalarTypeKind.String),
    constraints: [new MaxLengthConstraint(64)]);
var fieldShape = new Shape(new("Request"), [field]);
var shapeConstraint = new Shape(new("Request"),
    [new FieldDefinition(new("RequestId"), new ScalarTypeRef(ScalarTypeKind.String))],
    constraints: [new MaxLengthConstraint(64, FieldPath.FromField("RequestId"))]);
var rows = new List<object>();
foreach (var (name, text, pv2LengthAccepted) in new[] {
    ("ascii64", new string('a', 64), true), ("ascii65", new string('a', 65), false),
    ("emoji32", string.Concat(Enumerable.Repeat("😀", 32)), true),
    ("emoji32-plus-ascii", string.Concat(Enumerable.Repeat("😀", 32)) + "x", false) })
{
    var value = ObservationValue.FromString(text);
    var fields = new Dictionary<string, ObservationValue> { ["RequestId"] = value };
    var fieldAccepted = ObservationValidator.TryValidateAgainstShape(fields, fieldShape, out _);
    var shapeAccepted = ObservationValidator.TryValidateAgainstShape(fields, shapeConstraint, out _);
    var objectAccepted = ObservationValidator.TryValidateAgainstShape(ObservationValue.FromObject(fields), fieldShape, out _);
    var contractAccepted = ValueContract.FromField(field).IsSatisfiedByConstant(value);
    if (!fieldAccepted || !shapeAccepted || !objectAccepted || !contractAccepted)
        throw new InvalidOperationException("Pinned constraint behavior changed; revisit the audit.");
    rows.Add(new { name, utf16Length = text.Length, pv2LengthAccepted, fieldAccepted, shapeAccepted, objectAccepted, contractAccepted });
}
foreach (var value in new[] { ObservationValue.Null, ObservationValue.FromInt64(65) })
    if (ObservationValidator.TryValidateAgainstShape(new Dictionary<string, ObservationValue> { ["RequestId"] = value }, fieldShape, out _))
        throw new InvalidOperationException("Structural rejection control failed.");
if (ObservationValidator.TryValidateAgainstShape(new Dictionary<string, ObservationValue>(), fieldShape, out _))
    throw new InvalidOperationException("Required-field control failed.");
var projected = new ClrShapeGraphBuilder().AddShape<AttributedRequest>().Build();
var projectedConstraints = projected.Shapes.SelectMany(s => s.Fields).Sum(f => f.Constraints.Length);
if (projectedConstraints != 0)
    throw new InvalidOperationException("Pinned DataAnnotations projection changed; revisit the audit.");
Console.WriteLine(JsonSerializer.Serialize(new {
    package = "0.1.0-eval.b0af008", rows, structuralRejectionControls = 3,
    dataAnnotationsConstraintsProjected = projectedConstraints
}, new JsonSerializerOptions { WriteIndented = true }));

public sealed record AttributedRequest([property: MaxLength(64)] string RequestId);
