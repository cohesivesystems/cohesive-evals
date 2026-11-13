import build
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent

class HarnessTests(unittest.TestCase):
    def test_delta_and_mutation_anchors(self):
        mutations = build.load('test_pv2_mutations', ROOT / 'mutations.py')
        with tempfile.TemporaryDirectory() as directory:
            parent = build.previous.materialize(Path(directory)/'parent')
            refs = build.materialize(Path(directory)/'refs')
            for condition in build.harness.CONDITIONS:
                source = refs/condition/'src/Fulfillment.Application'
                changed = [p.name for p in source.glob('*.cs') if p.read_bytes() != (parent/condition/'src/Fulfillment.Application'/p.name).read_bytes()]
                self.assertEqual(changed, ['FulfillmentInput.cs'])
                for name,(file,before,_,_,_) in mutations.mutations(condition).items():
                    self.assertEqual((source/file).read_text().count(before),1,(condition,name))
            sources = [(refs/condition/'src/Fulfillment.Application/FulfillmentInput.cs').read_bytes()
                       for condition in build.harness.CONDITIONS]
            self.assertTrue(all(source == sources[0] for source in sources))

    def test_unknown_condition_is_rejected(self):
        mutations = build.load('test_pv2_mutations', ROOT / 'mutations.py')
        with self.assertRaises(ValueError):
            mutations.mutations('unknown')


if __name__ == '__main__':
    unittest.main()
