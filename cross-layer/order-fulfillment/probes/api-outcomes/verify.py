#!/usr/bin/env python3
"""Run AO1 against real hosts, then preserve seeded state across a clean restart."""
import argparse
import json
from pathlib import Path
import sys
import build
sys.path.insert(0,str(build.ROOT.parent / 'portable-validation/pv1'))
pv1 = build.load('ao1_runtime_world', build.ROOT.parent / 'portable-validation/pv1/verify.py')
from runtime import verification_run
checks = build.load('ao1_checks', build.ROOT / 'checks.py')

def verify(args):
    records = {}
    with verification_run(args.output, 'ao1', checks.BehavioralFailure) as session:
        for condition in ([args.condition] if args.condition else build.harness.CONDITIONS):
            session.condition = condition
            folder = args.fixtures / condition
            fingerprint = build.build_tools.verify_build(folder)
            world = pv1.World(folder,args.output/condition,session.container,session.port,condition,checks.fixture())
            test = checks.Checks(world)
            try:
                test.run()
                build.harness.stop(world.process)
                world.process,world.url = build.harness.start(world.executable,folder,world.env,world.log,world.ready_path)
                world.client = pv1.base.Client(world.url)
                test.reads()
                (world.output/'trace.json').write_text(json.dumps(test.trace,indent=2)+'\n')
                records[condition] = {'assertions':test.counts,'buildManifestSha256':fingerprint}
                assert build.build_tools.verify_build(folder)==fingerprint
            finally: world.close()
        if not args.condition:
            checks.require(len({json.dumps(x['assertions'],sort_keys=True) for x in records.values()})==1,
                           'AO1-07','condition equivalence', records)
        session.report(records)
    print('AO1 passed:', ', '.join(records),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--condition',choices=build.harness.CONDITIONS)
    args=parser.parse_args();args.fixtures=args.fixtures.resolve();args.output=args.output.resolve()
    verify(args)
