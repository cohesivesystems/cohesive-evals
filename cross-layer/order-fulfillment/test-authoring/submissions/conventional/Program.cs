using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Fulfillment.Application;

using var client = new HttpClient { BaseAddress = new Uri(args[0]) };
await new PackedSuite(client).Run();

internal sealed class PackedSuite(HttpClient client)
{
    private static readonly string[] States = ["Draft", "Submitted", "Packed", "Cancelled"];
    private static readonly string[] Actions = ["submit", "cancel", "pack", "unpack"];

    // One contract table drives independent domain, endpoint and concurrency checks.
    // Cells give the accepted destination or the conflict code.
    private static readonly string[,] Table =
    {
        { "Submitted", "Cancelled", "OrderNotPackable", "OrderNotUnpackable" },
        { "OrderNotDraft", "OrderNotCancellable", "Packed", "Submitted" },
        { "OrderNotDraft", "OrderNotCancellable", "Packed", "Submitted" },
        { "OrderCancelled", "Cancelled", "OrderNotPackable", "OrderNotUnpackable" }
    };

    private static string Decide(string state, string action) =>
        Table[Array.IndexOf(States, state), Array.IndexOf(Actions, action)];

    private static bool Accepted(string result) => Array.IndexOf(States, result) >= 0;

    public async Task Run()
    {
        DomainMatrix();
        await EndpointMatrix();
        await PackedFulfillment();
        await ReservationHistory();
        await ConcurrentCommands();
    }

    private static void DomainMatrix()
    {
        foreach (var state in States)
        foreach (var action in Actions)
        {
            var label = $"domain.{state}.{action}";
            Check.Equal(label + ".stateAvailable", true, Enum.TryParse<OrderStatus>(state, out var initial));
            Check.Equal(label + ".commandAvailable", true, Enum.TryParse<OrderCommand>(action, true, out var command));
            var current = new Order("opaque-ID", initial);
            var next = current.Apply(command);
            var expected = Decide(state, action);
            Check.Equal(label + ".result", Accepted(expected) ? expected : null, next?.Status.ToString());
            if (next is not null)
                Check.Equal(label + ".identity", current.Id, next.Id);
        }
    }

    private sealed record Reply(int Status, string Body)
    {
        internal JsonElement Json(string label)
        {
            try
            {
                using var document = JsonDocument.Parse(Body);
                return document.RootElement.Clone();
            }
            catch (JsonException)
            {
                Check.Equal(label + ".validJson", true, false);
                throw;
            }
        }
    }

    private async Task<Reply> Send(HttpMethod method, string path, string? body = null)
    {
        using var request = new HttpRequestMessage(method, path);
        if (body != null)
            request.Content = new StringContent(body, Encoding.UTF8, "application/json");
        using var response = await client.SendAsync(request);
        return new Reply((int)response.StatusCode, await response.Content.ReadAsStringAsync());
    }

    private static JsonElement Property(JsonElement value, string name) =>
        value.ValueKind == JsonValueKind.Object && value.TryGetProperty(name, out var field) ? field : default;

    private static string? Str(JsonElement value, string name)
    {
        var field = Property(value, name);
        return field.ValueKind == JsonValueKind.String ? field.GetString() : null;
    }

    private static int? Num(JsonElement value, string name)
    {
        var field = Property(value, name);
        return field.ValueKind == JsonValueKind.Number && field.TryGetInt32(out int count) ? count : null;
    }

    private static string PathFor(string id) => "/orders/" + Uri.EscapeDataString(id);

    private async Task<JsonElement> Get(string path, string label)
    {
        var response = await Send(HttpMethod.Get, path);
        Check.Equal(label + ".http", 200, response.Status);
        return response.Json(label);
    }

    private static void Summary(string label, JsonElement data, string id, string state)
    {
        Check.Equal(label + ".id", id, Str(data, "id"));
        Check.Equal(label + ".status", state, Str(data, "status"));
    }

    private async Task Views(string label, string id, string state, int quantity = 0, int stock = 20)
    {
        var path = PathFor(id);
        Summary(label + ".summary", await Get(path, label + ".summary"), id, state);
        var details = await Get(path + "/details", label + ".details");
        Summary(label + ".details", details, id, state);
        ReservationList(label + ".details", Property(details, "reservations"), "id", id, quantity, stock);
        var availability = await Get(path + "/availability", label + ".availability");
        ReservationList(label + ".availability", availability, "reservationId", id, quantity, stock);
    }

