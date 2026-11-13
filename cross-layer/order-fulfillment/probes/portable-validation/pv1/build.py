#!/usr/bin/env python3
"""Compose PV1 from G3 without changing any evolution checkpoint."""
import argparse
import importlib.util
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CASE = ROOT.parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

previous = load('pv1_parent_build', CASE / 'evolution/e3/build.py')
build_tools = previous.build_tools

def materialize(output):
    previous.materialize(output)
    for condition in ('conventional', 'cohesive'):
        folder = output / condition
        previous.snapshot.apply_delta(folder, ROOT / 'reference/common.patch', ROOT / 'reference/common.json')
        for path in (ROOT / 'reference/common').glob('*.cs'):
            target = folder / 'src/Fulfillment.Application' / path.name
            if target.exists():
                raise ValueError(f'New PV1 source already exists in parent: {path.name}')
            shutil.copy2(path, target)
        for name in ('batch.schema.json', 'batch-examples.json', 'batch-seed.json', 'BATCH.md'):
            shutil.copy2(ROOT / name, folder / name)
        shutil.copy2(ROOT / 'visible_checks.py', folder / 'tests/pv1_checks.py')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    refs = materialize(args.output.resolve())
    for condition in ('conventional', 'cohesive'):
        with (refs / condition / 'build.log').open('w') as log:
            build_tools.build_candidate(refs / condition, log)
        print(condition, 'built', flush=True)
