#!/usr/bin/env python3
"""Build the baseline's dependency closure from an immutable upstream Git archive."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as ET

REVISION = 'b0af008d85871ad8866d7d4311707ecd926529de'
VERSION = '0.1.0-eval.b0af008'
ROOTS = ['src/adapters/Cohesive.Adapters.Postgres.Services/Cohesive.Adapters.Postgres.Services.csproj',
         'src/adapters/Cohesive.Adapters.AspNet/Cohesive.Adapters.AspNet.csproj',
         'src/Cohesive.Analyzers/Cohesive.Analyzers.csproj']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('--package-source', help='Optional offline NuGet source')
    parser.add_argument('--extra-root', action='append', default=[])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--revision', help='Explicit source commit for a separate integration candidate')
    parser.add_argument('--version', help='Matching candidate package version')
    args = parser.parse_args()
    if bool(args.revision) != bool(args.version) or (args.revision and not args.output):
        parser.error('--revision and --version must be supplied together with --output')
    revision = args.revision or REVISION
    version = args.version or VERSION
    revision = subprocess.check_output(['git', '-C', str(args.repository), 'rev-parse', '--verify', '--end-of-options', revision + '^{commit}'], text=True).strip()
    roots = ROOTS + args.extra_root
    output = (args.output or Path(__file__).resolve().parents[1] / 'conditions/cohesive/packages').resolve()
    if args.revision and output.exists() and any(output.iterdir()):
        parser.error('A custom revision requires an empty package output directory')
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fulfillment-packages-') as temporary:
        source = Path(temporary)
        archive = source / 'source.tar'
        with archive.open('wb') as stream:
            subprocess.run(['git','-C',str(args.repository),'archive',revision], stdout=stream, check=True)
        with tarfile.open(archive) as tar:
            tar.extractall(source, filter='data')
        closure = []
        seen = set()
        def visit(project):
            project = project.resolve()
            if project in seen: return
            seen.add(project)
            for ref in ET.parse(project).findall('.//ProjectReference'):
                visit(project.parent / ref.attrib['Include'].replace('\\','/'))
            closure.append(project)
        for root in roots: visit(source/root)
        for root in roots:
            restore = ['dotnet','restore',root,'-p:NuGetAudit=false','-m:1','-nr:false','-v:q']
            if args.package_source: restore += ['--source',args.package_source]
            subprocess.run(restore,cwd=source,check=True)
            subprocess.run(['dotnet','build',root,'--no-restore',f'-p:Version={version}','-m:1','-nr:false','-v:q'],cwd=source,check=True)
        for project in closure:
            subprocess.run(['dotnet','pack',str(project),'--no-build','--no-restore','-c','Debug',f'-p:Version={version}',
                f'-p:RepositoryCommit={revision}','-p:IncludeSymbols=false','-o',str(output),'-v:q'],cwd=source,check=True)
    files = sorted(output.glob('*.nupkg'))
    manifest = {'sourceRevision':revision,'packageVersion':version,'packages':[
        {'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (output.parent/'dependency-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Packaged {len(files)} dependencies from {revision}.')

if __name__ == '__main__': main()
