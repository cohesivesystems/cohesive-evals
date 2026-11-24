"""Prepare pinned authoring fixtures and run isolated PostgreSQL hosts for rehearsal and grading."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'evolution'))
from harness import CONDITIONS, load
from cohesive_evals.runtime import capture, host, kestrel_url

builder = load('packed_reference', ROOT.parent / 'evolution/packed/build.py')
APP = Path('src/Fulfillment.Application')
PROJECT = APP / 'Fulfillment.Application.csproj'
DLL = APP / 'bin/Debug/net10.0/Fulfillment.Application.dll'


def prepare(output):
    """Materialize pinned production inputs and expose only the contract, production and scaffold."""
    pins = json.loads((ROOT / "pins.json").read_text())
    builder.materialize(output)
    for condition in CONDITIONS:
        folder = output / condition
        if builder.build_tools.reference_fingerprint(folder) != pins['inputSha256'][condition]:
            raise ValueError(f'Packed lifecycle fixture drift for {condition}')
        for name in ['tests', 'README.md', 'contract-examples.json']:
            path = folder / name
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        shutil.copytree(ROOT / 'scaffold', folder / 'Suite')
        shutil.copyfile(ROOT / 'task.md', folder / 'task.md')
        # The probe and suite reference the same application. Reuse the exact locked package closure.
        lock = ROOT.parent / 'evolution/packed/offline' / f'{condition}.lock.json'
        shutil.copyfile(lock, folder / 'Suite/packages.lock.json')
        subprocess.run(['dotnet', 'restore', 'Suite/Suite.csproj', '--locked-mode'], cwd=folder, check=True)
        subprocess.run(['dotnet', 'build', str(PROJECT), '--no-restore'], cwd=folder, check=True)


@contextmanager
def live(pg, folder, out, database):
    """Create a fresh seeded database, launch its production host, and yield the bound HTTP URL."""
    if not database.isidentifier() or not database.isascii():
        raise ValueError('Invalid internal database identifier')
    capture('docker', 'exec', pg.container, 'createdb', '-U', 'postgres', database)
    env = dict(os.environ, ConnectionStrings__Orders=f'Host=127.0.0.1;Port={pg.port};Database={database};Username=postgres;Password=fixture-only')
    seed = out / 'seed.json'
    seed.write_text(json.dumps({'orders': [{'id': s.lower(), 'status': s} for s in
                                          ['Draft', 'Submitted', 'Packed', 'Cancelled']],
                                'inventory': [{'sku': 'stock', 'available': 20}], 'reservations': []}))
    dll = str(folder / DLL)
    subprocess.run(['dotnet', dll, '--seed', str(seed)], cwd=folder, env=dict(env, FULFILLMENT_SETUP='1'),
                   check=True, timeout=90, stdout=subprocess.DEVNULL)
    log = out / 'host.log'
    offset = log.stat().st_size if log.exists() else 0
    with host(['dotnet', dll, '--urls', 'http://127.0.0.1:0'], folder, out, env) as process:
        yield kestrel_url(process, log, offset)


def install_typed_companion(folder):
    """Upgrade a disposable Cohesive fixture and select typed execution in the frozen suite."""
    companion = ROOT / 'typed'
    manifest = json.loads((companion / 'dependency-manifest.json').read_text())
    for package in manifest['packages']:
        source = companion / 'sdk' / package['file']
        if hashlib.sha256(source.read_bytes()).hexdigest() != package['sha256']:
            raise ValueError(f'Published SDK package changed: {source.name}')
        shutil.copyfile(source, folder / 'packages' / source.name)

    project = folder / PROJECT
    previous = json.loads((folder / 'dependency-manifest.json').read_text())['packageVersion']
    project_text = project.read_text()
    if project_text.count(f'[{previous}]') != 3:
        raise ValueError('Unexpected Cohesive project package references')
    project.write_text(project_text.replace(f'[{previous}]', f"[{manifest['packageVersion']}]"))
    for lock, target in [('application', APP), ('suite', Path('Suite'))]:
        shutil.copyfile(companion / f'{lock}.lock.json', folder / target / 'packages.lock.json')
    subprocess.run(['dotnet', 'restore', 'Suite/Suite.csproj', '--locked-mode'], cwd=folder, check=True)

    # Keep the author's oracle, HTTP cases and grading labels in one hash-checked source.
    program = folder / 'Suite/Program.cs'
    source = program.read_text()
    for before, after in [('internal static class Program', 'internal static partial class Program'),
                          ('        Offline();', '        TypedOffline();')]:
        if source.count(before) != 1:
            raise ValueError(f'Unexpected frozen suite entry point: {before}')
        source = source.replace(before, after)
    program.write_text(source)
    shutil.copyfile(companion / 'TypedOffline.cs', folder / 'Suite/TypedOffline.cs')
