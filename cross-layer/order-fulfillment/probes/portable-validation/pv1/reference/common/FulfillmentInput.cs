namespace Fulfillment.Application;

// Shared application validation after standard DTO deserialization. Nonpositive
// quantity remains valid input and is rejected by the domain, not this predicate.
public static class FulfillmentInput
{
    public static bool IsValid(FulfillmentRequest request) =>
        !string.IsNullOrWhiteSpace(request.RequestId) && !string.IsNullOrWhiteSpace(request.OrderId)
        && !string.IsNullOrWhiteSpace(request.Sku);
}
