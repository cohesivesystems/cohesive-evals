using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Cohesive.Prelude;
using Cohesive.Execution;
using Cohesive.Model;
using Cohesive.Transitions.Compilation;
using Cohesive.Transitions.Execution;
using Fulfillment.Application;

internal static class Program
{
    private static readonly HttpClient Client = new();
    private static readonly string[] States = ["Draft", "Submitted", "Packed", "Cancelled"];
    private static readonly string[] Commands = ["pack", "unpack", "submit", "cancel"];

    private sealed record Reply(int Http, string Body)
    {
        public JsonNode? Json()
        {
            try { return JsonNode.Parse(Body); }
            catch (JsonException) { return null; }
        }
    }

    private sealed record Expected(int Http, string Status, string? Code = null);

    // Independent lifecycle oracle shared by persisted HTTP and reference execution checks.
    private static Expected Decide(string state, string command) => (state, command) switch
    {
        ("Submitted" or "Packed", "pack") => new(200, "Packed"),
        ("Submitted" or "Packed", "unpack") => new(200, "Submitted"),
        ("Draft", "submit") => new(200, "Submitted"),
        ("Draft" or "Cancelled", "cancel") => new(200, "Cancelled"),
        (_, "pack") => new(409, state, "OrderNotPackable"),
        (_, "unpack") => new(409, state, "OrderNotUnpackable"),
        ("Cancelled", "submit") => new(409, state, "OrderCancelled"),
        (_, "submit") => new(409, state, "OrderNotDraft"),
        (_, "cancel") => new(409, state, "OrderNotCancellable"),
        _ => throw new ArgumentException("Unknown command", nameof(command))
    };

    private static void Offline()
    {
        var domain = new FulfillmentDomain();
        var transitions = domain.OrderTransitions;
        var plans = new Dictionary<string, CompiledTransitionPlan?>
        {
            ["pack"] = transitions.Pack.Compile().Plan,
            ["unpack"] = transitions.Unpack.Compile().Plan,
            ["submit"] = transitions.Submit.Compile().Plan,
            ["cancel"] = transitions.Cancel.Compile().Plan
        };
        foreach (string state in States)
        {
            var before = new Order("case-Sensitive/ß", "partition-X", Enum.Parse<OrderStatus>(state));
            var observation = ObservationValue.FromObject(before);
            foreach (string command in Commands)
            {
                string label = $"offline/{state}/{command}";
                var expected = Decide(state, command);
                var plan = plans[command] ?? throw new InvalidOperationException("Could not compile " + command);
                var result = TransitionReferenceInterpreter.DecideFullState(plan, new(label),
                    PortableValue.Concrete(plan.Definition.Input, ObservationValue.FromObject(default(Unit))),
                    PortableValue.Concrete(plan.Definition.Observation, observation));
                var accepted = result.Kind.ToString() is "Applied" or "NoChange";
                Check.Equal(label + "/accepted", expected.Http == 200, accepted);
                var after = TransitionStateProjector.Apply(observation, result).Deserialize<Order>()!;
                Check.Equal(label + "/state", expected.Status, after.Status.ToString());
                Check.Equal(label + "/id", before.Id, after.Id);
                Check.Equal(label + "/partition", before.Partition, after.Partition);
                var value = result.Outcome?.Value;
                if (command is "pack" or "unpack")
                    Check.Equal(label + "/outcome", expected.Http == 200, value?.GetBoolean());
                else if (command == "submit")
                {
                    var outcome = value?.Deserialize<SubmitOrderResult>();
                    string expectedOutcome = expected.Code == "OrderNotDraft" ? "NotDraft" : expected.Code ?? "Submitted";
                    Check.Equal(label + "/outcome", expectedOutcome, outcome?.Outcome.ToString());
                    Check.Equal(label + "/reported-state", expected.Status, outcome?.Status.ToString());
                    Check.Equal(label + "/process-outcome", state switch {
                        "Draft" => "ReservedAndSubmitted", "Cancelled" => "OrderCancelled", _ => "OrderRejected"
                    }, outcome?.FulfillmentOutcome.ToString());
                }
                else
                    Check.Equal(label + "/outcome", expected.Http == 200 ? "Cancelled" : "NotCancellable", value?.GetString());
            }
        }
    }

    private static async Task<Reply> Send(HttpMethod method, string path, string? body = null)
    {
        using var request = new HttpRequestMessage(method, path);
        if (body != null)
            request.Content = new StringContent(body, Encoding.UTF8, "application/json");
        using var response = await Client.SendAsync(request);
        return new((int)response.StatusCode, await response.Content.ReadAsStringAsync());
    }

    private static string? Field(JsonNode? node, string name) =>
        node is JsonObject obj && obj[name] is JsonValue v && v.TryGetValue<string>(out var text) ? text : null;

