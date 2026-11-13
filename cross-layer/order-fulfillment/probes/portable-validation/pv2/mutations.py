"""Buildable PV2 defects with exact named behavioral witnesses."""
def mutations(condition):
    limit = 'request.RequestId.Length <= 64'
    return {
        'stale-validator': ('FulfillmentInput.cs', limit, 'true', 'PV2-01', 'length boundary'),
        'reject-64': ('FulfillmentInput.cs', limit, 'request.RequestId.Length < 64', 'PV2-01', 'length boundary'),
        'accept-65': ('FulfillmentInput.cs', limit, 'request.RequestId.Length <= 65', 'PV2-01', 'length boundary'),
        'grapheme-counting': ('FulfillmentInput.cs', limit,
            'System.Globalization.StringInfo.ParseCombiningCharacters(request.RequestId).Length <= 64', 'PV2-01', 'length boundary'),
        'single-truncates': ('OperationQueue.cs', 'public IResult Admit(FulfillmentRequest request) => Submit(request).ToHttp();',
            'public IResult Admit(FulfillmentRequest request) => Submit(request with { RequestId = request.RequestId.Length > 64 ? request.RequestId[..64] : request.RequestId }).ToHttp();', 'PV2-01', 'length boundary'),
        'batch-truncates': ('BatchService.cs', 'queue.Submit(request);',
            'queue.Submit(request with { RequestId = request.RequestId.Length > 64 ? request.RequestId[..64] : request.RequestId });', 'PV2-01', 'length boundary'),
        'capacity-before-validation': ('OperationQueue.cs', 'if (!FulfillmentInput.IsValid(request)) return new(400);',
            'if (requests.Count < 1000 && !FulfillmentInput.IsValid(request)) return new(400);', 'PV2-02', 'capacity precedence'),
        'trim-identity': ('OperationQueue.cs', 'if (!FulfillmentInput.IsValid(request)) return new(400);',
            'if (!FulfillmentInput.IsValid(request)) return new(400);\n        request = request with { RequestId = request.RequestId.Trim() };', 'PV2-03', 'identity preservation'),
        'reset-identities': ('OperationQueue.cs', 'if (requests.TryGetValue(request.RequestId, out var previous))',
            'requests.Clear();\n            if (requests.TryGetValue(request.RequestId, out var previous))', 'PV2-03', 'identity preservation'),
    }
