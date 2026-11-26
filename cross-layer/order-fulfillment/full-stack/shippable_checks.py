"""Independent observations of the persisted shippable quantity and operator repair."""
from time import monotonic, sleep

from cohesive_evals.runtime import capture, run


def sql(pg, statement):
    """Execute evaluator-owned SQL on the disposable pilot database; SQL errors are setup failures."""
    return capture('docker', 'exec', pg.container, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1', '-Atc', statement)


def persisted_version(pg):
    """Read the unrelated row's tuple version so a full rewrite cannot masquerade as keyed maintenance."""
    return sql(pg, "SELECT xmin::text FROM order_shippable WHERE order_id = 'control'")


def check_view(pg, api, identity, quantity, expect, checks, label):
    """Allow bounded worker lag, then compare the entire public row to independently authored values."""
    expected = (200, {'orderId': identity, 'quantity': quantity})
    deadline = monotonic() + 20
    while True:
        settled = sql(pg, "SELECT r.revision = p.revision FROM shippable_request r CROSS JOIN shippable_progress p")
        if settled == 't' or monotonic() >= deadline:
            break
        sleep(0.1)
    observed = api.request('GET', f'/orders/{identity}/shippable')
    expect('shippable-' + label, (settled, observed), ('t', expected), checks)


def prove_resync(pg, api, dll, env, expect, checks):
    """Remove a published row while keeping its source, then require operator resync to restore it."""
    sql(pg, "DELETE FROM order_shippable WHERE order_id = 'control'")
    expect('reads-persisted-target', api.request('GET', '/orders/control/shippable')[0], 404, checks)
    expect('repair-source-intact', api.request('GET', '/orders/control/shipping'),
           (200, dict(id='control', status='Packed', held=False, remaining=4, released=0)), checks)
    run('dotnet', str(dll), '--resync-shippable', env=env)
    check_view(pg, api, 'control', 4, expect, checks, 'resync')