    private static int? Number(JsonNode? node, string name) =>
        node is JsonObject obj && obj[name] is JsonValue v && v.TryGetValue<int>(out var n) ? n : null;

    private static string PathFor(string id) => "/orders/" + Uri.EscapeDataString(id);

    private static async Task<string> Create(string label)
    {
        var response = await Send(HttpMethod.Post, "/orders");
        Check.Equal(label + "/create", 201, response.Http);
        var id = Field(response.Json(), "id");
        Check.Equal(label + "/nonblank-id", true, !string.IsNullOrWhiteSpace(id));
        return id!;
    }

    private static async Task Command(string id, string state, string command, string label, string? body = null)
    {
        var response = await Send(HttpMethod.Post, PathFor(id) + "/" + command, body);
        CheckCommand(label, id, Decide(state, command), response);
    }

    private static void CheckCommand(string label, string id, Expected expected, Reply response)
    {
        Check.Equal(label + "/http", expected.Http, response.Http);
        var json = response.Json();
        if (expected.Http == 200)
        {
            Check.Equal(label + "/id", id, Field(json, "id"));
            Check.Equal(label + "/status", expected.Status, Field(json, "status"));
        }
        else
            Check.Equal(label + "/code", expected.Code, Field(json, "code"));
    }

    private static async Task Views(string id, string status, string label, int? reserved = null, int stock = 20)
    {
        var path = PathFor(id);
        var summary = await Send(HttpMethod.Get, path);
        Check.Equal(label + "/summary/http", 200, summary.Http);
        Check.Equal(label + "/summary/id", id, Field(summary.Json(), "id"));
        Check.Equal(label + "/summary/status", status, Field(summary.Json(), "status"));
        var details = await Send(HttpMethod.Get, path + "/details");
        Check.Equal(label + "/details/http", 200, details.Http);
        var detail = details.Json() as JsonObject;
        Check.Equal(label + "/details/id", id, Field(detail, "id"));
        Check.Equal(label + "/details/status", status, Field(detail, "status"));
        Rows(detail?["reservations"], "id", label + "/details");
        var availability = await Send(HttpMethod.Get, path + "/availability");
        Check.Equal(label + "/availability/http", 200, availability.Http);
        Rows(availability.Json(), "reservationId", label + "/availability");

        void Rows(JsonNode? node, string key, string prefix)
        {
            var rows = node as JsonArray;
            Check.Equal(prefix + "/count", reserved == null ? 0 : 1, rows?.Count ?? -1);
            if (reserved != null)
            {
                var row = rows![0];
                Check.Equal(prefix + "/reservation-id", id, Field(row, key));
                Check.Equal(prefix + "/sku", "stock", Field(row, "sku"));
                Check.Equal(prefix + "/quantity", reserved, Number(row, "quantity"));
                Check.Equal(prefix + "/available", stock, Number(row, "availableStock"));
            }
        }
    }

    private static async Task Stock(int available, int limit, string label)
    {
        var response = await Send(HttpMethod.Get, "/inventory/stock");
        Check.Equal(label + "/inventory/http", 200, response.Http);
        var item = response.Json();
        Check.Equal(label + "/sku", "stock", Field(item, "sku"));
        Check.Equal(label + "/available", available, Number(item, "available"));
        Check.Equal(label + "/limit", limit, Number(item, "maxPerOrder"));
    }

    private static async Task Limit(int limit, string label)
    {
        var response = await Send(HttpMethod.Put, "/inventory/stock/quantity-limit",
            JsonSerializer.Serialize(new { maxPerOrder = limit }));
        Check.Equal(label + "/change-limit", 200, response.Http);
        Check.Equal(label + "/limit-value", limit, Number(response.Json(), "maxPerOrder"));
    }

    private sealed record Ticket(string Operation, string Url);
    private static string Request(string requestId, string orderId, string sku, int quantity) =>
        JsonSerializer.Serialize(new { requestId, orderId, sku, quantity });

    private static async Task<Ticket> Fulfill(string requestId, string id, string sku, int quantity, string outcome,
        Ticket? original = null)
    {
        var label = "fulfill/" + requestId + (original == null ? "" : "/replay");
        var admission = await Send(HttpMethod.Post, "/fulfillment", Request(requestId, id, sku, quantity));
        Check.Equal(label + "/admitted", 202, admission.Http);
        var json = admission.Json();
        var operation = Field(json, "operationId");
        var url = Field(json, "resultUrl");
        Check.Equal(label + "/operation-id", true, !string.IsNullOrWhiteSpace(operation));
        Check.Equal(label + "/result-url", true, !string.IsNullOrWhiteSpace(url));
        var ticket = new Ticket(operation!, url!);
        if (original != null)
        {
            Check.Equal(label + "/original-operation", original.Operation, ticket.Operation);
            Check.Equal(label + "/original-url", original.Url, ticket.Url);
        }
        // Poll the known public route on this host, with a bounded per-operation deadline.
        var timer = Stopwatch.StartNew();
        Reply result;
        do
        {
            result = await Send(HttpMethod.Get, "/fulfillment/results/" + Uri.EscapeDataString(ticket.Operation));
            if (result.Http != 202) break;
            await Task.Delay(15);
        } while (timer.Elapsed < TimeSpan.FromSeconds(12));
        Check.Equal(label + "/completion-http", 200, result.Http);
        Check.Equal(label + "/status", outcome == "ReservedAndSubmitted" ? "Submitted" : "Rejected", Field(result.Json(), "status"));
        Check.Equal(label + "/outcome", outcome, Field(result.Json(), "outcome"));
        return ticket;
    }

