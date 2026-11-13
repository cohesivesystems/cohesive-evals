"""Shared PostgreSQL lifecycle and failure reports for portable-validation probes."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
import build

harness = build.harness

@dataclass
class VerificationRun:
    output: Path
    container: str
    port: str = ''
    image_id: str = ''
    condition: str | None = None

    def report(self, records):
        (self.output/'report.json').write_text(json.dumps({
            'passed': True, 'postgresImage': harness.IMAGE,
            'postgresImageId': self.image_id, 'conditions': records}, indent=2)+'\n')

    def failure(self, error, behavioral):
        record = {'kind': 'behavioral' if behavioral else 'unqualified',
                  'condition': self.condition, 'detail': str(error)}
        if behavioral:
            record.update(obligation=error.obligation, assertion=error.assertion)
        (self.output/'failure.json').write_text(json.dumps(record, indent=2)+'\n')

@contextmanager
def verification_run(output, prefix, behavioral_failure):
    output.mkdir(parents=True, exist_ok=False)
    session = VerificationRun(output, prefix+'-'+uuid.uuid4().hex[:12])
    started = False
    try:
        try:
            session.image_id = harness.run('docker', 'image', 'inspect', harness.IMAGE, '--format', '{{.Id}}')
            harness.run('docker', 'run', '-d', '--name', session.container, '-e',
                        'POSTGRES_PASSWORD=fixture-only', '-p', '127.0.0.1::5432', harness.IMAGE)
            started = True
            for _ in range(100):
                if subprocess.run(['docker', 'exec', session.container, 'pg_isready', '-h',
                                   '127.0.0.1', '-U', 'postgres'], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL).returncode == 0:
                    break
                time.sleep(.1)
            else:
                raise RuntimeError('PostgreSQL readiness deadline')
            session.port = harness.run('docker', 'port', session.container, '5432/tcp').rsplit(':', 1)[1]
            yield session
        finally:
            if started:
                # A cleanup failure must not replace the original behavioral/setup error.
                pending = sys.exc_info()[0] is not None
                try:
                    subprocess.run(['docker', 'rm', '-f', session.container],
                                   stdout=subprocess.DEVNULL, check=True, timeout=30)
                except Exception as error:
                    if not pending:
                        raise
                    print(f'PostgreSQL cleanup also failed: {error}', file=sys.stderr)
    except behavioral_failure as error:
        session.failure(error, behavioral=True)
        raise
    except Exception as error:
        session.failure(error, behavioral=False)
        raise
