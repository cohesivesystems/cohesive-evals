"""Materialize the pinned G2 fixtures and apply the two reviewed, hash-checked packing deltas."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from harness import CONDITIONS, load
from snapshot import apply_delta, digest

parent = load('packing_g2', ROOT.parent / 'e2/build.py')
build_tools = parent.build_tools


def materialize(output):
    """Verify complete G2 inputs before applying deltas, changing the SDK or installing offline probes."""
    parent.materialize(output)
    pins = json.loads((ROOT / 'pins.json').read_text())
    for condition in CONDITIONS:
        folder = output / condition
        if build_tools.reference_fingerprint(folder) != pins[condition]:
            raise ValueError(f'G2 input fingerprint changed for {condition}')
        apply_delta(folder, ROOT / 'reference' / f'{condition}.patch', ROOT / 'reference' / f'{condition}.json')
        if condition == 'cohesive':
            manifest = ROOT / 'sdk/dependency-manifest.json'
            shutil.rmtree(folder / 'packages')
            (folder / 'packages').mkdir()
            for entry in json.loads(manifest.read_text())['packages']:
                package = manifest.parent / entry['file']
                if digest(package) != entry['sha256']:
                    raise ValueError(f'Package digest mismatch for {package.name}')
                shutil.copyfile(package, folder / 'packages' / package.name)
            shutil.copyfile(manifest, folder / manifest.name)
        probe = folder / 'tests/LifecycleProbe'
        probe.mkdir()
        shutil.copyfile(ROOT / 'offline/LifecycleProbe.csproj', probe / 'LifecycleProbe.csproj')
        shutil.copyfile(ROOT / 'offline' / f'{condition}.cs', probe / 'Program.cs')
        shutil.copyfile(ROOT / 'offline' / f'{condition}.lock.json', probe / 'packages.lock.json')
        shutil.copyfile(ROOT / 'visible_checks.py', folder / 'tests/packed_checks.py')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    for candidate in materialize(args.output.resolve()).iterdir():
        build_tools.build_candidate(candidate)
