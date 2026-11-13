#!/usr/bin/env python3
"""Require correct references to pass and running defects to fail named assertions."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import build
import mutations

sys.path.insert(0,str(build.CASE/'evolution'))
from harness import detected, CONDITIONS

def qualify(output):
    output.mkdir(parents=True,exist_ok=False)
    refs=build.materialize(output/'references');records=[]
    expected_count=sum(1+len(mutations.mutations(condition)) for condition in CONDITIONS)
    for condition in CONDITIONS:
        folder=refs/condition
        for name,mutation in {'known-good':None,**mutations.mutations(condition)}.items():
            out=output/condition/name;out.mkdir(parents=True)
            path=None;original=None
            try:
                if mutation:
                    file,before,after,obligation,assertion=mutation
                    path=folder/'src/Fulfillment.Application'/file;original=path.read_text()
                    if original.count(before)!=1:raise ValueError(('mutation anchor count',name,original.count(before)))
                    path.write_text(original.replace(before,after))
                with (out/'build.log').open('w') as log:build.build_tools.build_candidate(folder,log)
                manifest=folder/'build-manifest.json'
                (out/'build-manifest.json').write_bytes(manifest.read_bytes())
                fingerprint=build.build_tools.verify_build(folder)
                with (out/'verify.log').open('w') as log:
                    result=subprocess.run([sys.executable,'-B',str(build.ROOT/'verify.py'),'--fixtures',str(refs),
                        '--condition',condition,'--output',str(out/'verification')],stdout=log,stderr=log,timeout=300)
                failurepath=out/'verification/failure.json'
                failure=json.loads(failurepath.read_text()) if failurepath.exists() else None
                if mutation:
                    passed=detected(result.returncode,failure,obligation,assertion)
                else:
                    report=out/'verification/report.json'
                    passed=result.returncode==0 and report.exists() and json.loads(report.read_text()).get('passed') is True
                records.append({'condition':condition,'case':name,'passed':passed,'failure':failure,
                    'buildManifestSha256':fingerprint})
                (output/'report.json').write_text(json.dumps({'passed':all(x['passed'] for x in records),'complete':len(records)==expected_count,'cases':records},indent=2)+'\n')
                if not passed:raise RuntimeError(('qualification failed',condition,name,failure))
                print(condition,name,'qualified',flush=True)
            finally:
                if path is not None:path.write_text(original)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    qualify(parser.parse_args().output.resolve())
