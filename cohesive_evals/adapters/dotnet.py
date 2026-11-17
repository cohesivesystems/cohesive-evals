""".NET-specific builds, NuGet inputs and typed executable invocation."""

import json
from dataclasses import dataclass
from pathlib import Path
from ..contracts import AdapterConfig, AdapterError, Capability, ExecutionResult
from ..evidence import sha, dump
from ..runtime import run, capture, host


def input_hashes(folder: Path) -> dict[str, str]:
    """Fingerprint .NET source/configuration/package inputs, excluding generated output."""
    return {
        str(p.relative_to(folder)): sha(p)
        for p in sorted(folder.rglob("*"))
        if p.is_file()
        and not {"bin", "obj", "__pycache__"}.intersection(p.relative_to(folder).parts)
        and (
            p.suffix in {".cs", ".csproj", ".props", ".targets", ".nupkg"}
            or p.name in {"global.json", "NuGet.config", "packages.lock.json"}
        )
    }


@dataclass(frozen=True)
class DotnetLayout:
    """Adapter-owned project and output layout; generic contracts do not mention assemblies."""

    application: str
    offline: str


class DotnetAdapter:
    """Implement adapter/v1 using locked .NET builds and JSON observations."""

    def __init__(self, config: AdapterConfig, layout: DotnetLayout):
        """Bind an implementation identity and explicit executable paths."""
        self.config, self.layout = config, layout

    def artifacts(self, folder):
        """Hash the complete application output directory, not only its primary assembly."""
        return {
            str(p.relative_to(folder)): sha(p)
            for p in sorted((folder / self.layout.application).parent.rglob("*"))
            if p.is_file()
        }

    def build(self, folder, log=None):
        """Locked restore/build and a retained-compatible manifest; reject input mutation."""
        manifest = folder / "build-manifest.json"
        manifest.unlink(missing_ok=True)
        before = input_hashes(folder)
        try:
            run(
                "dotnet", "restore", "--locked-mode", cwd=folder, stdout=log, stderr=log
            )
            run(
                "dotnet",
                "build",
                "--no-restore",
                "--no-incremental",
                "-m:1",
                "-nr:false",
                cwd=folder,
                stdout=log,
                stderr=log,
            )
        except AdapterError as error:
            raise AdapterError("build", str(error)) from error
        if (
            before != input_hashes(folder)
            or not (folder / self.layout.application).is_file()
        ):
            raise AdapterError("build", "Inputs changed or application binary missing")
        dump(
            manifest,
            {
                "inputs": before,
                "artifacts": self.artifacts(folder),
                "sdk": capture("dotnet", "--version", cwd=folder),
            },
        )
        return sha(manifest)

    def observe(self, folder):
        """Reject stale source or changed output before trusting candidate observations."""
        manifest = json.loads((folder / "build-manifest.json").read_text())
        if (
            manifest["inputs"] != input_hashes(folder)
            or manifest["artifacts"] != self.artifacts(folder)
            or not (folder / self.layout.application).is_file()
        ):
            raise AdapterError(
                "infrastructure", "Source or executable drift since build"
            )
        return sha(folder / "build-manifest.json")

    def start(self, folder, output, environment, arguments):
        """Return a managed HTTP process context; readiness remains scenario-owned."""
        self.config.require(Capability.HTTP)
        self.observe(folder)
        return host(
            ["dotnet", str(folder / self.layout.application), *arguments],
            folder,
            output,
            environment,
        )

    def seed(self, folder, seed, environment, log):
        """Run the application-owned setup command; PostgreSQL itself is an optional fixture."""
        run(
            "dotnet",
            str(folder / self.layout.application),
            "--seed",
            str(seed),
            cwd=folder,
            env=environment,
            stdout=log,
            stderr=log,
            timeout=90,
        )

    def execute(self, folder, capability, argument):
        """Run one declared offline operation; malformed output is never a behavioral result."""
        self.config.require(capability)
        if capability == Capability.HTTP:
            raise AdapterError(
                "unsupported", "HTTP execution uses start and public requests"
            )
        reply = capture(
            "dotnet", str(folder / self.layout.offline), str(argument), timeout=60
        )
        try:
            payload = json.loads(reply)
        except ValueError as error:
            raise AdapterError(
                "protocol", "Offline consumer returned malformed JSON"
            ) from error
        return ExecutionResult(capability, payload)

    def build_consumer(self, output, prepare_locks=False):
        """Build the production application and typed offline consumer with exact input/output provenance."""
        condition = self.config.condition
        refs = output / "references"
        folder = output / "suites" / condition
        with (folder / "build.log").open("w") as log:
            self.build(refs / condition, log)
            before = input_hashes(refs / condition)
            props = ["-p:FixtureRoot=" + str(refs)]
            run(
                *[
                    "dotnet",
                    "restore",
                    "Suite.csproj",
                    *props,
                    *([] if prepare_locks else ["--locked-mode"]),
                ],
                cwd=folder,
                stdout=log,
                stderr=log,
                timeout=180,
            )
            run(
                *[
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
                timeout=180,
            )
        if before != input_hashes(refs / condition):
            raise ValueError("Production inputs changed")
        self.observe(refs / condition)
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
