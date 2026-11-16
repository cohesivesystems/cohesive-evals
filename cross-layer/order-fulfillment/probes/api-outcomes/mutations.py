"""One buildable application fault per case; independent named behavioral expectations."""

def mutations(condition):
    if condition not in ('conventional','cohesive'): raise ValueError(condition)
    def case(file, before, after, number, assertion):
        return file, before, after, 'AO1-'+number, assertion
    conventional = condition == 'conventional'
    backend='FulfillmentBackend.cs'
    common={
        'replay-evicted': case('OperationQueue.cs','if (requests.TryGetValue(request.RequestId, out var previous))',
            'requests.Clear();\n            if (requests.TryGetValue(request.RequestId, out var previous))','05','shared replay and identity'),
        'conflicting-intent-replayed': case('OperationQueue.cs','return previous.Request == request ? new(202, previous.Admission)',
            'return true ? new(202, previous.Admission)','05','shared replay and identity'),
        'batch-stops-at-rejection': case('BatchService.cs','items.Add(new(items.Count, admission, completion));',
            'items.Add(new(items.Count, admission, completion));\n            if (completion?.Body is Completion { Status: "Rejected" }) break;',
            '05','mixed batch preservation'),
    }
    if conventional:
        common.update({
            'missing-archived-guard':case('Domain.cs','OrderStatus.Archived => SubmissionOutcome.OrderArchived,','OrderStatus.Archived => SubmissionOutcome.NotDraft,','01','archived direct submission'),
            'stale-direct-code':case(backend,'SubmissionOutcome.OrderArchived => Results.Conflict(new ErrorResponse("OrderArchived")),','SubmissionOutcome.OrderArchived => Results.Conflict(new ErrorResponse("OrderNotDraft")),','01','archived direct submission'),
            'wrong-http-category':case(backend,'SubmissionOutcome.OrderArchived => Results.Conflict(new ErrorResponse("OrderArchived")),','SubmissionOutcome.OrderArchived => Results.Ok(new ErrorResponse("OrderArchived")),','01','archived direct submission'),
            'existing-outcome-drift':case(backend,'SubmissionOutcome.NotDraft => Results.Conflict(new ErrorResponse("OrderNotDraft")),','SubmissionOutcome.NotDraft => Results.Conflict(new ErrorResponse("OrderArchived")),','01','existing direct outcomes'),
            'stale-terminal-code':case('FulfillmentResults.cs','SubmissionOutcome.OrderArchived => "OrderArchived",','SubmissionOutcome.OrderArchived => "OrderRejected",','02','archived fulfillment outcome'),
            'skip-release':case(backend,'await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");','// Defect: skip compensation.','02','archived compensation'),
            'double-release':case(backend,'await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");','await store.Stock(request.Sku, request.Quantity * 2, true, operationId + "/release");','02','archived compensation'),
            'reservation-on-rejection':case(backend,'return FulfillmentResults.FromSubmission(submitted);','await store.CreateReservation(new(request.OrderId, request.OrderId, request.Sku, request.Quantity), operationId + "/bad-reservation");\n        return FulfillmentResults.FromSubmission(submitted);','02','archived compensation'),
            'archived-before-inventory':case(backend,'if (await store.Inventory(request.Sku) is null)', 'if (order.Status == OrderStatus.Archived) return Reject("OrderArchived");\n        if (await store.Inventory(request.Sku) is null)','03','rejection precedence'),
            'wrong-entity-id':case(backend,'await store.Submit(id) switch','await store.Submit(id == "ao1-case" ? "ao1-Case" : id) switch','04','bound entity identity'),
            'constant-input':case(backend,'QuantityLimitInput.Get(context).MaxPerOrder','1','04','bound input meaning'),
            'read-status-erased':case(backend,'new(order.Id, order.Status.ToString())','new(order.Id, order.Status == OrderStatus.Archived ? "Draft" : order.Status.ToString())','06','archived read and restart'),
        })
    else:
        domain='FulfillmentDomain.cs'
        guard='.Requires(order => order.Status != OrderStatus.Archived, order => new SubmitOrderResult(order.Status, SubmissionOutcome.OrderArchived, FulfillmentOutcome.OrderArchived))'
        release='await process.Transition(domain.InventoryTransitions.Release, input.Sku, new StockQuantity(input.Quantity));'
        common.update({
            'missing-archived-guard':case(domain,guard,'','01','archived direct submission'),
            'stale-direct-code':case(backend,'SubmissionOutcome.OrderArchived => "OrderArchived",','SubmissionOutcome.OrderArchived => "OrderNotDraft",','01','archived direct submission'),
            'existing-outcome-drift':case(backend,'SubmissionOutcome.NotDraft => "OrderNotDraft",','SubmissionOutcome.NotDraft => "OrderArchived",','01','existing direct outcomes'),
            'stale-terminal-code':case(domain,guard,guard.replace('FulfillmentOutcome.OrderArchived','FulfillmentOutcome.OrderRejected'),'02','archived fulfillment outcome'),
            'skip-release':case(domain,release,'// Defect: skip compensation.','02','archived compensation'),
            'double-release':case(domain,release,release.replace('input.Quantity','input.Quantity * 2'),'02','archived compensation'),
            'reservation-on-rejection':case(domain,'return new FulfillmentResult(FulfillmentStatus.Rejected, submitted.FulfillmentOutcome);','await process.Transition(domain.ReservationTransitions.Create, input.OrderId,\n            new Reservation(input.OrderId, stock.Entity.Partition, input.OrderId, input.Sku, input.Quantity));\n        return new FulfillmentResult(FulfillmentStatus.Rejected, submitted.FulfillmentOutcome);','02','archived compensation'),
            'archived-before-inventory':case(domain,'var stock = await process.PointRead(domain.Inventory, input.Sku,','if (original.Entity.Status == OrderStatus.Archived)\n            return new FulfillmentResult(FulfillmentStatus.Rejected, FulfillmentOutcome.OrderArchived);\n        var stock = await process.PointRead(domain.Inventory, input.Sku,','03','rejection precedence'),
            'constant-input':case(backend,'.Input(context => QuantityLimitInput.Get(context.HttpContext))','.Input(context => new QuantityLimit(1))','04','bound input meaning'),
            'read-status-erased':case(backend,'new(order.Id, order.Status.ToString())','new(order.Id, order.Status == OrderStatus.Archived ? "Draft" : order.Status.ToString())','06','archived read and restart'),
        })
        # A route rewrite is well typed and occurs before the endpoint extracts identity.
        common['wrong-entity-id']=case('Program.cs','app.Services.GetRequiredService<IFulfillmentBackend>().MapSubmit(app);',
            'app.Use(async (context, next) => { if (context.Request.RouteValues["id"]?.ToString() == "ao1-case") context.Request.RouteValues["id"] = "ao1-Case"; await next(context); });\napp.Services.GetRequiredService<IFulfillmentBackend>().MapSubmit(app);','04','bound entity identity')
    return common
