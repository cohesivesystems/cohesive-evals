"""Apply reviewable source deltas only to their exact recorded parent inputs."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def apply_delta(folder, patch, manifest):
    hashes = json.loads(manifest.read_text())
    with tempfile.TemporaryDirectory(prefix='eval-snapshot-') as directory:
        staging = Path(directory)
        for relative, expected in hashes.items():
            path = Path(relative)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe delta path')
            source = folder / path
            if digest(source) != expected['before']:
                raise ValueError(f'Parent snapshot drift: {relative}')
            target = staging / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.exists():
                shutil.copy2(source, target)
        # Isolated staging has no enclosing repository. No fuzzy source replacement,
        # offset fallback to a changed parent, or mutation of the preserved checkpoint.
        subprocess.run(['git', 'apply', '--check', '--whitespace=error-all', str(patch.resolve())], cwd=staging, check=True)
        subprocess.run(['git', 'apply', '--whitespace=error-all', str(patch.resolve())], cwd=staging, check=True)
        actual_paths = {str(p.relative_to(staging)) for p in staging.rglob('*') if p.is_file()}
        if actual_paths != {p for p, h in hashes.items() if h['after'] is not None}:
            raise ValueError('Delta changed unmanifested files')
        for relative, expected in hashes.items():
            if digest(staging / relative) != expected['after']:
                raise ValueError(f'Delta output drift: {relative}')
        for relative, expected in hashes.items():
            target = folder / relative
            if expected['after'] is None:
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(staging / relative, target)
