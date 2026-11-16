#!/usr/bin/env python3
"""Reuse the shared runtime defect qualifier; static negatives are separate."""
import argparse
from pathlib import Path
import build
import sys
sys.path.insert(0,str(build.ROOT.parent/'portable-validation/pv1'))
runner=build.load('ao1_qualifier',build.ROOT.parent/'portable-validation/pv1/qualify.py')
cases=build.load('ao1_mutations',build.ROOT/'mutations.py')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    runner.qualify(parser.parse_args().output.resolve(),builder=build,cases=cases.mutations)
