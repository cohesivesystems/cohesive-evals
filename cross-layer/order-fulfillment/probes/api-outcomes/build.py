#!/usr/bin/env python3
"""Compose AO1 from the immutable qualified typed-input stage."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
CASE = ROOT.parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'evolution'))
import harness
load = harness.load
previous = load('ao1_parent_build', ROOT.parent / 'portable-validation/typed-input/build.py')
build_tools = previous.build_tools

def materialize(output):
    previous.materialize(output)
    for condition in harness.CONDITIONS:
        previous.apply_delta(output / condition, ROOT / f'reference/{condition}.patch',
                             ROOT / f'reference/{condition}.json')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    refs = materialize(parser.parse_args().output.resolve())
    for condition in harness.CONDITIONS:
        with (refs / condition / 'build.log').open('w') as log:
            build_tools.build_candidate(refs / condition, log)
        print(condition, 'built', flush=True)
