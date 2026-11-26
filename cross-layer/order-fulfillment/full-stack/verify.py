"""Verify the old-to-new PostgreSQL upgrade through real hosts and the retained lifecycle oracle."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import runpy
import shutil

from build import APP, LIFECYCLE, ROOT, build, compile_suite, evolve
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
    with host(['dotnet', str(folder / APP / 'bin/Debug/net10.0/Fulfillment.Application.dll'),
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


def retained(folder, label, checks):
    """Check the frozen executor against #70's independent oracle on every reachable state/command."""
    prior = runpy.run_path(str(LIFECYCLE / 'grade.py'))
    suite = folder / 'Suite'
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
        retained(folder, 'checkpoint-retains-130-lifecycle-paths', checks)
        env = dict(os.environ, ConnectionStrings__Orders=f'Host=127.0.0.1;Port={pg.port};Database=postgres;Username=postgres;Password=fixture-only')
        seed = output / 'legacy.json'
        seed.write_text(json.dumps(dict(orders=[dict(id='legacy', status='Submitted', remaining=3)],
                                        inventory=[], reservations=[])))
        run('dotnet', str(folder / APP / 'bin/Debug/net10.0/Fulfillment.Application.dll'), '--seed', str(seed),
            env=dict(env, FULFILLMENT_SETUP='1'))
        denied = (409, {'code': 'NotShippable'})
        invalid = (409, {'code': 'NotReleasable'})
        with serve(folder, output, env) as api:
            expect('legacy-pack', shipping(api, 'pack'), (200, dict(id='legacy', status='Packed')), checks)
            expect('legacy-hold', shipping(api, 'hold'), (200, state(3, True)), checks)
            expect('legacy-held-rejection', shipping(api, 'ship', 1), denied, checks)
        with serve(folder, output, env) as api:
            expect('legacy-restart', shipping(api), (200, state(3, True)), checks)
        old_column = capture('docker', 'exec', pg.container, 'psql', '-U', 'postgres', '-Atc',
                             "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='cohesive_orders' AND column_name='released'")
        expect('legacy-schema-has-no-allowance', old_column, '0', checks)
        migration = (ROOT / 'partial-release/migrate.sql').read_text()
        for _ in range(2):
            run('docker', 'exec', '-i', pg.container, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1',
                input=migration, text=True)
        evolve(folder)
        retained(folder, 'evolution-retains-130-lifecycle-paths', checks)
        with serve(folder, output, env) as api:
            expect('same-legacy-row-defaults-zero', shipping(api), (200, state(3, True, 0)), checks)
            expect('zero-release', shipping(api, 'release-quantity', 0), invalid, checks)
            expect('negative-release', shipping(api, 'release-quantity', -1), invalid, checks)
            expect('partial-release', shipping(api, 'release-quantity', 1), (200, state(3, True, 1)), checks)
            expect('over-release', shipping(api, 'release-quantity', 2147483647), invalid, checks)
            expect('over-ship', shipping(api, 'ship', 2), denied, checks)
            expect('rejections-preserve-allowance', shipping(api), (200, state(3, True, 1)), checks)
        with serve(folder, output, env) as api:
            expect('restart-preserves-allowance', shipping(api), (200, state(3, True, 1)), checks)
            expect('consume-allowance', shipping(api, 'ship', 1), (200, state(2, True, 0)), checks)
            expect('held-remainder-cannot-ship', shipping(api, 'ship', 1), denied, checks)
            expect('release-again', shipping(api, 'release-quantity', 1), (200, state(2, True, 1)), checks)
            expect('unpack', shipping(api, 'unpack'), (200, dict(id='legacy', status='Submitted')), checks)
            expect('cannot-release-while-unpacked', shipping(api, 'release-quantity', 1), invalid, checks)
            expect('repack', shipping(api, 'pack'), (200, dict(id='legacy', status='Packed')), checks)
            expect('repack-preserves-allowance', shipping(api), (200, state(2, True, 1)), checks)
            expect('additive-release', shipping(api, 'release-quantity', 1), (200, state(2, True, 2)), checks)
            expect('hold-revokes-allowance', shipping(api, 'hold'), (200, state(2, True, 0)), checks)
            expect('full-release', shipping(api, 'release'), (200, state(2, False, 0)), checks)
            expect('cannot-release-unheld', shipping(api, 'release-quantity', 1), invalid, checks)
            expect('finish', shipping(api, 'ship', 2), (200, state(0, False, 0, 'Shipped')), checks)
            expect('terminal-replay-rejected', shipping(api, 'ship', 1), denied, checks)
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