    private static async Task TransportTransitions()
    {
        foreach (string command in new[] { "pack", "unpack" })
        {
            foreach (var (suffix, body) in new (string, string?)[] {
                ("absent", null), ("case-sensitive", """{"id":"submitted"}"""), ("broken-body", "[" ) })
            {
                string id = suffix == "case-sensitive" ? "SUBMITTED" : "absent";
                var reply = await Send(HttpMethod.Post, PathFor(id) + "/" + command, body);
                Check.Equal($"{command}/missing/{suffix}/http", 404, reply.Http);
                Check.Equal($"{command}/missing/{suffix}/empty", "", reply.Body);
            }
        }

        foreach (string state in States)
        {
            string seed = state.ToLowerInvariant();
            await Views(seed, state, "seed/" + seed);
        }
        foreach (string state in new[] { "Draft", "Cancelled" })
        {
            string seed = state.ToLowerInvariant();
            foreach (string command in new[] { "pack", "unpack" })
            {
                string label = $"wire/{state}/{command}";
                await Command(seed, state, command, label, "{");
                await Views(seed, state, label);
            }
        }

        foreach (var (id, initial, sequence) in new[] {
            ("submitted", "Submitted", new[] { "unpack","pack","pack","submit","cancel","unpack","unpack","pack","unpack" }),
            ("packed", "Packed", new[] { "submit","cancel","pack","unpack","pack","pack" })
        })
        {
            string state = initial;
            for (int i = 0; i < sequence.Length; i++)
            {
                string command = sequence[i];
                string label = $"wire/{id}/{i}/{command}";
                string? body = (command is "pack" or "unpack") ? (i % 3) switch {
                    0 => "{", 1 => """{"id":"draft","status":"Cancelled","orderId":"packed","partition":"other"}""",
                    _ => null
                } : null;
                await Command(id, state, command, label, body);
                state = Decide(state, command).Status;
                await Views(id, state, label);
            }
        }
        await Views("cancelled", "Cancelled", "unrelated/cancelled");
        await Views("draft", "Draft", "unrelated/draft");
        await Stock(20, int.MaxValue, "after-lifecycle-roundtrips");
    }

