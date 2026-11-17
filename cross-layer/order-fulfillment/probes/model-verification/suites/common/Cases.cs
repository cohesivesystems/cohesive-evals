public sealed record Case(string Name, string Sku, int Available, int MaxPerOrder, bool Quarantined, int Quantity);
public sealed record State(string Sku, int Available, int MaxPerOrder, bool Quarantined);
public sealed record Result(string Name, string Outcome, string FulfillmentOutcome, State After, bool ScopePreserved);
