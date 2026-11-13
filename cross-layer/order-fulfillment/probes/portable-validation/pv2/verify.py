#!/usr/bin/env python3
"""PV2 boundary, ordering, replay and physical-preservation checks."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'pv1'))
import verify as pv1
checks = pv1.build.load('pv2_checks', ROOT / 'length_checks.py')
visible = pv1.build.load('pv2_visible', ROOT / 'visible_checks.py')
harness = pv1.harness

def verify(args):
    args.output.mkdir(parents=True, exist_ok=False)
    container = 'pv2-'+uuid.uuid4().hex[:12]
    started = False
    condition = None
    records = {}
    try:
        image = harness.run('docker', 'image', 'inspect', harness.IMAGE, '--format', '{{.Id}}')
        harness.run('docker', 'run', '-d', '--name', container, '-e', 'POSTGRES_PASSWORD=fixture-only', '-p', '127.0.0.1::5432', harness.IMAGE)
        started = True
        for _ in range(100):
            if subprocess.run(['docker','exec',container,'pg_isready','-h','127.0.0.1','-U','postgres'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(.1)
        else:
            raise RuntimeError('PostgreSQL readiness deadline')
        port = harness.run('docker', 'port', container, '5432/tcp').rsplit(':', 1)[1]
        for condition in ([args.condition] if args.condition else harness.CONDITIONS):
            folder = args.fixtures / condition
            fingerprint = pv1.build.build_tools.verify_build(folder)
            results = {}
            for scenario in ('run', 'capacity'):
                world = pv1.World(folder, args.output/condition/scenario, container, port, condition, checks.fixture())
                try:
                    results[scenario] = getattr(checks.Checks(world), scenario)()
                finally:
                    world.close()
            world = pv1.World(folder, args.output/condition/'visible', container, port, condition, checks.fixture())
            try:
                results['visibleChecks'] = visible.exercise(world.url)
            finally:
                world.close()
            assert pv1.build.build_tools.verify_build(folder) == fingerprint
            records[condition] = {**results, 'buildManifestSha256': fingerprint}
        if not args.condition:
            for scenario in ('run', 'capacity', 'visibleChecks'):
                checks.require(records['conventional'][scenario] == records['cohesive'][scenario], 'PV2-03', 'condition equivalence', scenario)
        (args.output/'report.json').write_text(json.dumps({'passed':True, 'postgresImage':harness.IMAGE, 'postgresImageId':image, 'conditions':records}, indent=2)+'\n')
        print('PV2 passed:', ', '.join(records), flush=True)
    except checks.BehavioralFailure as error:
        (args.output/'failure.json').write_text(json.dumps({'kind':'behavioral', 'condition':condition, 'obligation':error.obligation, 'assertion':error.assertion, 'detail':str(error)}, indent=2)+'\n')
        raise
    except Exception as error:
        (args.output/'failure.json').write_text(json.dumps({'kind':'unqualified', 'condition':condition, 'detail':str(error)}, indent=2)+'\n')
        raise
    finally:
        if started:
            subprocess.run(['docker','rm','-f',container], stdout=subprocess.DEVNULL, check=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--condition', choices=harness.CONDITIONS)
    args = parser.parse_args()
    args.fixtures = args.fixtures.resolve()
    args.output = args.output.resolve()
    verify(args)
