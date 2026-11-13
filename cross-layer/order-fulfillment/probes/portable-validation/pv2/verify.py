#!/usr/bin/env python3
"""PV2 boundary, ordering, replay and physical-preservation checks."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'pv1'))
import verify as pv1
from runtime import verification_run
checks = pv1.build.load('pv2_checks', ROOT / 'length_checks.py')
visible = pv1.build.load('pv2_visible', ROOT / 'visible_checks.py')
harness = pv1.harness

def verify(args):
    records = {}
    with verification_run(args.output, 'pv2', checks.BehavioralFailure) as session:
        container, port = session.container, session.port
        for condition in ([args.condition] if args.condition else harness.CONDITIONS):
            session.condition = condition
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
                checks.require(all(records[c][scenario] == records[harness.CONDITIONS[0]][scenario] for c in harness.CONDITIONS), 'PV2-03', 'condition equivalence', scenario)
        session.report(records)
    print('PV2 passed:', ', '.join(records), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--condition', choices=harness.CONDITIONS)
    args = parser.parse_args()
    args.fixtures = args.fixtures.resolve()
    args.output = args.output.resolve()
    verify(args)
