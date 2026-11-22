"""Exercise lag, crash replay, and resync overlap against a separately running availability worker."""

import argparse
from contextlib import ExitStack, contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys

SYNC = Path(__file__).resolve().parent.parent / "materialized-availability"
sys.path.insert(0, str(SYNC))
from verify import (CONDITIONS, SEED, RequirementFailure, build_tools, check_read, dump, expect,
                    expected_rows, launch, physical, sql, submit, verification_run, wire)
from cohesive_evals.runtime import capture, host, run, wait


@contextmanager
def before_acknowledgement(db, http_host):
    """Hold a PostgreSQL lock that stops only checkpoint writes; source and projection commits stay visible."""
    gate = subprocess.Popen(["docker", "exec", "-e", "PGAPPNAME=checkpoint_gate", db.container, "psql",
                             "-U", "postgres", "-v", "ON_ERROR_STOP=1", "-c",
                             "BEGIN; LOCK TABLE availability_progress IN SHARE MODE; SELECT pg_sleep(90)"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait(http_host, lambda: sql(db, "SELECT count(*) FROM pg_stat_activity WHERE "
             "application_name='checkpoint_gate' AND wait_event='PgSleep'") == "1", "checkpoint gate")
        yield
    finally:
        sql(db, "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name='checkpoint_gate'")
        gate.wait(timeout=10)


def published(db, worker):
    """Wait for the worker to reach its real blocked acknowledgement, after committing projection rows."""
    wait(worker, lambda: sql(db, "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type='Lock' "
         "AND query LIKE 'UPDATE availability_progress SET revision%'") == "1", "worker acknowledgement")


def versions(db):
    """Observe a physical row version per order to distinguish rewritten unrelated rows on this fixture."""
    return json.loads(sql(db, """SELECT json_object_agg(order_id, x) FROM
        (SELECT order_id, min(xmin::text) x FROM order_availability GROUP BY order_id) v"""))


def check_read_limits(folder, output, client, dll, env):
    """Reuse the G0 seed generator and check exact counts and raw response bytes at its four boundaries."""
    full = json.loads(capture(sys.executable, str(folder / "tests/contract_tests.py"), "--seed"))
    keys = {"rows-at", "rows-over", "bytes-availability-1000000", "bytes-availability-1000001"}
    reservations = [r for r in full["reservations"] if r["orderId"] in keys]
    skus = {r["sku"] for r in reservations}
    seed = {"orders": [o for o in full["orders"] if o["id"] in keys],
            "inventory": [i for i in full["inventory"] if i["sku"] in skus], "reservations": reservations}
    path = output / "limit-seed.json"
    dump(path, seed)
    run("dotnet", str(dll), "--seed", str(path), env=dict(env, FULFILLMENT_SETUP="1"))
    status, rows = client.request("GET", "/orders/rows-at/availability")
    expect((status, len(rows)), (200, 1000), "inclusive-row-limit")
    status, raw = client.request_bytes("GET", "/orders/bytes-availability-1000000/availability")
    expect((status, len(raw)), (200, 1_000_000), "inclusive-byte-limit")
    for order in ("rows-over", "bytes-availability-1000001"):
        expect(client.request("GET", f"/orders/{order}/availability"),
               (422, {"code": "ReadResultTooLarge"}), "over-read-limit")
    return {"rowsAtLimit": len(rows), "bytesAtLimit": len(raw), "overLimitStatus": 422}


def check(folder, output, condition):
    """Run one independent production HTTP and worker trace against an isolated database."""
    with verification_run(output, "asyncavailability", RequirementFailure) as db:
        db.condition = condition
        fingerprint = build_tools.verify_build(folder)
        env = dict(os.environ, ConnectionStrings__Orders=f"Host=127.0.0.1;Port={db.port};Database=postgres;"
                   "Username=postgres;Password=fixture-only;Options=-c session_preload_libraries=auto_explain "
                   "-c auto_explain.log_min_duration=0 -c auto_explain.log_format=json")
        dll = folder / "src/Fulfillment.Application/bin/Debug/net10.0/Fulfillment.Application.dll"
        seed = {**SEED, "orders": [*SEED["orders"], {"id": "C", "status": "Draft"}]}
        seed_path = output / "seed.json"
        dump(seed_path, seed)
        run("dotnet", str(dll), "--seed", str(seed_path), env=dict(env, FULFILLMENT_SETUP="1"))
        orders = {o["id"] for o in seed["orders"]}
        stock = {i["sku"]: i["available"] for i in seed["inventory"]}
        reservations = list(seed["reservations"])

        with launch(folder, output, env) as (client, server):
            def checkpoint():
                """Read the separate durable source and publication watermarks through HTTP."""
                status, value = client.request("GET", "/availability/checkpoint")
                expect(status, 200, "checkpoint-status")
                return value

            def reserve(order, quantity):
                """Settle a real command and update the oracle from its declared effects."""
                submit(client, server, dict(requestId="reserve-" + order, orderId=order, sku="X", quantity=quantity),
                       dict(status="Submitted", outcome="ReservedAndSubmitted"))
                stock["X"] -= quantity
                reservations.append(dict(id=order, orderId=order, sku="X", quantity=quantity))
                return expected_rows(orders, reservations, stock)

            def worker(once=False):
                """Launch the same production worker continuously or for exactly one captured cut."""
                mode = "--availability-worker-once" if once else "--availability-worker"
                return host(["dotnet", str(dll), mode], folder, output, env)

            def catch_up(revision):
                """Wait for the specified checkpoint with an active worker and stop it afterward."""
                with worker() as process:
                    wait(process, lambda: checkpoint()["applied"] >= revision, "publication checkpoint")

            original = expected_rows(orders, reservations, stock)
            baseline = checkpoint()
            expect(baseline["applied"], baseline["requested"], "initial-checkpoint")
            start_versions = versions(db)
            rows = reserve("B", 2)
            lag = checkpoint()
            expect(lag["requested"] > lag["applied"] == baseline["applied"], True, "lag-observable")
            stale = client.request("GET", "/orders/A/availability")
            expect(stale, wire(original, "A"), "stale-while-paused")
            with before_acknowledgement(db, server):
                with worker() as process:
                    published(db, process)
                    expect(physical(db), rows, "published-before-ack")
                    process.kill()
                    process.wait(timeout=10)
            expect(checkpoint()["applied"], baseline["applied"], "crash-before-checkpoint")
            after = versions(db)
            rewritten = sorted(key for key in start_versions if start_versions[key] != after[key])
            catch_up(lag["requested"])
            expect(physical(db), rows, "replay-no-duplicates")
            replay = {}
            for key in ("A", "B", "U"):
                reply = client.request("GET", f"/orders/{key}/availability")
                expect(reply, wire(rows, key), "fanout-after-replay")
                replay[key] = reply[1]

            cut = int(capture("dotnet", str(dll), "--resync-availability", env=env).splitlines()[-1])
            expect(cut > lag["requested"], True, "resync-issued")
            with worker_after_gate(db, server, worker) as finish:
                newer_rows = reserve("C", 1)
                latest = checkpoint()["requested"]
                expect(latest > cut, True, "write-during-rebuild")
                expect(client.request("GET", "/orders/A/availability"), wire(rows, "A"), "rebuild-old-snapshot")
            expect(finish.returncode, 0, "one-cut-exit")
            expect(checkpoint()["applied"], cut, "checkpoint-captured-cut")
            catch_up(latest)
            expect(physical(db), newer_rows, "catch-up-includes-overlap")
            traces = {key: check_read(db, client, key, newer_rows) for key in ("A", "B", "C", "U", "missing")}
            final = checkpoint()
            limits = check_read_limits(folder, output, client, dll, env)
            db.report({condition: {"buildManifestSha256": fingerprint, "initial": baseline, "paused": lag,
                       "resyncCut": cut, "overlappingWrite": latest, "final": final, "readLimits": limits,
                       "pausedAvailabilityA": stale[1], "availabilityAfterReplay": replay,
                       "ordersRewrittenAfterB": rewritten, "finalPlans": traces}})


@contextmanager
def worker_after_gate(db, server, worker):
    """Release the gate before waiting for this one-cut worker to exit, including on test failure."""
    with ExitStack() as processes:
        with before_acknowledgement(db, server):
            process = processes.enter_context(worker(once=True))
            published(db, process)
            yield process
        process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("condition", choices=CONDITIONS)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    check((args.fixtures / args.condition).resolve(), args.output.resolve(), args.condition)
