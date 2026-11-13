"""Independent PV2 expectations; never import the application predicate or schema."""
import json
from checks import BehavioralFailure, canonical, check_items, require

LONG_ORDER = 'order-' + 'o' * 65
LONG_SKU = 'sku-' + 's' * 65

def fixture():
    return {'orders': [{'id': name, 'status': 'Draft'} for name in
                       ('success', 'quarantined', 'zero', 'negative', 'short', 'sentinel', LONG_ORDER)],
            'inventory': [
                {'sku': 'stock', 'available': 10, 'maxPerOrder': 5, 'quarantined': False},
                {'sku': 'quarantine', 'available': 0, 'maxPerOrder': 1, 'quarantined': True},
                {'sku': 'empty', 'available': 0, 'maxPerOrder': 5, 'quarantined': False},
                {'sku': LONG_SKU, 'available': 3, 'maxPerOrder': 5, 'quarantined': False},
                {'sku': 'sentinel', 'available': 13, 'maxPerOrder': 4, 'quarantined': False}],
            'reservations': []}

def request(identity, order='missing', sku='stock', quantity=1):
    return dict(requestId=identity, orderId=order, sku=sku, quantity=quantity)

def admitted(outcome='OrderMissing'):
    return {'status': 202, 'outcome': outcome}

# Literal expected outcomes distinguish UTF-16 units from scalars or graphemes.
BOUNDARIES = [('a', True), ('b'*63, True), ('c'*64, True), ('d'*65, False),
              ('😀'*31+'x', True), ('😀'*32, True), ('😀'*32+'x', False), ('😀'*33, False),
              ('e\u0301'*32, True), ('e\u0301'*32+'x', False), ('', False), (' '*64, False)]

class Checks:
    def __init__(self, world):
        self.world = world
        self.trace = []
        self.identities = set()

    def send(self, mode, requests, expected, obligation, assertion):
        if mode == 'batch':
            reply = self.world.send_batch(json.dumps(requests))
            require(self.world.batch_status == 200, obligation, assertion, (self.world.batch_status, reply))
            require(isinstance(reply, dict) and isinstance(reply.get('items'), list), obligation, assertion, reply)
            items = reply['items']
        else:
            items = [self.world.http(json.dumps(item), index) for index, item in enumerate(requests)]
        try:
            check_items(items, expected)
        except BehavioralFailure as error:
            raise BehavioralFailure(obligation, assertion, str(error)) from error
        self.identities.update(item['admission']['body']['operationId'] for item in items if item['admission']['status'] == 202)
        self.trace.append({'mode': mode, 'requests': requests, 'items': items})
        return items

    def facts(self, expected, assertion='preservation'):
        observed = self.world.facts()
        require(canonical(observed) == canonical(expected), 'PV2-02', assertion, observed)

    def run(self):
        expected = fixture()
        for mode in ('http', 'batch'):
            for identity, valid in BOUNDARIES:
                self.send(mode, [request(identity)], [admitted() if valid else {'status': 400}], 'PV2-01', 'length boundary')
        self.facts(expected)

        # Exact case/text and long entity identifiers remain significant.
        for mode, identity in [('http', 'Case'), ('batch', 'case'), ('http', ' spaced '), ('batch', 'spaced')]:
            self.send(mode, [request(identity)], [admitted()], 'PV2-03', 'identity preservation')
        require(len(self.identities) == 10, 'PV2-03', 'identity preservation', len(self.identities))
        self.send('batch', [request('long-entities', LONG_ORDER, LONG_SKU)], [admitted('ReservedAndSubmitted')], 'PV2-01', 'entity identifiers')
        next(x for x in expected['orders'] if x['id'] == LONG_ORDER)['status'] = 'Submitted'
        next(x for x in expected['inventory'] if x['sku'] == LONG_SKU)['available'] -= 1
        expected['reservations'].append({'id': LONG_ORDER, 'orderId': LONG_ORDER, 'sku': LONG_SKU, 'quantity': 1})
        self.facts(expected)

        invalid = 'p' * 65
        for mode in ('http', 'batch'):
            bad = [request(invalid, 'success'), request(invalid, 'missing'),
                   request(invalid, 'quarantined', 'quarantine', 0), request(invalid, 'short', 'empty')]
            self.send(mode, bad, [{'status': 400}]*len(bad), 'PV2-02', 'validation precedence')
        self.facts(expected)

        good = request('p'*64, 'success', quantity=2)
        rejected = request('q'*64, 'quarantined', 'quarantine', 2)
        # Invalid first, middle and last inputs cannot stop valid siblings.
        mixed = [request(invalid), good, request(invalid), rejected,
                 request('zero', 'zero', quantity=0), request('negative', 'negative', quantity=-1), request(invalid)]
        results = self.send('batch', mixed, [{'status':400}, admitted('ReservedAndSubmitted'), {'status':400},
                            admitted('InventoryQuarantined'), admitted('InvalidQuantity'), admitted('InvalidQuantity'), {'status':400}],
                            'PV2-02', 'mixed outcomes')
        next(x for x in expected['orders'] if x['id'] == 'success')['status'] = 'Submitted'
        next(x for x in expected['inventory'] if x['sku'] == 'stock')['available'] -= 2
        expected['reservations'].append({'id': 'success', 'orderId': 'success', 'sku': 'stock', 'quantity': 2})
        self.facts(expected)
        status, _ = self.world.client.request('POST', '/inventory/quarantine/clear-quarantine')
        if status != 200:
            raise RuntimeError(('setup command failed', status))
        next(x for x in expected['inventory'] if x['sku'] == 'quarantine')['quarantined'] = False
        for index, intent, outcome in [(1, good, 'ReservedAndSubmitted'), (3, rejected, 'InventoryQuarantined')]:
            replay = self.send('http', [intent], [admitted(outcome)], 'PV2-03', 'retained replay')[0]
            require(replay == {**results[index], 'index': 0}, 'PV2-03', 'retained replay', replay)
        first = self.send('http', [request('single-first')], [admitted()], 'PV2-03', 'retained replay')
        replay = self.send('batch', [request('single-first')], [admitted()], 'PV2-03', 'retained replay')
        require(first == replay, 'PV2-03', 'retained replay', (first, replay))
        self.send('batch', [{**good, 'quantity': 3}], [{'status':409, 'code':'RequestIdentityConflict'}], 'PV2-03', 'identity conflict')
        self.facts(expected)
        self.world.output.joinpath('trace.json').write_text(json.dumps(self.trace, indent=2)+'\n')
        return {'commands': len(self.trace), 'finalFacts': canonical(expected)}

    def capacity(self):
        # An invalid attempt must consume neither a retained ID nor capacity.
        self.send('batch', [request('z'*65)], [{'status':400}], 'PV2-02', 'capacity precedence')
        first = self.send('http', [request('capacity-0')], [admitted()], 'PV2-03', 'retained replay')[0]
        for i in range(1, 1000):
            self.send('http', [request('capacity-'+str(i))], [admitted()], 'PV2-02', 'capacity accounting')
        for mode in ('http', 'batch'):
            results = self.send(mode, [request('z'*65), request('new'), request('capacity-0')],
                                [{'status':400}, {'status':503}, admitted()], 'PV2-02', 'capacity precedence')
            require({**results[2], 'index':0} == first, 'PV2-03', 'retained replay', results)
        self.facts(fixture())
        self.world.output.joinpath('trace.json').write_text(json.dumps(self.trace, indent=2)+'\n')
        return {'commands': len(self.trace), 'retainedIdentities': len(self.identities)}
