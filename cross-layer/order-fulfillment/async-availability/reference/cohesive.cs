namespace Fulfillment.Application;

public sealed partial class AvailabilityMaintenance
{
    static readonly string[] SourceTables = ["cohesive_orders", "cohesive_reservations", "cohesive_inventory"];
}
