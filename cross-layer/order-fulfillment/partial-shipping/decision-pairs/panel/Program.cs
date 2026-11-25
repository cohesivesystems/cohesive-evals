using System.Text.Json;
using Cohesive.Machines;
using Cohesive.Model.Authoring;
using Cohesive.Transitions.Assurance;
using Cohesive.Transitions.Authoring;
using Cohesive.Transitions.Machines;

var probe = Model.Make();
if (args is ["select"])
{
    var options = new CaseSelectionOptions<Article, Assessment> { MaxCases = 8, MaxCandidates = 1024 }
        .StateRange(a => a.Limit, 1, 4).InputRange(a => a.Risk, -1, 6);
    var suite = probe.SelectCases(new("fixture", 0, false, 2, -9), new(2), options);
    Console.WriteLine(JsonSerializer.Serialize(suite.Cases.Select(c => new Input(c.State.Phase, c.State.Embargo, c.State.Limit, c.Input.Risk))));
}
else if (args is ["execute"])
{
    var inputs = JsonSerializer.Deserialize<Input[]>(Console.In.ReadToEnd())!;
    var rows = inputs.Select((x, i) => {
        var run = probe.Execute(new("fixture", x.Phase, x.Embargo, x.Limit, -9), new(x.Risk), new($"case-{i}"));
        return new { Accepted = run.Decision.IsAccepted, run.Outcome, run.State };
    });
    Console.WriteLine(JsonSerializer.Serialize(rows));
}
else throw new ArgumentException("Expected select or execute.");

public sealed record Input(int Phase, bool Embargo, int Limit, int Risk);
public sealed record Article(string Id, int Phase, bool Embargo, int Limit, int LastScore);
public sealed record Assessment(int Risk);

static class Model
{
    public static TransitionProbe<Article, Assessment, bool> Make()
    {
        var machine = Machine.Define("publication", "1");
        var queued = machine.State("queued").Initial();
        var published = machine.State("published").Final();
        var review = machine.State("review");
        var withdrawn = machine.State("withdrawn").Final();
        machine.Edge("resubmit").From(review).To(queued);
        machine.Edge("withdraw").From(queued).To(withdrawn);
        var assess = machine.Action("assess");
        var publishEdge = assess.Edge("publish").From(queued).To(published);
        var reviewEdge = assess.Edge("review").From(queued).To(review);
#if TIE_REVIEW
        publishEdge.When((Article a, Assessment r) => r.Risk < a.Limit);
        reviewEdge.When((Article a, Assessment r) => r.Risk >= a.Limit);
#elif FIXED_LIMIT
        publishEdge.When((Article a, Assessment r) => r.Risk <= 2);
        reviewEdge.When((Article a, Assessment r) => r.Risk > 2);
#else
        publishEdge.When((Article a, Assessment r) => r.Risk <= a.Limit);
        reviewEdge.When((Article a, Assessment r) => r.Risk > a.Limit);
#endif
#if REASSESS_REVIEW
        assess.Edge("review-publish").From(review).To(published).When((Article a, Assessment r) => r.Risk <= a.Limit);
#endif
        var entity = new MachineDiscriminatorBinding<Article, int>(machine.Build(), a => a.Phase)
            .Map(queued, 0).Map(published, 1).Map(review, 2).Map(withdrawn, 3)
            .Bind(ObjectEntityDefinition.For<Article>(new("article")));
        var t = TransitionAuthoring.Create<Article, Assessment, bool>(entity.Shape, new("assess"), new("1"), t => {
#if EMBARGO_LOW
            t.Requires(new("clear"), (a,r) => !a.Embargo || r.Risk < a.Limit, (_,_) => false);
#elif !IGNORE_EMBARGO
            t.Requires(new("clear"), (a,r) => !a.Embargo, (_,_) => false);
#endif
#if REJECT_ZERO
            t.Requires(new("valid"), (a,r) => r.Risk > 0, (_,_) => false);
#elif ALLOW_NEGATIVE
            t.Requires(new("valid"), (a,r) => r.Risk >= -1, (_,_) => false);
#else
            t.Requires(new("valid"), (a,r) => r.Risk >= 0, (_,_) => false);
#endif
#if REJECT_MAX
            t.Requires(new("upper"), (a,r) => r.Risk < 6, (_,_) => false);
#endif
            t.Move(assess, (_,_) => false);
#if STORE_LIMIT
            t.Set(new("score"), a => a.LastScore, (a,r) => a.Limit);
#elif STORE_ZERO
            t.Set(new("score"), a => a.LastScore, (a,r) => 0);
#elif !STALE_SCORE
            t.Set(new("score"), a => a.LastScore, (a,r) => r.Risk);
#endif
            t.Return(true);
        });
        return TransitionAssurance.Prepare(t);
    }
}
