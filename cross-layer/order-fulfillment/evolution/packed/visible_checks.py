"""Public example of packing and unpacking an already submitted order."""
SEED = {'orders': [{'id': 'packing-example', 'status': 'Submitted'}], 'inventory': [], 'reservations': []}


def exercise(Client, url):
    """Return the HTTP observations from one round trip through the submitted state."""
    client = Client(url)
    for command, status in [('pack', 'Packed'), ('unpack', 'Submitted')]:
        client.expect(command, 'POST', f'/orders/packing-example/{command}', 200,
                      expected={'id': 'packing-example', 'status': status})
    return client.observations
