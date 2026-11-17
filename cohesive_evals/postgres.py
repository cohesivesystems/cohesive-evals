"""Shared PostgreSQL lifecycle and failure reports for portable-validation probes."""

from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
from .runtime import capture
from .qualification import failure

IMAGE = "postgres:17.10-alpine3.24"


@dataclass
class VerificationRun:
    """Optional PostgreSQL fixture and report context, with an initialized failure location."""

    output: Path
    container: str
    port: str = ""
    image_id: str = ""
    condition: str | None = None

    def report(self, records):
        """Persist successful observations with the actual database image identity."""
        (self.output / "report.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "postgresImage": IMAGE,
                    "postgresImageId": self.image_id,
                    "conditions": records,
                },
                indent=2,
            )
            + "\n"
        )

    def failure(self, error, behavioral):
        """Preserve the original failure, including errors before any scenario starts."""
        record = {
            **({"kind": "behavioral"} if behavioral else failure(error)),
            "condition": self.condition,
            "detail": str(error),
        }
        if behavioral:
            record.update(assertion=error.assertion)
        (self.output / "failure.json").write_text(json.dumps(record, indent=2) + "\n")


@contextmanager
def verification_run(output, prefix, behavioral_failure):
    """Start an optional isolated database and always remove it, preserving primary failures."""
    output.mkdir(parents=True, exist_ok=False)
    session = VerificationRun(output, prefix + "-" + uuid.uuid4().hex[:12])
    started = False
    try:
        try:
            session.image_id = capture(
                "docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"
            )
            capture(
                "docker",
                "run",
                "-d",
                "--name",
                session.container,
                "-e",
                "POSTGRES_PASSWORD=fixture-only",
                "-p",
                "127.0.0.1::5432",
                IMAGE,
            )
            started = True
            for _ in range(100):
                if (
                    subprocess.run(
                        [
                            "docker",
                            "exec",
                            session.container,
                            "pg_isready",
                            "-h",
                            "127.0.0.1",
                            "-U",
                            "postgres",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                    ).returncode
                    == 0
                ):
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("PostgreSQL readiness deadline")
            session.port = capture(
                "docker", "port", session.container, "5432/tcp"
            ).rsplit(":", 1)[1]
            yield session
        finally:
            if started:
                # A cleanup failure must not replace the original behavioral/setup error.
                pending = sys.exc_info()[0] is not None
                try:
                    subprocess.run(
                        ["docker", "rm", "-f", session.container],
                        stdout=subprocess.DEVNULL,
                        check=True,
                        timeout=30,
                    )
                except Exception as error:
                    if not pending:
                        raise
                    print(f"PostgreSQL cleanup also failed: {error}", file=sys.stderr)
    except behavioral_failure as error:
        session.failure(error, behavioral=True)
        raise
    except Exception as error:
        session.failure(error, behavioral=False)
        raise
