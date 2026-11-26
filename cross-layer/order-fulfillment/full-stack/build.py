"""Materialize the pinned lifecycle host at either full-stack checkpoint."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LIFECYCLE = ROOT.parent / 'lifecycle-sequences'
sys.path.insert(0, str(ROOT.parent / 'partial-shipping'))
from fixture import APP, compile_suite, fixtures


def overlay(folder, patch):
    """Apply a versioned source delta; mismatched inputs fail the build."""
    subprocess.run(['git', 'apply', str(patch)], cwd=folder, check=True)


def build(output, evolved=False):
    """Build a disposable checkpoint host using the lifecycle replay SDK and lockfiles."""
    fixtures(output, stage=LIFECYCLE / 'replay')
    folder = output / 'cohesive'
    overlay(folder, LIFECYCLE / 'reference/cohesive.patch')
    overlay(folder, ROOT / 'checkpoint/host.patch')
    if evolved:
        evolve(folder)
    else:
        compile_suite(folder)
    return folder


def evolve(folder):
    """Upgrade the existing checkout, preserving its external PostgreSQL database."""
    overlay(folder, ROOT / 'partial-release/host.patch')
    compile_suite(folder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--partial-release', action='store_true')
    args = parser.parse_args()
    build(args.output.resolve(), args.partial_release)
