using System.Collections.Immutable;
using System.Text.Json;
using Cohesive.Assurance;
using Cohesive.Authoring;
using Cohesive.Execution;
using Cohesive.Model;
using Cohesive.Model.Serialization;
using Cohesive.Transitions.Assurance;
using Cohesive.Transitions.Execution;
using Fulfillment.Application;

var domain = new FulfillmentDomain();
var transition = domain.InventoryTransitions.Reserve;
var compilation = transition.Compile();
if (!compilation.IsSuccessful) throw new InvalidOperationException(string.Join(";", compilation.Validation.Diagnostics));
var plan = compilation.Plan!;
var reference = ClaimReference.FromExecution(transition.Reference);
var author = new ExpressionAuthoring();
var graph = domain.Inventory.Definition.StateShape;
var beforeInput = author.Input(author.Clr.Shape<InventoryItem>(ShapeGraphDocument.FromGraph(graph.Graph), graph.QualifiedId), "before");
var afterInput = author.Input<InventoryItem>("after");
var claim = Claim.Define("mv1.available-nonnegative", "1", reference, Ref("model-observations"), Ref("independent-policy"), Ref("config"))
    .ForEachCommitted(reference).Require(afterInput, ClaimInputRole.After, state => state.Available >= 0).Build();

string Evaluate(ObservationValue before, ObservationValue command, ObservationValue after)
{
    // An explicit reference-model observation, never a production commit receipt.
    var observation = new SemanticObservation("candidate", "audit", 1, 1, reference, SemanticObservationKind.Commit,
        ImmutableDictionary<ClaimInputRole, ObservationValue>.Empty.Add(ClaimInputRole.Before, before)
            .Add(ClaimInputRole.Command, command).Add(ClaimInputRole.After, after));
    var batch = new TraceObservationBatch(new(Ref("model-observations"), Ref("single-entity"), [new(reference, ["audit"])]),
        reference, Ref("epoch"), [new(Ref("alternative"), [observation],
            [new(reference, "audit", 1, 1, ObservationClosure.Closed, Ref("closure"))])],
        EnumerationCompleteness.Complete, Ref("enumeration"));
    var result = TraceClaimEvaluator.Evaluate(claim, batch);
    if (result.Status != AssuranceAttemptStatus.Completed) throw new InvalidOperationException(result.Serialize());
    if (TraceEvaluation.Reevaluate(result.Serialize()).Serialize() != result.Serialize()) throw new InvalidOperationException("Evidence replay drift");
    return result.Verdict.ToString();
}

var inputs = JsonSerializer.Deserialize<AuditInput[]>(File.ReadAllText(args[0]))!;
var rows = inputs.Select(input =>
{
    var before = new InventoryItem("audit", "local", input.Available, input.MaxPerOrder, input.Quarantined);
    var beforeValue = ObservationValue.FromObject(before);
    var command = ObservationValue.FromObject(new StockQuantity(input.Quantity));
    var decision = TransitionReferenceInterpreter.DecideFullState(plan, new("audit-" + input.Name),
        PortableValue.Concrete(plan.Definition.Input, command), PortableValue.Concrete(plan.Definition.Observation, beforeValue));
    if (decision.Kind is not (Cohesive.Transitions.IR.TransitionDecisionKind.Applied or Cohesive.Transitions.IR.TransitionDecisionKind.AdmissionRejected))
        throw new InvalidOperationException(decision.Kind.ToString());
    var afterValue = TransitionStateProjector.Apply(beforeValue, decision);
    var after = afterValue.Deserialize<InventoryItem>()!;
    var outcome = (decision.Outcome?.Value ?? throw new InvalidOperationException("No outcome")).Deserialize<StockResult>()!;
    return new { input.Name, Outcome = outcome.Outcome.ToString(), After = after.Available,
        Unchanged = after == before, Decision = decision.Kind.ToString(),
        Assurance = decision.Kind == Cohesive.Transitions.IR.TransitionDecisionKind.Applied ? Evaluate(beforeValue, command, afterValue) : "not-evaluated-rejection" };
}).ToArray();

var admissionClaim = Claim.Define("mv1.prestate", "1", reference, Ref("model-observations"), Ref("policy"), Ref("config"))
    .ForEachCommitted(reference).Require(beforeInput, ClaimInputRole.Before, state => state.Available >= 0).Build();
string admissionDiagnostic;
try
{
    TransitionAssurance.CheckAdmission(transition, admissionClaim, beforeInput,
        new[] { new InventoryItem("audit", "local", 10, 4) }, Ref("catalog"), Ref("config")).Build();
    throw new InvalidOperationException("Command-dependent finite admission unexpectedly supported");
}
catch (NotSupportedException error) { admissionDiagnostic = error.Message; }

// Positive finite-admission control: the actual state-only order submission model.
var orderTransition = domain.OrderTransitions.Submit;
var orderReference = ClaimReference.FromExecution(orderTransition.Reference);
var orderAuthor = new ExpressionAuthoring();
var orderGraph = domain.Orders.Definition.StateShape;
var orderInput = orderAuthor.Input(orderAuthor.Clr.Shape<Order>(ShapeGraphDocument.FromGraph(orderGraph.Graph), orderGraph.QualifiedId), "order");
var orderClaim = Claim.Define("mv1.only-draft-admitted", "1", orderReference, Ref("model-observations"), Ref("policy"), Ref("config"))
    .ForEachCommitted(orderReference).Require(orderInput, ClaimInputRole.Before, order => order.Status == OrderStatus.Draft).Build();
var orderCatalog = Enum.GetValues<OrderStatus>().Select(status => new Order("audit", "local", status)).ToArray();
var finite = FiniteGuardChecker.Check(TransitionAssurance.CheckAdmission(orderTransition, orderClaim, orderInput,
    orderCatalog, Ref("four-status-catalog"), Ref("config")).Build());
if (FiniteGuardCheckResult.Recheck(finite.Serialize()).Serialize() != finite.Serialize()) throw new InvalidOperationException("Finite evidence replay drift");
File.WriteAllText(Path.Combine(Path.GetDirectoryName(args[1])!, "order-admission.json"), finite.Serialize());

string typedArithmetic;
try
{
    var commandInput = author.Input<StockQuantity>("command");
    Claim.Define("mv1.exact-delta", "1", reference, Ref("model-observations"), Ref("policy"), Ref("config"))
        .ForEachCommitted(reference).Require(beforeInput, commandInput, afterInput,
            (before, command, after) => after.Available == before.Available - command.Quantity).Build();
    typedArithmetic = "supported";
}
catch (ExpressionAuthoringException error) { typedArithmetic = error.Message; }

var negative = ObservationValue.FromObject(new InventoryItem("audit", "local", -1, 4));
var negativeVerdict = Evaluate(negative, ObservationValue.FromObject(new StockQuantity(1)), negative);
if (negativeVerdict != "Violated") throw new InvalidOperationException("Independent claim negative control failed");
File.WriteAllText(args[1], ExecutionDefinitionJsonSerializer.Serialize(transition.Document));
Console.WriteLine(JsonSerializer.Serialize(new { rows, admissionDiagnostic, negativeVerdict,
    guardCount = transition.Definition.Preconditions.Length, transition = reference, typedArithmetic,
    finiteOrderControl = new { verdict = finite.Verdict.ToString(), nonVacuity = finite.NonVacuity.ToString(), finite.Visited, finite.EnumerationComplete } }));

static ClaimReference Ref(string name) => new(new("mv1-audit://" + name), "1", name);