    private static void ReservationList(string label, JsonElement rows, string idKey, string id,
        int quantity, int stock)
    {
        int count = rows.ValueKind == JsonValueKind.Array ? rows.GetArrayLength() : -1;
        Check.Equal(label + ".count", quantity == 0 ? 0 : 1, count);
        if (quantity == 0) return;
        var row = rows[0];
        Check.Equal(label + ".reservationId", id, Str(row, idKey));
        Check.Equal(label + ".sku", "stock", Str(row, "sku"));
        Check.Equal(label + ".quantity", quantity, Num(row, "quantity"));
        Check.Equal(label + ".availableStock", stock, Num(row, "availableStock"));
    }

    private async Task Inventory(string label, int stock, int limit)
    {
        var data = await Get("/inventory/stock", label);
        Check.Equal(label + ".sku", "stock", Str(data, "sku"));
        Check.Equal(label + ".available", stock, Num(data, "available"));
        Check.Equal(label + ".maxPerOrder", limit, Num(data, "maxPerOrder"));
    }

    private async Task SetLimit(string label, int limit, int stock)
    {
        var reply = await Send(HttpMethod.Put, "/inventory/stock/quantity-limit",
            JsonSerializer.Serialize(new { maxPerOrder = limit }));
        Check.Equal(label + ".http", 200, reply.Status);
        var data = reply.Json(label);
        Check.Equal(label + ".available", stock, Num(data, "available"));
        Check.Equal(label + ".limit", limit, Num(data, "maxPerOrder"));
    }

    private async Task<string> Create(string label)
    {
        var reply = await Send(HttpMethod.Post, "/orders");
        Check.Equal(label + ".http", 201, reply.Status);
        var id = Str(reply.Json(label), "id");
        Check.Equal(label + ".nonblankId", true, !string.IsNullOrWhiteSpace(id));
        return id!;
    }

    private async Task Command(string label, string id, string from, string action, string? body = null)
    {
        var expected = Decide(from, action);
        var reply = await Send(HttpMethod.Post, PathFor(id) + "/" + action, body);
        Check.Equal(label + ".http", Accepted(expected) ? 200 : 409, reply.Status);
        var data = reply.Json(label);
        if (Accepted(expected))
            Summary(label + ".response", data, id, expected);
        else
            Check.Equal(label + ".code", expected, Str(data, "code"));
    }

    private async Task EndpointMatrix()
    {
        // The bogus body specifies another extant order and the opposite lifecycle command.
        // Exercise malformed JSON too: these routes do not parse the body.
        const string body = """{"id":"cancelled","orderId":"draft","status":"Draft","command":"cancel","sku":"stock","quantity":20}""";
        foreach (var state in States)
            await Views("seed." + state, state.ToLowerInvariant(), state);
        foreach (var action in new[] { "pack", "unpack" })
        {
            var missing = await Send(HttpMethod.Post, "/orders/PACKED/" + action, "{");
            Check.Equal("missing." + action + ".http", 404, missing.Status);
            Check.Equal("missing." + action + ".body", "", missing.Body);
        }

        foreach (var (id, initial, steps) in new (string, string, string[])[]
        {
            ("draft", "Draft", ["pack", "unpack", "cancel", "pack", "unpack", "submit", "cancel"]),
            ("cancelled", "Cancelled", ["unpack", "pack"]),
            ("packed", "Packed", ["pack", "cancel", "submit", "unpack", "unpack", "pack"]),
            ("submitted", "Submitted", ["cancel", "submit", "unpack", "pack", "pack", "unpack"])
        })
        {
            var state = initial;
            for (int i = 0; i < steps.Length; ++i)
            {
                var action = steps[i];
                var label = $"http.{id}.{i}.{state}.{action}";
                await Command(label, id, state, action, action is "pack" or "unpack" ? (i % 2 == 0 ? body : "{") : null);
                var result = Decide(state, action);
                if (Accepted(result)) state = result;
                await Views(label, id, state);
            }
        }
        await Inventory("http.stockPreserved", 20, int.MaxValue);
        await Views("http.unrelatedCancelled", "cancelled", "Cancelled");
        await Views("http.unrelatedPacked", "packed", "Packed");
    }

