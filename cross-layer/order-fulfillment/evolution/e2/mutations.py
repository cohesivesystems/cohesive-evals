"""Generation-specific, exactly anchored application defects."""
def mutations(condition):
    cases = {
        'lost-replay': ('OperationQueue.cs', 'Results.Json(previous.Admission, statusCode: 202)',
                        'Results.Conflict(new ErrorResponse("LostReplay"))', 'E2-03'),
    }
    if condition == 'conventional':
        cases.update({
            'stock-outcome-projection': ('FulfillmentResults.cs', 'StockOutcome.QuantityLimitExceeded => "QuantityLimitExceeded"', 'StockOutcome.QuantityLimitExceeded => "InsufficientStock"', 'E2-02'),
            'cancel-submitted': ('Domain.cs', 'order.Status is OrderStatus.Draft or OrderStatus.Cancelled', 'true', 'E2-01'),
            'non-idempotent-cancel': ('Domain.cs', 'order.Status is OrderStatus.Draft or OrderStatus.Cancelled', 'order.Status == OrderStatus.Draft', 'E2-01'),
            'direct-submit-code': ('FulfillmentBackend.cs', 'SubmissionOutcome.OrderCancelled => Results.Conflict(new ErrorResponse("OrderCancelled"))',
                                   'SubmissionOutcome.OrderCancelled => Results.Conflict(new ErrorResponse("OrderNotDraft"))', 'E2-02'),
            'fulfillment-code': ('FulfillmentResults.cs', 'SubmissionOutcome.OrderCancelled => "OrderCancelled"', 'SubmissionOutcome.OrderCancelled => "OrderRejected"', 'E2-02'),
            'early-cancellation': ('FulfillmentBackend.cs', 'if (order is null) return Reject("OrderMissing");',
                                   'if (order is null) return Reject("OrderMissing");\n        if (order.Status == OrderStatus.Cancelled) return Reject("OrderCancelled");', 'E2-02'),
            'skipped-compensation': ('FulfillmentBackend.cs', 'await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");', '', 'E2-02'),
        })
    else:
        cases.update({
            'stock-outcome-projection': ('FulfillmentDomain.cs', 'StockOutcome.QuantityLimitExceeded, FulfillmentOutcome.QuantityLimitExceeded)', 'StockOutcome.QuantityLimitExceeded, FulfillmentOutcome.InsufficientStock)', 'E2-02'),
            'cancel-submitted': ('FulfillmentDomain.cs', 'order.Status == OrderStatus.Draft || order.Status == OrderStatus.Cancelled', 'true', 'E2-01'),
            'non-idempotent-cancel': ('FulfillmentDomain.cs', 'order.Status == OrderStatus.Draft || order.Status == OrderStatus.Cancelled', 'order.Status == OrderStatus.Draft', 'E2-01'),
            'direct-submit-code': ('FulfillmentBackend.cs', 'SubmissionOutcome.OrderCancelled => "OrderCancelled"',
                                   'SubmissionOutcome.OrderCancelled => "OrderNotDraft"', 'E2-02'),
            'fulfillment-code': ('FulfillmentDomain.cs', 'SubmissionOutcome.OrderCancelled, FulfillmentOutcome.OrderCancelled)',
                                 'SubmissionOutcome.OrderCancelled, FulfillmentOutcome.OrderRejected)', 'E2-02'),
            'early-cancellation': ('FulfillmentDomain.cs', 'var existing = await process.PointRead(domain.Reservations, input.OrderId);',
                                   'if (original.Entity.Status == OrderStatus.Cancelled)\n            return new FulfillmentResult(FulfillmentStatus.Rejected, FulfillmentOutcome.OrderCancelled);\n        var existing = await process.PointRead(domain.Reservations, input.OrderId);', 'E2-02'),
            'skipped-compensation': ('FulfillmentDomain.cs', 'await process.Transition(domain.InventoryTransitions.Release, input.Sku, new StockQuantity(input.Quantity));', '', 'E2-02'),
        })
    return cases


EXPECTED_ASSERTIONS = {
    'stock-outcome-projection': 'limit before cancellation',
    'cancel-submitted': 'cancellation state table',
    'non-idempotent-cancel': 'idempotent cancellation',
    'direct-submit-code': 'direct submit outcome',
    'fulfillment-code': 'cancelled fulfillment',
    'early-cancellation': 'missing inventory before cancellation',
    'skipped-compensation': 'cancelled fulfillment',
    'lost-replay': 'retained admission',
}
