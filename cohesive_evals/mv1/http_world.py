"""MV1 fixture setup and read-only physical observer; no production mappings imported."""

from contextlib import ExitStack
import json
import os
import socket
import uuid
import urllib.error
import urllib.request
from ..runtime import capture, wait, HttpClient
from .fixture import adapter


class World:
    """Own one seeded application host; optional PostgreSQL is supplied by the scenario."""

    def __init__(self, folder, output, container, port, condition, seed):
        """Create isolated facts and host; clean up on any partial construction failure."""
        self.output, self.container, self.condition = output, container, condition
        output.mkdir(parents=True)
        self.resources = ExitStack()
        self.database = "mv" + uuid.uuid4().hex[:12]
        capture(
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            "postgres",
            "-c",
            f"CREATE DATABASE {self.database}",
        )
        environment = dict(
            os.environ,
            ConnectionStrings__Orders=f"Host=127.0.0.1;Port={port};Database={self.database};Username=postgres;Password=fixture-only;Timeout=10",
            ASPNETCORE_ENVIRONMENT="Production",
        )
        seedfile = output / "seed.json"
        seedfile.write_text(json.dumps(seed))
        engine = adapter(condition)
        try:
            with (output / "host.log").open("w") as log:
                engine.seed(
                    folder, seedfile, dict(environment, FULFILLMENT_SETUP="1"), log
                )
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                http_port = sock.getsockname()[1]
            self.url = f"http://127.0.0.1:{http_port}"
            self.process = self.resources.enter_context(
                engine.start(folder, output, environment, ["--urls", self.url])
            )
            self.ready_path = "/orders/" + seed["orders"][0]["id"]
            self.wait(self.ready, "host readiness")
            self.client = HttpClient(self.url)
        except BaseException:
            self.close()
            raise

    def ready(self):
        """Probe public readiness without treating connection startup as behavioral failure."""
        try:
            with urllib.request.urlopen(
                self.url + self.ready_path, timeout=1
            ) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError):
            return False

    def wait(self, predicate, label):
        """Wait for a public result while checking host liveness."""
        return wait(self.process, predicate, label)

    def facts(self):
        """Read independently named tables and normalize their public business facts."""
        tables = {
            "conventional": ("orders", "id", "inventory", "reservations", "id"),
            "cohesive": (
                "cohesive_orders",
                "order_id",
                "cohesive_inventory",
                "cohesive_reservations",
                "reservation_id",
            ),
        }
        order, oid, inventory, reservation, rid = tables[self.condition]
        sql = f"""SELECT json_build_object(
        'orders',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT {oid} AS id,status FROM {order}) x),
        'inventory',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT sku,available,max_per_order AS "maxPerOrder",quarantined FROM {inventory}) x),
        'reservations',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT {rid} AS id,order_id AS "orderId",sku,quantity FROM {reservation}) x));"""
        return json.loads(
            capture(
                "docker",
                "exec",
                self.container,
                "psql",
                "-U",
                "postgres",
                "-d",
                self.database,
                "-At",
                "-c",
                sql,
            )
        )

    def close(self):
        """Stop the managed host even after failed setup or an assertion."""
        self.resources.close()
