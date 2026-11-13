#!/usr/bin/env python3
"""Compose G2 from the preserved G1 references and complete E2 source overlays."""
import argparse
import importlib.util
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CASE = ROOT.parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

previous = load('e1_build', ROOT.parent / 'e1/build.py')
build_tools = previous.build_tools

def materialize(output):
    previous.materialize(output)
    for condition in ('conventional', 'cohesive'):
        folder = output / condition
        for overlay in ('common', condition):
            for path in (ROOT / 'reference' / overlay).glob('*.cs'):
                shutil.copy2(path, folder / 'src/Fulfillment.Application' / path.name)
        shutil.copy2(ROOT / 'visible_checks.py', folder / 'tests/e2_checks.py')
        for name, text in previous.contracts.documents('G2').items():
            (folder / name).write_text(text)
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixtures = materialize(args.output.resolve())
    for condition in ('conventional', 'cohesive'):
        folder = fixtures / condition
        with (folder / 'build.log').open('w') as log:
            build_tools.build_candidate(folder, log)
        print(condition, 'built', flush=True)

if __name__ == '__main__':
    main()
