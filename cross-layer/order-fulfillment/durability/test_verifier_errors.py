"""Infrastructure failures must preserve their original assertion and context."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('recovery_verifier', ROOT/'verify.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class VerifierErrors(unittest.TestCase):
    def test_postgres_readiness_failure_before_scenarios(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(sys, 'argv', ['verify.py', '--output', temp]), \
                 patch.object(verifier, 'verify_build', return_value='test-build'), \
                 patch.object(verifier, 'run', return_value=''), \
                 patch.object(verifier.subprocess, 'run'), \
                 patch.object(verifier, 'wait_until', side_effect=AssertionError('Deadline exceeded: PostgreSQL ready')):
                with self.assertRaisesRegex(AssertionError, 'Deadline exceeded: PostgreSQL ready'):
                    verifier.main()
            failure = json.loads((Path(temp)/'assertion-failure.json').read_text())
            self.assertEqual(failure, {'error': 'Deadline exceeded: PostgreSQL ready', 'condition': None, 'point': None})


if __name__ == '__main__':
    unittest.main()
