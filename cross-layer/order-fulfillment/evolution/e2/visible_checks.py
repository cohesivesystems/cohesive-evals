"""Public cancellation examples using the existing HTTP test client."""
SEED = {'orders': [{'id': 'cancel-visible', 'status': 'Draft'}],
        'inventory': [{'sku': 'cancel-visible', 'available': 5}], 'reservations': []}

def exercise(Client, url):
    client = Client(url)
    for label in ('cancel draft', 'cancel again'):
        client.expect(label, 'POST', '/orders/cancel-visible/cancel', 200,
                      expected={'id': 'cancel-visible', 'status': 'Cancelled'})
    client.expect('submit cancelled', 'POST', '/orders/cancel-visible/submit', 409,
                  expected={'code': 'OrderCancelled'})
    client.fulfill('cancel-visible-request', 'cancel-visible', 'cancel-visible', 1, 'OrderCancelled')
    client.expect('cancel preserves stock', 'GET', '/inventory/cancel-visible', 200,
                  expected={'sku': 'cancel-visible', 'available': 5, 'maxPerOrder': 2147483647})
    return client.observations
