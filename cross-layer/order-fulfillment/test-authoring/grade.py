"""Grade frozen author suites and independently confirm paired defects on isolated live fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

from pilot import APP, CONDITIONS, ROOT, live, prepare
from cohesive_evals.http_client import HttpClient
from cohesive_evals.postgres import IMAGE, verification_run

CONTROL_HASH = 'd40da24dcdef528b82339686cf0c783ab6859ecb2078d3662c07346ff61a5e60'
# Each witness has a known-good observation and one deliberately wrong observation.
WITNESSES = {
    'reject-repeat-pack': ('POST', '/orders/packed/pack', [200, 'Packed'], [409, 'OrderNotPackable']),
    'reopen-cancelled': ('POST', '/orders/cancelled/unpack', [409, 'OrderNotUnpackable'], [200, 'Submitted']),
    'unpack-route-dispatches-pack': ('POST', '/orders/submitted/unpack', [200, 'Submitted'], [200, 'Packed']),
    'wrong-pack-conflict-code': ('POST', '/orders/draft/pack', [409, 'OrderNotPackable'], [409, 'OrderNotDraft']),
    'stale-packed-details': ('GET', '/orders/packed/details', [200, 'Packed'], [200, 'Submitted']),
    'missing-compensation': ('GET', '/inventory/stock', [200, 20], [200, 18]),
}


def write_json(path, value):
    """Persist a readable result after each completed candidate."""
    path.write_text(json.dumps(value, indent=2) + '\n')


def confirm(url, name, mutated):
    """Observe the planted defect through public HTTP, failing setup on an unexpected witness."""
    http = HttpClient(url)
    if name == 'missing-compensation':
        status, receipt = http.request('POST', '/fulfillment', {
            'orderId': 'packed', 'requestId': 'confirm-compensation', 'sku': 'stock', 'quantity': 2})
        if status != 202:
            raise ValueError(('witness admission', status, receipt))
        deadline = time.monotonic() + 20
        while True:
            status, body = http.request('GET', receipt['resultUrl'])
            if status != 202:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('witness completion')
            time.sleep(.02)
        if (status, body) != (200, {'status': 'Rejected', 'outcome': 'OrderRejected'}):
            raise ValueError(('witness completion', status, body))
    method, path, correct, defective = WITNESSES[name]
    status, body = http.request(method, path)
    value = body.get('code', body.get('status', body.get('available')))
    actual = [status, value]
    if actual != (defective if mutated else correct):
        raise ValueError(('witness mismatch', name, actual, correct, defective))
    return actual


def execute(folder, out, url):
    """Run a compiled suite and distinguish named mismatches from execution and setup errors."""
    dll = folder / 'Suite/bin/Debug/net10.0/Suite.dll'
    try:
        result = subprocess.run(['dotnet', str(dll), url], cwd=folder, capture_output=True,
                                text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return {'outcome': 'timeout'}
    (out / 'suite.log').write_text(result.stdout + result.stderr)
    checks = []
    for line in result.stdout.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and set(row) == {'label', 'expected', 'actual', 'passed'}:
            checks.append(row)
    failed = [row for row in checks if row['passed'] is False]
    outcome = 'execution-error'
    if result.returncode == 0 and checks and all(row['passed'] is True for row in checks):
        outcome = 'pass'
    elif result.returncode == 10 and len(failed) == 1 and failed[0]['label'] and failed[0]['expected'] != failed[0]['actual']:
        outcome = 'named-failure'
    return {'outcome': outcome, 'exit': result.returncode, 'assertionsReached': len(checks), 'failure': failed}


def grade(output):
    """Build each isolated mutation, verify its live witness and replay each submitted suite twice."""
    manifest = ROOT / 'controls.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != CONTROL_HASH:
        raise ValueError('Pre-session control pin changed')
    controls = json.loads(manifest.read_text())
    if set(WITNESSES) != {row['id'] for row in controls}:
        raise ValueError('Every control requires a paired independent witness')
    results = []
    with verification_run(output, 'test-authoring-grade', ()) as pg:
        fixtures = output / 'fixtures'
        prepare(fixtures)
        metadata = {'postgresImage': IMAGE, 'postgresImageId': pg.image_id,
                    'dotnet': subprocess.check_output(['dotnet', '--version'],
                                                      cwd=fixtures / CONDITIONS[0], text=True).strip()}
        write_json(output / 'environment.json', metadata)
        for condition in CONDITIONS:
            folder = fixtures / condition
            suite = ROOT / 'submissions' / condition / 'Program.cs'
            if hashlib.sha256(suite.read_bytes()).hexdigest() != json.loads((ROOT / 'sessions.json').read_text())[condition]['sha256']:
                raise ValueError('Frozen suite hash changed')
            shutil.copyfile(suite, folder / 'Suite/Program.cs')
            for index, control in enumerate([None, *controls]):
                name = control['id'] if control else 'reference'
                directory = output / condition / name
                directory.mkdir(parents=True)
                record = {'condition': condition, 'candidate': name, 'runs': []}
                original = None
                try:
                    if control:
                        delta = control[condition]
                        path = folder / APP / delta['file']
                        original = path.read_text()
                        if original.count(delta['before']) != 1:
                            raise ValueError('Mutation anchor drift')
                        path.write_text(original.replace(delta['before'], delta['after']))
                    with (directory / 'build.log').open('w') as log:
                        subprocess.run(['dotnet', 'build', 'Suite/Suite.csproj', '--no-restore', '--no-incremental'],
                                       cwd=folder, stdout=log, stderr=log, check=True, timeout=120)
                    with live(pg, folder, directory, f'w_{condition}_{index}') as url:
                        names = [name] if control else list(WITNESSES)
                        record['witnesses'] = {n: confirm(url, n, control is not None) for n in names}
                    for attempt in range(2):
                        out = directory / str(attempt)
                        out.mkdir()
                        with live(pg, folder, out, f's_{condition}_{index}_{attempt}') as url:
                            record['runs'].append(execute(folder, out, url))
                except Exception as error:
                    record['setupError'] = repr(error)
                finally:
                    if original is not None:
                        path.write_text(original)
                results.append(record)
                write_json(output / 'results.json', results)
                print(condition, name, [r['outcome'] for r in record['runs']], record.get('setupError', ''), flush=True)
                if not control and [r['outcome'] for r in record['runs']] != ['pass', 'pass']:
                    break  # A suite without a valid reference run cannot earn mutation credit.

    complete = len(results) == len(CONDITIONS) * (len(controls) + 1)
    for record in results:
        outcomes = [attempt['outcome'] for attempt in record['runs']]
        allowed = [['pass', 'pass']]
        if record['candidate'] != 'reference':
            allowed.append(['named-failure', 'named-failure'])
        if record.get('setupError') or outcomes not in allowed:
            complete = False
    if not complete:
        raise RuntimeError(f'Incomplete or inconsistent grading; inspect {output / "results.json"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    grade(parser.parse_args().output.resolve())
