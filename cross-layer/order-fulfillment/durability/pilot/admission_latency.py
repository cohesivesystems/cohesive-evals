"""Compare unmetered HTTP admission latency on two SDK builds in isolated emulator runs."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
from statistics import median
from time import perf_counter

from capacity import RequirementFailure, application_host, expect, request_for
from cohesive_evals.evidence import dump
from cohesive_evals.postgres import verification_run
from cohesive_evals.runtime import durable_task_scheduler, run


def measure(client, start, concurrency, count):
    """Time distinct successful submissions through receipt delivery and report wall-clock throughput."""
    def submit(index):
        """Return elapsed milliseconds after verifying HTTP admission."""
        before = perf_counter()
        response = client.request("POST", "/fulfillment", request_for(index))
        elapsed = (perf_counter() - before) * 1000
        expect(response[0], 202, "latency sample admitted")
        return round(elapsed, 3)

    with ThreadPoolExecutor(concurrency) as pool:
        before = perf_counter()
        samples = list(pool.map(submit, range(start, start + count)))
        duration = perf_counter() - before
    return dict(concurrency=concurrency, elapsedMs=samples, medianMs=median(samples),
                p95Ms=sorted(samples)[math.ceil(count * 0.95) - 1], requestsPerSecond=count / duration)


def trial(app, output, image, concurrency):
    """Launch a fresh database, scheduler and app for one warm latency sample."""
    with verification_run(output, "admission-latency", RequirementFailure) as db, durable_task_scheduler(image) as url:
        env = dict(os.environ, DURABLE_TASK_CONNECTION=url,
                   ConnectionStrings__Orders=f"Host=127.0.0.1;Port={db.port};Database=postgres;Username=postgres;Password=fixture-only")
        seed = output / "seed.json"
        dump(seed, dict(orders=[dict(id="a", status="Draft")], inventory=[], reservations=[]))
        run("dotnet", str(app), "--seed", str(seed), env=dict(env, FULFILLMENT_SETUP="1"))
        with application_host(app, output, env) as client:
            measure(client, 0, concurrency, 16)
            result = measure(client, 16, concurrency, 100)
        db.report({"latency": result})
        return result


def main():
    """Run counterbalanced trials with both application DLLs explicitly configured as unlimited."""
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("before", "after", "output"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = Path(__file__).resolve().parents[1] / "dependency-manifest.json"
    image = json.loads(manifest.read_text())["schedulerImage"]
    results = []
    for concurrency in (1, 8):
        for index, label in enumerate(("before", "after", "after", "before")):
            app = getattr(args, label).resolve()
            result = trial(app, args.output / f"c{concurrency}-{index}-{label}", image, concurrency)
            results.append(dict(build=label, **result))
    dump(args.output / "samples.json", results)


if __name__ == "__main__":
    main()
