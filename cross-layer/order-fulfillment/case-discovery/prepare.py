"""Build isolated Ship author fixtures from the pinned Packed lifecycle and released SDK."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'test-authoring'))
from pilot import APP, CONDITIONS, PROJECT, prepare


def build(output, *, relock=False):
    """Verify the Packed pins and SDK digests, apply the lifecycle evolution and restore its locks."""
    prepare(output)
    manifest = json.loads((ROOT / 'sdk/dependency-manifest.json').read_text())
    for condition in CONDITIONS:
        folder = output / condition
        subprocess.run(['git', 'apply', str(ROOT / 'reference' / f'{condition}.patch')], cwd=folder, check=True)
        suite = folder / 'Suite'
        # Start from the same proposal scaffold for both authors, without the prior pilot's oracle.
        for child in suite.glob('*.cs'):
            child.unlink()
        for name in ['Program.cs', 'Cases.cs']:
            shutil.copyfile(ROOT / 'scaffold' / name, suite / name)
        shutil.copyfile(ROOT / 'scaffold' / f'{condition}.cs', suite / 'Adapter.cs')
        shutil.copyfile(ROOT / 'task.md', folder / 'task.md')
        if condition == 'cohesive':
            for artifact in manifest['packages']:
                package = ROOT / 'sdk' / artifact['file']
                if hashlib.sha256(package.read_bytes()).hexdigest() != artifact['sha256']:
                    raise ValueError(f'SDK package drift: {package.name}')
                shutil.copyfile(package, folder / 'packages' / package.name)
            old = json.loads((folder / 'dependency-manifest.json').read_text())['packageVersion']
            project = folder / PROJECT
            version = manifest['packageVersion']
            project.write_text(project.read_text().replace(f'[{old}]', f'[{version}]'))
            suite_project = suite / 'Suite.csproj'
            suite_project.write_text(suite_project.read_text().replace('</ItemGroup>',
                f'<PackageReference Include="Cohesive.Transitions.Assurance" Version="[{version}]" /></ItemGroup>'))
            for name, target in [('app', folder / APP), ('suite', suite)]:
                if not relock:
                    shutil.copyfile(ROOT / 'reference' / f'{name}.lock.json', target / 'packages.lock.json')
            subprocess.run(['dotnet', 'restore', 'Suite/Suite.csproj',
                            '--force-evaluate' if relock else '--locked-mode'], cwd=folder, check=True)
            if relock:
                for name, target in [('app', folder / APP), ('suite', suite)]:
                    shutil.copyfile(target / 'packages.lock.json', ROOT / 'reference' / f'{name}.lock.json')
        subprocess.run(['dotnet', 'build', 'Suite/Suite.csproj', '--no-restore'], cwd=folder, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--relock', action='store_true')
    args = parser.parse_args()
    build(args.output.resolve(), relock=args.relock)