    private sealed record Admission(string Operation, string Url);

    private async Task<Admission> Fulfill(string label, string requestId, string id, string sku, int quantity,
        string outcome, Admission? retained = null)
    {
        var body = JsonSerializer.Serialize(new { requestId, orderId = id, sku, quantity });
        var response = await Send(HttpMethod.Post, "/fulfillment", body);
        Check.Equal(label + ".admission.http", 202, response.Status);
        var data = response.Json(label);
        var operation = Str(data, "operationId");
        var url = Str(data, "resultUrl");
        Check.Equal(label + ".operationId", true, !string.IsNullOrWhiteSpace(operation));
        Check.Equal(label + ".resultUrl", true, !string.IsNullOrWhiteSpace(url));
        if (retained != null)
        {
            Check.Equal(label + ".retainedId", retained.Operation, operation);
            Check.Equal(label + ".retainedUrl", retained.Url, url);
        }

        // Keep all probes on the assigned host even if a candidate returns a malformed link.
        var valid = Uri.TryCreate(client.BaseAddress, url, out var resultUri)
            && resultUri.Scheme == client.BaseAddress!.Scheme && resultUri.Authority == client.BaseAddress.Authority;
        Check.Equal(label + ".localResult", true, valid);
        var timer = Stopwatch.StartNew();
        Reply result;
        do
        {
            result = await Send(HttpMethod.Get, resultUri!.PathAndQuery);
            if (result.Status != 202) break;
            if (timer.Elapsed.TotalSeconds > 8)
                throw new TimeoutException(label + " did not complete");
            await Task.Delay(10);
        } while (true);

        Check.Equal(label + ".completion.http", 200, result.Status);
        var completed = result.Json(label);
        Check.Equal(label + ".outcome", outcome, Str(completed, "outcome"));
        Check.Equal(label + ".status", outcome == "ReservedAndSubmitted" ? "Submitted" : "Rejected", Str(completed, "status"));
        return new Admission(operation!, url!);
    }

    private async Task PackedFulfillment()
    {
        // A packed order without a reservation must traverse every earlier inventory decision.
        await SetLimit("precedence.limit", 5, 20);
        foreach (var (id, sku, qty, outcome) in new (string, string, int, string)[]
        {
            ("missing", "absent", 0, "OrderMissing"),
            ("packed", "absent", 0, "InventoryMissing"),
            ("packed", "stock", 0, "InvalidQuantity"),
            ("packed", "stock", -3, "InvalidQuantity"),
            ("packed", "stock", 6, "QuantityLimitExceeded"),
            ("packed", "stock", 21, "QuantityLimitExceeded"),
            ("packed", "stock", 5, "OrderRejected"),
            ("cancelled", "stock", 5, "OrderCancelled")
        })
        {
            var key = $"precedence.{id}.{sku}.{qty}";
            await Fulfill(key, key, id, sku, qty, outcome);
            await Inventory(key + ".effects", 20, 5);
            await Views(key + ".packed", "packed", "Packed");
        }
        await SetLimit("precedence.raise", 21, 20);
        var retained = await Fulfill("precedence.stock", "no-stock", "packed", "stock", 21, "InsufficientStock");
        await SetLimit("precedence.lower", 4, 20);
        await Command("precedence.unpack", "packed", "Packed", "unpack");
        await Fulfill("precedence.replayAfterUnpack", "no-stock", "packed", "stock", 21, "InsufficientStock", retained);
        await Fulfill("precedence.freshAfterUnpack", "fresh-no-stock", "packed", "stock", 21, "QuantityLimitExceeded");
        await Inventory("precedence.endStock", 20, 4);
        await Views("precedence.endOrder", "packed", "Submitted");
    }

