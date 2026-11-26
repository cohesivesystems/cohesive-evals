"""Frozen logical fixture, mutation trace and independent pick-list oracle for issue 76."""
from collections import Counter
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class Order:
    """Warehouse facts for one order; repeated SKU lines are intentional."""
    id: str
    location: str
    priority: int
    packed: bool
    held: bool
    lines: tuple


def fixture():
    """Return active orders, adversarial controls and location-scoped physical stock."""
    orders, stock = {}, {}
    for loc in range(32):
        location = f'L{loc:02}'
        for index in range(100):
            sku = 'shared' if index in range(9, 80, 10) else f'S{index:02}'
            stock[location, sku] = 8 if sku == 'shared' else 1
            order = Order(f'O{loc:02}{index:03}', location, index % 10, True, False, ((sku, 1),))
            orders[order.id] = order
    for index, lines in enumerate([(), (('missing', 1),), (('low', 2),),
                                   (('low', 1), ('low', 1)), (('ok', 1), ('ok', 1)),
                                   (('ok', 1), ('missing', 1))]):
        order = Order(f'C{index}', 'controls', 1, True, False, lines)
        orders[order.id] = order
    stock['controls', 'ok'] = 2
    stock['controls', 'low'] = 1
    stock['elsewhere', 'missing'] = 10
    return orders, stock


def page(orders, stock, location):
    """Compute wire rows from source facts without using candidate query or storage code."""
    eligible = []
    for order in orders.values():
        if order.location != location or not order.packed or order.held or not order.lines:
            continue
        need = Counter()
        for sku, quantity in order.lines:
            need[sku] += quantity
        if all(stock.get((location, sku), 0) >= total for sku, total in need.items()):
            eligible.append(order)
    eligible.sort(key=lambda order: (-order.priority, order.id))
    return [dict(orderId=o.id, priority=o.priority) for o in eligible[:50]]


def digest(value):
    """Hash canonical JSON including array order, value types and exact object keys."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def trace():
    """Yield 6,000 single-location mutations in scheduled commit order."""
    for tick in range(6000):
        loc = tick % 32
        phase = tick // 32 % 4
        yield (f'L{loc:02}', 'hold' if phase % 2 == 0 else 'stock',
               f'O{loc:02}089' if phase % 2 == 0 else 'shared', (True, 0, False, 8)[phase])


def freeze():
    """Generate compact golden pages and a digest of the complete mutation/expected-page stream."""
    orders, stock = fixture()
    pages = {loc: [digest(page(orders, stock, loc))] for loc in sorted({o.location for o in orders.values()} | {'unknown'})}
    stream = []
    for i, (loc, kind, key, val) in enumerate(trace()):
        if kind == 'hold':
            orders[key] = replace(orders[key], held=val)
        else:
            stock[loc, key] = val
        phase = i // 32 % 4
        if i < 128:
            pages[loc].append(digest(page(orders, stock, loc)))
        stream.append([loc, kind, key, val, pages[loc][phase + 1]])
    assert all(len(set(pages[f'L{i:02}'])) == 4 for i in range(32))
    return dict(pages=pages, traceSha256=digest(stream))


if __name__ == '__main__':
    assert freeze() == json.loads(Path(__file__).with_name('golden.json').read_text())
