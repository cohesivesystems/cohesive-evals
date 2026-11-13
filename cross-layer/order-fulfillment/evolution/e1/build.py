#!/usr/bin/env python3
"""Compose and build maintainer-only G1 references from G0 plus committed overlays."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CASE = ROOT.parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

build_tools = load('reference_build', CASE/'durability/build.py')
contracts = load('contract_bundle', ROOT.parent/'contracts/bundle.py')


def materialize(output):
    output.mkdir(parents=True, exist_ok=False)
    for condition in ('conventional', 'cohesive'):
        folder = output/condition
        shutil.copytree(CASE/'conditions'/condition, folder, ignore=shutil.ignore_patterns('bin','obj','__pycache__'))
        for overlay in ('common', condition):
            for path in (ROOT/'reference'/overlay).glob('*.cs'):
                shutil.copy2(path, folder/'src/Fulfillment.Application'/path.name)
        shutil.copy2(ROOT/'visible_checks.py', folder/'tests/e1_checks.py')
        for name, text in contracts.documents('G1').items():
            (folder/name).write_text(text)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=CASE/'artifacts/e1-reference')
    args = parser.parse_args()
    materialize(args.output.resolve())
    for condition in ('conventional','cohesive'):
        folder=args.output.resolve()/condition
        with (folder/'build.log').open('w') as log:
            build_tools.build_candidate(folder, log)
        print(condition, 'built', flush=True)


if __name__ == '__main__': main()
