"""Maintainer-only sequential G0 model and persisted business-fact checks."""
import copy
import json
import random
from pathlib import Path

SEEDS = (17, 83, 251)


def fixture():
    data = {'orders': [], 'inventory': [], 'reservations': []}
    for seed in SEEDS:
        prefix = f'inv-{seed}-'
        data['orders'] += [{'id': prefix+str(i), 'status': 'Draft'} for i in range(8)]
        data['inventory'] += [{'sku': prefix+name, 'available': amount}
                              for name, amount in [('stock', 5), ('other', 7), ('untouched', 11)]]
    return data


def commands(seed):
    prefix = f'inv-{seed}-'
    # Deterministic last-unit, compensation, replay-after-state-change and identity
    # conflict coverage before randomized operations against the same small world.
    result = [
        {'kind': 'fulfill', 'order': '0', 'sku': 'stock', 'quantity': 3},
        {'kind': 'fulfill', 'order': '1', 'sku': 'stock', 'quantity': 2},
        {'kind': 'fulfill', 'order': '2', 'sku': 'stock', 'quantity': 1},
        {'kind': 'replay', 'index': 0},
        {'kind': 'conflict', 'index': 0},
        {'kind': 'fulfill', 'order': '0', 'sku': 'stock', 'quantity': 3},
        {'kind': 'submit', 'order': '3'},
        {'kind': 'fulfill', 'order': '3', 'sku': 'other', 'quantity': 2},
    ]
    rng = random.Random(seed)
    for _ in range(52):
        if rng.random() < .2:
            result.append({'kind': rng.choice(['replay', 'conflict']), 'index': rng.randrange(100)})
        elif rng.random() < .2:
            result.append({'kind': 'submit', 'order': str(rng.randrange(7))})
        else:
            result.append({'kind': 'fulfill', 'order': rng.choice([str(i) for i in range(7)]+['missing']),
                           'sku': rng.choice(['stock', 'other', 'missing']),
                           'quantity': rng.choice([-1, 0, 1, 2, 3, 5, 6, 8])})
    for command in result:
        if 'order' in command: command['order'] = prefix+command['order']
        if 'sku' in command: command['sku'] = prefix+command['sku']
    return result


class Model:
    def __init__(self, seed):
        prefix = f'inv-{seed}-'
        self.orders = {prefix+str(i): 'Draft' for i in range(8)}
        self.initial = {prefix+name: count for name, count in [('stock', 5), ('other', 7), ('untouched', 11)]}
        self.stock = dict(self.initial)
        self.reservations = []

    def fulfill(self, order, sku, quantity):
        existing = next((r for r in self.reservations if r['orderId'] == order), None)
        if order not in self.orders: return 'OrderMissing'
        if existing:
            return ('ReservedAndSubmitted' if existing['sku'] == sku and existing['quantity'] == quantity
                    and self.orders[order] == 'Submitted' else 'ReservationConflict')
        if sku not in self.stock: return 'InventoryMissing'
        if quantity <= 0: return 'InvalidQuantity'
        if quantity > self.stock[sku]: return 'InsufficientStock'
        if self.orders[order] != 'Draft': return 'OrderRejected'
        self.orders[order] = 'Submitted'
        self.stock[sku] -= quantity
        self.reservations.append({'id': order, 'orderId': order, 'sku': sku, 'quantity': quantity})
        return 'ReservedAndSubmitted'


def check_facts(model, facts):
    inventory = {item['sku']: item['available'] for item in facts['inventory']}
    rows = facts['reservations']
    assert inventory.keys() == model.initial.keys(), 'inventory identity/isolation'
    assert all(value >= 0 for value in inventory.values()), 'negative stock'
    assert len({r['id'] for r in rows}) == len(rows), 'duplicate reservation identity'
    assert len({r['orderId'] for r in rows}) == len(rows), 'duplicate reservation per order'
    assert all(r['orderId'] in model.orders and r['sku'] in inventory and r['quantity'] > 0 for r in rows), 'reservation integrity'
    for sku, initial in model.initial.items():
        reserved = sum(r['quantity'] for r in rows if r['sku'] == sku)
        assert inventory[sku] + reserved == initial, ('stock conservation', sku)
    assert inventory == model.stock, 'stock/model or rejection preservation'
    assert sorted(rows, key=lambda r: r['id']) == sorted(model.reservations, key=lambda r: r['id']), 'reservation/model or completion'


