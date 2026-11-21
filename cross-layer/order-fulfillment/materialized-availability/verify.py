"""Grade persisted availability through production HTTP, physical rows, and actual PostgreSQL plans."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import uuid

from build import CONDITIONS, build_tools
from cohesive_evals.evidence import dump
from cohesive_evals.postgres import verification_run
from cohesive_evals.runtime import HttpClient, capture, host, kestrel_url, run, wait

SEED = {
    "orders": [{"id": key, "status": status} for key, status in
               [("A", "Submitted"), ("B", "Draft"), ("R", "Submitted"), ("U", "Submitted")]],
    "inventory": [{"sku": "X", "available": 5}, {"sku": "Y", "available": 7}],
    "reservations": [{"id": "a1", "orderId": "A", "sku": "X", "quantity": 1},
                     {"id": "u1", "orderId": "U", "sku": "Y", "quantity": 4}],
}
TARGET = "order_availability"


class RequirementFailure(AssertionError):
    """Identify the exact independent requirement violated by a running reference."""

    def __init__(self, assertion, actual, expected):
        """Preserve the assertion name for mutant classification."""
        self.assertion = assertion
        super().__init__(f"{assertion}: observed {actual!r}, expected {expected!r}")


def expect(actual, expected, name):
    """Reject a public or physical observation that disagrees with the oracle."""
    if actual != expected:
        raise RequirementFailure(name, actual, expected)


def sql(db, statement):
    """Execute inspector SQL in a separate session; SQL failures are infrastructure errors."""
    return capture("docker", "exec", db.container, "psql", "-XqAt", "-v", "ON_ERROR_STOP=1",
                   "-U", "postgres", "-c", statement)


def physical(db):
    """Read all persisted rows, including the sentinel for an empty order."""
    return json.loads(sql(db, """
        SELECT coalesce(json_agg(json_build_array(order_id,reservation_id,sku,quantity,available)
            ORDER BY order_id COLLATE "C",reservation_id COLLATE "C"),'[]') FROM order_availability
    """))


def expected_rows(orders, reservations, inventory):
    """Join independent seed and command facts; preserve an empty order as a single null row."""
    rows = []
    for order in sorted(orders):
        matches = sorted((r for r in reservations if r["orderId"] == order), key=lambda r: r["id"])
        rows.extend([[order, r["id"], r["sku"], r["quantity"], inventory[r["sku"]]] for r in matches]
                    or [[order, None, None, None, None]])
    return rows


def wire(rows, order):
    """Translate oracle rows to the public contract and distinguish unknown from empty."""
    matched = [r for r in rows if r[0] == order]
    if not matched:
        return 404, None
    return 200, [dict(reservationId=r[1], sku=r[2], quantity=r[3], availableStock=r[4])
                 for r in matched if r[1] is not None]


@contextmanager
def launch(folder, output, env):
    """Run the ordinary app and wait for listening without warming either read endpoint."""
    dll = folder / "src/Fulfillment.Application/bin/Debug/net10.0/Fulfillment.Application.dll"
    log = output / "host.log"
    offset = log.stat().st_size if log.exists() else 0
    with host(["dotnet", str(dll), "--urls", "http://127.0.0.1:0"], folder, output, env) as process:
        yield HttpClient(kestrel_url(process, log, offset)), process


def plan_relations(node):
    """Collect every physical relation accessed by a plan, including nested subplans."""
    result = [node["Relation Name"]] if "Relation Name" in node else []
    for child in node.get("Plans", []):
        result.extend(plan_relations(child))
    return result


def check_read(db, client, order, rows):
    """Bracket one actual GET with log markers and require every native plan to use projection storage."""
    tag = uuid.uuid4().hex
    sql(db, f"DO $$ BEGIN RAISE LOG 'begin{tag}'; END $$")
    reply = client.request("GET", f"/orders/{order}/availability")
    sql(db, f"DO $$ BEGIN RAISE LOG 'end{tag}'; END $$")
    expect(reply, wire(rows, order), "public-availability")
    logs = subprocess.check_output(["docker", "logs", db.container], stderr=subprocess.STDOUT, text=True)
    begin, end = "LOG:  begin" + tag, "LOG:  end" + tag
    if begin not in logs or end not in logs.split(begin, 1)[1]:
        raise RuntimeError("PostgreSQL log markers unavailable")
    section = logs.split(begin, 1)[1].split(end, 1)[0]
    plans = [json.JSONDecoder().raw_decode(chunk.lstrip())[0]
             for chunk in section.split(" plan:")[1:]]
    if not plans:
        raise RuntimeError("PostgreSQL returned no query plan for the measured GET")
    relations = [name for plan in plans for name in plan_relations(plan["Plan"])]
    expect(set(relations), {TARGET}, "projection-only-read")
    return [{"query": plan["Query Text"], "plan": plan["Plan"]} for plan in plans]


def submit(client, process, request, expected):
    """Wait only for the operation's terminal result; the projection gets no grace period."""
    status, receipt = client.request("POST", "/fulfillment", request)
    expect(status, 202, "admission")

    def terminal():
        """Return the first nonpending HTTP reply, including any failure."""
        reply = client.request("GET", receipt["resultUrl"])
        return reply if reply[0] != 202 else None

    expect(wait(process, terminal, "terminal result"), (200, expected), "completion")
    return receipt


