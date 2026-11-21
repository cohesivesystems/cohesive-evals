"""Bounded subprocess and HTTP lifecycle, without scenario or SDK knowledge."""

from contextlib import contextmanager
import re
import socket
import subprocess
import time
import uuid
from .errors import AdapterError
from .http_client import HttpClient


def run(*command, timeout=120, **kwargs):
    """Run a bounded command; setup/execution failures cannot become business assertions."""
    try:
        return subprocess.run(command, check=True, timeout=timeout, **kwargs)
    except (subprocess.SubprocessError, OSError) as error:
        raise AdapterError("infrastructure", str(error)) from error


def capture(*command, **kwargs) -> str:
    """Return stripped command output or a classified infrastructure failure."""
    return run(*command, text=True, capture_output=True, **kwargs).stdout.strip()


@contextmanager
def durable_task_scheduler(image):
    """Start the pinned emulator, wait for its listener, and clean up on exit."""
    name = "durability-scheduler-" + uuid.uuid4().hex
    capture("docker", "run", "-d", "--name", name, "-p", "127.0.0.1::8080", image)
    try:
        port = int(capture("docker", "port", name, "8080/tcp").rsplit(":", 1)[1])
        deadline = time.monotonic() + 30
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise AdapterError(
                        "infrastructure", "scheduler listener deadline"
                    ) from error
                time.sleep(0.1)
        yield f"Endpoint=http://127.0.0.1:{port};TaskHub=default;Authentication=None"
    finally:
        capture("docker", "rm", "-f", name)


def kestrel_url(process, log_path, offset):
    """Read this launch's loopback address from the host log or fail on exit/deadline."""

    def address():
        """Ignore earlier launches when polling the shared log."""
        with log_path.open("rb") as log:
            log.seek(offset)
            match = re.search(
                rb"Now listening on: (http://127[.]0[.]0[.]1:[0-9]+)\r?\n", log.read()
            )
            return match.group(1).decode() if match else None

    return wait(process, address, "Kestrel listening address")


@contextmanager
def host(command, folder, output, environment):
    """Own a host and log until context exit, including failed readiness or assertions."""
    with (output / "host.log").open("a") as log:
        try:
            process = subprocess.Popen(
                command,
                cwd=folder,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
            )
        except OSError as error:
            raise AdapterError("infrastructure", str(error)) from error
        try:
            yield process
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


def wait(process, predicate, label, timeout=30):
    """Poll until readiness/completion; process exit and deadlines are infrastructure failures."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AdapterError(
                "infrastructure", f"{label}: host exited ({process.returncode})"
            )
        result = predicate()
        if result:
            return result
        time.sleep(0.02)
    raise AdapterError("infrastructure", label + " deadline")
