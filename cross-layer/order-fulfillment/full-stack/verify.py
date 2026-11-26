"""Verify the old-to-new PostgreSQL upgrade through real hosts and the retained lifecycle oracle."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess

from build import HOST_DLL, LIFECYCLE, ROOT, build, compile_suite
from cohesive_evals.http_client import HttpClient
from cohesive_evals.postgres import verification_run
from cohesive_evals.runtime import capture, host, kestrel_url, run


class Mismatch(AssertionError):
    """Name a failed observable contract separately from infrastructure errors."""

    def __init__(self, name, expected, actual):
        """Record the failed obligation and its public evidence."""
        self.assertion = name
        super().__init__(f'{name}: expected {expected!r}, got {actual!r}')


def expect(name, actual, expected, checks):
    """Record a named passing observation or fail with the actual result."""
    if actual != expected:
        raise Mismatch(name, expected, actual)
    checks.append(name)


@contextmanager
def serve(folder, output, env):
    """Launch the selected compiled host against the carried database until context exit."""
    log = output / 'host.log'
    offset = log.stat().st_size if log.exists() else 0
    with host(['dotnet', str(folder / HOST_DLL),
               '--urls', 'http://127.0.0.1:0'], folder, output, env) as process:
        yield HttpClient(kestrel_url(process, log, offset))


def state(remaining, held, released=None, status='Packed'):
    """Expected shipping observation for the one carried order, in either public schema."""
    view = dict(id='legacy', status=status, held=held, remaining=remaining)
    if released is not None:
        view['released'] = released
    return view


def shipping(client, command='shipping', quantity=None):
    """Call one public command or read the persisted shipping state."""
    return client.request('GET' if command == 'shipping' else 'POST', '/orders/legacy/' + command,
                          None if quantity is None else {'quantity': quantity})


def problem_code(client, command, quantity):
    """Read the declared status and domain code from the public Problem Details response."""
    status, problem = shipping(client, command, quantity)
    return status, problem.get('code')


def retained(folder, label, checks, *, original=False):
    """Check each version's typed executor against #70's independent lifecycle oracle."""
    prior = runpy.run_path(str(LIFECYCLE / 'grade.py'))
    suite = folder / 'Suite'
    if original:
        for name in ['Adapter.cs', 'Cases.cs']:
            (suite / name).unlink(missing_ok=True)
        shutil.copyfile(LIFECYCLE / 'Program.cs', suite / 'Program.cs')
        shutil.copyfile(LIFECYCLE / 'submissions/cohesive.cs', suite / 'Submission.cs')
        compile_suite(folder)
    expect(label, prior['differences'](folder, prior['coverage']()), [], checks)


def verify(output):
    """Create the legacy row, migrate in place, exercise release boundaries and verify restart."""
    with verification_run(output, 'partial-release', Mismatch) as pg:
        checks = []
        folder = build(output / 'checkpoint')
        retained(folder, 'checkpoint-retains-130-lifecycle-paths', checks, original=True)
        env = dict(os.environ, ConnectionStrings__Orders=f'Host=127.0.0.1;Port={pg.port};Database=postgres;Username=postgres;Password=fixture-only')
        seed = output / 'legacy.json'
        seed.write_text(json.dumps(dict(orders=[dict(id='legacy', status='Submitted', remaining=3)],
                                        inventory=[], reservations=[])))
        run('dotnet', str(folder / HOST_DLL), '--seed', str(seed),
            env=dict(env, FULFILLMENT_SETUP='1'))
        denied = (409, {'code': 'NotShippable'})

        with serve(folder, output, env) as api:
            expect('legacy-pack', shipping(api, 'pack'), (200, dict(id='legacy', status='Packed')), checks)
            expect('legacy-hold', shipping(api, 'hold'), (200, state(3, True)), checks)
            expect('legacy-held-rejection', shipping(api, 'ship', 1), denied, checks)
        with serve(folder, output, env) as api:
            expect('legacy-restart', shipping(api), (200, state(3, True)), checks)
        old_column = capture('docker', 'exec', pg.container, 'psql', '-U', 'postgres', '-Atc',
                             "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='cohesive_orders' AND column_name='released'")
        expect('legacy-schema-has-no-allowance', old_column, '0', checks)
        folder = build(output / 'evolved', evolved=True)
        startup = subprocess.run(['dotnet', str(folder / HOST_DLL), '--urls', 'http://127.0.0.1:0'],
                                 cwd=folder, env=env, capture_output=True, text=True, timeout=15)
        diagnostic = startup.stdout + startup.stderr
        expect('unmigrated-host-rejects-mapping-at-startup',
               startup.returncode != 0 and all(part in diagnostic for part in
               ('postgres.schema.columnMismatch', 'cohesive_orders', 'column released')), True, checks)
        migration = (ROOT / 'partial-release/migrate.sql').read_text()
        for _ in range(2):
            run('docker', 'exec', '-i', pg.container, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1',
                input=migration, text=True)
        retained(folder, 'evolution-retains-130-lifecycle-paths', checks)
        with serve(folder, output, env) as api:
            expect('same-legacy-row-defaults-zero', shipping(api), (200, state(3, True, 0)), checks)
            expect('malformed-body', api.request_bytes('POST', '/orders/legacy/release-quantity', raw=b'{')[0], 400, checks)
            expect('zero-ship', problem_code(api, 'ship', 0), (400, 'orders.ship.InvalidQuantity'), checks)
            expect('zero-release', problem_code(api, 'release-quantity', 0), (400, 'orders.release.InvalidQuantity'), checks)
            expect('negative-release', problem_code(api, 'release-quantity', -1), (400, 'orders.release.InvalidQuantity'), checks)
            expect('partial-release', shipping(api, 'release-quantity', 1), (200, state(3, True, 1)), checks)
            expect('over-release', problem_code(api, 'release-quantity', 2147483647), (409, 'orders.release.ExceedsHeldQuantity'), checks)
            expect('over-ship', problem_code(api, 'ship', 2), (409, 'orders.ship.Held'), checks)
            expect('rejections-preserve-allowance', shipping(api), (200, state(3, True, 1)), checks)
        with serve(folder, output, env) as api:
            expect('restart-preserves-allowance', shipping(api), (200, state(3, True, 1)), checks)
            expect('consume-allowance', shipping(api, 'ship', 1), (200, state(2, True, 0)), checks)
            expect('held-remainder-cannot-ship', problem_code(api, 'ship', 1), (409, 'orders.ship.Held'), checks)
            expect('release-again', shipping(api, 'release-quantity', 1), (200, state(2, True, 1)), checks)
            expect('unpack', shipping(api, 'unpack'), (200, dict(id='legacy', status='Submitted')), checks)
            expect('cannot-release-while-unpacked', problem_code(api, 'release-quantity', 1), (409, 'orders.release.NotPacked'), checks)
            expect('repack', shipping(api, 'pack'), (200, dict(id='legacy', status='Packed')), checks)
            expect('repack-preserves-allowance', shipping(api), (200, state(2, True, 1)), checks)
            expect('additive-release', shipping(api, 'release-quantity', 1), (200, state(2, True, 2)), checks)
            expect('hold-revokes-allowance', shipping(api, 'hold'), (200, state(2, True, 0)), checks)
            expect('full-release', shipping(api, 'release'), (200, state(2, False, 0)), checks)
            expect('cannot-release-unheld', problem_code(api, 'release-quantity', 1), (409, 'orders.release.NotHeld'), checks)
            expect('finish', shipping(api, 'ship', 2), (200, state(0, False, 0, 'Shipped')), checks)
            expect('terminal-replay-rejected', problem_code(api, 'ship', 1), (409, 'orders.ship.NotShippable'), checks)
            expect('terminal-state-preserved', shipping(api), (200, state(0, False, 0, 'Shipped')), checks)
        capture('docker', 'exec', pg.container, 'createdb', '-U', 'postgres', 'fresh')
        fresh = dict(env, ConnectionStrings__Orders=env['ConnectionStrings__Orders'].replace('Database=postgres;', 'Database=fresh;'))
        with serve(folder, output, fresh) as api:
            status, created = api.request('POST', '/orders')
            expect('fresh-schema-create', status, 201, checks)
            path = '/orders/' + created['id']
            expect('new-order-default', api.request('GET', path + '/shipping'),
                   (200, dict(id=created['id'], status='Draft', held=False, remaining=1, released=0)), checks)
            for command in ['submit', 'pack', 'hold']:
                expect('fresh-' + command, api.request('POST', path + '/' + command)[0], 200, checks)
            expect('fresh-release-last-unit', api.request('POST', path + '/release-quantity', {'quantity': 1})[0], 200, checks)
            expect('fresh-ship-last-approved-unit', api.request('POST', path + '/ship', {'quantity': 1}),
                   (200, dict(id=created['id'], status='Shipped', held=True, remaining=0, released=0)), checks)
        pg.report(dict(cohesive=dict(checks=checks, legacyOrder='legacy', reseededAfterUpgrade=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='Fresh directory for logs, built host and evidence')
    verify(parser.parse_args().output.resolve())