    private async Task ReservationHistory()
    {
        var id = await Create("history.create");
        var reserved = await Fulfill("history.reserve", "original", id, "stock", 4, "ReservedAndSubmitted");
        await Command("history.pack", id, "Submitted", "pack", "{");
        await Inventory("history.packedStock", 16, 4);
        await Views("history.packed", id, "Packed", 4, 16);
        await Command("history.packAgain", id, "Packed", "pack");
        await Command("history.submitWhilePacked", id, "Packed", "submit");
        await Command("history.cancelWhilePacked", id, "Packed", "cancel");
        await SetLimit("history.lowerLimit", 1, 16);
        var conflict = await Fulfill("history.matchWhilePacked", "match-packed", id, "stock", 4, "ReservationConflict");
        await Fulfill("history.mismatchWhilePacked", "mismatch-packed", id, "absent", 0, "ReservationConflict");
        await Fulfill("history.replayWhilePacked", "original", id, "stock", 4, "ReservedAndSubmitted", reserved);
        var changed = await Send(HttpMethod.Post, "/fulfillment", JsonSerializer.Serialize(
            new { requestId = "original", orderId = id, sku = "stock", quantity = 1 }));
        Check.Equal("history.identityConflict.http", 409, changed.Status);
        Check.Equal("history.identityConflict.code", "RequestIdentityConflict", Str(changed.Json("history.identityConflict"), "code"));

        // A second order changes live stock while the first remains packed.
        var other = await Create("history.other");
        await Fulfill("history.otherReserve", "other", other, "stock", 1, "ReservedAndSubmitted");
        await Views("history.currentStockInPackedViews", id, "Packed", 4, 15);
        await Command("history.unpack", id, "Packed", "unpack", "{");
        await Views("history.unpacked", id, "Submitted", 4, 15);
        await Command("history.unpackAgain", id, "Submitted", "unpack");
        await Fulfill("history.replayConflictAfterUnpack", "match-packed", id, "stock", 4, "ReservationConflict", conflict);
        await Fulfill("history.matchAfterUnpack", "match-submitted", id, "stock", 4, "ReservedAndSubmitted");
        await Fulfill("history.mismatchAfterUnpack", "mismatch-submitted", id, "absent", -1, "ReservationConflict");
        await Command("history.repack", id, "Submitted", "pack");
        await Views("history.repacked", id, "Packed", 4, 15);
        await Views("history.otherUnchanged", other, "Submitted", 1, 15);
        await Inventory("history.netStockAndLimit", 15, 1);
    }

    private async Task ConcurrentCommands()
    {
        // Race lifecycle commands on a fresh Draft. Enumerate legal serial executions
        // with the same responses (including IDs) and persisted final state.
        string[] actions = ["submit", "cancel", "pack", "unpack", "submit"];
        for (int round = 0; round < 12; ++round)
        {
            var label = "race." + round;
            var id = await Create(label + ".create");
            var tasks = Enumerable.Range(0, actions.Length)
                .Select(i => actions[(round + i) % actions.Length])
                .Select(async action => (action, response: await Send(HttpMethod.Post, PathFor(id) + "/" + action)))
                .ToArray();
            var observations = await Task.WhenAll(tasks);
            var values = new string[actions.Length];
            for (int i = 0; i < observations.Length; ++i)
            {
                var reply = observations[i].response;
                Check.Equal(label + "." + i + ".isLifecycleReply", true, reply.Status is 200 or 409);
                var value = reply.Json(label);
                if (reply.Status == 200)
                    Check.Equal(label + "." + i + ".id", id, Str(value, "id"));
                values[i] = reply.Status + "/" + Str(value, reply.Status == 200 ? "status" : "code");
            }
            var summary = await Get(PathFor(id), label + ".persisted");
            var finalState = Str(summary, "status");
            bool Matches(string state, int seen)
            {
                if (seen == (1 << actions.Length) - 1) return state == finalState;
                for (int i = 0; i < actions.Length; ++i)
                {
                    if ((seen & (1 << i)) != 0) continue;
                    var expected = Decide(state, observations[i].action);
                    var ok = Accepted(expected);
                    if (values[i] == (ok ? "200/" : "409/") + expected &&
                        Matches(ok ? expected : state, seen | (1 << i))) return true;
                }
                return false;
            }
            Check.Equal(label + ".matchesSerialHistory", true, Matches("Draft", 0));
        }
        await Inventory("race.stockPreserved", 15, 1);
    }
}
