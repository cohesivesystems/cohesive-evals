"""Regression checks for the shared adapter boundary and nonbehavioral failure handling."""

from contextlib import nullcontext
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from cohesive_evals.contracts import (
    AdapterConfig,
    AdapterError,
    Capability,
    ExecutionResult,
)
from cohesive_evals.mv1 import oracle
from cohesive_evals.mv1.observations import validate
from cohesive_evals.postgres import verification_run
from cohesive_evals.runtime import host
from cohesive_evals.snapshots import apply_delta


class PortableAdapter:
    """Test-only non-.NET implementation: no model, packages, database or plugin loader."""

    config = AdapterConfig(
        "portable-control", "python", "stdlib", frozenset({Capability.OFFLINE})
    )

    def build(self, folder, log=None):
        """An interpreted control has no compilation step."""
        return "test-source"

    def start(self, folder, output, environment, arguments):
        """Refuse HTTP because this control declares only offline execution."""
        self.config.require(Capability.HTTP)
        return nullcontext()

    def execute(self, folder, capability, argument):
        """Return an independently supplied observation through the same typed boundary."""
        self.config.require(capability)
        return ExecutionResult(capability, json.loads(argument))

    def observe(self, folder):
        """Return the interpreted control identity without assuming an assembly layout."""
        return "test-source"


class InfrastructureTests(unittest.TestCase):
    """Keep malformed evidence and unavailable capabilities out of detection credit."""

    def test_configuration_and_independent_capabilities(self):
        """Reject version coercion, unknown versions and unsupported operations before work."""
        for version in (True, "1", 2):
            with self.assertRaises(AdapterError):
                AdapterConfig("x", "typescript", "future", frozenset(), version)
        control = PortableAdapter()
        with self.assertRaises(AdapterError):
            ExecutionResult(Capability.OFFLINE, [], version=2)
        for capability in (Capability.HTTP, Capability.INSPECT, Capability.GENERATE):
            with self.assertRaises(AdapterError) as caught:
                control.execute(Path("."), capability, "[]")
            self.assertEqual("unsupported", caught.exception.category)

    def test_non_dotnet_observations_use_same_independent_oracle(self):
        """Prove grading needs no model, SDK, NuGet, host or PostgreSQL service."""
        case = dict(
            Name="one",
            Sku="sku",
            Available=4,
            MaxPerOrder=4,
            Quarantined=False,
            Quantity=1,
        )
        observation = dict(
            Name="one",
            Outcome="Reserved",
            FulfillmentOutcome="ReservedAndSubmitted",
            After=dict(Sku="sku", Available=3, MaxPerOrder=4, Quarantined=False),
            ScopePreserved=True,
        )
        result = PortableAdapter().execute(
            Path("."), Capability.OFFLINE, json.dumps([observation])
        )
        self.assertEqual(
            1, oracle.check([case], result.payload, "original")["accepted"]
        )

    def test_boolean_integer_coercion_and_extra_fields_are_protocol_failures(self):
        """Reject malformed wire types before any business interpretation."""
        good = dict(
            Name="one",
            Outcome="Reserved",
            FulfillmentOutcome="ReservedAndSubmitted",
            After=dict(Sku="sku", Available=1, MaxPerOrder=4, Quarantined=False),
            ScopePreserved=True,
        )
        bad = [
            {**good, "After": {**good["After"], "Available": True}},
            {**good, "After": {**good["After"], "Quarantined": 0}},
            {**good, "ScopePreserved": 1},
            {**good, "extra": "ignored"},
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(AdapterError) as caught:
                validate([value])
            self.assertEqual("protocol", caught.exception.category)

    def test_early_database_failure_keeps_original_detail(self):
        """An error before the first condition must not be replaced by an unbound variable."""
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch(
                "cohesive_evals.postgres.capture",
                side_effect=RuntimeError("image unavailable"),
            ),
        ):
            output = Path(tmp) / "run"
            with self.assertRaisesRegex(RuntimeError, "image unavailable"):
                with verification_run(output, "test", oracle.BehavioralFailure):
                    self.fail("Database setup unexpectedly succeeded")
            result = json.loads((output / "failure.json").read_text())
            self.assertEqual("unqualified", result["kind"])
            self.assertIsNone(result["condition"])
            self.assertIn("image unavailable", result["detail"])

    def test_host_cleanup_after_verifier_failure(self):
        """A failing verifier cannot leave its application process running."""
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with self.assertRaisesRegex(ValueError, "check failed"):
                with host(
                    [sys.executable, "-c", "import time; time.sleep(60)"],
                    folder,
                    folder,
                    None,
                ) as process:
                    raise ValueError("check failed")
            self.assertIsNotNone(process.poll())

    def test_patch_paths_cannot_escape_snapshot(self):
        """Reject unsafe manifests before invoking Git or mutating source."""
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            manifest = folder / "manifest.json"
            manifest.write_text(
                json.dumps({"../escape": {"before": None, "after": "x"}})
            )
            with self.assertRaisesRegex(ValueError, "Unsafe delta path"):
                apply_delta(folder, folder / "unused.patch", manifest)
