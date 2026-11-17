"""Compose pinned production references and build their small offline .NET consumers.

All source transformations use reviewed patches plus before/after hashes. Python owns
build orchestration and evidence; input generation and execution live in .NET.
"""

from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent / "sdk"
sys.path.insert(0, str(ROOT.parents[1] / "api-outcomes"))
import build as ao1

CONDITIONS = ao1.harness.CONDITIONS
VERSIONS = ("original", "revised")


def sha(path):
    """Return a file's SHA-256 for source, package and output provenance."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    """Freeze suite source and the SDK manifest/patches; package bytes are checked separately."""
    files = list(ROOT.rglob("*")) + list(SDK.glob("*"))
    return {
        str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else "../sdk/" + p.name: sha(
            p
        )
        for p in sorted(files)
        if p.is_file()
        and p.suffix in (".cs", ".csproj", ".py", ".patch", ".json")
        and "__pycache__" not in p.parts
    }


def materialize(output, version):
    """Create isolated references and adapters, applying only pinned policy/SDK patches."""
    if version not in VERSIONS:
        raise ValueError(version)
    refs = ao1.materialize(output / "references")
    if version == "revised":
        for condition in CONDITIONS:
            ao1.previous.apply_delta(
                refs / condition,
                ROOT / f"reference/{condition}.patch",
                ROOT / f"reference/{condition}.json",
            )
    manifest = json.loads((SDK / "dependency-manifest.json").read_text())
    for entry in manifest["packages"]:
        if sha(SDK / "packages" / entry["file"]) != entry["sha256"]:
            raise ValueError("SDK package drift: " + entry["file"])
    cohesive = refs / "cohesive"
    ao1.previous.apply_delta(cohesive, SDK / "reference.patch", SDK / "reference.json")
    shutil.rmtree(cohesive / "packages")
    shutil.copytree(SDK / "packages", cohesive / "packages")
    shutil.copy2(
        SDK / "dependency-manifest.json", cohesive / "dependency-manifest.json"
    )
    suites = output / "suites"
    for name in (*CONDITIONS, "common"):
        shutil.copytree(ROOT / name, suites / name)
    shutil.copy2(cohesive / "global.json", suites / "global.json")
    shutil.copytree(cohesive / "packages", suites / "packages")
    shutil.copy2(cohesive / "NuGet.config", suites / "NuGet.config")
    return refs


def compile_adapter(output, condition, prepare_locks=False):
    """Build production and its adapter; reject source drift and record output hashes.

    Normal runs use locked restore. Lock preparation is an explicit maintainer-only
    bootstrap step; it does not change production source or its already pinned lock.
    """
    refs = output / "references"
    folder = output / "suites" / condition
    with (folder / "build.log").open("w") as log:
        ao1.build_tools.build_candidate(refs / condition, log)
        before = ao1.build_tools.input_hashes(refs / condition)
        props = ["-p:FixtureRoot=" + str(refs)]
        subprocess.run(
            [
                "dotnet",
                "restore",
                "Suite.csproj",
                *props,
                *([] if prepare_locks else ["--locked-mode"]),
            ],
            cwd=folder,
            stdout=log,
            stderr=log,
            check=True,
            timeout=180,
        )
        subprocess.run(
            [
                "dotnet",
                "build",
                "Suite.csproj",
                "--no-restore",
                "-p:BuildProjectReferences=false",
                "-m:1",
                "-nr:false",
                *props,
            ],
            cwd=folder,
            stdout=log,
            stderr=log,
            check=True,
            timeout=180,
        )
    if before != ao1.build_tools.input_hashes(refs / condition):
        raise ValueError("Production inputs changed")
    ao1.build_tools.verify_build(refs / condition)
    if prepare_locks:
        shutil.copy2(
            folder / "packages.lock.json", ROOT / condition / "packages.lock.json"
        )
    manifest = {
        "production": sha(refs / condition / "build-manifest.json"),
        "sources": {
            p.name: sha(p)
            for p in sorted(folder.glob("*"))
            if p.suffix in (".cs", ".csproj") or p.name == "packages.lock.json"
        },
        "common": {
            p.name: sha(p) for p in sorted((output / "suites/common").glob("*.cs"))
        },
        "outputs": {
            str(p.relative_to(folder)): sha(p)
            for p in sorted((folder / "bin").rglob("*"))
            if p.is_file()
        },
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def invoke(output, condition, argument):
    """Run the typed .NET consumer; process failures/timeouts never become test results."""
    folder = output / "suites" / condition
    result = subprocess.run(
        ["dotnet", str(folder / "bin/Debug/net10.0/Suite.dll"), str(argument)],
        text=True,
        capture_output=True,
        timeout=60,
    )
    if result.returncode:
        raise RuntimeError(("adapter execution", result.returncode, result.stderr))
    return json.loads(result.stdout)
