import copy
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify
from defects import defects, apply


class EvaluationTests(unittest.TestCase):
    """Regression controls for evaluator integrity and failure classification."""

    def setUp(self):
        """Create one independent valid case/result pair for classification challenges."""
        self.case = dict(
            Name="one",
            Sku="sku",
            Available=4,
            MaxPerOrder=4,
            Quarantined=False,
            Quantity=1,
        )
        self.good = dict(
            Name="one",
            Outcome="Reserved",
            FulfillmentOutcome="ReservedAndSubmitted",
            After=dict(Sku="sku", Available=3, MaxPerOrder=4, Quarantined=False),
            ScopePreserved=True,
        )

    def test_only_named_behavior_gets_credit(self):
        """Ensure wrong assertions, malformed results and surviving faults earn no detection credit."""
        classify = lambda value: qualify.classify(
            [self.case], value, "original", "domain outcome"
        )
        self.assertEqual("survived", classify([self.good])["kind"])
        bad = {**self.good, "Outcome": "InsufficientStock"}
        self.assertEqual("detected", classify([bad])["kind"])
        bad = {**self.good, "After": {**self.good["After"], "Available": 4}}
        self.assertEqual("wrong-assertion", classify([bad])["kind"])
        self.assertEqual("wrong-assertion", classify([])["kind"])
        for unavailable in (None, {}, [dict()], "not JSON"):
            with self.subTest(value=unavailable):
                self.assertNotEqual("detected", classify(unavailable)["kind"])

    def test_missing_optional_scope_is_not_success(self):
        """Require complete preservation evidence rather than accepting missing result fields."""
        bad = {k: v for k, v in self.good.items() if k != "ScopePreserved"}
        self.assertEqual(
            "unqualified",
            qualify.classify([self.case], [bad], "original", "accepted delta")["kind"],
        )

    def test_rejection_checks_every_field(self):
        """Challenge every inventory field on rejected commands."""
        case = {**self.case, "Quantity": 0}
        result = {
            **self.good,
            "Outcome": "InvalidQuantity",
            "FulfillmentOutcome": "InvalidQuantity",
            "After": {**self.good["After"], "Available": 4},
        }
        for key, value in [
            ("Sku", "wrong"),
            ("Available", 3),
            ("MaxPerOrder", 3),
            ("Quarantined", True),
        ]:
            bad = {**result, "After": {**result["After"], key: value}}
            classified = qualify.classify(
                [case], [bad], "original", "rejection preservation"
            )
            self.assertEqual("detected", classified["kind"])

    def test_source_freeze_drift_fails_before_execution(self):
        """Stop qualification when source bytes no longer match the recorded freeze."""
        with patch.object(qualify.fixture, "sha", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "source changed"):
                qualify.check_freeze(Path("/unused"))

    def test_mutation_anchors_once_in_both_versions(self):
        """Validate every fault anchor and keep evaluator files out of candidate fixtures."""
        with tempfile.TemporaryDirectory() as tmp:
            for version in qualify.fixture.VERSIONS:
                root = Path(tmp) / version
                qualify.fixture.materialize(root, version)
                self.assertFalse(
                    any(
                        "evaluation" in p.relative_to(root).parts
                        for p in root.rglob("*")
                    )
                )
                for condition in qualify.fixture.CONDITIONS:
                    for defect in defects(condition):
                        path = root / "references" / condition / defect.path
                        original = path.read_text()
                        with self.subTest(
                            version=version, condition=condition, defect=defect.name
                        ):
                            apply(root / "references" / condition, defect)
                            self.assertNotEqual(original, path.read_text())
                            path.write_text(original)

    def test_stale_or_wrong_model_authority_is_rejected(self):
        """Challenge each component of exact model identity independently."""
        reference = dict(definitionId="reserve", revisionId="5", fingerprint="abc")
        qualify.require_model(reference, dict(reference))
        for key in reference:
            with self.subTest(key=key), self.assertRaisesRegex(
                ValueError, "authority mismatch"
            ):
                qualify.require_model(reference, {**reference, key: "wrong"})

    def test_build_runtime_and_timeout_failures_never_get_credit(self):
        """Inject execution/setup failures into the qualification pipeline and require unqualified reports."""
        errors = [
            subprocess.CalledProcessError(1, ["dotnet", "build"]),
            subprocess.TimeoutExpired(["dotnet"], 60),
            RuntimeError("no result"),
        ]
        for error in errors:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as tmp:
                frozen = Path(tmp) / "frozen"
                for version in qualify.fixture.VERSIONS:
                    for condition in qualify.fixture.CONDITIONS:
                        folder = frozen / version / "suites" / condition
                        folder.mkdir(parents=True)
                        (folder / "suite.json").write_text(
                            json.dumps({"cases": [self.case]})
                        )
                with patch.object(qualify, "check_freeze"), patch.object(
                    qualify, "controls", return_value={}
                ), patch.object(
                    qualify, "defects", return_value=defects("conventional")[:1]
                ), patch.object(
                    qualify.fixture, "materialize"
                ), patch.object(
                    qualify, "apply"
                ), patch.object(
                    qualify.fixture, "compile_adapter", side_effect=error
                ), patch.object(
                    qualify.fixture, "sha", return_value="test"
                ), patch(
                    "builtins.print"
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "Qualification incomplete"
                    ):
                        qualify.run(frozen, Path(tmp) / "out")
                report = json.loads((Path(tmp) / "out/report.json").read_text())
                self.assertFalse(report["passed"])
                self.assertEqual(
                    {"unqualified"}, {r["kind"] for r in report["records"]}
                )

    def test_same_fault_families_and_assertions(self):
        """Keep conceptual fault families and expected assertions matched across conditions."""
        a, b = (
            [(d.name, d.assertion) for d in defects(c)]
            for c in qualify.fixture.CONDITIONS
        )
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
