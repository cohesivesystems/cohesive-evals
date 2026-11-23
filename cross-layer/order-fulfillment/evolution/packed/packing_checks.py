"""Independent order lifecycle oracle, including settled PostgreSQL state and concurrent histories."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from harness import load

parent = load('packing_parent_checks', Path(__file__).resolve().parents[1] / 'e2/cancellation_checks.py')
BehavioralFailure = parent.BehavioralFailure
require = parent.require

# Strings starting with Order are the contract's conflict codes; other values are destinations.
TABLE = {
    'Draft': {'submit': 'Submitted', 'cancel': 'Cancelled', 'pack': 'OrderNotPackable', 'unpack': 'OrderNotUnpackable'},
    'Submitted': {'submit': 'OrderNotDraft', 'cancel': 'OrderNotCancellable', 'pack': 'Packed', 'unpack': 'Submitted'},
    'Packed': {'submit': 'OrderNotDraft', 'cancel': 'OrderNotCancellable', 'pack': 'Packed', 'unpack': 'Submitted'},
    'Cancelled': {'submit': 'OrderCancelled', 'cancel': 'Cancelled', 'pack': 'OrderNotPackable', 'unpack': 'OrderNotUnpackable'},
}


def fixture():
    """Seed distinct orders for each independent cell, race, and fulfillment witness."""
    orders = [{'id': f'packed-{state}-{command}', 'status': state} for state in TABLE for command in TABLE[state]]
    orders.extend({'id': f'packed-{key}', 'status': state} for key, state in
                  [('0', 'Draft'), ('direct', 'Draft'), ('fulfill', 'Draft'), ('race', 'Submitted'), ('other', 'Draft')])
    return {'orders': orders, 'inventory': [{'sku': 'packed-stock', 'available': 8}], 'reservations': []}


def decision(order, state, command):
    """Return the public response and next status for one serial step."""
    outcome = TABLE[state][command]
    if outcome.startswith('Order'):
        return (409, {'code': outcome}), state
    return (200, {'id': order, 'status': outcome}), outcome


class Checks(parent.Checks):
    """Drive the HTTP app against a contract table and compare all scoped database facts."""
    prefix = 'packed'
    seed_fixture = staticmethod(fixture)

    def command(self, order, command, witness=None):
        """Apply one expected decision and verify the reads and all persistent facts."""
        entity = self.order(order)
        expected, status = decision(order, entity['status'], command)
        result = self.http('POST', f'/orders/{order}/{command}', raw=b'{')
        require(result == expected, 'lifecycle', (witness or 'transition response', order, command, result, expected))
        entity['status'] = status
        self.record('lifecycle', {'order': order, 'command': command}, result, 'stock and reservation preservation')
        self.views(order)
        self.views('packed-other')
        rows = [{'reservationId': r['id'], 'sku': r['sku'], 'quantity': r['quantity'],
                 'availableStock': self.inventory(r['sku'])['available']}
                for r in self.state['reservations'] if r['orderId'] == order]
        require(self.http('GET', f'/orders/{order}/availability') == (200, rows), 'lifecycle', 'availability read')

    def race(self, order, commands):
        """Require responses indexed by command and final state to fit the same serial history."""
        state = self.order(order)['status']
        gate = Barrier(2)

        def send(command):
            """Release both clients together and return this command's response."""
            gate.wait(timeout=10)
            return self.http('POST', f'/orders/{order}/{command}')

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = dict(zip(commands, pool.map(send, commands)))
        final = self.http('GET', '/orders/' + order)
        for first, second in [commands, commands[::-1]]:
            one, intermediate = decision(order, state, first)
            two, end = decision(order, intermediate, second)
            if responses == {first: one, second: two} and final == (200, {'id': order, 'status': end}):
                self.order(order)['status'] = end
                self.record('lifecycle', {'race': commands}, responses)
                return
        raise BehavioralFailure('lifecycle', ('legal serial history', responses, final))

    def run(self):
        """Exercise every cell, both submission paths, replay and two serialization races."""
        for state, commands in TABLE.items():
            for command in commands:
                self.command(f'packed-{state}-{command}', command, f'{state} {command}')
        for command in ['pack', 'unpack']:
            require(self.c.request_bytes('POST', f'/orders/missing/{command}') == (404, b''), 'lifecycle', 'empty 404')
        self.command('packed-direct', 'submit')
        self.command('packed-direct', 'pack')
        self.new_request('packed-direct', 'packed-stock', 9, 'inventory before packed rejection')
        self.new_request('packed-direct', 'packed-stock', 1, 'packed rejection releases reserved stock')
        key = self.new_request('packed-fulfill', 'packed-stock', 2)
        self.command('packed-fulfill', 'pack')
        self.command('packed-fulfill', 'pack')
        self.replay(key)
        self.race('packed-0', ['submit', 'cancel'])
        self.race('packed-race', ['pack', 'unpack'])
        # Both winners are legal; the trace retains the actual winner for each database.
        return {'tableCells': sum(map(len, TABLE.values())), 'serializableRaces': 2}

    def after_restart(self):
        """Check the original packed reservation and resume its lifecycle without reseeding."""
        self.record('lifecycle', 'restart', None, 'packed survives restart')
        self.views('packed-fulfill')
        self.command('packed-fulfill', 'unpack')
        self.command('packed-fulfill', 'pack')
