#!/usr/bin/env python3
"""Materialize maintainer-only reference solutions without altering participant G0."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent

def input_hashes(folder):
    paths=[p for p in folder.rglob('*') if p.is_file() and not {'bin','obj','__pycache__'}.intersection(p.relative_to(folder).parts)
           and (p.suffix in ['.cs','.csproj','.props','.targets','.nupkg'] or p.name in ['global.json','NuGet.config','packages.lock.json'])]
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def artifact_hashes(folder):
    output=folder/'src/Fulfillment.Application/bin/Debug/net10.0'
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}


def reference_fingerprint(folder):
    return hashlib.sha256(json.dumps(input_hashes(folder),sort_keys=True).encode()).hexdigest()


def build_candidate(folder, log=None):
    manifest=folder/'build-manifest.json'
    manifest.unlink(missing_ok=True)
    before=input_hashes(folder)
    subprocess.run(['dotnet','restore','--locked-mode'],cwd=folder,stdout=log,stderr=log,check=True,timeout=120)
    subprocess.run(['dotnet','build','--no-restore','--no-incremental','-m:1','-nr:false'],cwd=folder,stdout=log,stderr=log,check=True,timeout=120)
    assert before==input_hashes(folder), 'Inputs changed during build'
    artifacts=artifact_hashes(folder)
    assert any(p.endswith('/Fulfillment.Application.dll') for p in artifacts), 'Application binary missing'
    manifest.write_text(json.dumps({'inputs':before,'artifacts':artifacts,
        'sdk':subprocess.check_output(['dotnet','--version'],cwd=folder,text=True).strip()},indent=2)+'\n')


def verify_build(folder):
    manifest=json.loads((folder/'build-manifest.json').read_text())
    assert manifest['inputs']==input_hashes(folder), 'Source/configuration changed since build'
    assert manifest['artifacts']==artifact_hashes(folder), 'Executable artifacts changed since build'
    assert any(p.endswith('/Fulfillment.Application.dll') for p in manifest['artifacts']), 'Application binary missing'
    return hashlib.sha256((folder/'build-manifest.json').read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT.parent/'artifacts/durable-reference')
    args=parser.parse_args();args.output=args.output.resolve()
    manifest=json.loads((ROOT/'dependency-manifest.json').read_text())
    for p in manifest['packages']:
        assert hashlib.sha256((ROOT/'packages'/p['file']).read_bytes()).hexdigest()==p['sha256']
    for condition in ['conventional','cohesive']:
        folder=args.output/condition
        if folder.exists(): shutil.rmtree(folder)
        shutil.copytree(ROOT.parent/'conditions'/condition,folder,ignore=shutil.ignore_patterns('bin','obj','__pycache__'))
        app=folder/'src/Fulfillment.Application'
        for overlay in ['common',condition]:
            for p in (ROOT/'reference'/overlay).glob('*'):
                if p.is_file(): shutil.copy2(p,app/p.name.removesuffix('.overlay'))
        if condition=='cohesive':
            for package in (ROOT/'packages').glob('*.nupkg'):
                shutil.copy2(package,folder/'packages'/package.name)
        build_candidate(folder)

if __name__=='__main__':main()
