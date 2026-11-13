using System.Globalization;
using System.Text.Json;

namespace Fulfillment.Application;

// Wire decoding and input-only rules are shared by HTTP and batch. Domain rules
// stay in the backend; notably, nonpositive quantity is not an input error.
public static class FulfillmentInput
{
    public static bool IsValid(FulfillmentRequest request) =>
        !string.IsNullOrWhiteSpace(request.RequestId) && !string.IsNullOrWhiteSpace(request.OrderId)
        && !string.IsNullOrWhiteSpace(request.Sku);

    public static FulfillmentRequest? Parse(JsonElement item)
    {
        if (item.ValueKind != JsonValueKind.Object) return null;
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in item.EnumerateObject())
            if (!names.Add(property.Name)) return null;
        string? Text(string name) => item.TryGetProperty(name, out var value)
            && value.ValueKind == JsonValueKind.String ? value.GetString() : null;
        var requestId = Text("requestId");
        var orderId = Text("orderId");
        var sku = Text("sku");
        if (requestId is null || orderId is null || sku is null
            || !item.TryGetProperty("quantity", out var quantity) || !Integer(quantity, out var number)) return null;
        var request = new FulfillmentRequest(requestId, orderId, sku, number);
        return IsValid(request) ? request : null;
    }

    // Inspect decimal digits exactly: floating-point/decimal rounding must not
    // admit a fractional JSON value that happens to round to an integer.
    static bool Integer(JsonElement value, out int result)
    {
        result = 0;
        if (value.ValueKind != JsonValueKind.Number) return false;
        var parts = value.GetRawText().ToLowerInvariant().Split('e');
        var mantissa = parts[0];
        var negative = mantissa.StartsWith('-');
        if (negative) mantissa = mantissa[1..];
        var point = mantissa.IndexOf('.');
        var fraction = point < 0 ? 0 : mantissa.Length - point - 1;
        var digits = mantissa.Replace(".", "").TrimStart('0');
        if (digits.Length == 0) return true;
        if (parts.Length == 2 && !int.TryParse(parts[1], NumberStyles.AllowLeadingSign,
                CultureInfo.InvariantCulture, out _)) return false;
        var exponent = parts.Length == 2 ? int.Parse(parts[1], CultureInfo.InvariantCulture) : 0;
        long scale = (long)exponent - fraction;
        var trimmed = digits.TrimEnd('0');
        scale += digits.Length - trimmed.Length;
        if (scale < 0 || trimmed.Length + scale > 10) return false;
        var integer = (negative ? "-" : "") + trimmed + new string('0', (int)scale);
        return int.TryParse(integer, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out result);
    }

    public static async Task<IResult> AdmitHttp(HttpRequest http, OperationQueue queue)
    {
        try
        {
            using var document = await JsonDocument.ParseAsync(http.Body, cancellationToken: http.HttpContext.RequestAborted);
            return Parse(document.RootElement) is { } request ? queue.Admit(request) : Results.BadRequest();
        }
        catch (JsonException) { return Results.BadRequest(); }
    }
}
