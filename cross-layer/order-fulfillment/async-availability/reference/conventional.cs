namespace Fulfillment.Application;

public sealed partial class AvailabilityMaintenance
{
    static readonly string[] SourceTables = ["orders", "reservations", "inventory"];
}