def check(folder, output, condition):
    """Run the same trace for either condition and record source identity and native access evidence."""
    with verification_run(output, "availability", RequirementFailure) as db:
        db.condition = condition
        fingerprint = build_tools.verify_build(folder)
        connection = f"Host=127.0.0.1;Port={db.port};Database=postgres;Username=postgres;Password=fixture-only"
        env = dict(os.environ, ConnectionStrings__Orders=connection +
                   ";Options=-c session_preload_libraries=auto_explain -c auto_explain.log_min_duration=0 -c auto_explain.log_format=json")
        seed = output / "seed.json"
        dump(seed, SEED)
        dll = folder / "src/Fulfillment.Application/bin/Debug/net10.0/Fulfillment.Application.dll"
        run("dotnet", str(dll), "--seed", str(seed), env=dict(env, FULFILLMENT_SETUP="1"))
        orders = {o["id"] for o in SEED["orders"]}
        stock = {i["sku"]: i["available"] for i in SEED["inventory"]}
        reservations = list(SEED["reservations"])
        rows = expected_rows(orders, reservations, stock)
        expect(physical(db), rows, "seed-before-get")
        # Exercise backfill on an already populated source database.
        kind = "MATERIALIZED VIEW" if condition == "conventional" else "TABLE"
        sql(db, f"DROP {kind} {TARGET}")
        trace = {}
        with launch(folder, output, env) as (client, process):
            expect(physical(db), rows, "startup-backfill")
            for key in ("A", "B", "missing"):
                trace[key] = check_read(db, client, key, rows)
            status, created = client.request("POST", "/orders")
            expect(status, 201, "create")
            orders.add(created["id"])
            rows = expected_rows(orders, reservations, stock)
            expect(physical(db), rows, "created-before-get")
            expect(client.request("POST", f"/orders/{created['id']}/submit"),
                   (200, {"id": created["id"], "status": "Submitted"}), "direct-submit")
            expect(client.request("GET", f"/orders/{created['id']}/availability"), (200, []), "direct-empty")
            request = dict(requestId="reserve-b", orderId="B", sku="X", quantity=2)
            receipt = submit(client, process, request, dict(status="Submitted", outcome="ReservedAndSubmitted"))
            stock["X"] -= request["quantity"]
            reservations.append(dict(id="B", orderId="B", sku="X", quantity=request["quantity"]))
            rows = expected_rows(orders, reservations, stock)
            observed = physical(db)
            expect([r for r in observed if r[0] == "A"], [r for r in rows if r[0] == "A"], "shared-sku-fanout")
            expect(observed, rows, "settled-before-get")
            for key in ("A", "B", "U"):
                expect(client.request("GET", f"/orders/{key}/availability"), wire(rows, key), "settled-read")
            expect(client.request("POST", "/fulfillment", request), (202, receipt), "replay")
            expect(physical(db), rows, "replay-preserves-projection")
            submit(client, process, dict(requestId="reject-r", orderId="R", sku="X", quantity=1),
                   dict(status="Rejected", outcome="OrderRejected"))
            expect(physical(db), rows, "compensated-before-get")
            for key in ("A", "B"):
                expect(client.request("GET", f"/orders/{key}/availability"), wire(rows, key), "compensated-read")
        expect(physical(db), rows, "persisted-while-stopped")
        with launch(folder, output, env) as (client, _):
            expect(physical(db), rows, "restart-before-get")
            for key in ("A", "B", "U", created["id"], "missing"):
                expect(client.request("GET", f"/orders/{key}/availability"), wire(rows, key), "restart-read")
        db.report({condition: {"buildManifestSha256": fingerprint, "samplePlans": trace,
                               "settledRows": [r for r in observed if r[0] in ("A", "B", "U")]}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("condition", choices=CONDITIONS)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    check((args.fixtures / args.condition).resolve(), args.output.resolve(), args.condition)
