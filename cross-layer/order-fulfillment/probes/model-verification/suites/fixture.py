"""Exact AO1 production inputs; an explicit separate precedence revision for maintenance."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'api-outcomes'))
import build as ao1
CONDITIONS=ao1.harness.CONDITIONS
VERSIONS=('original','revised')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def materialize(output,version):
    if version not in VERSIONS:raise ValueError(version)
    refs=ao1.materialize(output/'references')
    if version=='revised':
        for c in CONDITIONS:
            ao1.previous.apply_delta(refs/c,ROOT/f'reference/{c}.patch',ROOT/f'reference/{c}.json')
    suites=output/'suites'
    for name in (*CONDITIONS,'common'):shutil.copytree(ROOT/name,suites/name)
    shutil.copy2(refs/'cohesive/global.json',suites/'global.json')
    # Reuse the production closure. No extra SDK packages or production source edits.
    shutil.copytree(refs/'cohesive/packages',suites/'packages')
    shutil.copy2(refs/'cohesive/NuGet.config',suites/'NuGet.config')
    return refs

def compile_adapter(output,condition,prepare_locks=False):
    refs=output/'references';folder=output/'suites'/condition
    with (folder/'build.log').open('w') as log:
        # Preserve the existing production build/manifest contract for integration runners.
        ao1.build_tools.build_candidate(refs/condition,log)
        before=ao1.build_tools.input_hashes(refs/condition)
        props=['-p:FixtureRoot='+str(refs)]
        subprocess.run(['dotnet','restore','Suite.csproj',*props,*([] if prepare_locks else ['--locked-mode'])],cwd=folder,stdout=log,stderr=log,check=True,timeout=180)
        subprocess.run(['dotnet','build','Suite.csproj','--no-restore','-p:BuildProjectReferences=false','-m:1','-nr:false',*props],cwd=folder,stdout=log,stderr=log,check=True,timeout=180)
    if before!=ao1.build_tools.input_hashes(refs/condition):raise ValueError('Production inputs changed')
    ao1.build_tools.verify_build(refs/condition)
    if prepare_locks:shutil.copy2(folder/'packages.lock.json',ROOT/condition/'packages.lock.json')
    manifest={'production':sha(refs/condition/'build-manifest.json'),
        'sources':{p.name:sha(p) for p in sorted(folder.glob('*')) if p.suffix in ('.cs','.csproj') or p.name=='packages.lock.json'},
        'common':sha(output/'suites/common/Cases.cs'),
        'outputs':{str(p.relative_to(folder)):sha(p) for p in sorted((folder/'bin').rglob('*')) if p.is_file()}}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def invoke(output,condition,argument):
    folder=output/'suites'/condition
    result=subprocess.run(['dotnet',str(folder/'bin/Debug/net10.0/Suite.dll'),str(argument)],text=True,capture_output=True,timeout=60)
    if result.returncode:raise RuntimeError(('adapter execution',result.returncode,result.stderr))
    return json.loads(result.stdout)
