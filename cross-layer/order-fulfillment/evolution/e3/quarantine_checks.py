"""Independent G3 decision model, reusing E2's existing command assertions."""
import copy
import importlib.util
import json
from pathlib import Path
import random
import time

spec = importlib.util.spec_from_file_location('e3_prior_checks', Path(__file__).resolve().parents[1] / 'e2/cancellation_checks.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
BehavioralFailure = prior.BehavioralFailure
require = prior.require


def fixture():
    return {'orders': [{'id': f'e3-{i}', 'status': 'Cancelled' if i == 18 else 'Submitted' if i == 19 else 'Draft'} for i in range(20)],
            'inventory': [{'sku': 'e3-stock', 'available': 12},
                          {'sku': 'e3-other', 'available': 7, 'maxPerOrder': 2},
                          {'sku': 'e3-sentinel', 'available': 13, 'maxPerOrder': 4, 'quarantined': True}],
            'reservations': []}


class Checks(prior.Checks):
    def __init__(self, Client, url, observe, output):
        self.c = Client(url)
        self.observe = observe
        self.output = output
        self.trace = []
        data = fixture()
        self.state = {'orders': copy.deepcopy(data['orders']),
                      'inventory': [{'maxPerOrder': 2147483647, 'quarantined': False, **item} for item in data['inventory']],
                      'reservations': []}
        self.history = {}
        self.counter = 0

    def record(self, obligation, command, observed, assertion='settled facts/preservation'):
        facts = self.observe()
        canonical = lambda state: {k: sorted(v, key=lambda item: json.dumps(item, sort_keys=True)) for k, v in state.items()}
        entry = {'obligation': obligation, 'command': command, 'observed': observed,
                 'expectedFacts': copy.deepcopy(self.state), 'facts': facts}
        self.trace.append(entry)
        (self.output / 'e3-trace.json').write_text(json.dumps(self.trace, indent=2) + '\n')
        require(canonical(facts) == canonical(self.state), obligation, (assertion, entry))

    def quarantine(self, sku, value, raw=None):
        item = self.inventory(sku)
        command = 'quarantine' if value else 'clear-quarantine'
        result = self.http('POST', f'/inventory/{sku}/{command}', raw=raw)
        expected = (200, {**item, 'quarantined': value}) if item else (404, None)
        require(result == expected, 'E3-01', ('quarantine response', result, expected))
        if item:
            item['quarantined'] = value
        self.record('E3-01', {command: sku}, result, 'quarantine preservation')

    def new_request(self, order, sku, quantity, witness='fulfillment outcome'):
        self.counter += 1
        request = {'requestId': f'e3-request-{self.counter}', 'orderId': order, 'sku': sku, 'quantity': quantity}
        item, entity = self.inventory(sku), self.order(order)
        existing = next((row for row in self.state['reservations'] if row['orderId'] == order), None)
        if not entity:
            outcome = 'OrderMissing'
        elif existing:
            outcome = 'ReservedAndSubmitted' if existing['sku'] == sku and existing['quantity'] == quantity and entity['status'] == 'Submitted' else 'ReservationConflict'
        elif not item:
            outcome = 'InventoryMissing'
        elif quantity <= 0:
            outcome = 'InvalidQuantity'
        elif item['quarantined']:
            outcome = 'InventoryQuarantined'
        elif quantity > item['maxPerOrder']:
            outcome = 'QuantityLimitExceeded'
        elif quantity > item['available']:
            outcome = 'InsufficientStock'
        elif entity['status'] == 'Cancelled':
            outcome = 'OrderCancelled'
        elif entity['status'] != 'Draft':
            outcome = 'OrderRejected'
        else:
            outcome = 'ReservedAndSubmitted'
            entity['status'] = 'Submitted'
            item['available'] -= quantity
            self.state['reservations'].append({'id': order, 'orderId': order, 'sku': sku, 'quantity': quantity})
        response = self.http('POST', '/fulfillment', request)
        require(response[0] == 202, 'E3-02', ('admission', response))
        receipt = response[1]
        deadline = time.monotonic() + 20
        while True:
            result = self.http('GET', receipt['resultUrl'])
            if result[0] != 202:
                break
            if time.monotonic() > deadline:
                raise RuntimeError('Fulfillment did not complete')
            time.sleep(.02)
        expected = {'status': 'Submitted' if outcome == 'ReservedAndSubmitted' else 'Rejected', 'outcome': outcome}
        require(result == (200, expected), 'E3-02', (witness, request, result, expected))
        self.history[request['requestId']] = (request, receipt, expected)
        self.record('E3-02', request, result, witness)
        return request['requestId']

    def replay(self, key):
        request, receipt, completion = self.history[key]
        require(self.http('POST', '/fulfillment', request) == (202, receipt), 'E3-03', 'retained admission')
        require(self.http('GET', receipt['resultUrl']) == (200, completion), 'E3-03', 'retained completion')
        conflict = self.http('POST', '/fulfillment', {**request, 'quantity': 0 if request['quantity'] != 0 else 1})
        require(conflict == (409, {'code': 'RequestIdentityConflict'}), 'E3-03', 'identity conflict')
        self.record('E3-03', {'replay': key}, completion)

    def run(self):
        for item in self.state['inventory']:
            require(self.http('GET', '/inventory/' + item['sku']) == (200, item), 'E3-01', 'seed/default/read')
        self.record('E3-01', 'seed', None)
        self.configure('e3-stock', 2)
        self.quarantine('e3-missing', True, raw=b'{')
        self.quarantine('e3-missing', False)
        self.quarantine('e3-stock', True, raw=b'{')
        self.quarantine('e3-stock', True, raw=b'null')
        rejected = self.new_request('e3-0', 'e3-stock', 1, 'quarantine enforcement')
        self.new_request('e3-0', 'e3-stock', 0, 'invalid quantity before quarantine')
        self.new_request('e3-0', 'e3-stock', 13, 'quarantine before limit')
        self.new_request('e3-missing', 'e3-stock', 1, 'order missing before quarantine')
        self.new_request('e3-0', 'e3-missing', 1)
        self.new_request('e3-18', 'e3-stock', 1, 'quarantine before cancellation')
        self.submit('e3-1') # Direct submission has no inventory dependency.
        self.quarantine('e3-stock', False)
        self.quarantine('e3-stock', False)
        self.replay(rejected)
        self.new_request('e3-0', 'e3-stock', 13, 'limit after clear')
        self.configure('e3-stock', 2147483647)
        self.new_request('e3-0', 'e3-stock', 13, 'shortage after limit raised')
        self.new_request('e3-18', 'e3-stock', 1, 'cancelled compensation')
        self.new_request('e3-19', 'e3-stock', 1, 'submitted compensation')
        success = self.new_request('e3-0', 'e3-stock', 2)
        self.quarantine('e3-stock', True)
        self.configure('e3-stock', 1) # A limit update must retain quarantine.
        self.replay(success)
        self.new_request('e3-0', 'e3-stock', 2, 'existing reservation before quarantine')
        self.new_request('e3-0', 'e3-stock', 1, 'reservation conflict before quarantine')
        self.cancel('e3-2')
        self.new_request('e3-2', 'e3-stock', 1, 'quarantine before cancellation')
        rng = random.Random(163)
        for _ in range(60):
            kind = rng.randrange(6)
            order = 'e3-' + str(rng.randrange(18))
            sku = rng.choice(['e3-stock', 'e3-other'])
            if kind == 0:
                self.quarantine(sku, rng.choice([False, True]))
            elif kind == 1:
                self.configure(sku, rng.choice([1, 2, 4, 2147483647]))
            elif kind == 2:
                self.cancel(order)
            elif kind == 3:
                self.submit(order)
            elif kind == 4:
                self.new_request(order, sku, rng.choice([-1, 0, 1, 2, 9]))
            else:
                self.replay(rng.choice(list(self.history)))
        # Persist both Boolean values with nondefault limits for the restart check.
        self.quarantine('e3-stock', True)
        self.quarantine('e3-other', False)
        return {'commands': len(self.trace), 'finalFacts': self.state}

    def after_restart(self):
        self.record('E3-01', 'clean restart', None)
        for item in self.state['inventory']:
            require(self.http('GET', '/inventory/' + item['sku']) == (200, item), 'E3-01', 'persistent quarantine view')
        self.history.clear()
        self.counter += 1000
        self.new_request('e3-18', 'e3-stock', 1, 'persistent quarantine enforcement')
        self.quarantine('e3-stock', False)
        self.new_request('e3-18', 'e3-stock', 1, 'cancelled compensation')
