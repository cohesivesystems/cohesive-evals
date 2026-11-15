import build
import json
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
            self.assertNotIn('RequestId.Length', (source / 'FulfillmentInput.cs').read_text())
            self.assertIn('MaxLength(64)', (source / 'Contracts.cs').read_text())

    def test_contract_source_exception_is_explicit_and_exact(self):
        pins = json.loads((ROOT / 'contract-sources.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            refs = build.materialize(Path(directory) / 'refs')
            with self.assertRaises(AssertionError): build.harness.matching_artifacts(refs, [])
            build.harness.matching_artifacts(refs, [], pins)
            with self.assertRaises(AssertionError): build.harness.matching_artifacts(refs, [], {'cohesive': pins['cohesive']})
            with self.assertRaises(AssertionError): build.harness.matching_artifacts(refs, [], {**pins, 'cohesive': 'wrong'})
            program = refs / 'cohesive/src/Fulfillment.Application/Program.cs'
            program.write_text(program.read_text() + '\n// drift\n')
            with self.assertRaises(AssertionError): build.harness.matching_artifacts(refs, [], pins)

    def test_unknown_condition_is_rejected(self):
        mutations = build.load('typed_input_bad_condition', ROOT / 'mutations.py')
        with self.assertRaises(ValueError): mutations.mutations('unknown')

if __name__ == '__main__': unittest.main()
