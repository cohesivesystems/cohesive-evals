#!/usr/bin/env python3
"""Qualify PV2 using the same named-assertion runner as PV1."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'pv1'))
import qualify as runner
builder = runner.build.load('pv2_build', ROOT / 'build.py')
cases = runner.build.load('pv2_mutations', ROOT / 'mutations.py')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    runner.qualify(parser.parse_args().output.resolve(), builder=builder, cases=cases.mutations)
