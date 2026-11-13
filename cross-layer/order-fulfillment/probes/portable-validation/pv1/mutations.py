"""Buildable defects and their exact independent behavioral witnesses."""
def mutations(condition):
    cases={
        'batch-options-drift':('BatchCli.cs','item.Deserialize<FulfillmentRequest>(jsonOptions.Value.SerializerOptions)',
            'item.Deserialize<FulfillmentRequest>(new JsonSerializerOptions(jsonOptions.Value.SerializerOptions) { NumberHandling = System.Text.Json.Serialization.JsonNumberHandling.Strict })','PV1-01','input decoding'),
        'missing-required-input':('Program.cs','RespectRequiredConstructorParameters = true','RespectRequiredConstructorParameters = false','PV1-01','input decoding'),
        'stop-after-invalid':('BatchService.cs','items.Add(new(items.Count, admission, completion));',
            'items.Add(new(items.Count, admission, completion));\n                        if (request is null) break;', 'PV1-02','ordered results'),
        'oversized-executes':('BatchService.cs','requests.Count > 100','requests.Count > 101','PV1-02','envelope'),
        'cross-entry-replay-lost':('OperationQueue.cs','public IResult Admit(FulfillmentRequest request) => Submit(request).ToHttp();',
            'public IResult Admit(FulfillmentRequest request) => Results.Conflict(new ErrorResponse("LostReplay"));','PV1-03','cross-entry replay'),
        'batch-changes-quantity':('BatchService.cs','queue.Submit(request);','queue.Submit(request with { Quantity = request.Quantity + 1 });','PV1-01','outcomes'),
        'reject-domain-input':('FulfillmentInput.cs','!string.IsNullOrWhiteSpace(request.RequestId)',
            'request.Quantity > 0 && !string.IsNullOrWhiteSpace(request.RequestId)','PV1-01','outcomes'),
    }
    if condition=='conventional':
        cases['bypass-quarantine']=('Domain.cs','item.Quarantined ?','false ?','PV1-01','outcomes')
        cases['skip-compensation']=('FulfillmentBackend.cs','await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");','','PV1-04','settled facts')
    else:
        cases['bypass-quarantine']=('FulfillmentDomain.cs','!item.Quarantined,','true,','PV1-01','outcomes')
        cases['skip-compensation']=('FulfillmentDomain.cs','await process.Transition(domain.InventoryTransitions.Release, input.Sku, new StockQuantity(input.Quantity));','','PV1-04','settled facts')
    return cases
