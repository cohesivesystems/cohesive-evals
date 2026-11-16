#!/usr/bin/env python3
"""Compose the typed-input SDK stage from preserved PV2."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from pv2 import build as previous
load = previous.load
harness = previous.harness
build_tools = previous.build_tools
apply_delta = load('typed_input_snapshot', previous.CASE / 'evolution/snapshot.py').apply_delta

def materialize(output):
    previous.materialize(output)
    folder = output / 'cohesive'
    apply_delta(folder, ROOT / 'reference/cohesive.patch', ROOT / 'reference/cohesive.json')
    manifest = json.loads((ROOT / 'dependency-manifest.json').read_text())
    for entry in manifest['packages']:
        if hashlib.sha256((ROOT / 'packages' / entry['file']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('SDK package hash mismatch: ' + entry['file'])
    shutil.rmtree(folder / 'packages')
    shutil.copytree(ROOT / 'packages', folder / 'packages')
    shutil.copy2(ROOT / 'dependency-manifest.json', folder / 'dependency-manifest.json')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    refs = materialize(parser.parse_args().output.resolve())
    for condition in harness.CONDITIONS:
        with (refs / condition / 'build.log').open('w') as log:
            build_tools.build_candidate(refs / condition, log)
        print(condition, 'built', flush=True)
