"""Shared build execution, verification and defect qualification for evolution profiles.

Behavioral expectations remain in each generation's independent check module.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent
CASE = ROOT.parent
CHECK_MODULES = {'e1': 'checks.py', 'e2': 'cancellation_checks.py', 'e3': 'quarantine_checks.py'}
GENERATIONS = tuple(CHECK_MODULES)
CONDITIONS = ('conventional', 'cohesive')
IMAGE = 'postgres:17.10-alpine3.24'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile(generation):
    folder = ROOT / generation
    checks_file = CHECK_MODULES[generation]
    return {
        'name': generation,
        'build': load(generation + '_build', folder / 'build.py'),
        'checks': load(generation + '_checks', folder / checks_file),
        'visible': load(generation + '_visible', folder / 'visible_checks.py'),
        'mutations': load(generation + '_mutations', folder / 'mutations.py'),
    }


def selected_profiles(generation, only_generation=False):
    names = [generation] if only_generation else GENERATIONS[:GENERATIONS.index(generation) + 1]
    return [profile(name) for name in names]


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def start(executable, folder, env, log, ready_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    process = subprocess.Popen(['dotnet', str(executable), '--urls', url], cwd=folder,
                               env=env, stdout=log, stderr=log)
    try:
        for _ in range(150):
            if process.poll() is not None:
                raise RuntimeError('Host exited during startup')
            try:
                urllib.request.urlopen(url + ready_path, timeout=1).close()
                return process, url
            except (urllib.error.URLError, TimeoutError):
                time.sleep(.1)
        raise RuntimeError('Host readiness deadline')
    except BaseException:
        stop(process)
        raise


def observe(container, condition, generation, target_generation=None):
    # Identifiers and scope are selected from trusted profile constants, never request data.
    assert generation in GENERATIONS
    tables = {
        'conventional': ('orders', 'id', 'inventory', 'reservations', 'id'),
        'cohesive': ('cohesive_orders', 'order_id', 'cohesive_inventory', 'cohesive_reservations', 'reservation_id'),
    }
    order, order_id, inventory, reservation, reservation_id = tables[condition]
    prefix = generation + '-%'
    quarantine_column = ',quarantined' if target_generation == 'e3' else ''
    sql = f'''SELECT json_build_object(
      'orders',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT {order_id} AS id,status FROM {order} WHERE {order_id} LIKE '{prefix}') x),
      'inventory',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT sku,available,max_per_order AS "maxPerOrder"{quarantine_column} FROM {inventory} WHERE sku LIKE '{prefix}') x),
      'reservations',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT {reservation_id} AS id,order_id AS "orderId",sku,quantity FROM {reservation} WHERE order_id LIKE '{prefix}') x));'''
    facts = json.loads(run('docker', 'exec', container, 'psql', '-U', 'postgres', '-d', condition, '-At', '-c', sql))
    if target_generation == 'e3' and generation != 'e3':
        facts['inventory'] = [prior_inventory(item) for item in facts['inventory']]
    return facts


def prior_inventory(item):
    # Earlier worlds never issue quarantine commands. Check the new neutral field
    # before adapting their unchanged expectations; never silently discard it.
    if item.get('quarantined') is not False:
        raise AssertionError(('prior inventory quarantine default/preservation', item))
    return {key: value for key, value in item.items() if key != 'quarantined'}


def prior_client(Client, target_generation):
    if target_generation != 'e3':
        return Client

    class PriorClient(Client):
        def request(self, method, path, body=None, raw=None):
            status, value = super().request(method, path, body, raw)
            if status == 200 and path.startswith('/inventory/') and isinstance(value, dict):
                value = prior_inventory(value)
            return status, value

    return PriorClient


def matching_artifacts(fixtures, profiles):
    paths = ['src/Fulfillment.Application/' + name for name in
             ['Program.cs', 'Contracts.cs', 'QuantityLimitInput.cs', 'OperationQueue.cs', 'ReadResults.cs']]
    paths += ['CONTRACT.md', 'schemas.json', 'seed.schema.json', 'contract-examples.json']
    paths += [f"tests/{p['name']}_checks.py" for p in profiles]
    for path in paths:
        assert (fixtures / 'conventional' / path).read_bytes() == (fixtures / 'cohesive' / path).read_bytes(), path


def verify(args):
    args.output.mkdir(parents=True, exist_ok=False)
    profiles = selected_profiles(args.generation, args.only_generation)
    build_tools = profiles[-1]['build'].build_tools
    failure_types = tuple(p['checks'].BehavioralFailure for p in profiles)
    base = load('baseline_http', CASE / 'conditions/conventional/tests/contract_tests.py')
    Client = base.Client

    EarlierClient = prior_client(Client, args.generation)

    class InventoryClient(EarlierClient):
        def expect(self, label, method, path, status, body=None, expected=None, raw=None):
            if path.startswith('/inventory/') and isinstance(expected, dict) and 'maxPerOrder' not in expected:
                expected = {**expected, 'maxPerOrder': 2147483647}
            return super().expect(label, method, path, status, body, expected, raw)

    base.Client = InventoryClient
    invariants = load('baseline_invariants', CASE / 'verification/invariants.py')
    name = 'evolution-' + uuid.uuid4().hex[:12]
    started = False
    records = {}
    condition = None
    try:
        if not args.condition:
            matching_artifacts(args.fixtures, profiles)
        image_id = run('docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}')
        run('docker', 'run', '-d', '--name', name, '-e', 'POSTGRES_PASSWORD=fixture-only',
            '-p', '127.0.0.1::5432', IMAGE)
        started = True
        for _ in range(100):
            if subprocess.run(['docker', 'exec', name, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(.1)
        else:
            raise RuntimeError('PostgreSQL readiness deadline')
        port = run('docker', 'port', name, '5432/tcp').rsplit(':', 1)[1]
        for condition in ([args.condition] if args.condition else CONDITIONS):
            folder = args.fixtures / condition
            fingerprint = build_tools.verify_build(folder)
            output = args.output / condition
            output.mkdir()
            run('docker', 'exec', name, 'psql', '-U', 'postgres', '-c', f'CREATE DATABASE {condition}')
            data = {'orders': [], 'inventory': [], 'reservations': []}
            seeds = [p['checks'].fixture() for p in profiles]
            if not args.only_generation:
                seeds += [p['visible'].SEED for p in profiles] + [base.SEED, invariants.fixture()]
            for seed in seeds:
                for key in data:
                    data[key] += seed[key]
            seed_file = output / 'seed.json'
            seed_file.write_text(json.dumps(data))
            executable = folder / 'src/Fulfillment.Application/bin/Debug/net10.0/Fulfillment.Application.dll'
            env = dict(os.environ, ConnectionStrings__Orders=f'Host=127.0.0.1;Port={port};Database={condition};Username=postgres;Password=fixture-only;Timeout=10', ASPNETCORE_ENVIRONMENT='Production')
            ready_path = '/orders/' + profiles[0]['name'] + '-0'
            observations = {}
            with (output / 'host.log').open('w') as log:
                subprocess.run(['dotnet', str(executable), '--seed', str(seed_file)], cwd=folder,
                               env=dict(env, FULFILLMENT_SETUP='1'), stdout=log, stderr=log, check=True, timeout=90)
                process, url = start(executable, folder, env, log, ready_path)
                checkers = []
                try:
                    if not args.only_generation:
                        observations['baseline'] = base.exercise(url)
                        observations['invariants'] = invariants.exercise(EarlierClient, url,
                            lambda seed: invariants.observe(run, name, condition, seed), output)
                    for p in profiles:
                        generation = p['name']
                        ProfileClient = Client if generation == 'e3' else EarlierClient
                        if not args.only_generation:
                            observations['visible' + generation.upper()] = p['visible'].exercise(ProfileClient, url)
                        checker = p['checks'].Checks(ProfileClient, url,
                            lambda g=generation: observe(name, condition, g, args.generation), output)
                        observations[generation] = checker.run()
                        checkers.append((generation, checker))
                finally:
                    stop(process)
                process, url = start(executable, folder, env, log, ready_path)
                try:
                    for generation, checker in checkers:
                        ProfileClient = Client if generation == 'e3' else EarlierClient
                        checker.c = ProfileClient(url)
                        checker.after_restart()
                        observations[generation]['commands'] = len(checker.trace)
                        observations[generation]['cleanRestartVerified'] = True
                finally:
                    stop(process)
            assert build_tools.verify_build(folder) == fingerprint, 'Build changed during verification'
            records[condition] = {**observations, 'buildManifestSha256': fingerprint}
        if not args.condition:
            for key in observations:
                assert records['conventional'][key] == records['cohesive'][key], ('condition equivalence', key)
        report = {'passed': True, 'generation': args.generation,
                  'priorCheckpointsVerified': not args.only_generation,
                  'postgresImage': IMAGE, 'postgresImageId': image_id, 'conditions': records}
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(args.generation, 'verification passed:', ', '.join(records), flush=True)
    except failure_types as error:
        (args.output / 'failure.json').write_text(json.dumps({
            'kind': 'behavioral', 'condition': condition, 'obligation': error.obligation,
            'assertion': error.assertion, 'detail': str(error)}, indent=2) + '\n')
        raise
    except Exception as error:
        (args.output / 'failure.json').write_text(json.dumps({
            'kind': 'unqualified', 'condition': condition, 'detail': str(error)}, indent=2) + '\n')
        raise
    finally:
        if started:
            subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, check=True)


def detected(result_code, failure, obligation, assertion):
    return (result_code != 0 and failure is not None and failure.get('kind') == 'behavioral'
            and failure.get('obligation') == obligation and failure.get('assertion') == assertion)


def qualify(args):
    args.output.mkdir(parents=True, exist_ok=False)
    p = profile(args.generation)
    fixtures = p['build'].materialize(args.output / 'references')
    build_tools = p['build'].build_tools
    records = []
    for condition in CONDITIONS:
        folder = fixtures / condition
        for name, mutation in {'known-good': None, **p['mutations'].mutations(condition)}.items():
            candidate = args.output / condition / name
            candidate.mkdir(parents=True)
            original = None
            try:
                if mutation:
                    file, before, after, obligation = mutation
                    path = folder / 'src/Fulfillment.Application' / file
                    original = path.read_text()
                    assert original.count(before) == 1, (condition, name, 'mutation anchor drift')
                    path.write_text(original.replace(before, after))
                    (candidate / 'mutation.json').write_text(json.dumps({
                        'file': file, 'before': before, 'after': after, 'expectedObligation': obligation,
                        'originalSha256': hashlib.sha256(original.encode()).hexdigest()}, indent=2) + '\n')
                with (candidate / 'build.log').open('w') as log:
                    build_tools.build_candidate(folder, log)
                fingerprint = build_tools.verify_build(folder)
                (candidate / 'build-manifest.json').write_bytes((folder / 'build-manifest.json').read_bytes())
                command = [sys.executable, '-B', str(ROOT / 'verify.py'), '--generation', args.generation,
                           '--fixtures', str(fixtures), '--condition', condition, '--output', str(candidate / 'verification')]
                if mutation:
                    command += ['--only-generation']
                with (candidate / 'verification.log').open('w') as log:
                    result = subprocess.run(command, stdout=log, stderr=log, timeout=600)
                assert build_tools.verify_build(folder) == fingerprint, 'Build changed during qualification'
                failed = candidate / 'verification/failure.json'
                failure = json.loads(failed.read_text()) if failed.exists() else None
                if mutation:
                    assert detected(result.returncode, failure, obligation, p['mutations'].EXPECTED_ASSERTIONS[name]), (condition, name, 'not qualified', failure)
                else:
                    assert result.returncode == 0 and (candidate / 'verification/report.json').exists(), (condition, 'known-good failed', failure)
                records.append({'condition': condition, 'case': name, 'passed': True,
                                'obligation': failure['obligation'] if failure else None,
                                'assertion': failure['assertion'] if failure else None,
                                'buildManifestSha256': fingerprint})
                print(condition, name, 'qualified', flush=True)
            finally:
                if original is not None:
                    path.write_text(original)
    (args.output / 'report.json').write_text(json.dumps({'passed': True, 'generation': args.generation, 'cases': records}, indent=2) + '\n')


def main_verify(generation=None):
    parser = argparse.ArgumentParser(description='Verify a generation and its active predecessors.')
    parser.add_argument('--generation', choices=GENERATIONS, default=generation, required=generation is None)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--condition', choices=CONDITIONS)
    parser.add_argument('--only-generation', '--e1-only', '--e2-only', action='store_true')
    args = parser.parse_args()
    args.fixtures = args.fixtures.resolve()
    args.output = args.output.resolve()
    verify(args)


def main_qualify(generation=None):
    parser = argparse.ArgumentParser(description='Qualify named behavioral defects for a generation.')
    parser.add_argument('--generation', choices=GENERATIONS, default=generation, required=generation is None)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    qualify(args)
