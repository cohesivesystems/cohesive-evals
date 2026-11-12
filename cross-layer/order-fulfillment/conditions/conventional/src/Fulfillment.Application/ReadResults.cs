using System.Text.Json;

namespace Fulfillment.Application;

// Public response limits, independent of storage representation. These check the
// materialized result; they are not streaming or database-memory guarantees.
public static class ReadResults
{
    public const int MaximumReservations = 1000;
    public const int MaximumBytes = 1_000_000;
    static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public static IResult Reply<T>(T value, int reservationCount)
    {
        if (reservationCount > MaximumReservations)
            return TooLarge();
        var bytes = JsonSerializer.SerializeToUtf8Bytes(value, Json);
        return bytes.Length > MaximumBytes
            ? TooLarge()
            : Results.Bytes(bytes, "application/json; charset=utf-8");
    }

    static IResult TooLarge() => Results.Json(new ErrorResponse("ReadResultTooLarge"), statusCode: 422);
}