def qualify_checker():
    """Checker-level defect qualification; not full mutated-application qualification."""
    model = Model(17)
    model.fulfill('inv-17-0', 'inv-17-stock', 3)
    good = {'inventory': [{'sku': k, 'available': v} for k, v in model.stock.items()],
            'reservations': copy.deepcopy(model.reservations)}
    check_facts(model, good)
    defects = {}
    bad = copy.deepcopy(good); bad['inventory'][0]['available'] = -1; defects['negative stock'] = bad
    bad = copy.deepcopy(good); bad['inventory'][0]['available'] -= 1; defects['double decrement'] = bad
    bad = copy.deepcopy(good); bad['reservations'].append({**bad['reservations'][0], 'id': 'duplicate'}); defects['duplicate order reservation'] = bad
    bad = copy.deepcopy(good); bad['reservations'][0]['sku'] = 'absent'; defects['dangling reference'] = bad
    bad = copy.deepcopy(good); bad['reservations'] = []; defects['missing reservation'] = bad
    bad = copy.deepcopy(good); bad['inventory'][-1]['available'] -= 1; defects['unrelated stock mutation'] = bad
    for name, bad in defects.items():
        try: check_facts(model, bad)
        except AssertionError: continue
        raise AssertionError('Checker accepted seeded defect: '+name)
    return list(defects)


def observe(run, container, condition, seed):
    # Test-only mappings to business facts, executed in a read-only transaction.
    # Only this workload's namespace is included; contract fixtures intentionally
    # include preexisting multi-reservation orders and are not conservation seeds.
    tables = ('orders', 'inventory', 'reservations', 'id') if condition == 'conventional' else (
        'cohesive_orders', 'cohesive_inventory', 'cohesive_reservations', 'reservation_id')
    _, inventory, reservations, identity = tables
    prefix = f'inv-{seed}-%'
    query = f"""BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object(
 'inventory', (SELECT coalesce(json_agg(row_to_json(i)), '[]'::json) FROM
   (SELECT sku, available FROM {inventory} WHERE sku LIKE '{prefix}' ORDER BY sku) i),
 'reservations', (SELECT coalesce(json_agg(row_to_json(r)), '[]'::json) FROM
   (SELECT {identity} AS id, order_id AS "orderId", sku, quantity FROM {reservations}
    WHERE order_id LIKE '{prefix}' OR sku LIKE '{prefix}' OR {identity} LIKE '{prefix}' ORDER BY {identity}) r));
COMMIT;"""
    return json.loads(run('docker', 'exec', container, 'psql', '-X', '-qAt', '-v', 'ON_ERROR_STOP=1',
                          '-U', 'postgres', '-d', condition, '-c', query))


def exercise(client_type, url, observer, output):
    reports = []
    for seed in SEEDS:
        model = Model(seed)
        client = client_type(url)
        history, trace = [], []
        trace_file = Path(output)/f'invariants-{seed}.json'
        def snapshot(record=None):
            facts = observer(seed)
            if record is not None:
                record['facts'] = facts
                record['expected'] = {'stock': dict(model.stock), 'reservations': copy.deepcopy(model.reservations), 'orders': dict(model.orders)}
            check_facts(model, facts)
            for order, status in model.orders.items():
                rows = [dict(id=r['id'], sku=r['sku'], quantity=r['quantity'], availableStock=model.stock[r['sku']])
                        for r in model.reservations if r['orderId'] == order]
                assert client.request('GET', '/orders/'+order+'/details') == (200, {'id': order, 'status': status, 'reservations': rows}), 'public projection/model'
            return facts
        snapshot()
        for index, command in enumerate(commands(seed)):
            entry = {'step': index, 'command': command, 'status': 'started'}
            trace.append(entry)
            trace_file.write_text(json.dumps({'seed': seed, 'trace': trace}, indent=2)+'\n')
            try:
                kind = command['kind']
                if kind == 'fulfill':
                    outcome = model.fulfill(command['order'], command['sku'], command['quantity'])
                    request, receipt = client.fulfill(f'inv-{seed}-request-{index}', command['order'], command['sku'], command['quantity'], outcome)
                    history.append((request, receipt, {'status': 'Submitted' if outcome == 'ReservedAndSubmitted' else 'Rejected', 'outcome': outcome}))
                elif kind == 'submit':
                    order = command['order']
                    expected = ((200, {'id':order, 'status':'Submitted'}) if model.orders[order] == 'Draft'
                                else (409, {'code':'OrderNotDraft'}))
                    assert client.request('POST', '/orders/'+order+'/submit') == expected
                    model.orders[order] = 'Submitted'
                else:
                    request, receipt, result = history[command['index'] % len(history)]
                    if kind == 'replay':
                        assert client.request('POST', '/fulfillment', request) == (202, receipt), 'replay identity'
                        assert client.request('GET', receipt['resultUrl']) == (200, result), 'replay result'
                    else:
                        assert client.request('POST', '/fulfillment', {**request, 'quantity':request['quantity']+1}) == (409, {'code':'RequestIdentityConflict'}), 'identity conflict'
                snapshot(entry)
                entry['status'] = 'passed'
            except Exception as error:
                entry['status'] = 'failed'; entry['error'] = str(error)
                raise
            finally:
                trace_file.write_text(json.dumps({'seed': seed, 'trace': trace}, indent=2)+'\n')
        reports.append({'seed': seed, 'commands': len(trace), 'facts': observer(seed)})
    return reports
