#!/usr/bin/env python3
"""Compatibility entry point; execution lives in the shared evolution harness."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import main_verify

if __name__ == '__main__':
    main_verify('e2')
