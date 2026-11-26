"""Materialize the pinned lifecycle host at either full-stack checkpoint."""
import argparse
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
LIFECYCLE = ROOT.parent / 'lifecycle-sequences'
shipping = runpy.run_path(str(ROOT.parent / 'partial-shipping/fixture.py'))
APP = shipping['APP']
HOST_DLL = APP / 'bin/Debug/net10.0/Fulfillment.Application.dll'
compile_suite = shipping['compile_suite']


def overlay(folder, patch):
    """Apply a versioned source delta; mismatched inputs fail the build."""
    subprocess.run(['git', 'apply', str(patch)], cwd=folder, check=True)


def build(output, evolved=False, *, relock=False, shippable=False):
    """Build a disposable checkpoint host using the lifecycle replay SDK and lockfiles."""
    if shippable and not evolved:
        raise ValueError("Shippable quantity requires the partial-release checkpoint.")
    stage = ROOT / 'partial-release' if evolved else LIFECYCLE / 'replay'
    if shippable:
        stage = ROOT / 'shippable'
    shipping['fixtures'](output, stage=stage, relock=relock)
    folder = output / 'cohesive'
    overlay(folder, LIFECYCLE / 'reference/cohesive.patch')
    overlay(folder, ROOT / 'checkpoint/host.patch')
    if evolved:
        overlay(folder, ROOT / 'partial-release/host.patch')
        for name in ['Cases.cs', 'Adapter.cs']:
            (folder / 'Suite' / name).unlink()
        shutil.copyfile(ROOT / 'partial-release/SequenceRunner.cs', folder / 'Suite/Program.cs')
    if shippable:
        overlay(folder, ROOT / "shippable/host.patch")
    compile_suite(folder)
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--partial-release', action='store_true')
    parser.add_argument('--shippable', action='store_true')
    args = parser.parse_args()
    build(args.output.resolve(), args.partial_release or args.shippable, shippable=args.shippable)
