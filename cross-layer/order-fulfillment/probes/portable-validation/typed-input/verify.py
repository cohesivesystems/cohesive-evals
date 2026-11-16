#!/usr/bin/env python3
"""Reuse PV2 lifecycle/checks, adding independent nonblank-policy witnesses."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'pv1'))
import verify as pv1
runner = pv1.build.load('typed_input_verifier', ROOT.parent / 'pv2/verify.py')
runner.checks = pv1.build.load('typed_input_required_checks', ROOT / 'required_checks.py')
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--condition', choices=runner.harness.CONDITIONS)
    args = parser.parse_args()
    args.fixtures = args.fixtures.resolve()
    args.output = args.output.resolve()
    runner.verify(args)
