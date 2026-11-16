#!/usr/bin/env python3
"""Retain reports plus compressed raw logs, traces and manifests from completed runs."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import build

RUNS=('ao1','qualification','diagnostics','alias','retained-typed','retained-pv1','retained-g0-g3')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def record(fixtures,runs):
    if set(runs)!=set(RUNS):raise ValueError('Supply each named run exactly once: '+', '.join(RUNS))
    evidence=build.ROOT/'evidence';evidence.mkdir(exist_ok=True)
    reports={}
    for name,folder in runs.items():
        data=json.loads((folder/'report.json').read_text())
        if data.get('passed') is not True or data.get('complete',True) is not True:raise ValueError(('incomplete run',name))
        shutil.copy2(folder/'report.json',evidence/(name+'.json'))
        reports[name]=digest(evidence/(name+'.json'))
    for condition in build.harness.CONDITIONS:
        build.build_tools.verify_build(fixtures/condition)
        shutil.copy2(fixtures/condition/'build-manifest.json',evidence/(condition+'-build-manifest.json'))
    # Preserve the actual diagnostics, witness patches, manifests and physical traces.
    # Exclude materialized references (packages and binaries are pinned elsewhere).
    files=[]
    for name,folder in sorted(runs.items()):
        for path in sorted(folder.rglob('*')):
            rel=path.relative_to(folder)
            if path.is_file() and not {'references','bin','obj'}.intersection(rel.parts) and path.suffix in ('.json','.log','.patch'):
                files.append((name+'/'+str(rel),path))
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as tar:
        for name,path in files:
            data=path.read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644
            tar.addfile(info,io.BytesIO(data))
    (evidence/'raw.tar.gz').write_bytes(gzip.compress(stream.getvalue(),mtime=0))
    source={str(p.relative_to(build.CASE)):digest(p) for p in sorted(build.CASE.rglob('*'))
        if p.is_file() and p.suffix in ('.py','.patch','.json','.md')
        and not {'artifacts','evidence','bin','obj','.git','__pycache__'}.intersection(p.relative_to(build.CASE).parts)
        and p.name!='evidence.json'}
    index={'parentCommit':'e9d79180bc230d4efa7c2cb3133bf6ad72cbd6f0',
        'sdkRevision':'b0c442ab5645907968d6b605edeb1dd54550130d','packageVersion':'0.1.0-eval.b0c442a',
        'reports':reports,'runtimeDefects':{'conventional':15,'cohesive':14},
        'staticNegatives':{'compile':3,'registration':3},'aliasWitnessRuns':4,'harnessTests':25,
        'evidenceSha256':{p.name:digest(p) for p in sorted(evidence.iterdir()) if p.is_file()},
        'rawFiles':{name:digest(path) for name,path in files},'sourceSha256':source}
    (build.ROOT/'evidence.json').write_text(json.dumps(index,indent=2)+'\n')
    print('Recorded',len(files),'raw artifacts;',len(source),'source inputs')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--run',action='append',required=True,metavar='NAME=PATH')
    args=parser.parse_args()
    pairs=[x.split('=',1) for x in args.run]
    if len({x[0] for x in pairs})!=len(pairs):raise ValueError('Duplicate run')
    record(args.fixtures.resolve(),{name:Path(path).resolve() for name,path in pairs})
