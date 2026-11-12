"""Fast regression checks for report classification, audits and visible-test evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from run import InfrastructureError, ROOT, audit, manifest, validate_oracle, visible_result

CONFIG = json.loads((ROOT/'config.v0.1.json').read_text())


def report():
    allocation = CONFIG['oracle']['checksByObligation']
    return {'schemaVersion': CONFIG['oracle']['reportSchemaVersion'], 'condition': 'conventional',
            'behavioralChecks': [{'id': f'LSM-BHV-{i:03}', 'status': 'passed', 'evidence': 'observed'} for i in range(1, 7)],
            'obligations': [{'id': key, 'status': 'passed', 'checks': ids} for key, ids in allocation.items()],
            'treatmentIntegrityChecks': [{'id': 'LSM-TI-CONV-001', 'status': 'passed', 'evidence': 'observed'}],
            'treatmentIntegrity': 'passed', 'outcome': 'passed'}


class OracleEvidenceTests(unittest.TestCase):
    def test_complete_and_evidenced_submission_failure(self):
        self.assertEqual(validate_oracle(report(), CONFIG, 'conventional', 0)[1:], ('passed', 'passed'))
        bad = report()
        bad['behavioralChecks'][0]['status'] = 'failed'
        bad['obligations'][0]['status'] = 'failed'
        bad['outcome'] = 'failed'
        self.assertEqual(validate_oracle(bad, CONFIG, 'conventional', 1)[1:], ('failed', 'passed'))

    def test_reject_invalid_or_inconsistent_evidence(self):
        cases = []
        for key in ('obligations', 'behavioralChecks', 'treatmentIntegrityChecks'):
            for value in ([], None, [{}]):
                bad = report(); bad[key] = value; cases.append(bad)
        bad = report(); bad['obligations'][1] = copy.deepcopy(bad['obligations'][0]); cases.append(bad)
        bad = report(); bad['obligations'][0]['checks'] = []; cases.append(bad)
        bad = report(); bad['behavioralChecks'][0]['status'] = 'failed'; cases.append(bad)
        for key, value in [('condition', 'cohesive'), ('schemaVersion', 'unknown'), ('outcome', 'failed'), ('treatmentIntegrity', 'failed')]:
            bad = report(); bad[key] = value; cases.append(bad)
        for bad in cases:
            with self.subTest(report=bad):
                with self.assertRaises(InfrastructureError):
                    validate_oracle(bad, CONFIG, 'conventional', 0)
        for code in (1, 70, -9):
            with self.assertRaises(InfrastructureError):
                validate_oracle(report(), CONFIG, 'conventional', code)


class WorkspaceTests(unittest.TestCase):
    def test_text_paths_symlinks_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'workspace'; root.mkdir(); log = Path(temp)/'audit.log'
            config = {'forbiddenText': ['hidden oracle'], 'forbiddenPathNames': ['observed.json'],
                      'conditions': {'conventional': {'allowedTopLevel': ['src']}}}
            (root/'src').mkdir(); source = root/'src/name\nwith-newline.cs'; source.write_text('clean')
            self.assertTrue(audit(root, config, 'conventional', True, log))
            self.assertEqual(manifest(root)['files'][0]['path'], 'src/name\nwith-newline.cs')
            source.write_text('hidden oracle')
            self.assertFalse(audit(root, config, 'conventional', False, log))
            source.write_text('clean')
            link = root/'outside'; link.symlink_to(Path(temp)/'absent')
            self.assertFalse(audit(root, config, 'conventional', False, log))
            link.unlink(); (root/'observed.json').write_text('{}')
            self.assertFalse(audit(root, config, 'conventional', False, log))


class VisibleTests(unittest.TestCase):
    def test_process_failure_is_not_a_failed_test(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with self.assertRaises(InfrastructureError): visible_result(folder, 70)
            p = folder/'tests.trx'
            p.write_text('<TestRun><ResultSummary><Counters executed="3" failed="1"/></ResultSummary></TestRun>')
            self.assertEqual(visible_result(folder, 1), 'failed')
            with self.assertRaises(InfrastructureError): visible_result(folder, 70)
            p.write_text('<TestRun><ResultSummary><Counters executed="0" failed="0"/></ResultSummary></TestRun>')
            with self.assertRaises(InfrastructureError): visible_result(folder, 0)


if __name__ == '__main__':
    unittest.main()
