#!/usr/bin/env python3
"""Qualify typed-input admission with the existing named-assertion runner."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'pv1'))
import qualify as runner
builder = runner.build.load('typed_input_build', ROOT / 'build.py')
cases = runner.build.load('typed_input_mutations', ROOT / 'mutations.py')
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    runner.qualify(parser.parse_args().output.resolve(), builder=builder, cases=cases.mutations)
