"""Bounded subprocess and HTTP lifecycle, without scenario or SDK knowledge."""

from contextlib import contextmanager
import json
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from .contracts import AdapterError


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


class HttpClient:
    """Return public HTTP status/body observations; leave business interpretation to checks."""

    def __init__(self, url):
        """Bind the local host base URL."""
        self.url = url

    def request(self, method, path, body=None, raw=None):
        """Send JSON or exact bytes and decode the reply; malformed JSON is protocol failure."""
        status, payload = self.request_bytes(method, path, body, raw)
        try:
            return status, json.loads(payload) if payload else None
        except (ValueError, UnicodeError) as error:
            raise AdapterError("protocol", "HTTP response is not JSON") from error

    def request_bytes(self, method, path, body=None, raw=None):
        """Return the status and exact response bytes, including bodies on HTTP errors."""
        data = (
            raw
            if raw is not None
            else json.dumps(body).encode() if body is not None else None
        )
        request = urllib.request.Request(
            self.url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            response = urllib.request.urlopen(request, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        except (urllib.error.URLError, TimeoutError) as error:
            raise AdapterError("infrastructure", str(error)) from error
        with response:
            return response.status, response.read()
