"""Check the pilot's 1,000-identity admission contract across an abrupt host restart."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import uuid

from cohesive_evals.contracts import AdapterError
from cohesive_evals.evidence import dump
from cohesive_evals.postgres import verification_run
from cohesive_evals.runtime import HttpClient, capture, host, run, wait


class RequirementFailure(AssertionError):
    """Name a violated public guarantee so setup failures stay distinguishable."""

    def __init__(self, assertion, actual):
        """Retain the assertion name and actual observation for grading."""
        self.assertion = assertion
        super().__init__(f"{assertion}: {actual}")


def expect(actual, expected, name):
    """Compare an HTTP observation against a required status or retained receipt."""
    if actual != expected:
        raise RequirementFailure(name, actual)


@contextmanager
def scheduler(image):
    """Provide an isolated scheduler connection and remove the container on exit."""
    name = 'pilot-capacity-' + uuid.uuid4().hex[:10]
    capture('docker', 'run', '-d', '--name', name, '-p', '127.0.0.1::8080', image)
    try:
        port = capture('docker', 'port', name, '8080/tcp').rsplit(':', 1)[1]
        yield f'Endpoint=http://127.0.0.1:{port};TaskHub=default;Authentication=None'
    finally:
        capture('docker', 'rm', '-f', name)


def check(application, output, condition):
    """Fill a fresh application through HTTP and challenge capacity, replay and conflict twice."""
    manifest = Path(__file__).resolve().parents[1] / 'dependency-manifest.json'
    image = json.loads(manifest.read_text())['schedulerImage']
    with verification_run(output, 'pilot-capacity', RequirementFailure) as database, scheduler(image) as connection:
        database.condition = condition
        env = dict(os.environ, DURABLE_TASK_CONNECTION=connection,
                   ConnectionStrings__Orders=f'Host=127.0.0.1;Port={database.port};Database=postgres;Username=postgres;Password=fixture-only')
        seed = output / 'seed.json'
        dump(seed, {'orders': [{'id':'a','status':'Draft'}], 'inventory': [], 'reservations': []})
        run('dotnet', str(application), '--seed', str(seed), env=dict(env, FULFILLMENT_SETUP='1'))
        request = dict(requestId='r0', orderId='a', sku='missing', quantity=1)
        for phase in ('fill', 'restart'):
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                url = f'http://127.0.0.1:{sock.getsockname()[1]}'
            client = HttpClient(url)
            with host(['dotnet', str(application), '--urls', url], application.parent, output, env) as proc:
                def ready():
                    """Retry startup connection errors until the bounded host readiness deadline."""
                    try:
                        return client.request('GET', '/orders/a')[0] == 200
                    except AdapterError:
                        return False

                wait(proc, ready, 'capacity host readiness')
                if phase == 'fill':
                    first = client.request('POST', '/fulfillment', request)
                    expect(first[0], 202, 'first admission')
                    for index in range(1, 1000):
                        reply = client.request('POST', '/fulfillment', {**request, 'requestId': f'r{index}'})
                        expect(reply[0], 202, f'admit identity {index + 1}')
                expect(client.request('POST', '/fulfillment', {**request, 'requestId':'overflow'})[0], 503, phase + ' at capacity')
                expect(client.request('POST', '/fulfillment', request), first, phase + ' retained identity')
                expect(client.request('POST', '/fulfillment', {**request, 'quantity':2})[0], 409, phase + ' identity conflict')
                proc.kill()
                proc.wait(timeout=10)
        database.report({condition:{'distinctAdmissions':1000, 'restartCapacityReplayConflict':True}})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('application', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('condition')
    arguments = parser.parse_args()
    check(arguments.application.resolve(), arguments.output.resolve(), arguments.condition)
