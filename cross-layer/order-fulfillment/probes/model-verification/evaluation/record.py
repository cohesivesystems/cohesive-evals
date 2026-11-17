#!/usr/bin/env python3
"""Bundle review evidence without copying SDK packages or executable build outputs."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    """Return the SHA-256 of the exact file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    """Write a readable UTF-8 JSON artifact with a final newline."""
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def record(args):
    """Bundle completed reports and raw evidence, checking the HTTP/offline source correspondence."""
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    pairs = [item.split("=", 1) for item in args.run]
    runs = {name: Path(path).resolve() for name, path in pairs}
    required = {
        "references",
        "qualification",
        "versioned-http",
        "retained-ao1",
        "retained-typed",
        "retained-pv1",
        "retained-evolution",
    }
    if set(runs) != required or len(pairs) != len(required):
        raise ValueError("Supply each run exactly once: " + ", ".join(sorted(required)))
    equality = {}
    for version in ("original", "revised"):
        for condition in ("conventional", "cohesive"):
            relative = Path(version) / "references" / condition / "build-manifest.json"
            http = json.loads((args.http_fixtures / relative).read_text())
            offline = json.loads((runs["references"] / relative).read_text())
            if http["inputs"] != offline["inputs"]:
                raise ValueError(
                    "HTTP and offline production inputs differ: " + str(relative)
                )
            equality[version + "/" + condition] = {
                "sameInputs": True,
                "httpBuildManifestSha256": sha(args.http_fixtures / relative),
                "offlineBuildManifestSha256": sha(runs["references"] / relative),
            }
    # Keep the actual HTTP build identities even if only adapter metadata changed later.
    runs["http-references"] = args.http_fixtures
    reports = {}
    for name, path in runs.items():
        if name == "http-references":
            continue
        report = json.loads((path / "report.json").read_text())
        if report.get("passed") is not True:
            raise ValueError("Nonpassing report: " + name)
        (output / (name + ".json")).write_bytes((path / "report.json").read_bytes())
        reports[name] = sha(path / "report.json")
    archived = {}
    with (output / "raw.tar.gz").open("wb") as raw, gzip.GzipFile(
        fileobj=raw, mode="wb", filename="", mtime=0
    ) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            for name, root in runs.items():
                for path in sorted(root.rglob("*")):
                    relative = path.relative_to(root)
                    if (
                        not path.is_file()
                        or any(
                            p in ("bin", "obj", "packages", "__pycache__", ".git")
                            for p in relative.parts
                        )
                        or path.suffix
                        not in (
                            ".json",
                            ".log",
                            ".cs",
                            ".csproj",
                            ".sql",
                            ".props",
                            ".targets",
                            ".config",
                        )
                    ):
                        continue
                    if (
                        "references" in relative.parts
                        and path.name != "build-manifest.json"
                    ):
                        continue
                    key = name + "/" + str(relative)
                    data = path.read_bytes()
                    info = tarfile.TarInfo(key)
                    info.size = len(data)
                    info.mode = 0o644
                    tar.addfile(info, io.BytesIO(data))
                    archived[key] = hashlib.sha256(data).hexdigest()
            index = json.dumps(archived, indent=2).encode()
            info = tarfile.TarInfo("raw-index.json")
            info.size = len(index)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(index))
    sources = {
        str(p.relative_to(ROOT.parent)): sha(p)
        for folder in ("suites", "evaluation", "sdk")
        for p in sorted((ROOT.parent / folder).rglob("*"))
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix in (".py", ".cs", ".csproj", ".json", ".patch")
    }
    measurements = {
        str(p.relative_to(ROOT.parent)): {
            "lines": len(p.read_text().splitlines()),
            "nonblankLines": sum(
                bool(line.strip()) for line in p.read_text().splitlines()
            ),
        }
        for p in sorted((ROOT.parent / "suites").rglob("*"))
        if p.suffix in (".py", ".cs")
    }
    dump(
        output / "manifest.json",
        {
            "reports": reports,
            "archiveSha256": sha(output / "raw.tar.gz"),
            "archivedFileCount": len(archived),
            "archiveIndex": "raw-index.json",
            "sources": sources,
            "httpProductionInputEquality": equality,
        },
    )
    dump(
        output / "authored-work.json",
        {
            "scope": "Raw source counts, shared files counted once; no task-time or causal advantage estimate",
            "files": measurements,
            "developmentStage": "SDK-based generation/execution replaces the development prototype; no blinded trial",
            "policyMaintenance": "Versioned independent precedence oracle; unchanged generator and input catalog; explicit production reference patches",
        },
    )
    print(
        "Recorded",
        len(archived),
        "files;",
        (output / "raw.tar.gz").stat().st_size,
        "archive bytes",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, metavar="NAME=PATH")
    parser.add_argument("--http-fixtures", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    record(parser.parse_args())
