#!/usr/bin/env python3
"""Check the upgraded candidate against the original conventional G0 using the existing verifier."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import prepare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preparation',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    prepared=args.preparation.resolve()
    config=json.loads((prepared/'evidence/pilot.json').read_text())
    if json.loads((prepared/'preparation.json').read_text())['status']!='prepared':
        raise ValueError('Preparation did not pass')
    seed=prepared/'cohesive-mcp-off'
    if prepare.runner.manifest(seed)!=json.loads((prepared/'evidence/participant-manifest.json').read_text()):
        raise ValueError('Prepared participant files changed')
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    fixtures=output/'fixtures';fixtures.mkdir()
    prepare.export_tree(prepare.REPO,config['fixtureRevision'],fixtures/'conventional',
        'cross-layer/order-fulfillment/conditions/conventional')
    shutil.copytree(seed,fixtures/'cohesive',ignore=shutil.ignore_patterns('.git'))
    report={'status':'invalid','scored':False,'agentInvoked':False}
    try:
        for condition in ['conventional','cohesive']:
            with (output/(condition+'-build.log')).open('x') as log:
                subprocess.run(['dotnet','build','-m:1','-nodeReuse:false','-p:UseSharedCompilation=false'],
                    cwd=fixtures/condition,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        with (output/'verification.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(prepare.HERE.parent/'verification/verify.py'),
                '--fixtures',str(fixtures),'--output',str(output/'verification')],
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        verification=json.loads((output/'verification/report.json').read_text())
        if not verification.get('passed') or not verification.get('pairEquivalenceChecked'):
            raise ValueError('G0 parity not established')
        report.update(status='passed',frameworkRevision=config['frameworkRevision'],
            fixtureRevision=config['fixtureRevision'],verification=verification,
            limitations=['Baseline public HTTP and invariant checks only','No held-out scoring or agent run',
                'Tool-on/off files are identical; tool treatment must be enforced by a future agent driver'])
    except Exception as error:
        report['error']=str(error);raise
    finally:
        prepare.runner.write_json(output/'report.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
