#!/usr/bin/env python3
"""Prepare matching unscored MCP-on/off fixtures from pinned source and package inputs."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location('evaluation_runner', REPO/'relations/runner/run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def verify_packages(directory, config):
    manifest = json.loads((directory.parent/'dependency-manifest.json').read_text())
    if manifest['sourceRevision'] != config['frameworkRevision'] or manifest['packageVersion'] != config['packageVersion']:
        raise ValueError('Package producer does not match the pilot pin')
    expected = {p['file'] for p in manifest['packages']}
    if {p.name for p in directory.glob('*.nupkg')} != expected:
        raise ValueError('Package closure differs from its manifest')
    for item in manifest['packages']:
        path = directory/item['file']
        if path.parent != directory or path.is_symlink() or runner.digest(path) != item['sha256']:
            raise ValueError('Package hash/path mismatch')
    return manifest


def export_tree(repository, revision, destination, prefix=None):
    # Git archive excludes working-tree changes and history; extraction refuses unsafe paths.
    archive = destination.parent/(destination.name+'.tar')
    with archive.open('wb') as stream:
        subprocess.run(['git', '-C', str(repository), 'archive', revision + (':'+prefix if prefix else '')], stdout=stream, check=True)
    destination.mkdir()
    with tarfile.open(archive) as tar:
        if any(member.issym() or member.islnk() for member in tar):
            raise ValueError('Source archives cannot contain links')
        tar.extractall(destination, filter='data')
    archive.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohesive-source', type=Path, required=True)
    parser.add_argument('--packages', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((HERE/'pilot.json').read_text())
    packages = args.packages.resolve()
    manifest = verify_packages(packages, config)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    evidence = output/'evidence'; evidence.mkdir()
    runner.write_json(evidence/'pilot.json', config)
    tooling = [*HERE.glob('*.py'), *HERE.glob('*.json'), HERE/'DEVELOPMENT.md',
        *list((HERE/'Development').glob('*')), *list((HERE/'Server').glob('*')), REPO/'relations/runner/run.py']
    runner.write_json(evidence/'tooling-inputs.json', {'files':[
        {'path':p.relative_to(REPO).as_posix(),'sha256':runner.digest(p)} for p in sorted(tooling)]})
    commands = []
    def run(arguments, cwd):
        index = len(commands)
        commands.append({'arguments':list(map(str, arguments)), 'cwd':str(cwd)})
        runner.write_json(evidence/'commands.json', commands)
        with (evidence/f'prepare-{index:02}.log').open('w') as log:
            subprocess.run(list(map(str, arguments)), cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=config['commandTimeoutSeconds'])
    try:
        fixture = output/'cohesive-mcp'
        export_tree(REPO, config['fixtureRevision'], fixture, config['fixturePath'])
        shutil.rmtree(fixture/'packages')
        shutil.copytree(packages, fixture/'packages')
        runner.write_json(fixture/'dependency-manifest.json', manifest)
        project = fixture/'src/Fulfillment.Application/Fulfillment.Application.csproj'
        tree = ET.parse(project)
        for reference in tree.findall('.//PackageReference'):
            if reference.attrib['Include'].startswith('Cohesive'):
                reference.set('Version', '['+config['packageVersion']+']')
        tree.write(project, encoding='unicode')
        # Old lockfiles are incompatible with the deliberately upgraded candidate dependency closure.
        for lock in fixture.rglob('packages.lock.json'): lock.unlink()
        shutil.copytree(HERE/'Development', fixture/'Development')
        exporter = fixture/'Development/Fulfillment.Development.csproj'
        exporter.write_text(exporter.read_text().replace('PILOT_PACKAGE_VERSION', config['packageVersion']))
        shutil.copy2(HERE/'DEVELOPMENT.md', fixture/'DEVELOPMENT.md')
        with tempfile.TemporaryDirectory(prefix='mcp-server-producer-') as temporary:
            source = Path(temporary)/'source'
            export_tree(args.cohesive_source, config['frameworkRevision'], source)
            host = source/'eng/mcp-pilot-host'; host.mkdir()
            shutil.copy2(HERE/'Server/Program.cs', host/'Program.cs')
            (host/'Fulfillment.SemanticServer.csproj').write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>
<OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>
</PropertyGroup><ItemGroup><ProjectReference Include="../../src/Cohesive/Cohesive.csproj" /><ProjectReference Include="../../src/Cohesive.Semantics/Cohesive.Semantics.csproj" /><ProjectReference Include="../../src/adapters/Cohesive.Adapters.Mcp.Development/Cohesive.Adapters.Mcp.Development.csproj" /></ItemGroup></Project>''')
            run(['dotnet','publish',host/'Fulfillment.SemanticServer.csproj','-c','Debug','-m:1','-nodeReuse:false',
                 '-p:UseSharedCompilation=false','-p:DebugType=None','-o',fixture/'tools/server'], source)
        run(['dotnet','restore',exporter,'--force-evaluate'], fixture)
        run(['dotnet','build',exporter,'--no-restore','-m:1','-nodeReuse:false','-p:UseSharedCompilation=false'], fixture)
        run(['dotnet','run','--project','Development','--no-build','--',fixture], fixture)
        # Both arms have identical source, dependencies, guide and server artifacts; only tool connection differs.
        shutil.copytree(fixture, output/'cohesive-mcp-off')
        manifests = {}
        for condition in config['conditions']:
            workspace = output/condition
            # Build products are regenerated per arm and are not participant starting source.
            for path in list(workspace.rglob('bin')) + list(workspace.rglob('obj')):
                if path.is_dir(): shutil.rmtree(path)
            shutil.rmtree(workspace/'artifacts')
            manifests[condition] = runner.manifest(workspace)
            audit_config = {'forbiddenPathNames':['oracle','qualification','.github','evolution','protocol.md'],
                'forbiddenText':['LSM-QUAL-', 'hold/evolution', 'private scoring'],
                'conditions':{condition:{'allowedTopLevel':['CONTRACT.md','Directory.Build.props','Fulfillment.slnx',
                    'NuGet.config','README.md','dependency-manifest.json','global.json','packages','schemas.json',
                    'src','tests','Development','DEVELOPMENT.md','tools']}}}
            if not runner.audit(workspace, audit_config, condition, True, evidence/(condition+'-audit.log')):
                raise ValueError('Participant material audit failed')
            run(['git','init','-q'], workspace)
            run(['git','add','.'], workspace)
            run(['git','-c','user.name=Fixture','-c','user.email=fixture@localhost','commit','-qm','Application starting point'], workspace)
        if manifests['cohesive-mcp'] != manifests['cohesive-mcp-off']:
            raise ValueError('Tool-on/off participant files differ')
        runner.write_json(evidence/'participant-manifest.json', manifests['cohesive-mcp'])
        runner.write_json(output/'connections.json', {
            'cohesive-mcp-off': None,
            'cohesive-mcp': {'command':'dotnet','args':[str(fixture/'tools/server/Fulfillment.SemanticServer.dll'),str(fixture)]}})
        runner.write_json(output/'preparation.json', {'status':'prepared','scored':False,'agentInvoked':False,
            'frameworkRevision':config['frameworkRevision'],'fixtureRevision':config['fixtureRevision'],
            'participantFilesIdentical':True,'limitation':'Process isolation and scorer integration are not provided by this preparer.'})
        print(output)
    except Exception as error:
        runner.write_json(output/'preparation.json', {'status':'invalid','scored':False,'error':str(error)})
        raise

if __name__ == '__main__': main()
