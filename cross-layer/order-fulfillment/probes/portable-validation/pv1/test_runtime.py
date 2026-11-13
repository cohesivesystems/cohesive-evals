import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
from checks import BehavioralFailure
from runtime import verification_run

class RuntimeTests(unittest.TestCase):
    def test_setup_failure_has_no_condition(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'run'
            with patch('runtime.harness.run', side_effect=RuntimeError('image missing')), patch('runtime.subprocess.run') as command:
                with self.assertRaisesRegex(RuntimeError, 'image missing'):
                    with verification_run(output, 'test', BehavioralFailure):
                        self.fail('setup must not yield')
            self.assertEqual(json.loads((output/'failure.json').read_text()),
                             {'kind':'unqualified', 'condition':None, 'detail':'image missing'})
            command.assert_not_called()

    def test_readiness_failure_cleans_up_and_preserves_error(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'run'
            with patch('runtime.harness.run', return_value='image'), patch('runtime.time.sleep'), \
                 patch('runtime.subprocess.run', return_value=Mock(returncode=1)) as command:
                with self.assertRaisesRegex(RuntimeError, 'readiness deadline'):
                    with verification_run(output, 'test', BehavioralFailure):
                        self.fail('unready database must not yield')
            self.assertEqual(command.call_args.args[0][:3], ['docker','rm','-f'])
            record = json.loads((output/'failure.json').read_text())
            self.assertEqual((record['kind'], record['condition']), ('unqualified', None))

    def test_cleanup_failure_does_not_hide_behavioral_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'run'
            cleanup = subprocess.CalledProcessError(1, ['docker','rm'])
            with patch('runtime.harness.run', return_value='127.0.0.1:5432'), \
                 patch('runtime.subprocess.run', side_effect=[Mock(returncode=0), cleanup]), patch('runtime.sys.stderr'):
                with self.assertRaisesRegex(BehavioralFailure, 'witness'):
                    with verification_run(output, 'test', BehavioralFailure) as session:
                        session.condition = 'conventional'
                        raise BehavioralFailure('PV2-01', 'length boundary', 'witness')
            record = json.loads((output/'failure.json').read_text())
            self.assertEqual(record, {'kind':'behavioral', 'condition':'conventional', 'detail':'witness',
                                      'obligation':'PV2-01', 'assertion':'length boundary'})

    def test_success_records_metadata_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'run'
            with patch('runtime.harness.run', side_effect=['image-id','container','127.0.0.1:5432']), \
                 patch('runtime.subprocess.run', return_value=Mock(returncode=0)) as command:
                with verification_run(output, 'test', BehavioralFailure) as session:
                    self.assertEqual(session.port, '5432')
                    session.report({'example': {'passed':True}})
            self.assertEqual(command.call_args.args[0][:3], ['docker','rm','-f'])
            report = json.loads((output/'report.json').read_text())
            self.assertTrue(report['passed'])
            self.assertEqual(report['postgresImageId'], 'image-id')
            self.assertFalse((output/'failure.json').exists())
