#!/usr/bin/env python3
"""Compose PV2 from qualified PV1; keep both prior references unchanged."""
import argparse
import importlib.util
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CASE = ROOT.parents[2]
spec = importlib.util.spec_from_file_location('pv2_parent_build', ROOT.parent / 'pv1/build.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
build_tools = previous.build_tools

def materialize(output):
    previous.materialize(output)
    for condition in ('conventional', 'cohesive'):
        folder = output / condition
        previous.previous.snapshot.apply_delta(folder, ROOT / 'reference/common.patch', ROOT / 'reference/common.json')
        shutil.copy2(ROOT / 'REQUEST-ID.md', folder / 'REQUEST-ID.md')
        shutil.copy2(ROOT / 'visible_checks.py', folder / 'tests/pv2_checks.py')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    refs = materialize(parser.parse_args().output.resolve())
    for condition in ('conventional', 'cohesive'):
        with (refs / condition / 'build.log').open('w') as log:
            build_tools.build_candidate(refs / condition, log)
        print(condition, 'built', flush=True)
