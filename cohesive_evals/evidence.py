"""Deterministic hashes and readable JSON evidence shared across scenarios."""

import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    """Hash exact file bytes; missing evidence raises instead of producing a placeholder."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    """Write UTF-8 JSON evidence without silently creating an unexpected output location."""
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
