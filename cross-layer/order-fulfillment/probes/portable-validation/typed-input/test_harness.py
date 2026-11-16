import build
import json
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent

class HarnessTests(unittest.TestCase):
    def test_delta_and_named_mutation_anchors(self):
        mutations = build.load('typed_input_test_mutations', ROOT / 'mutations.py')
        with tempfile.TemporaryDirectory() as directory:
            parent = build.previous.materialize(Path(directory) / 'parent')
            refs = build.materialize(Path(directory) / 'refs')
            before = parent / 'conventional'
            after = refs / 'conventional'
            for path in before.rglob('*'):
                if path.is_file(): self.assertEqual(path.read_bytes(), (after / path.relative_to(before)).read_bytes())
            for condition in build.harness.CONDITIONS:
                source = refs / condition / 'src/Fulfillment.Application'
                for name, (file, anchor, _, _, _) in mutations.mutations(condition).items():
                    self.assertEqual((source / file).read_text().count(anchor), 1, (condition, name))
            source = refs / 'cohesive/src/Fulfillment.Application'
            self.assertFalse((source / 'FulfillmentInput.cs').exists())
            self.assertIn('inputs.Validate(request).IsValid', (source / 'OperationQueue.cs').read_text())
            self.assertIn('MaxLength(64)', (source / 'Contracts.cs').read_text())

    def test_shared_source_exceptions_are_explicit_and_exact(self):
        pins = json.loads((ROOT / 'shared-source-pins.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            refs = build.materialize(Path(directory) / 'refs')
            with self.assertRaises(AssertionError): build.harness.matching_artifacts(refs, [])
            build.harness.matching_artifacts(refs, [], pins)
            with self.assertRaises(AssertionError): build.harness.matching_artifacts(refs, [], {'src/Fulfillment.Application/Contracts.cs': {'cohesive': 'missing-control'}})
            with self.assertRaises(AssertionError): build.harness.matching_artifacts(refs, [], {**pins, 'src/Fulfillment.Application/Contracts.cs': {'cohesive': 'wrong', 'conventional': 'wrong'}})
            with self.assertRaises(AssertionError): build.harness.matching_artifacts(refs, [], {**pins, 'CONTRACT.md': {'cohesive': 'wrong', 'conventional': 'wrong'}})
            program = refs / 'cohesive/src/Fulfillment.Application/ReadResults.cs'
            program.write_text(program.read_text() + '\n// drift\n')
            with self.assertRaises(AssertionError): build.harness.matching_artifacts(refs, [], pins)

    def test_required_witness_distinguishes_admission_from_server_failure(self):
        import sys
        sys.path.insert(0, str(ROOT.parent / 'pv1'))
        checks = build.load('typed_required_classification', ROOT / 'required_checks.py')
        for status, error_type in [(202, checks.BehavioralFailure), (500, RuntimeError)]:
            world = SimpleNamespace(facts=lambda: {}, client=SimpleNamespace(request=lambda *args: (status, {})))
            with patch.object(checks.previous.Checks, 'run', return_value={}):
                with self.assertRaises(error_type): checks.Checks(world).run()

    def test_unknown_condition_is_rejected(self):
        mutations = build.load('typed_input_bad_condition', ROOT / 'mutations.py')
        with self.assertRaises(ValueError): mutations.mutations('unknown')

if __name__ == '__main__': unittest.main()
