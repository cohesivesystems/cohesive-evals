#!/usr/bin/env python3
"""Run the complete baseline verifier against the durable reference applications."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from build import verify_build

ROOT=Path(__file__).resolve().parent

def main():
    image=json.loads((ROOT/'dependency-manifest.json').read_text())['schedulerImage']
    name='order-regression-dts-'+uuid.uuid4().hex[:10]
    references=ROOT.parent/'artifacts/durable-reference'
    manifests={c:verify_build(references/c) for c in ['conventional','cohesive']}
    started=False
    try:
        subprocess.run(['docker','run','-d','--name',name,'-p','127.0.0.1::8080',image],check=True,stdout=subprocess.DEVNULL)
        started=True
        port=subprocess.check_output(['docker','port',name,'8080/tcp'],text=True).strip().rsplit(':',1)[1]
        env=dict(os.environ,DURABLE_TASK_CONNECTION=f'Endpoint=http://127.0.0.1:{port};TaskHub=default;Authentication=None')
        subprocess.run([sys.executable,'-B',str(ROOT.parent/'verification/verify.py'),
            '--fixtures',str(ROOT.parent/'artifacts/durable-reference'),'--condition-specific-execution',
            '--output',str(ROOT.parent/'artifacts/durable-regression')],env=env,check=True)
        assert manifests=={c:verify_build(references/c) for c in manifests}, 'Build changed during regression'
    finally:
        if started:subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,check=True)

if __name__=='__main__':main()
