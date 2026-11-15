#!/usr/bin/env python3
"""Run the unchanged independent PV2 verifier against this stage."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1] / 'pv2/verify.py'), run_name='__main__')
