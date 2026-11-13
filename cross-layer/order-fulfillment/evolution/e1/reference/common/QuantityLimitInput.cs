using System.Text.Json;
using System.Globalization;
namespace Fulfillment.Application;

public sealed record QuantityLimit(int MaxPerOrder);

// Identical transport parsing in both conditions. Domain enforcement stays local
// to each implementation. Invalid configuration is rejected before entity lookup.
public sealed class QuantityLimitInput : IEndpointFilter
{
    static readonly object Key = new();
    public static QuantityLimit Get(HttpContext context) => (QuantityLimit)context.Items[Key]!;
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        try
        {
            using var body = await JsonDocument.ParseAsync(context.HttpContext.Request.Body);
            if (body.RootElement.ValueKind != JsonValueKind.Object
                || !body.RootElement.TryGetProperty("maxPerOrder", out var value)
                || !TryPositiveInt32(value, out var number))
                return Results.BadRequest();
            context.HttpContext.Items[Key] = new QuantityLimit(number);
        }
        catch (JsonException) { return Results.BadRequest(); }
        return await next(context);
    }
    // Inspect the decimal representation exactly: floating/decimal rounding must
    // not turn a tiny fractional part into an accepted integer.
    static bool TryPositiveInt32(JsonElement value, out int number)
    {
        number = 0;
        if (value.ValueKind != JsonValueKind.Number) return false;
        var raw = value.GetRawText();
        if (raw.StartsWith('-')) return false;
        var e = raw.IndexOfAny(['e', 'E']);
        var exponent = 0;
        if (e >= 0 && !int.TryParse(raw[(e + 1)..], NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out exponent)) return false;
        var mantissa = e < 0 ? raw : raw[..e];
        var dot = mantissa.IndexOf('.');
        var fraction = dot < 0 ? 0 : mantissa.Length - dot - 1;
        var digits = mantissa.Replace(".", "").TrimStart('0');
        var significant = digits.TrimEnd('0');
        if (significant.Length == 0) return false;
        long scale = (long)exponent - fraction + digits.Length - significant.Length;
        if (scale < 0 || significant.Length + scale > 10) return false;
        return int.TryParse(significant + new string('0', (int)scale), NumberStyles.None,
            CultureInfo.InvariantCulture, out number) && number > 0;
    }

}
