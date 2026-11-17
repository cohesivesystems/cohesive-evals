"""Compose pinned production references and build their small offline .NET consumers.

All source transformations use reviewed patches plus before/after hashes. Python owns
build orchestration and evidence; input generation and execution live in .NET.
"""

from pathlib import Path
import shutil

from .paths import SUITES as ROOT, SDK, CONDITIONS, VERSIONS, REPO, CASE
from . import references
from ..adapters.dotnet import DotnetAdapter, DotnetLayout
from ..contracts import AdapterConfig, Capability
from ..evidence import sha
from ..snapshots import apply_delta


def adapter(condition):
    """Bind the explicit .NET implementation; capabilities are independent of the oracle."""
    if condition not in CONDITIONS:
        raise ValueError(condition)
    capabilities = {Capability.HTTP, Capability.OFFLINE, Capability.GENERATE}
    if condition == "cohesive":
        capabilities.add(Capability.INSPECT)
    return DotnetAdapter(
        AdapterConfig(condition, "csharp", condition, frozenset(capabilities)),
        DotnetLayout(
            "src/Fulfillment.Application/bin/Debug/net10.0/Fulfillment.Application.dll",
            "bin/Debug/net10.0/Suite.dll",
        ),
    )


def source_hashes():
    """Freeze suite source and the SDK manifest/patches; package bytes are checked separately."""
    files = (
        list(ROOT.rglob("*"))
        + list(SDK.glob("*"))
        + list((REPO / "cohesive_evals").rglob("*.py"))
        + list((REPO / "tests").glob("*.py"))
        + [REPO / "pyproject.toml"]
    )
    # Freeze the complete source recipe too: changes in a preserved parent invalidate the run.
    for folder in (
        CASE / "conditions",
        CASE / "evolution",
        CASE / "probes/portable-validation",
        CASE / "probes/api-outcomes",
    ):
        files.extend(folder.rglob("*"))
    return {
        str(p.relative_to(REPO)): sha(p)
        for p in sorted(set(files))
        if p.is_file()
        and p.suffix
        in (
            ".cs",
            ".csproj",
            ".py",
            ".patch",
            ".json",
            ".props",
            ".targets",
            ".config",
            ".toml",
        )
        and not {"__pycache__", "bin", "obj", "artifacts"}.intersection(p.parts)
    }


def materialize(output, version):
    """Create isolated references and adapters, applying only pinned policy/SDK patches."""
    if version not in VERSIONS:
        raise ValueError(version)
    refs = references.materialize(output / "references")
    if version == "revised":
        for condition in CONDITIONS:
            apply_delta(
                refs / condition,
                ROOT / f"reference/{condition}.patch",
                ROOT / f"reference/{condition}.json",
            )
    cohesive = refs / "cohesive"
    apply_delta(cohesive, SDK / "reference.patch", SDK / "reference.json")
    references.packages(SDK, cohesive)
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
    result = adapter(condition).build_consumer(output, prepare_locks)
    if prepare_locks:
        shutil.copy2(
            output / "suites" / condition / "packages.lock.json",
            ROOT / condition / "packages.lock.json",
        )
    return result


def invoke(output, condition, argument):
    """Run the typed .NET consumer; process failures/timeouts never become test results."""
    folder = output / "suites" / condition
    capability = (
        Capability.INSPECT
        if argument == "--describe"
        else (
            Capability.GENERATE
            if str(argument).startswith("--")
            else Capability.OFFLINE
        )
    )
    return adapter(condition).execute(folder, capability, str(argument)).payload
