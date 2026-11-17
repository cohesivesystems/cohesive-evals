"""Independent oracle controls; SDK generation/execution has its own C# test suite."""

import unittest
from cohesive_evals.mv1 import oracle


class SuiteTests(unittest.TestCase):
    """Challenge requirement assertions without importing either candidate's implementation."""

    def test_wrong_model_cannot_supply_its_own_expected_answer(self):
        """A zero-quantity success is wrong even if a model generated that input and result."""
        case = dict(
            Name="zero",
            Sku="stock",
            Available=4,
            MaxPerOrder=4,
            Quarantined=False,
            Quantity=0,
        )
        answer = dict(
            Name="zero",
            Outcome="Reserved",
            FulfillmentOutcome="ReservedAndSubmitted",
            After=dict(Sku="stock", Available=4, MaxPerOrder=4, Quarantined=False),
            ScopePreserved=True,
        )
        with self.assertRaises(oracle.BehavioralFailure):
            oracle.check([case], [answer], "original")

    def test_precedence_revision_and_nonpositive_preservation(self):
        """Only the positive overlapping rejection changes when the policy evolves."""
        case = dict(Quantity=2, Available=0, MaxPerOrder=1, Quarantined=True)
        self.assertEqual(oracle.expected(case, "original"), "InventoryQuarantined")
        self.assertEqual(oracle.expected(case, "revised"), "QuantityLimitExceeded")
        for version in ("original", "revised"):
            self.assertEqual(
                oracle.expected({**case, "Quantity": 0}, version), "InvalidQuantity"
            )

    def test_output_identity_and_effects_are_independent_obligations(self):
        """Success alone cannot mask a wrong state, identity, terminal mapping or partition."""
        case = dict(
            Name="x",
            Sku="stock",
            Available=10,
            MaxPerOrder=4,
            Quarantined=False,
            Quantity=2,
        )
        result = dict(
            Name="x",
            Outcome="Reserved",
            FulfillmentOutcome="ReservedAndSubmitted",
            After=dict(Sku="stock", Available=8, MaxPerOrder=4, Quarantined=False),
            ScopePreserved=True,
        )
        self.assertEqual(oracle.check([case], [result], "original")["accepted"], 1)
        for change in (
            {"Name": "other"},
            {"After": {**result["After"], "Available": 10}},
            {"FulfillmentOutcome": "OrderRejected"},
            {"ScopePreserved": False},
        ):
            with self.assertRaises(oracle.BehavioralFailure):
                oracle.check([case], [{**result, **change}], "original")

    def test_missing_results_are_not_a_passing_suite(self):
        """An empty report cannot satisfy a nonempty requested case set."""
        with self.assertRaises(oracle.BehavioralFailure):
            oracle.check([dict(Name="missing")], [], "original")

    def test_unknown_policy_is_refused(self):
        """A typo in the policy version must not fall back to original semantics."""
        with self.assertRaises(ValueError):
            oracle.expected({}, "unknown")


if __name__ == "__main__":
    unittest.main()
