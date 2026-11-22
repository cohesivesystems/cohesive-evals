using Cohesive.Adapters.Postgres;

namespace Fulfillment.Application;

public sealed class AvailabilityProjection(PostgresMaterializedRows<ReservationAvailability> target)
{
    readonly PostgresMaterializedLookup<string, ReservationAvailability> byOrder = target.Lookup(row => row.OrderId);

    public Task Refresh() => target.ResyncAsync();

    public async Task<AvailabilityView[]?> Read(string id)
    {
        var rows = await byOrder.ReadAsync(id);
        if (rows.Length == 0) return null;
        return rows.Where(row => row.ReservationId is not null)
            .Select(row => row is (_, string reservationId, string sku, int quantity, int stock)
                ? new AvailabilityView(reservationId, sku, quantity, stock)
                : throw new InvalidOperationException("Incomplete persisted reservation."))
            .OrderBy(row => row.ReservationId, StringComparer.Ordinal)
            .ToArray();
    }
}
