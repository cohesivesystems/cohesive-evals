"""Infrastructure failures must preserve their original assertion and context."""
from contextlib import nullcontext
from concurrent.futures import Future
from http.client import RemoteDisconnected
import urllib.error
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('recovery_verifier', ROOT/'verify.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


capacity_spec = importlib.util.spec_from_file_location('capacity_verifier', ROOT/'pilot/capacity.py')
capacity = importlib.util.module_from_spec(capacity_spec)
capacity_spec.loader.exec_module(capacity)


class AdmissionGradingTests(unittest.TestCase):
    """Distinguish acknowledged work, ambiguous admission and exact capacity errors."""

    def test_early_acknowledgement_preserves_original_receipt(self):
        """A delivered receipt must survive the barrier so recovery polls the original operation."""
        pending = Future()
        receipt = {"operationId": "original", "resultUrl": "/fulfillment/results/original"}
        pending.set_result((202, receipt))
        self.assertEqual(verifier.acknowledged_receipt(pending), receipt)

    def test_only_interruption_permits_retry(self):
        """Treat a dropped connection as ambiguous and surface deadlines and unexpected replies."""
        interrupted = Future()
        interrupted.set_exception(verifier.ConnectionDropped("peer closed"))
        self.assertIsNone(verifier.acknowledged_receipt(interrupted))
        timed_out = Future()
        timed_out.set_exception(TimeoutError())
        with self.assertRaises(TimeoutError):
            verifier.acknowledged_receipt(timed_out)
        for reply in [(500, None), (202, None), (202, {"operationId": "lost"}),
                      (202, {"operationId": "x", "resultUrl": "/fulfillment/results/x", "extra": True})]:
            with self.subTest(reply=reply):
                pending = Future()
                pending.set_result(reply)
                with self.assertRaisesRegex(AssertionError, "admission at crash barrier"):
                    verifier.acknowledged_receipt(pending)

    def test_fixture_uses_shared_transport_failure_classification(self):
        """Direct and wrapped disconnects permit retry. Transport deadlines stay infrastructure failures."""
        client = verifier.suite.Client("http://fixture.invalid")
        for cause, dropped in [(RemoteDisconnected(), True),
                               (urllib.error.URLError(RemoteDisconnected()), True),
                               (urllib.error.URLError(TimeoutError()), False)]:
            with self.subTest(cause=cause), patch("urllib.request.urlopen", side_effect=cause):
                with self.assertRaises(verifier.AdapterError) as caught:
                    client.request("POST", "/fulfillment", {})
                self.assertEqual(caught.exception.category, "infrastructure")
                self.assertEqual(isinstance(caught.exception, verifier.ConnectionDropped), dropped)

    def test_capacity_rejects_wrong_bodies_with_correct_statuses(self):
        """Reject JSON null on overflow and a different domain code on conflicting replay."""
        receipt = (202, {"operationId": "retained", "resultUrl": "/fulfillment/results/retained"})
        for overflow, conflict, assertion in [
            (b"null", {"code": "RequestIdentityConflict"}, "at capacity"),
            (b"", {"code": "Other"}, "identity conflict"),
        ]:
            with self.subTest(assertion=assertion):
                client = Mock()
                client.request_bytes.return_value = (503, overflow)
                client.request.side_effect = [receipt, (409, conflict)]
                with self.assertRaisesRegex(capacity.RequirementFailure, assertion):
                    capacity.at_capacity(client, receipt, "restart")


class VerifierErrors(unittest.TestCase):
    def test_postgres_readiness_failure_before_scenarios(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(sys, 'argv', ['verify.py', '--output', temp]), \
                 patch.object(verifier, 'verify_build', return_value='test-build'), \
                 patch.object(verifier, 'durable_task_scheduler', return_value=nullcontext('scheduler')), \
                 patch.object(verifier, 'run', return_value=''), \
                 patch.object(verifier.subprocess, 'run'), \
                 patch.object(verifier, 'wait_until', side_effect=AssertionError('Deadline exceeded: PostgreSQL ready')):
                with self.assertRaisesRegex(AssertionError, 'Deadline exceeded: PostgreSQL ready'):
                    verifier.main()
            failure = json.loads((Path(temp)/'assertion-failure.json').read_text())
            self.assertEqual(failure, {'error': 'Deadline exceeded: PostgreSQL ready', 'condition': None, 'point': None})


if __name__ == '__main__':
    unittest.main()