    private static async Task ProcessHistory()
    {
        const string packed = "packed";
        await Limit(25, "packed/initial-limit");
        var checks = new (string Name, string Sku, int Quantity, string Outcome)[] {
            ("missing-sku", "absent", 0, "InventoryMissing"),
            ("zero", "stock", 0, "InvalidQuantity"),
            ("negative", "stock", -1, "InvalidQuantity"),
            ("above-both", "stock", 26, "QuantityLimitExceeded"),
            ("above-available", "stock", 25, "InsufficientStock"),
            ("exact-available", "stock", 20, "OrderRejected"),
            ("within-bounds", "stock", 3, "OrderRejected")
        };
        foreach (var test in checks)
        {
            await Fulfill(test.Name, packed, test.Sku, test.Quantity, test.Outcome);
            await Stock(20, 25, test.Name);
            await Views(packed, "Packed", test.Name);
        }
        await Limit(5, "packed/lower-limit");
        await Fulfill("above-limit-only", packed, "stock", 6, "QuantityLimitExceeded");
        await Stock(20, 5, "packed/limit-rejected");

        string id = await Create("reachable");
        await Views(id, "Draft", "reachable/new");
        var success = await Fulfill("original", id, "stock", 5, "ReservedAndSubmitted");
        await Views(id, "Submitted", "reachable/reserved", 5, 15);
        await Command(id, "Submitted", "pack", "reachable/pack", "not-json");
        await Views(id, "Packed", "reachable/packed", 5, 15);
        await Stock(15, 5, "reachable/packed-stock");
        await Command(id, "Packed", "pack", "reachable/pack-again");
        await Command(id, "Packed", "submit", "reachable/packed-submit");
        await Command(id, "Packed", "cancel", "reachable/packed-cancel");
        await Limit(1, "reachable/lower-limit");

        // Fresh intents inspect the current lifecycle. An admitted duplicate retains its result.
        await Fulfill("original", id, "stock", 5, "ReservedAndSubmitted", success);
        var conflict = await Fulfill("fresh-packed", id, "stock", 5, "ReservationConflict");
        await Fulfill("conflict-sku", id, "absent", -1, "ReservationConflict");
        await Fulfill("conflict-qty", id, "stock", 1, "ReservationConflict");
        var reused = await Send(HttpMethod.Post, "/fulfillment", Request("original", id, "stock", 1));
        Check.Equal("reachable/identity-conflict/http", 409, reused.Http);
        Check.Equal("reachable/identity-conflict/code", "RequestIdentityConflict", Field(reused.Json(), "code"));
        await Views(id, "Packed", "reachable/after-conflicts", 5, 15);
        await Stock(15, 1, "reachable/after-conflicts");

        await Command(id, "Packed", "unpack", "reachable/unpack", "null");
        await Views(id, "Submitted", "reachable/unpacked", 5, 15);
        await Fulfill("fresh-packed", id, "stock", 5, "ReservationConflict", conflict);
        await Fulfill("fresh-unpacked", id, "stock", 5, "ReservedAndSubmitted");
        await Fulfill("unpacked-mismatch", id, "stock", 4, "ReservationConflict");
        await Stock(15, 1, "reachable/no-double-reservation");
        await Command(id, "Submitted", "unpack", "reachable/unpack-again");
        await Command(id, "Submitted", "pack", "reachable/repack");

        string other = await Create("other");
        await Fulfill("other-success", other, "stock", 1, "ReservedAndSubmitted");
        await Views(id, "Packed", "reachable/live-availability", 5, 14);
        await Command(id, "Packed", "unpack", "reachable/final-unpack");
        await Views(other, "Submitted", "unrelated/reservation", 1, 14);
        await Views(id, "Submitted", "reachable/final", 5, 14);
        await Views(packed, "Packed", "unrelated/seed-packed");
        await Stock(14, 1, "reachable/final-stock");
    }

    private static async Task ConcurrentCommands()
    {
        string id = await Create("concurrent");
        await Command(id, "Draft", "submit", "concurrent/bootstrap");
        // Each same-command wave has exactly one possible final state in every serialization.
        string state = "Submitted";
        for (int wave = 0; wave < 4; wave++)
        {
            string command = wave % 2 == 0 ? "pack" : "unpack";
            var responses = await Task.WhenAll(Enumerable.Range(0, 10)
                .Select(_ => Send(HttpMethod.Post, PathFor(id) + "/" + command)));
            var expected = Decide(state, command);
            for (int i = 0; i < responses.Length; i++)
                CheckCommand($"concurrent/{wave}/{command}/{i}", id, expected, responses[i]);
            state = expected.Status;
            await Views(id, state, $"concurrent/{wave}/committed");
        }

        // A status read between two nonoverlapping waves cannot observe a stale prior write.
        // In a mixed wave every pack and unpack succeeds and reports its own destination.
        var commands = new[] { "pack", "unpack", "pack", "unpack", "pack", "unpack", "pack", "unpack" };
        var mixed = await Task.WhenAll(commands.Select(cmd => Send(HttpMethod.Post, PathFor(id) + "/" + cmd)));
        for (int i = 0; i < mixed.Length; i++)
            CheckCommand("concurrent/mixed/" + i, id, Decide("Submitted", commands[i]), mixed[i]);
        var final = await Send(HttpMethod.Get, PathFor(id));
        Check.Equal("concurrent/mixed/final-http", 200, final.Http);
        Check.Equal("concurrent/mixed/serializable", true, Field(final.Json(), "status") is "Packed" or "Submitted");

        // The pack/submit race from Draft has two feasible histories, distinguishable by pack's response.
        for (int i = 0; i < 4; i++)
        {
            var order = await Create("concurrent/race");
            var path = PathFor(order);
            var submit = Send(HttpMethod.Post, path + "/submit");
            var pack = Send(HttpMethod.Post, path + "/pack");
            await Task.WhenAll(submit, pack);
            CheckCommand("concurrent/submit/" + i, order, Decide("Draft","submit"), await submit);
            var packed = await pack;
            string prior = packed.Http == 409 ? "Draft" : "Submitted";
            CheckCommand("concurrent/pack/" + i, order, Decide(prior,"pack"), packed);
            await Views(order, prior == "Draft" ? "Submitted" : "Packed", "concurrent/final/" + i);
        }
        await Stock(14, 1, "concurrent/stock");
    }

    public static async Task Main(string[] args)
    {
        Client.BaseAddress = new Uri(args[0]);
        Offline();
        await TransportTransitions();
        await ProcessHistory();
        await ConcurrentCommands();
    }
}
