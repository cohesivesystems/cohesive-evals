"""Independent G3 decision model, reusing E2's existing command assertions."""
import importlib.util
from pathlib import Path
import random

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
    prefix = 'e3'
    seed_fixture = staticmethod(fixture)
    inventory_defaults = {**prior.Checks.inventory_defaults, 'quarantined': False}
    fulfillment_obligation = 'E3-02'
    replay_obligation = 'E3-03'

    def inventory_rejection(self, item, quantity):
        if item['quarantined']:
            return 'InventoryQuarantined'
        return super().inventory_rejection(item, quantity)

    def quarantine(self, sku, value, raw=None):
        item = self.inventory(sku)
        command = 'quarantine' if value else 'clear-quarantine'
        result = self.http('POST', f'/inventory/{sku}/{command}', raw=raw)
        expected = (200, {**item, 'quarantined': value}) if item else (404, None)
        require(result == expected, 'E3-01', ('quarantine response', result, expected))
        if item:
            item['quarantined'] = value
        self.record('E3-01', {command: sku}, result, 'quarantine preservation')

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
