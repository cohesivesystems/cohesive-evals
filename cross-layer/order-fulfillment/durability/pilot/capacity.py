"""Check the pilot's 1,000-identity admission contract across an abrupt host restart."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path

from cohesive_evals.contracts import AdapterError
from cohesive_evals.evidence import dump
from cohesive_evals.postgres import verification_run
from cohesive_evals.runtime import (
    HttpClient,
    durable_task_scheduler,
    host,
    kestrel_url,
    run,
    wait,
)


CAPACITY = 1000


class RequirementFailure(AssertionError):
    """Name a violated public guarantee so setup failures stay distinguishable."""

    def __init__(self, assertion, actual):
        """Retain the assertion name and actual observation for grading."""
        self.assertion = assertion
        super().__init__(f"{assertion}: {actual}")


def expect(actual, expected, name):
    """Compare an HTTP observation against a required status or retained receipt."""
    if actual != expected:
        raise RequirementFailure(name, actual)


@contextmanager
def application_host(application, output, env):
    """Yield a ready HTTP client for a fresh launch and kill the host on success."""
    log = output / "host.log"
    offset = log.stat().st_size if log.exists() else 0
    with host(
        ["dotnet", str(application), "--urls", "http://127.0.0.1:0"],
        application.parent,
        output,
        env,
    ) as proc:
        client = HttpClient(kestrel_url(proc, log, offset))

        def ready():
            """Wait until the seeded order can be read from the application."""
            try:
                return client.request("GET", "/orders/a")[0] == 200
            except AdapterError:
                return False

        wait(proc, ready, "capacity host readiness")
        yield client
        proc.kill()
        proc.wait(timeout=10)


def request_for(index):
    """Construct the public request for a distinct admission identity."""
    return dict(requestId=f"r{index}", orderId="a", sku="missing", quantity=1)


def at_capacity(client, receipt, phase):
    """Verify overflow, replay and conflict against the original HTTP receipt."""
    request = request_for(0)
    expect(
        client.request("POST", "/fulfillment", request_for(CAPACITY))[0],
        503,
        phase + " at capacity",
    )
    expect(
        client.request("POST", "/fulfillment", request),
        receipt,
        phase + " retained identity",
    )
    expect(
        client.request("POST", "/fulfillment", {**request, "quantity": 2})[0],
        409,
        phase + " identity conflict",
    )


def check(application, output, condition):
    """Fill a fresh application through HTTP and challenge capacity, replay and conflict twice."""
    manifest = Path(__file__).resolve().parents[1] / "dependency-manifest.json"
    image = json.loads(manifest.read_text())["schedulerImage"]
    with (
        verification_run(output, "pilot-capacity", RequirementFailure) as database,
        durable_task_scheduler(image) as connection,
    ):
        database.condition = condition
        env = dict(
            os.environ,
            DURABLE_TASK_CONNECTION=connection,
            ConnectionStrings__Orders=f"Host=127.0.0.1;Port={database.port};Database=postgres;Username=postgres;Password=fixture-only",
        )
        seed = output / "seed.json"
        dump(
            seed,
            {
                "orders": [{"id": "a", "status": "Draft"}],
                "inventory": [],
                "reservations": [],
            },
        )
        run(
            "dotnet",
            str(application),
            "--seed",
            str(seed),
            env=dict(env, FULFILLMENT_SETUP="1"),
        )
        with application_host(application, output, env) as client:
            receipt = client.request("POST", "/fulfillment", request_for(0))
            expect(receipt[0], 202, "first admission")
            for index in range(1, CAPACITY):
                reply = client.request("POST", "/fulfillment", request_for(index))
                expect(reply[0], 202, f"admit identity {index + 1}")
            at_capacity(client, receipt, "fill")
        with application_host(application, output, env) as client:
            at_capacity(client, receipt, "restart")
        database.report(
            {
                condition: {
                    "distinctAdmissions": CAPACITY,
                    "restartCapacityReplayConflict": True,
                }
            }
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("condition")
    arguments = parser.parse_args()
    check(
        arguments.application.resolve(), arguments.output.resolve(), arguments.condition
    )
