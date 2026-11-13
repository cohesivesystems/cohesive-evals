"""Public quarantine examples using the existing HTTP test client."""
SEED = {'orders': [{'id': 'quarantine-visible', 'status': 'Draft'}],
        'inventory': [{'sku': 'quarantine-visible', 'available': 5}], 'reservations': []}

def exercise(Client, url):
    client = Client(url)
    view = {'sku': 'quarantine-visible', 'available': 5, 'maxPerOrder': 2147483647}
    client.expect('quarantine default', 'GET', '/inventory/quarantine-visible', 200,
                  expected={**view, 'quarantined': False})
    client.expect('quarantine inventory', 'POST', '/inventory/quarantine-visible/quarantine', 200,
                  expected={**view, 'quarantined': True})
    client.fulfill('quarantine-visible-rejected', 'quarantine-visible', 'quarantine-visible', 1, 'InventoryQuarantined')
    client.expect('clear quarantine', 'POST', '/inventory/quarantine-visible/clear-quarantine', 200,
                  expected={**view, 'quarantined': False})
    client.fulfill('quarantine-visible-success', 'quarantine-visible', 'quarantine-visible', 1, 'ReservedAndSubmitted')
    return client.observations
