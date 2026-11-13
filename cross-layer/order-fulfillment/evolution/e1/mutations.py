"""Generation-specific, exactly anchored application defects."""
def mutations(condition):
    cases={
        'wrong-default':('Contracts.cs','int MaxPerOrder = int.MaxValue','int MaxPerOrder = 1','E1-01'),
        'lost-replay':('OperationQueue.cs','Results.Json(previous.Admission, statusCode: 202)',
                       'Results.Conflict(new ErrorResponse("LostReplay"))','E1-03')}
    if condition=='conventional':
        cases.update({
            'missing-limit':('Domain.cs','quantity > item.MaxPerOrder','false','E1-02'),
            'off-by-one':('Domain.cs','quantity > item.MaxPerOrder','quantity >= item.MaxPerOrder','E1-02'),
            'wrong-precedence':('Domain.cs','quantity > item.MaxPerOrder','quantity > item.MaxPerOrder && quantity <= item.Available','E1-02'),
            'configuration-changes-stock':('OrderStore.cs','SET max_per_order=$2 WHERE','SET max_per_order=$2, available=0 WHERE','E1-01'),
            'skipped-compensation':('FulfillmentBackend.cs','await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");','','E1-02')})
    else:
        cases.update({
            'missing-limit':('FulfillmentDomain.cs','input.Quantity <= item.MaxPerOrder','true','E1-02'),
            'off-by-one':('FulfillmentDomain.cs','input.Quantity <= item.MaxPerOrder','input.Quantity < item.MaxPerOrder','E1-02'),
            'wrong-precedence':('FulfillmentDomain.cs','input.Quantity <= item.MaxPerOrder','input.Quantity <= item.MaxPerOrder || input.Quantity > item.Available','E1-02'),
            'configuration-changes-stock':('FulfillmentDomain.cs','.Set(new("limit/update"), item => item.MaxPerOrder, (_, input) => input.MaxPerOrder)',
                  '.Set(new("limit/update"), item => item.MaxPerOrder, (_, input) => input.MaxPerOrder)\n                .Set(item => item.Available, 0)','E1-01'),
            'skipped-compensation':('FulfillmentDomain.cs','await process.Transition(domain.InventoryTransitions.Release, input.Sku, new StockQuantity(input.Quantity));','','E1-02')})
    return cases


EXPECTED_ASSERTIONS = {
    'wrong-default':'seed/default/read', 'lost-replay':'retained admission',
    'missing-limit':'limit enforcement', 'off-by-one':'inclusive boundary',
    'wrong-precedence':'limit before shortage', 'configuration-changes-stock':'integral input',
    'skipped-compensation':'lifecycle rejection preserves stock'}
