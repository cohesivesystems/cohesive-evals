"""E3 defects must build and fail their named public behavioral assertion."""

def mutations(condition):
    cases = {
        'wrong-default': ('Contracts.cs', 'bool Quarantined = false', 'bool Quarantined = true', 'E3-01'),
        'lost-replay': ('OperationQueue.cs', 'Results.Json(previous.Admission, statusCode: 202)',
                        'Results.Conflict(new ErrorResponse("LostReplay"))', 'E3-03'),
    }
    if condition == 'conventional':
        cases.update({
            'missing-quarantine': ('Domain.cs', 'item.Quarantined ?', 'false ?', 'E3-02'),
            'quarantine-after-limit': ('Domain.cs', 'item.Quarantined ?', 'item.Quarantined && quantity <= item.MaxPerOrder ?', 'E3-02'),
            'quarantine-before-invalid': ('Domain.cs', 'quantity <= 0 ?', 'quantity <= 0 && !item.Quarantined ?', 'E3-02'),
            'quarantine-resets-limit': ('OrderStore.cs', 'SET quarantined=$2 WHERE', 'SET quarantined=$2, max_per_order=2147483647 WHERE', 'E3-01'),
            'clear-does-not-clear': ('FulfillmentBackend.cs', 'store.SetQuarantine(sku, false)', 'store.SetQuarantine(sku, true)', 'E3-01'),
            'skipped-compensation': ('FulfillmentBackend.cs', 'await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");', '', 'E3-02'),
        })
    else:
        invalid_guard = '''.Requires((item, input) => input.Quantity > 0,
                    (_, _) => new StockResult(StockOutcome.InvalidQuantity, FulfillmentOutcome.InvalidQuantity))
                .Requires((item, input) => !item.Quarantined,'''
        cases.update({
            'missing-quarantine': ('FulfillmentDomain.cs', '!item.Quarantined,', 'true,', 'E3-02'),
            'quarantine-after-limit': ('FulfillmentDomain.cs', '!item.Quarantined,', '!item.Quarantined || input.Quantity > item.MaxPerOrder,', 'E3-02'),
            'quarantine-before-invalid': ('FulfillmentDomain.cs', invalid_guard, invalid_guard.replace('input.Quantity > 0', 'input.Quantity > 0 || item.Quarantined'), 'E3-02'),
            'quarantine-resets-limit': ('FulfillmentDomain.cs', '.Set(new("quarantine/update"), item => item.Quarantined, (_, input) => input.Quarantined)', '.Set(new("quarantine/update"), item => item.Quarantined, (_, input) => input.Quarantined)\n                .Set(item => item.MaxPerOrder, 2147483647)', 'E3-01'),
            'clear-does-not-clear': ('FulfillmentBackend.cs', '("ClearQuarantine", "/inventory/{id}/clear-quarantine", false)', '("ClearQuarantine", "/inventory/{id}/clear-quarantine", true)', 'E3-01'),
            'skipped-compensation': ('FulfillmentDomain.cs', 'await process.Transition(domain.InventoryTransitions.Release, input.Sku, new StockQuantity(input.Quantity));', '', 'E3-02'),
        })
    return cases


EXPECTED_ASSERTIONS = {
    'wrong-default': 'seed/default/read',
    'lost-replay': 'retained admission',
    'missing-quarantine': 'quarantine enforcement',
    'quarantine-after-limit': 'quarantine before limit',
    'quarantine-before-invalid': 'invalid quantity before quarantine',
    'quarantine-resets-limit': 'quarantine response',
    'clear-does-not-clear': 'quarantine response',
    'skipped-compensation': 'cancelled compensation',
}
