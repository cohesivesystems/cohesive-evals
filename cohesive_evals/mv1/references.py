"""Compose preserved scenario assets without importing historical probe implementations."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
from ..evidence import sha
from ..runtime import run
from ..snapshots import apply_delta
from .paths import CASE, CONDITIONS


def packages(source: Path, target: Path):
    """Install an exact manifested package feed; reject missing or extra package files."""
    manifest = json.loads((source / "dependency-manifest.json").read_text())
    expected = {p["file"]: p["sha256"] for p in manifest["packages"]}
    actual = {p.name: sha(p) for p in (source / "packages").glob("*.nupkg")}
    if actual != expected:
        raise ValueError("SDK package feed differs from manifest")
    shutil.rmtree(target / "packages")
    shutil.copytree(source / "packages", target / "packages")
    shutil.copy2(
        source / "dependency-manifest.json", target / "dependency-manifest.json"
    )


def materialize(output: Path):
    """Apply the reviewed G0→AO1 source recipe and final public G3 contract bundle."""
    output.mkdir(parents=True, exist_ok=False)
    evolution = CASE / "evolution"
    portable = CASE / "probes/portable-validation"
    with tempfile.TemporaryDirectory(prefix="mv1-contract-") as temp:
        contracts = Path(temp) / "bundle"
        # Consume the contract tool's public CLI, not its implementation/import chain.
        run(
            sys.executable,
            str(evolution / "contracts/bundle.py"),
            "--checkpoint",
            "G3",
            "--output",
            str(contracts),
        )
        for condition in CONDITIONS:
            folder = output / condition
            shutil.copytree(
                CASE / "conditions" / condition,
                folder,
                ignore=shutil.ignore_patterns("bin", "obj", "__pycache__"),
            )
            app = folder / "src/Fulfillment.Application"
            for overlay in ("common", condition):
                for path in (evolution / "e1/reference" / overlay).glob("*.cs"):
                    shutil.copy2(path, app / path.name)
            for generation in ("e1", "e2", "e3"):
                source = evolution / generation
                if generation != "e1":
                    apply_delta(
                        folder,
                        source / f"reference/{condition}.patch",
                        source / f"reference/{condition}.json",
                    )
                shutil.copy2(
                    source / "visible_checks.py",
                    folder / f"tests/{generation}_checks.py",
                )
            for path in contracts.iterdir():
                shutil.copy2(path, folder / path.name)
            for generation in ("pv1", "pv2"):
                source = portable / generation
                apply_delta(
                    folder,
                    source / "reference/common.patch",
                    source / "reference/common.json",
                )
                shutil.copy2(
                    source / "visible_checks.py",
                    folder / f"tests/{generation}_checks.py",
                )
                if generation == "pv1":
                    for path in (source / "reference/common").glob("*.cs"):
                        if (app / path.name).exists():
                            raise ValueError(
                                "New PV1 source already exists: " + path.name
                            )
                        shutil.copy2(path, app / path.name)
                    documents = (
                        "batch.schema.json",
                        "batch-examples.json",
                        "batch-seed.json",
                        "BATCH.md",
                    )
                else:
                    documents = ("REQUEST-ID.md",)
                for name in documents:
                    shutil.copy2(source / name, folder / name)
            typed = portable / "typed-input"
            if condition == "cohesive":
                apply_delta(
                    folder,
                    typed / "reference/cohesive.patch",
                    typed / "reference/cohesive.json",
                )
                packages(typed, folder)
            api = CASE / "probes/api-outcomes/reference"
            apply_delta(folder, api / f"{condition}.patch", api / f"{condition}.json")
    return output
